#!/usr/bin/env python3
"""Карта источников клиента — expected-сторона сверки координат.

Отвечает на вопрос «что клиент ОБЪЯВИЛ источником метрики»: книга, лист, метки строки.
Читается из машинного файла `_source-map.json` в базе клиента; проза паспорта здесь не
разбирается намеренно — defects.md A3.4 запрещает выводить лист из имени узла, A1.4 —
строку из имени метрики даже как fallback. Нет записи о метрике → метрика не привязана
(`source_unbound`), и это честный ответ, а не догадка.

Actual-сторону (откуда число прочитано физически) даёт extractor.py; независимость двух
сторон — единственное, что делает сверку координат проверкой, а не тавтологией.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# Два поддерживаемых места конфигурации базы: аспект метрик компании и канонический путь
# architecture.md. Окончательное место закрепляется диффом Э0-A; пока живут оба, но один
# и тот же артефакт в двух местах — отказ, а не «какой-нибудь выберем» (детерминизм).
CONFIG_DIRS = ("01_company/03_metrics", "metrics")
SOURCE_MAP_FILENAME = "_source-map.json"


class BaseConfigError(Exception):
    """Конфигурация базы битая или противоречивая → base_unreadable, rc 1.

    Натяжка на замороженный реестр кодов признана в runner-spec §3: своего кода для
    «битой раскладки» в реестре нет, а трактовать поломку как no_extractor нельзя —
    это выдало бы сломанную конфигурацию за отсутствие данных.
    """


# fileId Drive: буквы, цифры, дефис и подчёркивание, длиной от 20. Порог отделяет
# идентификатор от коротких имён; путь под шаблон не подходит из-за слэша и точки.
_ID = r"[A-Za-z0-9_-]{20,}"
# Живые формы адреса одной книги Google, которые встречаются в базах клиентов:
#   - ссылка из адресной строки таблицы:  docs.google.com/spreadsheets/d/<id>/edit#gid=…
#   - ссылка на файл в Drive:             drive.google.com/file/d/<id>/view
#   - ссылка из диалога «Поделиться»:     drive.google.com/open?id=<id>
# Порог длины одинаков во всех ветках намеренно: иначе обрезанный при вставке URL с коротким
# идентификатором молча стал бы «каноном», а тот же идентификатор голым — незнакомой записью,
# и одна книга снова получила бы два ключа — теперь уже внутри самого правила.
# Published-URL (`/d/e/2PACX-…`) под шаблон не подходит и остаётся как есть: там идентификатор
# публикации, а не книги, и приведение его к `gsheet:` дало бы ключ, не совпадающий ни с чем.
_GSHEET_URL = re.compile(
    rf"^https?://(?:docs\.google\.com/spreadsheets|drive\.google\.com)/(?:[^\s?#]*?/)?d/({_ID})")
_GSHEET_OPEN = re.compile(
    rf"^https?://drive\.google\.com/open\?(?:[^#\s]*&)?id=({_ID})")
_DRIVE_ID = re.compile(rf"^{_ID}$")


def canonical_source(address):
    """Адрес книги в канонической форме `{схема}:{идентификатор}`.

    Единственное место, где решается «это та же книга». Адрес — глобальный ключ трёх
    независимых артефактов: карта источников объявляет книгу, раскладка описывает, манифест
    приносит снимок. Сравнение идёт по совпадению строк, поэтому запись без схемы (голый
    fileId Drive) и запись с ней означают для кода **разные** книги — и метрика при этом
    получает `source_unavailable`, то есть руководителя отправляют чинить доступ, которого он
    не терял. Дважды за один день это ломалось живьём: добытчик писал голый fileId, карта —
    `gsheet:<fileId>`.

    Приводятся только формы, про которые известно, что они означают одну книгу: URL Google
    Sheets и голый fileId Drive. **Всё остальное возвращается как есть** — достраивать схему
    к незнакомой записи опаснее, чем оставить её неузнанной: канон допускает и относительный
    путь к локальному файлу (`metrics/book.xlsx`), и он превратился бы в адрес чужой схемы,
    а при появлении второго типа источника два разных ключа могли бы склеиться в один — и
    раскладка одной книги применилась бы к снимку другой.

    Симметрична `source_key` добытчика (`dev/infra/fetcher/manifest.py`): обе стороны шва
    приводят адрес к одной форме, и рассинхрон перестаёт быть возможным.
    """
    text = str(address).strip()
    if not text:
        return text
    for pattern in (_GSHEET_URL, _GSHEET_OPEN):
        match = pattern.match(text)
        if match:
            return "gsheet:" + match.group(1)
    if _DRIVE_ID.match(text):
        return "gsheet:" + text
    return text


def normalize_label(value):
    """Нормализация метки/имени листа для сравнения обеих сторон.

    Одна функция на expected и actual: NBSP и прочие пробелы → пробел, схлопывание
    повторов, trim, регистронезависимо, кавычки к общей форме. Мягче — пропустим R5,
    строже — получим ложный mapping_mismatch на каждой живой книге с двойным пробелом.
    """
    if value is None:
        return ""
    text = str(value)
    for ch in (" ", " ", "\t", "\n", "\r"):
        text = text.replace(ch, " ")
    for ch in ("«", "»", "“", "”", "„", "‟", "'", "‘", "’"):
        text = text.replace(ch, '"')
    return " ".join(text.split()).strip().lower()


def normalize_labels(values):
    return tuple(normalize_label(v) for v in values)


def _load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError) as exc:
        raise BaseConfigError(f"{path.name} не читается или не является JSON: {exc}") from exc


def _validate(doc, schema_name, path):
    try:
        import jsonschema
    except ImportError as exc:  # окружение без зависимостей — именованный отказ, не traceback
        raise BaseConfigError(
            "jsonschema не установлен — проверить конфигурацию базы нечем "
            "(см. scripts/requirements.txt)"
        ) from exc

    schema_dir = Path(__file__).resolve().parent.parent / "schema"
    schema = json.loads((schema_dir / schema_name).read_text(encoding="utf-8"))
    errors = sorted(jsonschema.Draft7Validator(schema).iter_errors(doc), key=lambda e: list(e.absolute_path))
    if errors:
        first = errors[0]
        where = "/".join(map(str, first.absolute_path)) or "<корень>"
        raise BaseConfigError(f"{path.name} не проходит {schema_name}: {where}: {first.message}")


def inside_base(base, path):
    """Путь остаётся внутри base ПОСЛЕ разыменования symlink.

    Проверять до resolve() бессмысленно: конфигурация, вынесенная за пределы базы и
    оставленная симлинком, читалась бы как своя, а раннер обещает читать только базу.
    """
    try:
        Path(path).resolve().relative_to(Path(base).resolve())
    except (ValueError, OSError):
        return False
    return True


def config_files(base, filename=None, subdir=None):
    """Пути конфигурации в поддерживаемых местах базы, в детерминированном порядке."""
    found = []
    for rel in CONFIG_DIRS:
        directory = Path(base) / rel
        if subdir:
            directory = directory / subdir
        if not directory.is_dir():
            if directory.is_symlink():
                raise BaseConfigError(
                    f"каталог конфигурации {directory.name} — оборванная ссылка"
                )
            continue
        if not inside_base(base, directory):
            # Каталог-симлинк наружу: пропустить его молча значит превратить поломку
            # конфигурации в штатный no_extractor.
            raise BaseConfigError(
                f"каталог конфигурации {directory.name} уводит за пределы --base"
            )
        if filename:
            candidate = directory / filename
            if candidate.is_file():
                found.append(candidate)
        else:
            found.extend(sorted(p for p in directory.glob("*.json") if p.is_file()))
    for path in found:
        if not inside_base(base, path):
            raise BaseConfigError(
                f"конфигурация {path.name} уводит за пределы --base — "
                "раннер читает только базу клиента"
            )
    return found


class Binding:
    """Объявленная привязка метрики: где клиент сказал искать её значение."""

    __slots__ = ("source", "sheet", "row_labels", "applies_to", "fact_column_label")

    def __init__(self, source, sheet, row_labels, applies_to, fact_column_label=None):
        self.source = source
        self.sheet = sheet
        self.row_labels = list(row_labels)
        self.applies_to = set(applies_to)
        # Expected-сторона выбора КОЛОНКИ: как книга называет колонку факта.
        # Нужна там, где период занимает несколько колонок с ролями, — иначе
        # раскладка выбирает колонку, а сверять её нечем.
        self.fact_column_label = fact_column_label

    @property
    def normalized(self):
        return normalize_label(self.sheet), normalize_labels(self.row_labels)

    @property
    def row_label(self):
        """Метка строки для отчёта: кортеж меток через « / » — как её читает человек."""
        return " / ".join(self.row_labels)


class SourceMap:
    """Разобранная карта источников клиента."""

    def __init__(self, bindings_by_key, declared_sources, written_sources=None):
        self._bindings = bindings_by_key
        self.declared_sources = declared_sources
        # {канонический адрес: как он записан в карте}. Нужен, чтобы книга называлась в
        # отчёте одинаково независимо от того, добыт её снимок или нет: иначе одна и та же
        # книга звалась бы `X` в удачном прогоне и `gsheet:X` при `snapshot_missing`, и
        # внешняя сверка по этому полю разъезжалась бы ровно на отказах.
        self.written_sources = dict(written_sources or {})

    def binding(self, name, file, period_basis):
        """Привязка пары под запрошенный тип периода; None — метрика не привязана.

        Привязка другого типа периода НЕ подставляется: у клиента закрытые месяцы и
        текущий читаются из разных книг, и молчаливая подмена дала бы число не из того
        источника (дефект A4.2).
        """
        for binding in self._bindings.get((name, file), []):
            if period_basis in binding.applies_to:
                return binding
        return None

    def all_bindings(self):
        for key, bindings in self._bindings.items():
            for binding in bindings:
                yield key, binding


def load_source_map(base):
    """Карта источников базы. Файла нет — пустая карта: все метрики непривязаны."""
    paths = config_files(base, filename=SOURCE_MAP_FILENAME)
    if not paths:
        return SourceMap({}, [])
    if len(paths) > 1:
        raise BaseConfigError(
            f"{SOURCE_MAP_FILENAME} найден в нескольких местах базы: "
            + ", ".join(p.as_posix() for p in paths)
        )
    path = paths[0]
    doc = _load_json(path)
    _validate(doc, "source-map.schema.json", path)

    # Перечень книг карты: две записи, сводящиеся к одной книге, схлопываются, а не роняют
    # прогон. Конкурировать тут нечему — раннер берёт из `sources[]` только сам адрес, а
    # привязки всё равно канонизируются; отказ означал бы, что повестка не собралась из-за
    # косметики переходного периода. Дубль ТОГО ЖЕ адреса — по-прежнему отказ: это уже не
    # разночтение формы, а противоречивая запись.
    written = {}
    declared = []
    for s in doc["sources"]:
        source = canonical_source(s["source"])
        if source in written:
            if s["source"] == written[source]:
                raise BaseConfigError(f"{path.name}: адрес книги объявлен дважды в sources[]")
            continue
        written[source] = s["source"]
        declared.append(source)

    bindings_by_key = {}
    for entry in doc["metrics"]:
        key = (entry["name"], entry["file"])
        if key in bindings_by_key:
            raise BaseConfigError(f"{path.name}: пара {key} описана дважды")
        parsed = []
        seen_basis = set()
        for raw in entry["bindings"]:
            source = canonical_source(raw["source"])
            if source not in declared:
                raise BaseConfigError(
                    f"{path.name}: привязка {key} ссылается на книгу {raw['source']!r}, "
                    "не объявленную в sources[]"
                )
            overlap = seen_basis & set(raw["applies_to"])
            if overlap:
                raise BaseConfigError(
                    f"{path.name}: у пары {key} две привязки на один тип периода {sorted(overlap)}"
                )
            seen_basis |= set(raw["applies_to"])
            parsed.append(Binding(source, raw["sheet"], raw["row_labels"], raw["applies_to"],
                                  raw.get("fact_column_label")))
        bindings_by_key[key] = parsed
    return SourceMap(bindings_by_key, declared, written)
