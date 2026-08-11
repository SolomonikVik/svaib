#!/usr/bin/env python3
"""Каталог метрик клиента — машинный «Реестр метрик» вертикали.

Обходит metrics-файлы клиента ЦЕЛИКОМ (client-scope, не scope объекта — boundary §3)
и отдаёт паспорта метрик: имя = ID, единица, направление. Физику источника не знает
и адреса из прозы паспорта не разбирает: привязка живёт в машинной карте источников
(source_map.py), потому что defects.md A3.4/A1.4 запрещают выводить лист из имени узла,
а строку — из имени метрики даже как fallback.

Границы (dev/metrics/runner-spec.md §9):
  - перечень файлов — только канонические имена metrics-spec (business + семь domain);
    маска «*metrics*.md» по поддереву ЗАПРЕЩЕНА: она затягивает metrics-history.md и
    заголовки архивных протоколов (находка №11 живого прогона 31.07, перечень 8 → 19);
  - ключи полей двуязычные — живая база клиента ведёт паспорта по-английски;
  - коллизии имён отдаются, не дедуплицируются: ключ метрики — пара (name, file);
  - чтение только внутри base, symlink наружу не разыменовывается.
"""
from __future__ import annotations

import re
from pathlib import Path

# Паспортом считается файл, чьё имя оканчивается на «-metrics.md» И лежащий в аспекте
# метрик (`03_metrics/`). Двойное условие выбрано по живой базе:
#   - маска «*metrics*.md» по поддереву запрещена — она затягивает metrics-history.md
#     и заголовки архивных протоколов встреч (находка №11: перечень 8 → 19);
#   - строгий перечень восьми канонических имён терял production-metrics.md с полутора
#     десятками живых метрик: имя неканонично, но это дефект базы класса B, и молча
#     выкидывать направление из клиентского перечня хуже, чем прочитать его.
METRICS_ASPECT_DIR = "03_metrics"
PASSPORT_SUFFIX = "-metrics.md"

_HEADING_RE = re.compile(r"^###\s+(?P<name>\S.*?)\s*$")
_SECTION_RE = re.compile(r"^##\s+(?P<title>\S.*?)\s*$")
_FIELD_RE = re.compile(r"^\*\*(?P<key>[^:*]+):\*\*\s*(?P<value>.*?)\s*$")

# Внутри секции ИСТОЧНИКОВ (мн. ч.) `### {source_id}` — идентификатор книги, а не
# метрика (metrics-spec, «Контракт привязки к источнику»). Без этого исключения source_crm
# уезжает в перечень метрик и на живой базе даёт ложный дубль имени.
# Секция в ЕДИНСТВЕННОМ числе подразделов по канону не имеет — фильтровать по ней нельзя:
# в живых файлах метрики нередко идут сразу за ней, без отдельной секции «Метрики», и
# такой фильтр выкосил бы весь файл.
_SOURCE_SECTIONS = {"источники", "sources"}

# Второй признак идентификатора источника: snake_case ASCII, как требует metrics-spec.
# Заголовок с пробелами или кириллицей внутри «## Источники» — всё-таки метрика.
_SOURCE_ID_RE = re.compile(r"^[a-z0-9_]+$")

# Незаполненный шаблон scaffold: `### {Каноническое имя}`. В живой базе такие файлы есть
# (customer-metrics, product-metrics) — принять плейсхолдер за метрику значит запросить
# у источника несуществующее имя и отчитаться о нём как о «нет значения».
_PLACEHOLDER_RE = re.compile(r"\{[^{}]*\}")

_UNIT_KEYS = {"единица", "unit"}
_DIRECTION_KEYS = {"направление", "direction"}

# Направление — точный маппинг канонических формулировок, без разбора смысла фразы.
# Подстрочная эвристика («есть „хорошо“ → up») здесь недопустима: «снижение — хорошо»
# — естественная запись для отвала и затрат, и она означает ровно down. Ошибка тут не
# видна ни валидатору (он direction не сверяет), ни oracle — а потребитель по ней
# трактует рост отвала как успех. Всё, что не в словаре, честно даёт null.
_DIRECTION_MAP = {
    "рост — хорошо": "up", "рост - хорошо": "up", "growth — good": "up", "growth - good": "up",
    "больше — лучше": "up", "up": "up",
    "рост — плохо": "down", "рост - плохо": "down", "growth — bad": "down", "growth - bad": "down",
    "снижение — хорошо": "down", "снижение - хорошо": "down", "меньше — лучше": "down",
    "down": "down",
}


class CatalogError(Exception):
    """Каталог не читается — база непригодна (base_unreadable, rc 1)."""


class Metric:
    """Паспорт метрики: то немногое, что раннер берёт из прозы клиента."""

    __slots__ = ("name", "file", "unit", "direction")

    def __init__(self, name, file, unit=None, direction=None):
        self.name = name
        self.file = file
        self.unit = unit
        self.direction = direction

    @property
    def key(self):
        return (self.name, self.file)

    def __repr__(self):  # pragma: no cover — диагностика
        return f"Metric({self.name!r}, {self.file!r}, unit={self.unit!r}, direction={self.direction!r})"


def normalize_direction(raw):
    """Направление метрики → up | down | None. Неизвестное — None, не догадка."""
    if not raw:
        return None
    low = " ".join(raw.strip().lower().replace("–", "—").replace("-", "—").split())
    return _DIRECTION_MAP.get(low)


def safe_relpath(base, path):
    """Base-relative POSIX путь; None, если цель уходит за пределы base.

    Проверка идёт ПОСЛЕ resolve(): symlink наружу базы обязан отсекаться так же,
    как «..» в тексте пути (runner-spec §2).
    """
    try:
        resolved = Path(path).resolve()
        base_resolved = Path(base).resolve()
        rel = resolved.relative_to(base_resolved)
    except (ValueError, OSError):
        return None
    return rel.as_posix()


def parse_passport(text, relpath):
    """Метрики одного metrics-файла: `### имя` + единица + направление.

    Поля метрики читаются до следующего заголовка любого уровня — поле, стоящее
    после `##`-секции, к предыдущей метрике не относится.
    """
    metrics = []
    current = None
    in_source_section = False
    for line in text.splitlines():
        section = _SECTION_RE.match(line)
        if section:
            in_source_section = section.group("title").strip().lower() in _SOURCE_SECTIONS
            current = None
            continue
        heading = _HEADING_RE.match(line)
        if heading:
            name = heading.group("name")
            current = None
            if in_source_section and _SOURCE_ID_RE.match(name):
                continue
            if _PLACEHOLDER_RE.search(name):
                continue
            current = Metric(name=name, file=relpath)
            metrics.append(current)
            continue
        if line.startswith("#### "):
            current = None
            continue
        if current is None:
            continue
        field = _FIELD_RE.match(line)
        if not field:
            continue
        key = field.group("key").strip().lower()
        value = field.group("value").strip()
        if key in _UNIT_KEYS:
            current.unit = value or None
        elif key in _DIRECTION_KEYS:
            current.direction = normalize_direction(value)
    return metrics


def build_catalog(base):
    """Каталог метрик клиента.

    Возвращает (metrics_by_key, files_scanned):
      metrics_by_key — {(name, file): Metric}, одноимённые метрики разных файлов
                       остаются разными записями (коллизии не склеиваются);
      files_scanned  — отсортированный перечень фактически прочитанных файлов,
                       он же доказательство client-scope в отчёте.
    """
    base_path = Path(base)
    if not base_path.is_dir():
        raise CatalogError(f"--base не является каталогом: {base}")

    metrics_by_key = {}
    files_scanned = []
    # rglob детерминизирован сортировкой: порядок обхода ФС в отчёт не течёт.
    for path in sorted(base_path.rglob("*" + PASSPORT_SUFFIX)):
        # Фильтр по аспекту метрик идёт ПЕРВЫМ: мусорная ссылка вне 03_metrics/
        # паспортом не считалась бы никогда, и ронять из-за неё повестку нельзя.
        if path.parent.name != METRICS_ASPECT_DIR:
            continue
        if not path.is_file():
            if path.is_symlink():
                # Битая ссылка на паспорт: тихо пропустить значит объявить scope="client"
                # по неполному обходу — часть клиента не просмотрена, а отчёт этого не
                # покажет.
                raise CatalogError(
                    f"паспорт {path.name} — оборванная ссылка; перечень метрик неполон"
                )
            continue
        rel = safe_relpath(base_path, path)
        if rel is None:
            # Тихо пропустить нельзя: паспорт выпал бы из client-scope, а отчёт всё
            # равно заявил бы scope = "client". Отказ честнее ложной полноты.
            raise CatalogError(
                f"паспорт {path.name} уводит за пределы --base — "
                "раннер читает только базу клиента"
            )
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise CatalogError(f"metrics-файл не читается: {rel}: {exc}") from exc
        files_scanned.append(rel)
        for metric in parse_passport(text, rel):
            if metric.key in metrics_by_key:
                # Два `### MRR` в одном файле: ключ контракта — пара {name, file}, и
                # двумя строками одна пара быть не может. Тихо взять первое определение
                # значит выбрать за клиента, какая из двух метрик настоящая.
                raise CatalogError(
                    f"{rel}: метрика {metric.name!r} описана дважды — "
                    "имя метрики уникально в пределах клиента (metrics-spec)"
                )
            metrics_by_key[metric.key] = metric

    if not files_scanned:
        raise CatalogError(
            "в базе нет ни одного паспорта метрик (*-metrics.md в 03_metrics/) — "
            "перечень метрик построить нельзя"
        )
    return metrics_by_key, sorted(files_scanned)


def duplicate_names(pairs):
    """Имена, встречающиеся более чем в одном файле перечня.

    Выводятся ИЗ ПЕРЕЧНЯ ЗАПРОСА, а не из признания каталога: валидатор контракта
    сверяет duplicate_name[] именно так (validate_contract.py, «дубли выводятся из
    запроса»), и производитель не может дубль скрыть.
    """
    files_by_name = {}
    for name, file in pairs:
        files_by_name.setdefault(name, set()).add(file)
    return {name: sorted(files) for name, files in files_by_name.items() if len(files) > 1}
