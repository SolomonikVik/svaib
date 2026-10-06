"""Адаптер транскрипта Claude Code: расход одного отрезка запуска скилла.

Транскрипт — JSONL сессии. Ответ модели пишется строкой на блок с одинаковыми `message.id` и
`usage`: вызов модели считается по `message.id` один раз. Отрезок — от блока `Skill` в ответе
модели или от запроса пользователя (команда `/плагин:скилл` или следующий ход запуска) до
следующего блока `Skill` включительно или до нового запроса. Токены ответа, в котором стоит
блок `Skill`, идут отрезку, внутри которого этот ответ дан; блоки после `Skill` в том же ответе —
уже новому. Субагенты отрезка — отдельные строки из их транскриптов `subagents/agent-<id>.jsonl`:
модель, четыре вида токенов, время и скилл пакета, который субагент исполнял. Формат
транскрипта — не контракт хоста: незнакомые строки пропускаются, отсутствующие величины пусты.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os

AGENT_TOOLS = ("Agent", "Task")
USAGE_KEYS = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")


def read(path: str) -> list[dict]:
    return read_from(path, None)


def read_from(path: str, needles) -> list[dict]:
    """Записи с первой строки, где встретился любой из `needles` (id вызова или запроса), —
    длинную сессию на каждом ходе целиком не разбираем. Ни одного не нашли — файл целиком."""
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except (OSError, TypeError):
        return []
    found = [raw.find(str(n).encode()) for n in needles or () if n]
    found = [i for i in found if i >= 0]
    if found:
        raw = raw[raw.rfind(b"\n", 0, min(found)) + 1:]
    entries = []
    for line in raw.decode("utf-8", errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict):
            entries.append(entry)
    return entries


def _ts(entry: dict) -> float | None:
    raw = entry.get("timestamp")
    if not isinstance(raw, str):
        return None
    try:
        return datetime.datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _blocks(entry: dict) -> list[dict]:
    message = entry.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    return [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []


def _text(entry: dict) -> str:
    message = entry.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, str):
        return content
    return "".join(b.get("text", "") for b in _blocks(entry) if b.get("type") == "text")


def _message_id(entry: dict):
    message = entry.get("message")
    return (message.get("id") if isinstance(message, dict) else None) or entry.get("requestId") or entry.get("uuid")


def _turn_start(entry: dict) -> bool:
    """Начало хода: запрос пользователя или ход, начатый хостом (вернулся фоновый субагент,
    пришло сообщение другой сессии), — запись пользователя с собственным `promptId`, не результат
    инструмента. Служебные вставки внутри хода несут `promptId` своего хода."""
    return entry.get("type") == "user" and bool(entry.get("promptId")) and \
        not any(b.get("type") == "tool_result" for b in _blocks(entry))


def _opens_next_call(entry: dict, run: dict, denied: set) -> bool:
    """Блок `Skill`, который открывает свою строку: скилл этого плагина, кроме повтора своего
    скилла после команды и отклонённого хостом вызова. Чужие скиллы своей строки не получают —
    их работа остаётся в этой."""
    for b in _blocks(entry) if entry.get("type") == "assistant" else []:
        if b.get("id") in denied:
            continue
        name = str((b.get("input") or {}).get("skill", "")) if b.get("type") == "tool_use" and b.get("name") == "Skill" else ""
        prefix, _, base = name.partition(":")
        if name and prefix == run.get("plugin") and not (not run.get("tool_use_id") and base == run.get("skill")):
            return True
    return False


def segment(entries: list[dict], run: dict):
    """(строки вызова, id ответа с его блоком `Skill` — токены этого ответа не его, оборван ли
    следующим вызовом).
    None — начало вызова в транскрипте не найдено."""
    start = None
    invoking = None
    if run.get("tool_use_id"):
        start = next((i for i, e in enumerate(entries) if e.get("type") == "assistant" and any(
            b.get("type") == "tool_use" and b.get("id") == run["tool_use_id"] for b in _blocks(e))), None)
        if start is not None:
            invoking = _message_id(entries[start])
    else:
        start = next((i for i, e in enumerate(entries)
                      if _turn_start(e) and e.get("promptId") == run.get("prompt_id")), None)
    if start is None:
        return None
    denied = {b.get("tool_use_id") for e in entries for b in _blocks(e) if b.get("type") == "tool_result" and b.get("is_error")}
    out: list[dict] = [entries[start]] if run.get("by_agent") else []  # запуск субагентом: его вызов — уже отрезок
    cut = False
    for entry in entries[start + 1:]:
        if _turn_start(entry) and entry.get("promptId") != run.get("prompt_id"):
            break
        out.append(entry)
        if _opens_next_call(entry, run, denied):  # строка на блок: дальше — уже следующий вызов
            cut = True
            break
    return out, invoking, cut


def _agent_results(entries: list[dict]) -> dict:
    return {b.get("tool_use_id"): e for e in entries for b in _blocks(e) if b.get("type") == "tool_result"}


def _agent_skill(entries: list[dict], resolve) -> tuple[str, str, str] | None:
    """Скилл пакета, который исполнял субагент: вызов `Skill` или чтение его `SKILL.md` —
    так модули зовут агентом с путём к инструкции. (скилл, путь SKILL.md, способ)."""
    if resolve is None:
        return None
    for entry in entries:
        if entry.get("type") != "assistant":
            continue
        for b in _blocks(entry):
            if b.get("type") != "tool_use":
                continue
            inp = b.get("input") if isinstance(b.get("input"), dict) else {}
            found = resolve("name", inp.get("skill")) if b.get("name") == "Skill" else \
                resolve("file", inp.get("file_path")) if b.get("name") == "Read" else \
                resolve("command", inp.get("command")) if b.get("name") == "Bash" else None
            if found:
                return found[0], found[1], "модель"
    return None


def measure_agent(sub_dir: str, agent_id: str, seen: dict, resolve=None, kind: str = "", depth: int = 0) -> list[dict]:
    """Строки субагента и его потомков. `seen` — сколько ответов агента уже учтено в запуске:
    возобновлённый агент пишет в тот же файл, повторно считаются только новые ответы."""
    entries = read(os.path.join(sub_dir, f"agent-{agent_id}.jsonl"))
    if not entries or depth > 5:
        return []
    if not kind:
        try:
            with open(os.path.join(sub_dir, f"agent-{agent_id}.meta.json"), encoding="utf-8") as f:
                kind = str(json.load(f).get("agentType") or "")
        except (OSError, ValueError, AttributeError):
            kind = ""
    order: list = []
    calls: dict = {}
    for entry in entries:
        message = entry.get("message")
        if entry.get("type") == "assistant" and isinstance(message, dict) and message.get("model") != "<synthetic>":
            mid = _message_id(entry)
            if mid not in calls:
                order.append(mid)
                calls[mid] = None
            if isinstance(message.get("usage"), dict):
                calls[mid] = message["usage"]
    skip = int(seen.get(agent_id) or 0)
    fresh = set(order[skip:])
    seen[agent_id] = len(order)
    out: list[dict] = []
    if fresh:
        models: list[str] = []
        tools: set = set()
        stamps: list[float] = []
        for entry in entries:
            if entry.get("type") != "assistant" or _message_id(entry) not in fresh:
                continue
            stamp = _ts(entry)
            if stamp is not None:
                stamps.append(stamp)
            model = (entry.get("message") or {}).get("model")
            if model and model not in models:
                models.append(model)
            tools.update(b["id"] for b in _blocks(entry) if b.get("type") == "tool_use" and b.get("id"))
        first = next((t for t in (_ts(e) for e in entries) if t is not None), None) if not skip else (min(stamps) if stamps else None)
        known = [calls[m] for m in order if m in fresh]

        def total(key: str) -> int | None:  # счётчика нет хоть в одном ответе — итог неизвестен
            return None if any(u is None or key not in u for u in known) else sum(int(u[key] or 0) for u in known)

        new = [e for e in entries if _message_id(e) in fresh]  # после возобновления агент мог взять другой скилл
        skill = _agent_skill(new, resolve) or _agent_skill(entries, resolve)
        out.append({"id": agent_id, "kind": kind, "skill": skill, "models": models,
                    "input": total(USAGE_KEYS[0]), "output": total(USAGE_KEYS[1]), "cache_read": total(USAGE_KEYS[2]),
                    "cache_write": total(USAGE_KEYS[3]), "turns": len(fresh), "tools": len(tools),
                    "start": first, "last": max(stamps) if stamps else first})
    results = _agent_results(entries)
    for entry in entries:  # субагент может сам звать субагентов: их файлы лежат рядом
        for b in _blocks(entry) if entry.get("type") == "assistant" else []:
            if b.get("type") == "tool_use" and b.get("name") in AGENT_TOOLS:
                res = (results.get(b.get("id")) or {}).get("toolUseResult")
                child = res.get("agentId") if isinstance(res, dict) else None
                if child and child != agent_id:
                    out.extend(measure_agent(sub_dir, child, seen, resolve, depth=depth + 1))
    return out


def _finished(entries: list[dict], agent_id: str) -> bool:
    """Фоновый субагент закончил: хост вставил уведомление о нём со статусом completed."""
    mark = f"<task-id>{agent_id}</task-id>"
    return any(entry.get("type") == "user" and mark in _text(entry) and "<status>completed</status>" in _text(entry)
               for entry in entries)


def measure(entries: list[dict], run: dict, transcript_path: str, resolve=None, final: bool = False,
            seen: dict | None = None) -> dict | None:
    """Расход отрезка; `denied` — хост отклонил вызов, `pending` — фоновый субагент без итога.
    Субагенты — отдельные строки (`agents`), в токены отрезка не входят. `resolve` узнаёт скилл
    пакета по имени, пути `SKILL.md` или команде; `final` — последнее закрытие, фон не ждём;
    `seen` — сколько ответов каждого субагента уже учтено в сессии, дополняется."""
    found = segment(entries, run)
    if found is None:
        return None
    part, invoking, cut = found
    results = _agent_results(entries)
    own = results.get(run.get("tool_use_id")) if run.get("tool_use_id") else None
    if own and any(b.get("is_error") for b in _blocks(own) if b.get("tool_use_id") == run["tool_use_id"]):
        return {"denied": True}
    calls: dict = {}
    answers: set = set()
    models: list[str] = []
    tools: set[str] = set()
    agents: list[str] = []
    version = None
    last = None
    last_answer = None
    for entry in part:
        if entry.get("isSidechain"):
            continue
        version = entry.get("version") or version
        stamp = _ts(entry)
        last = stamp if stamp is not None else last
        message = entry.get("message")
        if entry.get("type") != "assistant" or not isinstance(message, dict):
            continue  # незнакомая запись: пропустить, а не упасть
        last_answer = entry
        model = message.get("model")
        if model and model != "<synthetic>" and model not in models:
            models.append(model)
        if model != "<synthetic>" and _message_id(entry) != invoking:
            answers.add(_message_id(entry))
            if isinstance(message.get("usage"), dict):
                calls[_message_id(entry)] = message["usage"]
        for block in _blocks(entry):
            if block.get("type") == "tool_use" and block.get("id") and block.get("name") != "Skill":
                tools.add(block["id"])
                if block.get("name") in AGENT_TOOLS and block["id"] not in agents:
                    agents.append(block["id"])
    sub_rows: list[dict] = []
    pending = False
    counted: set = set()
    seen = {} if seen is None else seen
    sub_dir = os.path.join(os.path.splitext(transcript_path)[0], "subagents")
    for tool_id in agents:  # результат субагента ищем по всему транскрипту: он приходит позже
        result = (results.get(tool_id) or {}).get("toolUseResult")
        agent_id = result.get("agentId") if isinstance(result, dict) else None
        if not agent_id or agent_id in counted:  # возобновлённый в том же отрезке — один раз
            continue
        counted.add(agent_id)
        if result.get("isAsync") and not _finished(entries, agent_id) and not final:
            pending = True
            continue
        fresh = agent_id not in seen
        found = measure_agent(sub_dir, agent_id, seen, resolve)
        if not found and fresh:  # файла субагента нет: строка есть, расход неизвестен — не ноль
            found = [{"id": agent_id, "kind": "", "skill": None, "models": [], "input": None, "output": None,
                      "cache_read": None, "cache_write": None, "turns": None, "tools": None,
                      "start": None, "last": None}]
            seen[agent_id] = 0
        if result.get("isAsync") and not _finished(entries, agent_id):
            for row in found:
                row["unfinished"] = True  # последнее закрытие, фон ещё работает: учтено то, что есть
        sub_rows.extend(found)

    def total(key: str) -> int | None:
        if len(calls) < len(answers) or any(key not in u for u in calls.values()):  # неизвестно — не ноль
            return None
        return sum(int(u[key] or 0) for u in calls.values())

    return {
        "version": version,
        "models": models,
        "input": total(USAGE_KEYS[0]),
        "output": total(USAGE_KEYS[1]),
        "cache_read": total(USAGE_KEYS[2]),
        "cache_write": total(USAGE_KEYS[3]),
        "turns": len(answers),
        "tools": len(tools),
        "agents": sub_rows,
        "pending": pending,
        "error": bool(last_answer and last_answer.get("isApiErrorMessage")),  # ход кончился ошибкой API
        "last": last,
        "cut": cut,  # вызов кончился вызовом следующего скилла, а не концом хода
    }


def digest(text: str) -> str:
    return hashlib.sha1((text or "").strip().encode("utf-8")).hexdigest()


def has_final_text(entries: list[dict], want: str) -> bool:
    """Последний ответ хода уже в транскрипте — сверка по хэшу его текста целиком."""
    for entry in reversed(entries):
        if entry.get("type") == "assistant" and _text(entry).strip():
            mid = _message_id(entry)
            parts = [_text(e) for e in entries if e.get("type") == "assistant" and _message_id(e) == mid and _text(e)]
            return want in (digest("".join(parts)), digest("\n\n".join(parts)))
    return False
