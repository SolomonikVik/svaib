"""Адаптер транскрипта Claude Code: расход одного вызова скилла.

Транскрипт — JSONL сессии. Ответ модели пишется строкой на блок с одинаковыми `message.id` и
`usage`: вызов модели считается по `message.id` один раз. Отрезок вызова — от блока `Skill` в
ответе модели или от запроса `/плагин:скилл` до следующего блока `Skill` включительно или до
нового запроса пользователя. Токены ответа, в котором стоит блок `Skill`, идут вызову, внутри
которого этот ответ дан; блоки после `Skill` в том же ответе — уже новому вызову. Так
несколько скиллов в ходе делят расход без двойного счёта. Формат транскрипта — не контракт
хоста: незнакомые строки пропускаются, отсутствующие величины остаются пустыми.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os

AGENT_TOOLS = ("Agent", "Task")
USAGE_KEYS = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")


def read(path: str) -> list[dict]:
    entries = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if isinstance(entry, dict):
                    entries.append(entry)
    except OSError:
        return []
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


def _is_prompt(entry: dict) -> bool:
    """Запрос пользователя, а не результат инструмента и не служебная вставка хоста."""
    if entry.get("type") != "user" or entry.get("isMeta") or entry.get("isCompactSummary"):
        return False
    return not any(b.get("type") == "tool_result" for b in _blocks(entry))


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
                      if _is_prompt(e) and e.get("promptId") == run.get("prompt_id")), None)
    if start is None:
        return None
    denied = {b.get("tool_use_id") for e in entries for b in _blocks(e) if b.get("type") == "tool_result" and b.get("is_error")}
    out: list[dict] = []
    cut = False
    for entry in entries[start + 1:]:
        if _is_prompt(entry) and entry.get("promptId") not in (None, run.get("prompt_id")):
            break
        out.append(entry)
        if _opens_next_call(entry, run, denied):  # строка на блок: дальше — уже следующий вызов
            cut = True
            break
    return out, invoking, cut


def _subagent_tokens(path: str) -> int | None:
    calls = {}
    for entry in read(path):
        message = entry.get("message")
        if entry.get("type") == "assistant" and isinstance(message, dict) and isinstance(message.get("usage"), dict):
            calls[_message_id(entry)] = message["usage"]
    if not calls:
        return None
    return sum(int(u.get(k) or 0) for u in calls.values() for k in USAGE_KEYS)


def _finished(entries: list[dict], agent_id: str) -> bool:
    """Фоновый субагент закончил: хост вставил уведомление о нём со статусом completed."""
    mark = f"<task-id>{agent_id}</task-id>"
    return any(entry.get("type") == "user" and mark in _text(entry) and "<status>completed</status>" in _text(entry)
               for entry in entries)


def measure(entries: list[dict], run: dict, transcript_path: str) -> dict | None:
    """Расход вызова; `denied` — хост отклонил вызов, `pending` — фоновый субагент без итога."""
    found = segment(entries, run)
    if found is None:
        return None
    part, invoking, cut = found
    results = {b.get("tool_use_id"): e for e in entries for b in _blocks(e) if b.get("type") == "tool_result"}
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
    sub_tokens: int | None = 0
    pending = False
    counted: set = set()
    for tool_id in agents:  # результат субагента ищем по всему транскрипту: он приходит позже
        result = (results.get(tool_id) or {}).get("toolUseResult")
        agent_id = result.get("agentId") if isinstance(result, dict) else None
        tokens = None
        if agent_id and agent_id in counted:  # возобновлённый субагент пишет в тот же транскрипт — уже учтён
            continue
        counted.add(agent_id)
        if agent_id and result.get("isAsync") and not _finished(entries, agent_id):
            pending = True
        elif agent_id:
            sub_dir = os.path.join(os.path.splitext(transcript_path)[0], "subagents")
            tokens = _subagent_tokens(os.path.join(sub_dir, f"agent-{agent_id}.jsonl"))
            if tokens is None and isinstance(result.get("totalTokens"), int):
                tokens = result["totalTokens"]
        sub_tokens = None if tokens is None or sub_tokens is None else sub_tokens + tokens

    def total(key: str) -> int | None:
        if len(calls) < len(answers):  # у ответа нет usage — расход неизвестен, не ноль
            return None
        return sum(int(u.get(key) or 0) for u in calls.values())

    return {
        "version": version,
        "models": models,
        "input": total(USAGE_KEYS[0]),
        "output": total(USAGE_KEYS[1]),
        "cache_read": total(USAGE_KEYS[2]),
        "cache_write": total(USAGE_KEYS[3]),
        "turns": len(answers),
        "tools": len(tools),
        "agents": len(agents),
        "agent_tokens": sub_tokens,
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
