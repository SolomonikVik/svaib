#!/usr/bin/env python3
"""Инварианты пакета дельт — библиотека для spine (+ совместимый CLI).

Копия корневого `validate_deltas.py` с доработкой вывода (spine-contracts §3):

    validate(package: dict, phase: str) -> list[Violation]

`Violation{code, level, delta_ids, field, msg}`; `level ∈ package|node|entity|delta`
задаётся детерминированной таблицей `CODE_LEVEL` — по нему spine выбирает
retry-политику: package/node → rework узла → `failed`; entity/delta → doubtful
`unresolved`. Новое поле дельты `doubt_question` (вопрос пользователю на
doubtful-дельте, адрес K13; `home_question` по-прежнему допустим только на
canonical в recommended).

Два инварианта расходятся с корневым легаси намеренно (решения 29.07):

- **E00, вариант (а):** протокол встречи больше НЕ заводится ни сущностью
  ростера (`S10_protocol_entity_forbidden`, уровень package), ни дельтой
  (`S10_protocol_delta_forbidden`, уровень delta) — его публикует spine на
  `apply` из принятой выжимки. Каталог протоколов принадлежит публикациям:
  любая дельта под `protocol_path` — нарушение (`S10_protocol_dir_target`,
  уровень delta), исключений из ролевых инвариантов у неё больше нет.
  Легаси-коды `S10_protocol_missing`/`S10_protocol_duplicate`/
  `S11_protocol_channel` умерли вместе с E00-дельтой.
- **S13:** стратегический контур `01_company/01_strategic/` скилл не обновляет —
  дельта с таким `target_file`/`source_file` уходит в doubtful
  (`S13_strategic_target`), а запись в него терминально запрещена в spine.

Вход не разобран → `ValidationInputError` (в легаси это был exit 2).

CLI-обёртка сохраняет формат старого валидатора:
    python3 validate_deltas.py --phase coverage|final|both < package.json
    stdout: {"ok": bool, "violations": [{code, message, delta_ids}], "warnings": [...]}
    exit: 0 — инварианты держатся; 1 — есть нарушения; 2 — вход не разобран.

Только stdlib. Ничего не пишет на диск.
"""

from __future__ import annotations

import argparse
import json
import re
import sys

ROLES = {"canonical", "reference", "consequence"}
DISPOSITIONS = {"write", "summary_only", "unclear"}
SECTIONS = {"recommended", "doubtful"}
PHASES = ("coverage", "final", "both")
# Классы файлов вне uniqueness-инварианта: хроника, глоссарий, наблюдения о людях
EXEMPT_CLASSES = {"progress", "glossary", "team"}
# Core-классы: у одной сущности ≤1 canonical-дома СУММАРНО по всем этим классам
CORE_CLASSES = {"active", "backlog", "decisions", "overview"}
# Стратегический контур базы: скилл его не обновляет (норма S13 карты миграции).
# Здесь — мягкий гейт (дельта уходит в doubtful), терминальный запрет записи —
# в spine на apply/publish.
STRATEGIC_PREFIX = "01_company/01_strategic/"

LEVEL_PACKAGE = "package"
LEVEL_NODE = "node"
LEVEL_ENTITY = "entity"
LEVEL_DELTA = "delta"
LEVELS = (LEVEL_PACKAGE, LEVEL_NODE, LEVEL_ENTITY, LEVEL_DELTA)
# Уровни, которые spine чинит rework'ом узла и добивает в failed.
HARD_LEVELS = (LEVEL_PACKAGE, LEVEL_NODE)

# Детерминированная таблица code → level для ВСЕХ кодов валидатора
# (spine-contracts §7 п.2). package/node — структурные дефекты пакета, которые
# пометкой отдельной дельты не чинятся; entity/delta — адресуемые, уходят в
# doubtful `unresolved` после исчерпания rework.
CODE_LEVEL = {
    "S0": LEVEL_PACKAGE,
    "S1": LEVEL_PACKAGE,
    "S2": LEVEL_PACKAGE,
    "S3": LEVEL_DELTA,
    "S4": LEVEL_DELTA,
    "S5": LEVEL_DELTA,
    "S6": LEVEL_DELTA,
    "S7": LEVEL_ENTITY,
    "S8": LEVEL_ENTITY,
    "S9": LEVEL_ENTITY,
    "S10_meta_missing": LEVEL_PACKAGE,
    "S10_protocol_entity_forbidden": LEVEL_PACKAGE,
    "S10_protocol_delta_forbidden": LEVEL_DELTA,
    "S10_protocol_dir_target": LEVEL_DELTA,
    "S13_strategic_target": LEVEL_DELTA,
    "E1": LEVEL_PACKAGE,
    "A1": LEVEL_ENTITY,
    "A2": LEVEL_ENTITY,
    "A3": LEVEL_NODE,
    "A4": LEVEL_DELTA,
    "B1": LEVEL_ENTITY,
    "B2": LEVEL_DELTA,
    "B3": LEVEL_NODE,
    "B4": LEVEL_DELTA,
    "B5": LEVEL_DELTA,
    "B6": LEVEL_ENTITY,
    "B7": LEVEL_DELTA,
    "B8": LEVEL_DELTA,
    "B9": LEVEL_DELTA,
    "B10": LEVEL_DELTA,
    "B11": LEVEL_DELTA,
    "B12": LEVEL_DELTA,
}

# Поле пакета/дельты, к которому относится нарушение (§7 п.2 — `Violation.field`).
CODE_FIELD = {
    "S0": "$",
    "S1": "entities[].id",
    "S2": "deltas[].id",
    "S3": "target_file",
    "S4": "section",
    "S5": "role",
    "S6": "doubt_reason",
    "S7": "entities[].disposition",
    "S8": "entities[].disposition",
    "S9": "entities[].disposition",
    "S10_meta_missing": "protocol_required",
    "S10_protocol_entity_forbidden": "entities[].type",
    "S10_protocol_delta_forbidden": "entity_type",
    "S10_protocol_dir_target": "target_file",
    "S13_strategic_target": "target_file",
    "E1": "entities",
    "A1": "entities[].disposition",
    "A2": "entities[].id",
    "A3": "meeting_nodes",
    "A4": "entity_id",
    "B1": "target_file",
    "B2": "target_file",
    "B3": "dropped_nodes",
    "B4": "owner",
    "B5": "spec_id",
    "B6": "proposed_text",
    "B7": "proposed_text",
    "B8": "proposed_text",
    "B9": "canonical_external",
    "B10": "home_question",
    "B11": "card_home",
    "B12": "doubt_question",
}


class ValidationInputError(ValueError):
    """Пакет не разобран как валидный вход (в легаси — exit 2)."""


class Violation:
    """Типизированное нарушение: code + level + адрес (delta_ids/field)."""

    __slots__ = ("code", "level", "delta_ids", "field", "msg")

    def __init__(self, code, msg, delta_ids=(), level=None, field=None):
        self.code = code
        self.msg = msg
        self.delta_ids = sorted(str(i) for i in delta_ids)
        self.level = level or CODE_LEVEL[code]
        self.field = field if field is not None else CODE_FIELD.get(code)

    def as_dict(self):
        return {
            "code": self.code,
            "level": self.level,
            "delta_ids": list(self.delta_ids),
            "field": self.field,
            "msg": self.msg,
        }

    def legacy_dict(self):
        """Формат старого CLI: code + message + delta_ids."""
        return {"code": self.code, "message": self.msg, "delta_ids": list(self.delta_ids)}

    def __repr__(self):  # pragma: no cover — диагностика
        return "Violation({}/{}, {})".format(self.code, self.level, self.delta_ids)


def is_hard(violations):
    """Есть ли нарушение уровня package/node (rework узла, не doubtful)."""
    return any(v.level in HARD_LEVELS for v in violations)


def file_class(path):
    # Класс — по хвосту имени, префикс не значим: нумерация kit у клиентов
    # расходится с канонической (03_progress, 04_decisions, 02_glossary и
    # т.п.). Граница контракта: kit-префикс — 1-2 цифры, опционален
    # (active.md — тоже kit: класс задаёт суффикс, не номер); длинный
    # цифровой префикс (2026_progress.md) — не kit, остаётся other.
    p = path.replace("\\", "/")
    name = p.rsplit("/", 1)[-1]
    if re.search(r"(^|/)(\d{1,2}_)?team/", p):
        return "team"
    stem = name[:-3] if name.endswith(".md") else name
    stem = re.sub(r"^\d{1,2}_", "", stem)
    if stem in ("glossary", "speech-aliases"):
        return "glossary"
    if stem in ("active", "backlog", "decisions", "overview", "progress"):
        return stem
    return "other"


def node_of(path):
    p = path.replace("\\", "/").lstrip("/")
    while p.startswith("./") or p.startswith("/"):
        p = p.lstrip("/")
        if p.startswith("./"):
            p = p[2:]
    return p.split("/", 1)[0]


def norm_path(path):
    p = (path or "").replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p.lstrip("/")


def check(payload, phase):
    """Инварианты пакета. Возвращает (violations, warnings) — списки Violation."""
    if not isinstance(payload, dict):
        raise ValidationInputError("пакет дельт должен быть JSON-объектом")
    if phase not in PHASES:
        raise ValidationInputError("phase вне {}".format(sorted(PHASES)))

    violations = []
    warnings = []
    # both = инварианты обеих фаз на одном пакете (одноузловой путь)
    cov = phase in ("coverage", "both")
    fin = phase in ("final", "both")

    def add(code, message, delta_ids=(), ph=None, field=None):
        if ph and phase == "both":
            message = f"[{ph}] {message}"
        violations.append(Violation(code, message, delta_ids, field=field))

    def warn(code, message, delta_ids=(), field=None):
        # Канал предупреждений остаётся частью контракта check()/CLI, хотя
        # инвариантов уровня warning сейчас нет: единственный (легаси
        # S10_protocol_duplicate) умер вместе с E00-дельтой.
        warnings.append(Violation(code, message, delta_ids, field=field))

    entities = payload.get("entities", [])
    deltas = payload.get("deltas", [])
    meeting_nodes = payload.get("meeting_nodes", [])
    if not isinstance(entities, list) or not isinstance(deltas, list):
        raise ValidationInputError("поля entities и deltas должны быть списками")

    protocol_path = norm_path(payload.get("protocol_path")).rstrip("/")

    def under_protocol(d):
        if not protocol_path:
            return False
        return norm_path(d.get("target_file")).startswith(protocol_path + "/")

    # Дельта-протокол сама по себе запрещена (S10_protocol_delta_forbidden) —
    # ролевые инварианты на ней не считаются, чтобы одна ошибка не размножалась
    # в S5/B-коды. Каталог протоколов из этого исключения УБРАН: дельта под
    # protocol_path — обычная дельта по всем правилам плюс S10_protocol_dir_target.
    def is_protocol(d):
        return d.get("entity_type") == "protocol"

    def under_strategic(path):
        return norm_path(path).startswith(STRATEGIC_PREFIX)

    # Протокол — не канал раскладки: дельта-протокол не покрывает никакую
    # сущность ростера, поглощение сущности текстом протокола всплывает как
    # пропуск покрытия (A2), а не как покрытие.
    def counts_for_coverage(d):
        return not is_protocol(d)

    # --- Структурная валидация (обе фазы) ---
    entity_ids = [e.get("id") for e in entities]
    dup_entities = {i for i in entity_ids if entity_ids.count(i) > 1}
    if dup_entities:
        add("S1", f"дубли id в ростере сущностей: {sorted(dup_entities)}")
    known_entities = set(entity_ids)

    # E00, вариант (а): сущности-протокола не существует. Ростер её не заводит —
    # протокол не сущность памяти, а публикация spine из принятой выжимки.
    for e in entities:
        if e.get("type") == "protocol":
            add("S10_protocol_entity_forbidden",
                f"сущность {e.get('id')} типа protocol в ростере: протокол не "
                f"заводится ни сущностью, ни дельтой — его публикует spine из "
                f"принятой на confirm выжимки")

    delta_ids = [d.get("id") for d in deltas]
    dup_deltas = {i for i in delta_ids if delta_ids.count(i) > 1}
    if dup_deltas:
        add("S2", f"дубли id дельт: {sorted(dup_deltas)}", dup_deltas)

    for d in deltas:
        did = d.get("id", "?")
        if not d.get("target_file"):
            add("S3", "дельта без target_file", [did])
        if d.get("section") not in SECTIONS:
            add("S4", f"section вне {sorted(SECTIONS)}", [did])
        if fin and d.get("role") not in ROLES \
                and file_class(d.get("target_file", "")) not in EXEMPT_CLASSES \
                and not is_protocol(d):
            add("S5", f"role вне {sorted(ROLES)}", [did], ph="final")
        # E00, вариант (а) (решение 29.07): протокол публикует spine на apply из
        # принятой выжимки — дельтой он не заводится ни при каких условиях.
        if d.get("entity_type") == "protocol":
            add("S10_protocol_delta_forbidden",
                "протокол не заводится дельтой — публикует spine из принятой "
                "выжимки", [did])
        # Каталог протоколов принадлежит публикациям spine (`_summary.md` и
        # протокол, оба create-only): дельта туда — второй write-path к тому же
        # файлу. Пустой protocol_path в мете — проверка молчит.
        if under_protocol(d):
            add("S10_protocol_dir_target",
                f"target_file={d.get('target_file')!r} лежит в каталоге "
                f"протоколов {protocol_path}/ — он принадлежит публикациям "
                f"spine; сущность получает дельту в свой целевой файл", [did])
        # S13: стратегический контур базы скилл не обновляет.
        for path_field in ("target_file", "source_file"):
            if under_strategic(d.get(path_field)):
                add("S13_strategic_target",
                    f"{path_field}={d.get(path_field)!r} лежит в стратегическом "
                    f"контуре {STRATEGIC_PREFIX} — скилл его не обновляет "
                    f"(норма S13): стратегические файлы правит руководитель, "
                    f"дельта уходит в «Сомневаюсь»", [did], field=path_field)
                break

    # --- Видимость сущностей (обе фазы): пакет обязан показывать сомнения ---
    deltas_by_entity = {}
    for d in deltas:
        eid = d.get("entity_id")
        if eid and counts_for_coverage(d):
            deltas_by_entity.setdefault(eid, []).append(d)
    if fin and not entities:
        add("E1", "финальный пакет без ростера entities — инварианты видимости "
                  "(S7/S8/S9) не проверяемы; подай полный пакет", ph="final")
    for e in entities:
        eid = e.get("id")
        disp = e.get("disposition")
        own = deltas_by_entity.get(eid, [])
        if e.get("merged_into"):
            target = next((t for t in entities
                           if t.get("id") == e.get("merged_into")), None)
            if target is None:
                add("S8", f"merged_into={e.get('merged_into')} у сущности {eid} "
                          f"указывает на несуществующую запись ростера")
            elif target.get("merged_into"):
                add("S8", f"сущность {eid} слита в {e.get('merged_into')}, "
                          f"которая сама слита — цепочка/цикл слияний, "
                          f"указывай выжившую сущность")
            elif target.get("disposition") == "summary_only":
                add("S8", f"сущность {eid} слита в summary_only-сущность "
                          f"{e.get('merged_into')} — тихая потеря write/unclear "
                          f"через слияние")
            continue
        if disp == "unclear":
            visible = any(d.get("section") == "doubtful" for d in own) or any(
                d.get("section") == "recommended" and d.get("home_question")
                for d in own) or (
                (e.get("resolved_from_unclear") or "").strip()
                and any(d.get("section") == "recommended" for d in own))
            if not visible:
                add("S7", f"unclear-сущность {eid} ({e.get('label', '')}) невидима: "
                          f"нужна doubtful-дельта, recommended-дельта с "
                          f"home_question или resolved_from_unclear с "
                          f"recommended-дельтой")
        if disp == "summary_only" and own:
            add("S9", f"summary_only-сущность {eid} имеет дельты — противоречие "
                      f"disposition; понижать write/unclear до summary_only "
                      f"нельзя, сомнение оформляй doubtful-дельтой",
                [d.get("id", "?") for d in own])
        if fin and disp == "write" and not own:
            add("S8", f"write-сущность {eid} ({e.get('label', '')}) без единой "
                      f"дельты в финальном пакете — тихая потеря; спорную "
                      f"переводи в doubtful, слитую помечай merged_into",
                ph="final")

    # --- Фаза A: полнота покрытия ---
    if cov:
        for e in entities:
            if e.get("disposition") not in DISPOSITIONS:
                add("A1", f"сущность {e.get('id')} без валидного disposition "
                          f"({sorted(DISPOSITIONS)})", ph="coverage")
        covered = {d.get("entity_id") for d in deltas
                   if counts_for_coverage(d)}
        for e in entities:
            if e.get("disposition") == "write" and e.get("id") not in covered:
                add("A2", f"write-сущность {e.get('id')} ({e.get('label', '')}) "
                          f"не имеет ни одной дельты", ph="coverage")
        # A3 по всем префиксам пути, не по первому сегменту: узел встречи может
        # быть вложенным (контур досье clients/{контрагент} — гейт унификации 29.07;
        # ложный A3 был отложенным дефектом node_of, здесь — первое законное
        # расхождение копии с корневым легаси-валидатором)
        # Полный путь входит в покрытие наравне с префиксами: по scaffold контуром
        # бывает файл (карточка до разворачивания в каталог), и такой контур
        # покрывается дельтой ровно в него — префиксами он не покрывался НИКОГДА
        # (находка №24: последний сегмент отбрасывался, ложный A3 неустраним).
        delta_nodes = set()
        for d in deltas:
            parts = [p for p in norm_path(d.get("target_file", "")).split("/") if p]
            for i in range(1, len(parts) + 1):
                delta_nodes.add("/".join(parts[:i]))
        for n in meeting_nodes:
            if norm_path(n).rstrip("/") not in delta_nodes:
                add("A3", f"затронутый узел {n} не получил ни одной дельты",
                    ph="coverage")
        for d in deltas:
            if file_class(d.get("target_file", "")) in ("progress", "glossary"):
                continue
            eid = d.get("entity_id")
            if not eid:
                add("A4", "дельта без entity_id", [d.get("id", "?")],
                    ph="coverage")
            elif eid not in known_entities:
                add("A4", f"entity_id {eid} отсутствует в ростере",
                    [d.get("id", "?")], ph="coverage")

    # --- Фаза B: единственность дома и монотонность ---
    # Инварианты дома (B1/B2/B4/B6/B7) применяются к section=recommended:
    # doubtful — легитимное место альтернатив и спорных домов, ждущих решения
    # пользователя; считать их нарушением = ложный violation на каждом споре.
    if fin:
        canonical = {}
        for d in deltas:
            if d.get("role") != "canonical" \
                    or d.get("section") != "recommended":
                continue
            cls = file_class(d.get("target_file", ""))
            if cls in EXEMPT_CLASSES or is_protocol(d):
                continue
            group = "core" if cls in CORE_CLASSES else "other:" + cls
            key = (d.get("entity_id"), group)
            canonical.setdefault(key, []).append(d)
        for (eid, group), items in canonical.items():
            if len(items) > 1:
                add("B1", f"сущность {eid}: {len(items)} canonical-дома "
                          f"({group}) — {[i.get('target_file') for i in items]}; "
                          f"дом один, прочие вхождения — reference/consequence",
                    [i.get("id", "?") for i in items], ph="final")
        # Resolved reference: ссылка/следствие в recommended обязаны иметь
        # canonical той же сущности в recommended — либо явный флаг
        # canonical_external (дом уже существует в файле вне этого прогона).
        rec_canonical_eids = {d.get("entity_id") for d in deltas
                              if d.get("role") == "canonical"
                              and d.get("section") == "recommended"}
        for d in deltas:
            if d.get("section") != "recommended" or is_protocol(d):
                continue
            if d.get("role") not in ("reference", "consequence"):
                continue
            if d.get("canonical_external"):
                continue
            eid = d.get("entity_id")
            if eid and eid not in rec_canonical_eids:
                add("B9", f"{d.get('role')}-дельта сущности {eid} без "
                          f"canonical-дельты в recommended: битая ссылка "
                          f"(дом уже в базе → пометь canonical_external)",
                    [d.get("id", "?")], ph="final")
        for d in deltas:
            if d.get("section") != "recommended" or is_protocol(d):
                continue
            if d.get("role") == "canonical" \
                    and d.get("entity_type") == "decision" \
                    and file_class(d.get("target_file", "")) in ("active", "backlog"):
                add("B2", f"decision-сущность {d.get('entity_id')} с canonical-домом "
                          f"в {d.get('target_file')}: решение живёт в decisions; "
                          f"в active — только reference или consequence с owner",
                    [d.get("id", "?")], ph="final")
            if d.get("role") == "canonical" \
                    and d.get("entity_type") in ("task", "risk", "question") \
                    and file_class(d.get("target_file", "")) == "decisions":
                add("B2", f"{d.get('entity_type')}-сущность {d.get('entity_id')} "
                          f"с canonical-домом в {d.get('target_file')}: "
                          f"задачи/риски/вопросы не живут в decisions",
                    [d.get("id", "?")], ph="final")
            if d.get("role") == "canonical" \
                    and file_class(d.get("target_file", "")) in ("progress", "glossary"):
                add("B2", f"canonical-дом в {d.get('target_file')}: хроника и "
                          f"глоссарий — не дом сущности", [d.get("id", "?")],
                    ph="final")
            if file_class(d.get("target_file", "")) == "progress" \
                    and len(d.get("proposed_text") or "") > 700:
                add("B8", "progress-запись длиннее 700 символов — хроника, "
                          "не свалка контента", [d.get("id", "?")], ph="final")
        # Смысловой дубль сквозь дробление ростера: canonical-дельты РАЗНЫХ
        # сущностей с высокой текстовой близостью → merge или doubt.
        def low_text(text):
            return (text or "").lower()

        def tokens(text):
            return {w for w in "".join(
                c if c.isalnum() else " " for c in low_text(text)).split()
                if len(w) >= 4}
        canon_texts = [(d.get("id", "?"), d.get("entity_id"),
                        d.get("proposed_text") or "")
                       for d in deltas if d.get("role") == "canonical"
                       and d.get("section") == "recommended"
                       and not is_protocol(d)]
        for i in range(len(canon_texts)):
            for j in range(i + 1, len(canon_texts)):
                id_i, e_i, t_i = canon_texts[i]
                id_j, e_j, t_j = canon_texts[j]
                if e_i == e_j or len(t_i) < 80 or len(t_j) < 80:
                    continue
                a, b = tokens(t_i), tokens(t_j)
                if a and b and len(a & b) / len(a | b) >= 0.5:
                    add("B6", f"canonical-дельты разных сущностей ({e_i}, {e_j}) "
                              f"текстуально почти совпадают — вероятно, одна "
                              f"сущность раздроблена в ростере: объедини или "
                              f"отправь в doubtful", [id_i, id_j], ph="final")
        phase_a_nodes = set(payload.get("phase_a_nodes", []))
        rec_nodes = {node_of(d.get("target_file", ""))
                     for d in deltas if d.get("section") == "recommended"}
        dropped = {d.get("node"): (d.get("reason") or "").strip()
                   for d in payload.get("dropped_nodes", [])}
        for n in sorted(phase_a_nodes - rec_nodes):
            if n not in dropped or not dropped[n]:
                add("B3", f"узел {n} не покрыт ни одной recommended-дельтой — "
                          f"дельты в doubtful покрытием не считаются. Либо верни "
                          f"узлу recommended-дельту (копию меняй на ссылку/следствие), "
                          f"либо снимай узел явно: запись в dropped_nodes с причиной, "
                          f"его дельты — в doubtful", ph="final")
            elif not any(node_of(d.get("target_file", "")) == n
                         and d.get("section") == "doubtful" for d in deltas):
                add("B3", f"узел {n} снят ({dropped[n]}), но его дельты удалены — "
                          f"переведи их в doubtful, снятие должно быть видно "
                          f"пользователю", ph="final")
        for d in deltas:
            if d.get("section") != "recommended" or is_protocol(d):
                continue
            if d.get("role") == "reference" \
                    and len(d.get("proposed_text") or "") > 240:
                add("B7", "reference — короткая проекция/ссылка на canonical-дом "
                          "(≤240 символов), не копия текста сущности",
                    [d.get("id", "?")], ph="final")
            if d.get("role") == "consequence" and not (d.get("owner") or "").strip():
                add("B4", "consequence-дельта без owner — это пересказ, не следствие",
                    [d.get("id", "?")], ph="final")
        for d in deltas:
            if d.get("section") == "doubtful" \
                    and d.get("doubt_reason") not in ("dispute", "unresolved"):
                add("S6", "doubtful-дельта без doubt_reason (dispute|unresolved) — "
                          "пользователь не отличит спор от непочиненного",
                    [d.get("id", "?")], ph="final")
            if d.get("section") != "doubtful" and d.get("doubt_reason"):
                add("S6", "doubt_reason на non-doubtful дельте", [d.get("id", "?")],
                    ph="final")
            # Новое поле (§3): вопрос пользователю живёт на doubtful-дельте —
            # симметрично S6 и B10, чтобы поле не подменяло home_question.
            if d.get("section") != "doubtful" and d.get("doubt_question"):
                add("B12", "doubt_question допустим только на doubtful-дельте "
                           "(вопрос о спорной правке, не замена home_question)",
                    [d.get("id", "?")], ph="final")
        for d in deltas:
            if is_protocol(d):
                continue
            if d.get("home_question") and not (
                    d.get("role") == "canonical"
                    and d.get("section") == "recommended"):
                add("B10", "home_question допустим только на canonical-дельте в "
                           "recommended (вопрос о выборе легитимного дома, не "
                           "замена doubtful)", [d.get("id", "?")], ph="final")
            if d.get("card_home") and d.get("role") == "canonical" \
                    and d.get("target_file") != d.get("card_home") \
                    and not d.get("home_question"):
                add("B11", f"пометка card_home={d.get('card_home')} Фазы A "
                           f"проигнорирована без home_question — канонизатор не "
                           f"пересматривает предметность молча",
                    [d.get("id", "?")], ph="final")
        specs = {}
        for d in deltas:
            if d.get("spec_id"):
                specs.setdefault(d["spec_id"], set()).add(d.get("target_file"))
        for sid, files in specs.items():
            if len(files) > 1:
                add("B5", f"нарративная спецификация {sid} раздроблена по файлам: "
                          f"{sorted(files)}",
                    [d.get("id", "?") for d in deltas if d.get("spec_id") == sid],
                    ph="final")
        for d in deltas:
            if file_class(d.get("target_file", "")) in ("progress", "glossary"):
                continue
            eid = d.get("entity_id")
            if not eid:
                add("A4", "дельта без entity_id", [d.get("id", "?")], ph="final")
            elif known_entities and eid not in known_entities:
                add("A4", f"entity_id {eid} отсутствует в ростере",
                    [d.get("id", "?")], ph="final")

        # --- S10: meta протокола (Гейт A п.0; phase final/both) ---
        # Сам протокол дельтой не заводится (E00, вариант (а)) — meta остаётся:
        # по ней spine решает, публиковать ли протокол на apply, и куда.
        if "protocol_required" not in payload:
            add("S10_meta_missing",
                "в meta пакета нет поля protocol_required (true|false) — на "
                "phase final/both оно обязательно (Гейт A п.0); при "
                "protocol_required=true обязателен и protocol_path", ph="final")
        elif payload.get("protocol_required") and not protocol_path:
            add("S10_meta_missing",
                "protocol_required=true, но protocol_path пуст или "
                "отсутствует — укажи каталог протоколов, определённый на "
                "Гейте A п.0 по клиентскому правилу Шага 0", ph="final")

    return violations, warnings


def validate(package, phase):
    """Публичный Validation API (spine-contracts §3): только нарушения."""
    return check(package, phase)[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=list(PHASES), required=True)
    args = parser.parse_args()
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        json.dump({"ok": False, "violations": [
            {"code": "S0", "message": f"stdin не является валидным JSON: {exc}",
             "delta_ids": []}]}, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 2
    try:
        violations, warnings = check(payload, args.phase)
    except ValidationInputError as exc:
        json.dump({"ok": False, "violations": [
            {"code": "S0", "message": str(exc), "delta_ids": []}]},
            sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 2
    out = {"ok": not violations, "violations": [v.legacy_dict() for v in violations]}
    if warnings:
        out["warnings"] = [w.legacy_dict() for w in warnings]
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main())
