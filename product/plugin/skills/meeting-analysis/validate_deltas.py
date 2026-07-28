#!/usr/bin/env python3
"""Code-валидатор инвариантов L2-дельт (двухфазный L2, meeting-analysis).

Вызов (координатором, между фазами L2):
    python3 validate_deltas.py --phase coverage <<'VDEOF'
    { ...JSON... }
    VDEOF
    python3 validate_deltas.py --phase final <<'VDEOF'
    { ...JSON... }
    VDEOF
    # Одноузловой путь: один объединённый вызов после инлайн-канонизации
    python3 validate_deltas.py --phase both <<'VDEOF'
    { ...JSON... }
    VDEOF

`--phase both` гоняет инварианты ОБЕИХ фаз на одном пакете; сообщения об
ошибках несут префикс фазы (`[coverage]`/`[final]`). Контракт вызовов
(validation-contract.json): both засчитывается и как coverage, и как final.

stdin: JSON с полями:
    phase_a_nodes  — только для --phase final/both: write-узлы фазы A (список строк)
    meeting_nodes  — затронутые узлы этой встречи (список строк, напр. "08_ai-lab")
    protocol_required — meta Гейта A п.0: протокол встречи ещё не существует и
                     обязан быть создан (bool). На phase final/both поле
                     ОБЯЗАТЕЛЬНО: отсутствует → S10_meta_missing
    protocol_path  — каталог протоколов по клиентскому правилу Шага 0
                     (напр. "01_company/meetings"); обязателен при
                     protocol_required=true
    entities       — ростер сущностей выжимки:
                     {id, type, disposition: write|summary_only|unclear, label,
                      merged_into: id выжившей сущности (слита канонизатором),
                      resolved_from_unclear: причина (Фаза B разрешила сомнение)}
    deltas         — дельты: {id, entity_id, entity_type, spec_id, role,
                     target_file, operation, section: recommended|doubtful,
                     owner, proposed_text, doubt_reason, home_question,
                     card_home, canonical_external}
    dropped_nodes  — только для final/both: [{node, reason}] — узлы, снятые
                     Фазой B как ложные, с причиной

    Здесь перечислены поля, которые читает валидатор; полный служебный
    контракт дельты — в L2-procedure-scaffold-update.md (Шаг 3, Фаза A).

Дельты протокола (entity_type=protocol либо target_file под protocol_path) —
вне ролевой единственности (exempt): S5/B-инварианты дома к ним не применяются.
Протокол — контейнер, не канал раскладки: дельта под protocol_path
обязана иметь entity_type=protocol (иначе S11_protocol_channel), а
protocol-дельты не считаются покрытием не-protocol сущностей — исключены из
covered (A2) и own (S7/S8/S9): сущность «только в протоколе» всплывает как
пропуск покрытия, не как покрытая.

stdout: JSON {"ok": bool, "violations": [{code, message, delta_ids}],
              "warnings": [...] — только если есть; на exit-код не влияют}
exit: 0 — инварианты держатся; 1 — есть нарушения; 2 — вход не разобран.

Только stdlib. Ничего не пишет на диск.
"""

import argparse
import json
import re
import sys

ROLES = {"canonical", "reference", "consequence"}
DISPOSITIONS = {"write", "summary_only", "unclear"}
SECTIONS = {"recommended", "doubtful"}
# Классы файлов вне uniqueness-инварианта: хроника, глоссарий, наблюдения о людях
EXEMPT_CLASSES = {"progress", "glossary", "team"}
# Core-классы: у одной сущности ≤1 canonical-дома СУММАРНО по всем этим классам
# (не по-классово: canonical в active + canonical в overview = дубль; проекция
# в другой класс — это role=reference, не второй canonical).
CORE_CLASSES = {"active", "backlog", "decisions", "overview"}


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
    violations = []
    warnings = []
    # both = инварианты обеих фаз на одном пакете (одноузловой путь)
    cov = phase in ("coverage", "both")
    fin = phase in ("final", "both")

    def add(code, message, delta_ids=(), ph=None):
        if ph and phase == "both":
            message = f"[{ph}] {message}"
        violations.append(
            {"code": code, "message": message, "delta_ids": sorted(delta_ids)}
        )

    def warn(code, message, delta_ids=()):
        warnings.append(
            {"code": code, "message": message, "delta_ids": sorted(delta_ids)}
        )

    entities = payload.get("entities", [])
    deltas = payload.get("deltas", [])
    meeting_nodes = payload.get("meeting_nodes", [])

    protocol_path = norm_path(payload.get("protocol_path")).rstrip("/")

    def under_protocol(d):
        if not protocol_path:
            return False
        return norm_path(d.get("target_file")).startswith(protocol_path + "/")

    # Протокол встречи — exempt-класс: вне ролевой единственности
    def is_protocol(d):
        return d.get("entity_type") == "protocol" or under_protocol(d)

    # S11: протокол — контейнер, не канал раскладки. Protocol-дельта
    # покрывает только сущность типа protocol (E00): для E01+ она не входит
    # ни в own (S7/S8/S9), ни в covered (A2) — поглощение сущности текстом
    # протокола всплывает как пропуск покрытия, не как покрытие.
    protocol_entity_ids = {e.get("id") for e in payload.get("entities", [])
                           if e.get("type") == "protocol"}

    def counts_for_coverage(d):
        return not is_protocol(d) \
            or d.get("entity_id") in protocol_entity_ids

    # --- Структурная валидация (обе фазы) ---
    entity_ids = [e.get("id") for e in entities]
    dup_entities = {i for i in entity_ids if entity_ids.count(i) > 1}
    if dup_entities:
        add("S1", f"дубли id в ростере сущностей: {sorted(dup_entities)}")
    known_entities = set(entity_ids)

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
        if under_protocol(d) and d.get("entity_type") != "protocol":
            add("S11_protocol_channel",
                f"дельта под {protocol_path}/ с entity_type="
                f"{d.get('entity_type')!r}: протокол — контейнер выжимки, не "
                f"канал раскладки — под protocol_path допустима только дельта "
                f"entity_type=protocol (E00); сущность E01+ получает дельту в "
                f"свой целевой файл по обычным правилам", [did])

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
        delta_nodes = {node_of(d.get("target_file", "")) for d in deltas}
        for n in meeting_nodes:
            if n not in delta_nodes:
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
    # согласующего; считать их нарушением = ложный violation на каждом споре.
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
        def tokens(text):
            return {w for w in "".join(
                c if c.isalnum() else " " for c in low_text(text)).split()
                if len(w) >= 4}
        def low_text(text):
            return (text or "").lower()
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
                add("B3", f"canonicalizer сузил множество узлов: потерян {n} — "
                          f"копию меняй на ссылку/следствие; ложный узел фазы A "
                          f"снимай явно через dropped_nodes с причиной",
                    ph="final")
            elif not any(node_of(d.get("target_file", "")) == n
                         and d.get("section") == "doubtful" for d in deltas):
                add("B3", f"узел {n} снят ({dropped[n]}), но его дельты удалены — "
                          f"переведи их в doubtful, снятие должно быть видно "
                          f"согласующему", ph="final")
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
                          "согласующий не отличит спор от непочиненного",
                    [d.get("id", "?")], ph="final")
            if d.get("section") != "doubtful" and d.get("doubt_reason"):
                add("S6", "doubt_reason на non-doubtful дельте", [d.get("id", "?")],
                    ph="final")
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

        # --- S10: протокол встречи (meta Гейта A п.0; phase final/both) ---
        if "protocol_required" not in payload:
            add("S10_meta_missing",
                "в meta пакета нет поля protocol_required (true|false) — на "
                "phase final/both оно обязательно (Гейт A п.0); при "
                "protocol_required=true обязателен и protocol_path", ph="final")
        elif payload.get("protocol_required"):
            if not protocol_path:
                add("S10_meta_missing",
                    "protocol_required=true, но protocol_path пуст или "
                    "отсутствует — укажи каталог протоколов, определённый на "
                    "Гейте A п.0 по клиентскому правилу Шага 0", ph="final")
            else:
                created = [d for d in deltas
                           if d.get("section") == "recommended"
                           and d.get("operation") == "create"
                           and under_protocol(d)
                           and len(d.get("proposed_text") or "") >= 200]
                if not created:
                    near = [d.get("id", "?") for d in deltas
                            if under_protocol(d)]
                    add("S10_protocol_missing",
                        f"protocol_required=true, но в recommended нет "
                        f"create-дельты протокола под {protocol_path}/ с "
                        f"proposed_text ≥ 200 символов (санитарный минимум): "
                        f"doubtful не применяется и не считается, пустышка не "
                        f"проходит — перенеси содержимое принятой выжимки "
                        f"create-дельтой (Гейт A п.0)", near, ph="final")
        else:
            dup = [d.get("id", "?") for d in deltas if under_protocol(d)]
            if dup:
                warn("S10_protocol_duplicate",
                     f"protocol_required=false, но есть дельты под "
                     f"{protocol_path}/ — возможный дубль уже существующего "
                     f"протокола; судит ревью/согласующий", dup)

    return violations, warnings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["coverage", "final", "both"],
                        required=True)
    args = parser.parse_args()
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        json.dump({"ok": False, "violations": [
            {"code": "S0", "message": f"stdin не является валидным JSON: {exc}",
             "delta_ids": []}]}, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 2
    violations, warnings = check(payload, args.phase)
    out = {"ok": not violations, "violations": violations}
    if warnings:
        out["warnings"] = warnings
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main())
