"""Инварианты и формы артефактов meeting-analysis v3.

Нативная пересборка (пакет 4, спека 2026-08-09): код проверяет форму и факты
за O(1) и не ведёт циклов доводки. Реакция на несовпадение — пометка, вопрос
или одиночный перезапуск узла. Ревизионно-дайджестовая алгебра и якорный
резолвер не переехали: применение делает LLM-узел по фактическому состоянию
файла, вердикты привязаны к сущности, а не к подписи ревизии.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

SCHEMA_VERSION = "ma-v3/2"

# --- классы отказов и переходы ------------------------------------------

BLOCKER = "blocker"
REWORK = "rework"
QUESTION = "question"

_CLASSES = {
    "schema_invalid": REWORK,
    "brief_duplicate": REWORK,
    "coverage_missing": REWORK,
    "decision_conflict": BLOCKER,
    "verdict_missing": REWORK,
    "evidence_invalid": QUESTION,
    "context_leak": REWORK,
    "quote_fabricated": QUESTION,
    "phase_order": BLOCKER,
    "bad_usage": BLOCKER,
    "missing_input": BLOCKER,
    "transcript_changed": BLOCKER,
    "run_not_initialized": BLOCKER,
    "run_id_invalid": BLOCKER,
    "path_escapes_base": BLOCKER,
    "artifact_in_base": BLOCKER,
    "workspace_in_base": BLOCKER,
    "unknown_unit": REWORK,
    "digest_mismatch": BLOCKER,
    "decision_incomplete": BLOCKER,
    "apply_status_missing": BLOCKER,
    "protocol_overwrite": BLOCKER,
}

#: Реестр переходов: у каждого отказа есть исполнимый выход. Реестр мал по
#: конструкции — тупиковых состояний в конвейере два экрана и два замка не
#: создают; пустая строка возможна только у кода, которого нет в реестре,
#: и это дефект ядра, а не открытая ячейка.
TRANSITIONS: Dict[str, str] = {
    "schema_invalid": "перезапусти узел с текстом отказа; второй отказ подряд — вопрос человеку",
    "brief_duplicate": "перезапусти узел выжимки: одна сущность — один eid, одна цитата — одна сущность",
    "decision_conflict": "одна сущность принята в двух домах — оставьте один исход take, второй пункт reject",
    "coverage_missing": "перезапусти узел: каждая назначенная сущность обязана получить операцию",
    "verdict_missing": "перезапусти контролёра: вердикт обязан покрыть каждую операцию",
    "evidence_invalid": "улика не подтвердилась — пункт едет на экран спорным",
    "quote_fabricated": "цитата не подтверждена — пункт едет на экран спорным",
    "context_leak": "submit delivery (перепиши сводку без кухни разбора)",
    "phase_order": "render state — поле next называет команду",
    "bad_usage": "смотри --help команды",
    "missing_input": "check --base … --transcript … --meeting-date …",
    "transcript_changed": "перезапусти разбор: прогон опирается на зафиксированный текст",
    "run_not_initialized": "check --base … --transcript … --meeting-date …",
    "run_id_invalid": "назови прогон именем каталога (run-…), а не путём: рабочий каталог прогона — прямой ребёнок корня прогонов",
    "path_escapes_base": "исправь путь: файлы базы живут внутри неё",
    "artifact_in_base": "перенеси артефакт в inbox прогона (путь в data.inbox) и подай оттуда",
    "workspace_in_base": "задай XDG_STATE_HOME вне базы и повтори check",
    "unknown_unit": "назови юнит из карты либо верни вопрос человеку",
    "digest_mismatch": "render — покажи экран заново и решай против свежего показа",
    "decision_incomplete": "render decision — реши оставшиеся пункты",
    "apply_status_missing": "submit applied — статус записи нужен по каждому принятому пункту",
    "protocol_overwrite": "верни по этому файлу протокола skipped с причиной и подай отчёт заново; файл уже перезаписан — скажи это пользователю: восстановление идёт версионной историей базы",
}


def error_class(code: str) -> str:
    return _CLASSES.get(code, REWORK)


def transition(code: str) -> str:
    return TRANSITIONS.get(code, "")


# --- нормализация и цитаты ----------------------------------------------

_DASHES = {"—": "-", "–": "-", "−": "-", "‒": "-", "―": "-"}
_QUOTES = {"«": '"', "»": '"', "“": '"', "”": '"', "„": '"', "‟": '"',
           "‘": "'", "’": "'", "‚": "'", "‛": "'"}
#: Эмфаза — парная разметка ОДНОЙ строки: пара не пересекает границу строк,
#: одиночное подчёркивание внутри слова (`foo_bar`) не трогается.
_EMPHASIS = (
    re.compile(r"\*\*(.+?)\*\*"),
    re.compile(r"__(.+?)__"),
    re.compile(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])"),
    re.compile(r"(?<![\w_])_(?!\s)(.+?)(?<!\s)_(?![\w_])"),
)


def _strip_emphasis(line: str) -> str:
    for pattern in _EMPHASIS:
        previous = None
        while previous != line:
            previous = line
            line = pattern.sub(r"\1", line)
    return line


def normalize_line(text: str) -> str:
    """Сравнение строк: пробелы (включая NBSP), тире, кавычки, эмфаза, регистр."""
    out = unicodedata.normalize("NFC", text or "")
    for src, dst in _DASHES.items():
        out = out.replace(src, dst)
    for src, dst in _QUOTES.items():
        out = out.replace(src, dst)
    out = "\n".join(_strip_emphasis(line) for line in out.split("\n"))
    out = re.sub(r"[ \t   ]+", " ", out)
    return out.strip().lower()


def quote_tokens(text: str) -> List[str]:
    """Цитаты против ASR-транскрипта: без пунктуации, `ё → е`, по токенам."""
    base = normalize_line(text).replace("ё", "е")
    return re.findall(r"[\w]+", base, flags=re.UNICODE)


def quote_in_text(quote: str, haystack: str) -> bool:
    """Вхождение цитаты по границам слов: «ран» не найдётся внутри «экран»."""
    needle = quote_tokens(quote)
    if not needle:
        return False
    hay = quote_tokens(haystack)
    if len(needle) > len(hay):
        return False
    for start in range(len(hay) - len(needle) + 1):
        if hay[start:start + len(needle)] == needle:
            return True
    return False


#: Единственный владелец правила «что такое кавычка»: по нему находятся спаны
#: и по нему же снимаются кавычки с отсуженного парафраза. Два таких набора,
#: обязанных совпадать, разъехались бы при первой же правке пары.
#:
#: Спан ПАРНЫЙ: закрывает его пара своего открывающего знака, поэтому чужая
#: кавычка внутри пары (`«мы берём "жёлтый" вариант»`) спан не рвёт и вторым
#: спаном не считается — внешний её уже поглотил.
#:
#: Длины содержимого не ограничивает ничто: «AI» и «90» — цитаты ровно так же,
#: как фраза на строку, и короткая улика на экране решений весит не меньше
#: длинной. Порог здесь означал бы участок текста, который выглядит цитатой,
#: но не проходит ни сверку, ни судью.
#:
#: Одиночная кавычка — кавычка, но только на границе слова: апостроф стоит
#: ВНУТРИ слова (`don't`, `д'Артаньян`, `'90s`), кавычка — вокруг слова. Это
#: не эвристика «похоже на», а определение: без него одиночная кавычка либо
#: даёт провенансу дыру, либо ловит каждый апостроф.
#:
#: Пара не пересекает границу строк — как и эмфаза выше.
_QUOTE_SPAN = re.compile(
    r"«([^«»\n]+)»"
    r"|„([^„“”\n]+)[“”]"
    r"|“([^“”\n]+)”"
    r'|"([^"\n]+)"'
    r"|(?<!\w)['‘‚](?!\s)([^\n]+?)(?<!\s)['’‘](?!\w)"
)


def _span_body(match: "re.Match[str]") -> str:
    for group in match.groups():
        if group is not None:
            return group
    return ""


def quoted_spans(text: str) -> List[str]:
    """Фразы, поданные как дословная цитата встречи.

    Ярус 1 проверки цитат: поданное в кавычках обязано существовать в источнике.
    Несовпадение — не отказ и не цикл: спорную фразу судит быстрая модель
    (ярус 2), и только подтверждённая выдумка едет пометкой на экран.
    """
    return [body for body in (_span_body(m).strip()
                              for m in _QUOTE_SPAN.finditer(text or "")) if body]


def strip_quote_marks(text: str, quote: str) -> str:
    """Снять кавычки вокруг фразы — тем же детектором, что их нашёл.

    Парафраз, отсуженный судьёй, не остаётся в тексте записи дословностью.
    Снимает ровно та конструкция, которая кавычку и увидела: собственный
    список открывающих и закрывающих знаков отстал бы от детектора и оставил
    бы часть парафразов в кавычках.
    """
    key = normalize_line(quote)
    if not key:
        return text or ""

    def cut(match: "re.Match[str]") -> str:
        body = _span_body(match)
        return body if normalize_line(body) == key else match.group(0)

    return _QUOTE_SPAN.sub(cut, text or "")


def mentions_path(text: str, rel: str) -> bool:
    """Строка называет ИМЕННО этот путь, а не кусок чужого адреса.

    Улика правила связывается с домом, который она подтверждает: «строка стоит
    в файле» без этой связи подтверждает существование строки где-то в базе, а
    не то, что она про названный каталог.

    Путь узнаётся целиком: `01_company` внутри `01_company/meetings` — другой
    адрес, и совпадением не считается. Хвостовой слэш каталога допустим, потому
    что это тот же путь. Ни одного имени каталога здесь нет и быть не может:
    сравнивается то, что назвали, с тем, что написано.
    """
    needle = normalize_line(rel).strip("/")
    if not needle:
        return False
    pattern = re.compile(r"(?<![\w./-])" + re.escape(needle) + r"/?(?![\w./-])")
    return bool(pattern.search(normalize_line(text)))


def contains_fragment(text: str, fragment: str) -> bool:
    """Улика существует в файле: сырое вхождение первым, затем нормализованное."""
    if not (fragment or "").strip():
        return False
    if fragment in (text or ""):
        return True
    needle = normalize_line(fragment)
    return bool(needle) and needle in normalize_line(text)


def digest(payload: Any) -> str:
    """Отпечаток показа: решение человека принимается против того, что он видел."""
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# --- словари ------------------------------------------------------------

OPS = {"new", "update", "done", "dropped", "deferred", "noop"}
#: Источник закавыченной фразы объявляется явно и бывает ровно двух видов:
#: фраза встречи (её судит судья цитат) и строка файла базы (её проверяет код
#: по названному файлу). Третьего вида нет: незадекларированная кавычка — отказ формы.
QUOTE_SOURCES = {"meeting", "base"}
MODALITIES = {"committed", "intention", "deprioritized", "cancelled", "done_in_meeting"}
NOOP_REASONS = {"already_covered", "not_valuable", "episode"}
EPISODE_CLASSES = {"logistics", "small_talk", "repeat", "not_valuable"}
#: `revise` и `escalate` умерли вместе с циклами доводки: сомнение формулировки
#: и спор без критерия — один вердикт `doubt`, и решает его человек на экране.
VERDICTS = {"accept", "doubt", "duplicate", "episode", "wrong_file", "contradiction"}
OUTCOMES = {"take", "reject", "closed", "already", "edit"}
QUOTE_VERDICTS = {"exact", "paraphrase", "fabricated"}
APPLY_STATUSES = {"written", "failed", "skipped"}
#: Тема встречи — вторая половина имени файла протокола (правило v1: snake_case,
#: английский). Ядро строит из неё путь, поэтому форма проверяется здесь: точка,
#: слэш и пробел в имени означали бы адрес, которого человек не подтверждал.
TOPIC_SLUG = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")

#: Улика типизирована по вердикту: без неё вердикт не отсекает, а спорит.
EVIDENCE_FIELDS = {
    "duplicate": ("file", "quote"),
    "episode": ("quote", "class"),
    "contradiction": ("file", "quote"),
    "wrong_file": ("path",),
}


@dataclass
class Violation:
    code: str
    message: str
    field: str = ""
    eid: str = ""
    hint: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "error_class": error_class(self.code),
                "message": self.message, "field": self.field, "eid": self.eid,
                "hint": self.hint}


def require_fields(payload: Dict[str, Any], fields: Sequence[str], where: str) -> List[Violation]:
    out: List[Violation] = []
    for name in fields:
        if payload.get(name) in (None, ""):
            out.append(Violation("schema_invalid", f"нет обязательного поля {name}",
                                 field=f"{where}.{name}",
                                 hint=f"поле {name} обязательно; пример: \"{name}\": \"…\""))
    return out


# --- провенанс цитат ----------------------------------------------------


def quote_provenance(op: Dict[str, Any], where: str,
                     eid: str) -> Tuple[List[Violation], List[str], List[Dict[str, str]]]:
    """Источник каждой кавычки объявлен → (отказы формы, meeting-спаны, base-заявки).

    Форма решается здесь, факт — снаружи: meeting-фразу проверяет ярус 1 и судья
    цитат, base-фразу — код по названному файлу. Объявление, которому не отвечает
    ни один спан, отказом НЕ является: ядро само снимает кавычки с отсуженного
    парафраза, и переподанный пакет законно приходит с объявлением, но без спана.
    """
    entries = op.get("quote_sources") or []
    if not isinstance(entries, list):
        return ([Violation("schema_invalid", "quote_sources должен быть списком",
                           field=f"{where}.quote_sources", eid=eid,
                           hint='[{"text": "…", "source": "meeting"}]')], [], [])
    out: List[Violation] = []
    declared: Dict[str, Dict[str, Any]] = {}
    for idx, entry in enumerate(entries):
        at = f"{where}.quote_sources[{idx}]"
        if not isinstance(entry, dict):
            out.append(Violation("schema_invalid", "объявление источника должно быть объектом",
                                 field=at, eid=eid,
                                 hint='{"text": "…", "source": "meeting"}'))
            continue
        out += require_fields(entry, ["text", "source"], at)
        source = entry.get("source")
        if source and source not in QUOTE_SOURCES:
            out.append(Violation("schema_invalid", f"неизвестный источник цитаты {source}",
                                 field=f"{at}.source", eid=eid,
                                 hint=f"допустимо: {sorted(QUOTE_SOURCES)}"))
        if source == "base" and not str(entry.get("source_file") or "").strip():
            out.append(Violation("schema_invalid", "цитата из базы объявлена без файла",
                                 field=f"{at}.source_file", eid=eid,
                                 hint="source_file — файл базы, где эта строка стоит; "
                                      "без адреса код проверить её не может"))
        key = normalize_line(str(entry.get("text") or ""))
        if not key:
            continue
        if key in declared:
            out.append(Violation("schema_invalid",
                                 f"фраза {entry.get('text')!r} объявлена дважды",
                                 field=f"{at}.text", eid=eid,
                                 hint="одна фраза — один источник"))
        declared[key] = entry
    spans = quoted_spans(op.get("proposed_text") or "")
    meeting: List[str] = []
    claims: List[Dict[str, str]] = []
    for span in spans:
        entry = declared.get(normalize_line(span))
        if entry is None:
            out.append(Violation(
                "schema_invalid",
                f"закавыченная фраза {span!r} не объявлена в quote_sources",
                field=f"{where}.quote_sources", eid=eid,
                hint='источник объявляется явно: {"text": "…", "source": "meeting"} — '
                     'фраза встречи; {"text": "…", "source": "base", "source_file": '
                     '"product/03_backlog.md"} — строка файла базы; не уверен в '
                     "дословности — пиши без кавычек. Закавыченные фразы этой "
                     f"операции: {spans}"))
            continue
        if entry.get("source") == "base":
            claims.append({"quote": span,
                           "source_file": str(entry.get("source_file") or "")})
        elif entry.get("source") == "meeting":
            meeting.append(span)
    return out, meeting, claims


def base_quote_claims(payload: Any) -> List[Dict[str, str]]:
    """Объявленные строки базы с адресом файла — вход файловой сверки.

    Форму пакета к этому моменту уже проверил `validate_operations`; здесь
    только пересечение объявлений с фактическими кавычками текста записи.
    """
    out: List[Dict[str, str]] = []
    if not isinstance(payload, dict):
        return out
    seen = set()
    for idx, op in enumerate(payload.get("operations", []) or []):
        if not isinstance(op, dict):
            continue
        eid = str(op.get("eid", ""))
        _, _, claims = quote_provenance(op, f"operations[{idx}]", eid)
        for claim in claims:
            row = {"eid": eid, "quote": claim["quote"],
                   "source_file": claim["source_file"]}
            key = (row["eid"], row["quote"], row["source_file"])
            if key in seen:
                continue
            seen.add(key)
            out.append(row)
    return out


# --- артефакты узлов ----------------------------------------------------


def validate_map(payload: Any) -> List[Violation]:
    if not isinstance(payload, dict):
        return [Violation("schema_invalid", "карта должна быть объектом", field="$")]
    out = require_fields(payload, ["units"], "map")
    units = payload.get("units")
    if isinstance(units, list) and not units:
        out.append(Violation("schema_invalid", "карта без юнитов: встреча кого-то касалась",
                             field="map.units",
                             hint="нет подходящего юнита — назови ближайший, а предмет "
                                  "вынеси вопросом в questions: он доедет до паузы 1"))
    if isinstance(units, list):
        seen: Dict[str, int] = {}
        for idx, unit in enumerate(units):
            if not isinstance(unit, dict) or not unit.get("unit"):
                out.append(Violation("schema_invalid", "юнит без имени",
                                     field=f"map.units[{idx}].unit",
                                     hint='пример: {"unit": "product", "reason": "…"}'))
                continue
            name = str(unit["unit"])
            if not str(unit.get("reason") or "").strip():
                out.append(Violation("schema_invalid", f"юнит {name} без причины",
                                     field=f"map.units[{idx}].reason",
                                     hint="почему встреча его касается — одной фразой"))
            if name in seen:
                out.append(Violation("schema_invalid", f"юнит {name} назван дважды",
                                     field=f"map.units[{idx}].unit"))
            seen[name] = idx
    # `protocol_home` формой здесь не судится намеренно: дом протокола — не
    # обязанность узла, а правило базы, и оно бывает не записано. Всякая его
    # неполнота — неназванный каталог, улика без файла, улика, которой нет в
    # файле, — один и тот же исход: вопрос человеку на паузе 1 (`protocol_home`
    # в spine). Отказ здесь означал бы перезапуск узла ради того, чего в базе
    # нет, а второй судья формы разошёлся бы с первым при первой же правке.
    return out


def validate_brief(payload: Any, transcript: str) -> Tuple[List[Violation], List[Dict[str, Any]]]:
    """Форма выжимки → (отказы формы, флаги цитат для яруса 2).

    Цитата, не найденная в транскрипте, — не отказ: код видит байты, а нас
    интересует смысл. Флаг уходит быстрой модели; выдумкой пункт становится
    только после её вердикта.
    """
    if not isinstance(payload, dict):
        return [Violation("schema_invalid", "выжимка должна быть объектом", field="$")], []
    out = require_fields(payload, ["roster", "meeting"], "brief")
    meeting = payload.get("meeting")
    if meeting is not None and not isinstance(meeting, dict):
        out.append(Violation("schema_invalid", "meeting должен быть объектом",
                             field="brief.meeting", hint='{"gist": "…"}'))
    elif isinstance(meeting, dict):
        if not str(meeting.get("gist") or "").strip():
            out.append(Violation("schema_invalid", "нет meeting.gist — о чём была встреча",
                                 field="brief.meeting.gist",
                                 hint="три–пять фраз; их увидит человек на паузе 1"))
        topic = str(meeting.get("topic") or "").strip()
        if not topic:
            out.append(Violation("schema_invalid",
                                 "нет meeting.topic — из него строится имя протокола",
                                 field="brief.meeting.topic",
                                 hint="короткое название темы, snake_case, английский: "
                                      '"release_pipeline"'))
        elif not TOPIC_SLUG.match(topic):
            # форма темы — форма имени файла: путь строит ядро, и `../` или
            # пробел в нём означали бы адрес, которого никто не подтверждал
            out.append(Violation("schema_invalid",
                                 f"тема {topic!r} не годится в имя файла",
                                 field="brief.meeting.topic",
                                 hint="snake_case латиницей и цифрами: "
                                      '"release_pipeline", "1on1_erik"'))
    flags: List[Dict[str, Any]] = []
    roster = payload.get("roster")
    if not isinstance(roster, list):
        return out + [Violation("schema_invalid", "ростер должен быть списком",
                                field="brief.roster")], []

    seen_eids: Dict[str, int] = {}
    seen_quotes: Dict[str, str] = {}
    for idx, item in enumerate(roster):
        where = f"brief.roster[{idx}]"
        if not isinstance(item, dict):
            out.append(Violation("schema_invalid", "элемент ростера должен быть объектом",
                                 field=where))
            continue
        out += require_fields(item, ["eid", "type", "thread", "title", "quote"], where)
        if "unit" in item:
            # поле unit — провенанс правки пользователя (roster-overrides);
            # выжимка, сдавшая его, замаскировалась бы под решение человека
            out.append(Violation("schema_invalid",
                                 "поле unit в ростере запрещено — место называется в unit_hint",
                                 field=f"{where}.unit", eid=str(item.get("eid", "")) or None))
        eid = str(item.get("eid", ""))
        if eid:
            if eid in seen_eids:
                out.append(Violation("brief_duplicate", f"сущность {eid} встречается дважды",
                                     field=f"{where}.eid", eid=eid))
            seen_eids[eid] = idx
        quote = str(item.get("quote", ""))
        if quote:
            key = " ".join(quote_tokens(quote))
            if key and key in seen_quotes and seen_quotes[key] != eid:
                out.append(Violation("brief_duplicate", "цитата повторяется у разных сущностей",
                                     field=f"{where}.quote", eid=eid))
            seen_quotes[key] = eid
            if not quote_in_text(quote, transcript):
                flags.append({"eid": eid, "stage": "brief", "quote": quote})
        if item.get("type") in ("task", "decision") and not item.get("modality"):
            out.append(Violation("schema_invalid", "у задачи или решения нет модальности",
                                 field=f"{where}.modality", eid=eid,
                                 hint=f"одно из {sorted(MODALITIES)}"))
        modality = item.get("modality")
        if modality and modality not in MODALITIES:
            out.append(Violation("schema_invalid", f"неизвестная модальность {modality}",
                                 field=f"{where}.modality", eid=eid,
                                 hint=f"допустимо: {sorted(MODALITIES)}"))
        due = item.get("due")
        if due is not None and (not isinstance(due, str) or not due.strip()):
            out.append(Violation("schema_invalid", "срок задаётся строкой, как он прозвучал",
                                 field=f"{where}.due", eid=eid,
                                 hint="«до конца недели», «к 15-му»; срок не назван — поля нет"))
    return out, flags


def validate_operations(payload: Any, unit: str, assigned: Sequence[str],
                        known_eids: Sequence[str]) -> Tuple[List[Violation],
                                                            List[Dict[str, Any]]]:
    """Форма пакета операций → (отказы, флаги цитат `proposed_text` для яруса 2).

    Покрытие — форма пакета, не замок конвейера: каждая назначенная сущность
    получает судьбу в момент подачи, и это единственный момент, когда покрытие
    проверяется с отказом. Дальше оно живёт строкой `render state`.
    """
    if not isinstance(payload, dict):
        return [Violation("schema_invalid", "пакет операций должен быть объектом", field="$")], []
    out = require_fields(payload, ["unit", "editor_id", "operations"], "operations")
    if payload.get("unit") not in (None, "", unit):
        out.append(Violation("schema_invalid",
                             f"пакет назван для юнита {payload.get('unit')!r}, подан за {unit!r}",
                             field="operations.unit"))
    operations = payload.get("operations")
    if not isinstance(operations, list):
        return out + [Violation("schema_invalid", "operations должен быть списком",
                                field="operations.operations")], []
    flags: List[Dict[str, Any]] = []
    covered: Dict[str, int] = {}
    for idx, op in enumerate(operations):
        where = f"operations[{idx}]"
        if not isinstance(op, dict):
            out.append(Violation("schema_invalid", "операция должна быть объектом", field=where))
            continue
        out += require_fields(op, ["eid", "op"], where)
        eid = str(op.get("eid", ""))
        if eid and eid not in known_eids:
            # сущность, не прошедшую паузу 1, редактор породить не может:
            # выдуманный eid — кандидат в базу мимо подтверждённого ростера
            out.append(Violation("schema_invalid",
                                 f"сущности {eid} нет в подтверждённом ростере",
                                 field=f"{where}.eid", eid=eid))
        kind = op.get("op")
        if kind and kind not in OPS:
            out.append(Violation("schema_invalid", f"неизвестная операция {kind}",
                                 field=f"{where}.op", eid=eid, hint=f"допустимо: {sorted(OPS)}"))
        if eid:
            if eid in covered:
                out.append(Violation("schema_invalid",
                                     f"сущность {eid} получила две операции в одном пакете",
                                     field=f"{where}.eid", eid=eid,
                                     hint="одна сущность — одна судьба; проекция — поле "
                                          "projections[], не вторая операция"))
            covered[eid] = idx
        if kind == "noop" and op.get("noop_reason") not in NOOP_REASONS:
            out.append(Violation("schema_invalid", "у noop нет основания из закрытого списка",
                                 field=f"{where}.noop_reason", eid=eid,
                                 hint=f"допустимо: {sorted(NOOP_REASONS)}"))
        if kind in ("new", "update", "done", "dropped", "deferred") \
                and not op.get("journal_only"):
            target = op.get("target")
            if not isinstance(target, dict) or not target.get("file"):
                out.append(Violation("schema_invalid",
                                     f"операция {kind} без целевого файла",
                                     field=f"{where}.target.file", eid=eid,
                                     hint="target.file — файл юнита из фактического дерева; "
                                          "куда именно внутри файла — решает applier по канону "
                                          "формы"))
        if kind in ("new", "update") and not (op.get("proposed_text") or "").strip():
            out.append(Violation("schema_invalid", f"операция {kind} без текста записи",
                                 field=f"{where}.proposed_text", eid=eid))
        provenance, meeting_spans, _ = quote_provenance(op, where, eid)
        out += provenance
        for span in meeting_spans:
            flags.append({"eid": eid, "stage": "operations", "unit": unit, "quote": span})
    for eid in assigned:
        if eid not in covered:
            out.append(Violation("coverage_missing",
                                 f"сущность {eid} назначена юниту и осталась без судьбы",
                                 field="operations.operations", eid=eid,
                                 hint="каждая назначенная сущность получает операцию; "
                                      "нечего записывать — noop с основанием"))
    return out, flags


def validate_verdicts(payload: Any, unit: str,
                      operation_eids: Sequence[str]) -> List[Violation]:
    if not isinstance(payload, dict):
        return [Violation("schema_invalid", "пакет вердиктов должен быть объектом", field="$")]
    out = require_fields(payload, ["unit", "controller_id", "verdicts"], "verdicts")
    verdicts = payload.get("verdicts")
    if not isinstance(verdicts, list):
        return out + [Violation("schema_invalid", "verdicts должен быть списком",
                                field="verdicts.verdicts")]
    seen: Dict[str, int] = {}
    for idx, row in enumerate(verdicts):
        where = f"verdicts[{idx}]"
        if not isinstance(row, dict):
            out.append(Violation("schema_invalid", "вердикт должен быть объектом", field=where))
            continue
        out += require_fields(row, ["eid", "verdict"], where)
        eid = str(row.get("eid", ""))
        kind = row.get("verdict")
        if kind and kind not in VERDICTS:
            out.append(Violation("schema_invalid", f"неизвестный вердикт {kind}",
                                 field=f"{where}.verdict", eid=eid,
                                 hint=f"допустимо: {sorted(VERDICTS)}"))
        if eid in seen:
            out.append(Violation("schema_invalid", f"два вердикта по сущности {eid}",
                                 field=f"{where}.eid", eid=eid))
        seen[eid] = idx
        if eid and eid not in operation_eids:
            out.append(Violation("schema_invalid",
                                 f"вердикт по сущности {eid}, которой нет в пакете юнита",
                                 field=f"{where}.eid", eid=eid))
        needed = EVIDENCE_FIELDS.get(kind or "")
        if needed:
            evidence = row.get("evidence")
            if not isinstance(evidence, dict) or any(not evidence.get(k) for k in needed):
                out.append(Violation("schema_invalid",
                                     f"вердикт {kind} без типизированной улики",
                                     field=f"{where}.evidence", eid=eid,
                                     hint=f"обязательные поля улики: {list(needed)}"))
        if kind == "doubt" and not (row.get("note") or "").strip():
            out.append(Violation("schema_invalid", "сомнение без предмета спора",
                                 field=f"{where}.note", eid=eid,
                                 hint="note — что именно вызывает сомнение; решает человек"))
    for eid in operation_eids:
        if eid not in seen:
            out.append(Violation("verdict_missing",
                                 f"операция {eid} осталась без вердикта",
                                 field="verdicts.verdicts", eid=eid))
    return out


def validate_quotes(payload: Any) -> List[Violation]:
    if not isinstance(payload, dict):
        return [Violation("schema_invalid", "пакет вердиктов цитат должен быть объектом",
                          field="$")]
    out = require_fields(payload, ["judge_id", "quotes"], "quotes")
    rows = payload.get("quotes")
    if not isinstance(rows, list):
        return out + [Violation("schema_invalid", "quotes должен быть списком",
                                field="quotes.quotes")]
    for idx, row in enumerate(rows):
        where = f"quotes[{idx}]"
        if not isinstance(row, dict):
            out.append(Violation("schema_invalid", "вердикт цитаты должен быть объектом",
                                 field=where))
            continue
        out += require_fields(row, ["eid", "quote", "verdict"], where)
        if row.get("verdict") not in QUOTE_VERDICTS:
            out.append(Violation("schema_invalid",
                                 f"неизвестный вердикт цитаты {row.get('verdict')!r}",
                                 field=f"{where}.verdict", eid=str(row.get("eid", "")),
                                 hint=f"допустимо: {sorted(QUOTE_VERDICTS)}"))
    return out


def validate_relocation(payload: Any) -> List[Violation]:
    if not isinstance(payload, dict):
        return [Violation("schema_invalid", "ответ о переезде должен быть объектом", field="$")]
    out = require_fields(payload, ["eid", "editor_id", "accepted"], "relocation")
    if payload.get("accepted") is True:
        target = payload.get("target")
        if not isinstance(target, dict) or not target.get("file"):
            out.append(Violation("schema_invalid", "переезд принят без целевого файла",
                                 field="relocation.target.file",
                                 hint="target.file — файл юнита-адресата; заодно назови "
                                      "duplicate, если предмет у тебя уже записан"))
    elif payload.get("accepted") is False and not (payload.get("note") or "").strip():
        out.append(Violation("schema_invalid", "отказ от переезда без причины",
                             field="relocation.note",
                             hint="note уедет на экран как предмет спора"))
    return out


def status_row(row: Dict[str, Any], where: str, subject: str,
               eid: str = "") -> List[Violation]:
    """Общая форма статуса записи: словарь, причина у неудачи, адрес у `written`.

    Одна на обе половины отчёта — строку пункта и файл протокола: два списка
    правил, обязанных совпадать, разъехались бы при первой правке словаря.
    """
    out: List[Violation] = []
    status = row.get("status")
    if status not in APPLY_STATUSES:
        return [Violation("schema_invalid", f"неизвестный статус {status!r}",
                          field=f"{where}.status", eid=eid,
                          hint=f"допустимо: {sorted(APPLY_STATUSES)}")]
    if status in ("failed", "skipped") and not (row.get("note") or "").strip():
        out.append(Violation("schema_invalid", f"статус {status} без причины",
                             field=f"{where}.note", eid=eid,
                             hint=f"причину узнает пользователь — у {subject} "
                                  "она безымянной не бывает"))
    if status == "written" and not str(row.get("file") or "").strip():
        out.append(Violation("schema_invalid",
                             f"статус written без файла — {subject}",
                             field=f"{where}.file", eid=eid,
                             hint="written утверждает запись — значит, называет "
                                  "её адрес: без файла слитый отчёт нечем сверить"))
    return out


def validate_applied(payload: Any, expected: Sequence[str],
                     protocol_parts: Sequence[str] = ()) -> List[Violation]:
    """Статусы записи: по каждому принятому пункту, из закрытого словаря.

    Отчёт может быть склеен из строк нескольких applier'ов: статус один на
    пункт, каждая строка называет адрес своего пункта.

    Вторая половина отчёта — протокол встречи и архивная копия транскрипта.
    Пунктами они не являются (пункт — судьба сущности), поэтому живут отдельным
    разделом; спрашиваются так же строго: материал их нёс — статус обязателен,
    иначе замок 2 пропустил бы сводку о неизвестно чём.
    """
    if not isinstance(payload, dict):
        return [Violation("schema_invalid", "отчёт о записи должен быть объектом", field="$")]
    out = require_fields(payload, ["applier_id", "results"], "applied")
    protocol = payload.get("protocol")
    protocol = protocol if isinstance(protocol, dict) else {}
    for part in protocol_parts:
        row = protocol.get(part)
        if not isinstance(row, dict) or not str(row.get("status") or "").strip():
            out.append(Violation(
                "apply_status_missing",
                f"файл протокола ({part}) остался без статуса записи",
                field=f"applied.protocol.{part}.status",
                hint='protocol: {"summary": {"status": "written", "file": "…"}, '
                     '"transcript": {"status": "skipped", "note": "…"}}'))
            continue
        out += status_row(row, f"applied.protocol.{part}", f"файла протокола ({part})")
    rows = payload.get("results")
    if not isinstance(rows, list):
        return out + [Violation("schema_invalid", "results должен быть списком",
                                field="applied.results")]
    seen: Dict[str, int] = {}
    for idx, row in enumerate(rows):
        where = f"results[{idx}]"
        if not isinstance(row, dict):
            out.append(Violation("schema_invalid", "строка отчёта должна быть объектом",
                                 field=where))
            continue
        out += require_fields(row, ["eid", "status"], where)
        eid = str(row.get("eid", ""))
        if eid and eid not in expected:
            # статус по непринятому пункту — заявка на запись несогласованного
            out.append(Violation("schema_invalid",
                                 f"пункт {eid} не был принят на экране решений",
                                 field=f"{where}.eid", eid=eid))
        if eid in seen:
            out.append(Violation("schema_invalid", f"два статуса по пункту {eid}",
                                 field=f"{where}.eid", eid=eid))
        out += status_row(row, where, f"пункт {eid}" if eid else "пункт", eid)
        seen[eid] = idx
    for eid in expected:
        if eid not in seen:
            out.append(Violation("apply_status_missing",
                                 f"принятый пункт {eid} остался без статуса записи",
                                 field="applied.results", eid=eid))
    return out


def validate_delivery(payload: Any) -> List[Violation]:
    if not isinstance(payload, dict):
        return [Violation("schema_invalid", "сводка должна быть объектом", field="$")]
    out = require_fields(payload, ["text"], "delivery")
    if "audience" in payload:
        # защита от узла, живущего по старой схеме delivery/1
        out.append(Violation("schema_invalid",
                             "поле audience упразднено: сводка одна — участникам",
                             field="delivery.audience"))
    if isinstance(payload.get("text"), str) and not payload["text"].strip():
        out.append(Violation("schema_invalid", "сводка пуста",
                             field="delivery.text",
                             hint="пустой текст не сдаётся: отправлять нечего — "
                                  "скажи это пользователю прямо"))
    return out
