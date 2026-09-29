"""Расход явного вызова скилла Codex по локальному rollout.

Граница — turn_id, подтверждение — явная $команда во входе UserPromptSubmit.
token_usage_record считается по response_id; token_count — только проверка полноты,
его нарастающий итог не прибавляется. input_tokens включает оба вида кэша,
output_tokens — reasoning. Несколько скиллов одного хода не получают общий расход.
Формат rollout не является стабильным API: неизвестные величины остаются пустыми.
"""

from __future__ import annotations

import datetime
import hashlib
import html
import json
import os
import re


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
    except (OSError, TypeError):
        pass
    return entries


def payload(entry: dict) -> dict:
    value = entry.get("payload")
    return value if isinstance(value, dict) else {}


def session_meta(entries: list[dict]) -> dict:
    return next((payload(e) for e in entries if e.get("type") == "session_meta"), {})


def _text(item: dict) -> str:
    content = item.get("content")
    if not isinstance(content, list):
        return ""
    return "".join(b.get("text", "") for b in content
                   if isinstance(b, dict) and isinstance(b.get("text"), str))


def digest(text: str) -> str:
    return hashlib.sha1((text or "").strip().encode("utf-8")).hexdigest()


def has_final_text(entries: list[dict], want: str) -> bool:
    for entry in reversed(entries):
        p = payload(entry)
        if entry.get("type") == "response_item" and p.get("type") == "message" \
                and p.get("role") == "assistant" and p.get("phase") != "commentary" and _text(p).strip():
            return digest(_text(p)) == want
    return False


def segment(entries: list[dict], turn_id: str) -> list[dict] | None:
    start = next((i for i, e in enumerate(entries)
                  if e.get("type") in ("event_msg", "turn_context")
                  and payload(e).get("turn_id") == turn_id
                  and (e.get("type") == "turn_context" or payload(e).get("type") == "task_started")), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(entries))
                if entries[i].get("type") == "event_msg"
                and payload(entries[i]).get("type") == "task_started"
                and payload(entries[i]).get("turn_id") != turn_id), len(entries))
    return entries[start:end]


def _foreign_expansion(part: list[dict], run: dict) -> bool:
    """Хост разрешил совпавшее имя в скилл другого пакета — строку не пишем.
    Вставка <skill> бывает не всегда: в 0.157.1 хост также оставляет чтение модели.
    Явная команда уже подтверждена UserPromptSubmit и проверкой пакета писателем.
    """
    for e in part:
        p = payload(e)
        if e.get("type") != "response_item" or p.get("type") != "message" or p.get("role") != "user":
            continue
        for name, path in re.findall(r"<skill>\s*<name>([^<]+)</name>\s*<path>([^<]+)</path>", _text(p)):
            if name.rsplit(":", 1)[-1] == run["skill"] and os.path.realpath(html.unescape(path)) != os.path.realpath(run["skill_path"]):
                return True
    return False


def _number(value) -> int | None:
    return value if type(value) is int and value >= 0 else None


def _stamp(entry: dict) -> float | None:
    raw = entry.get("timestamp")
    try:
        return datetime.datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
    except (AttributeError, TypeError, ValueError):
        return None


def measure(entries: list[dict], run: dict, transcript_path: str) -> dict | None:
    part = segment(entries, run.get("prompt_id"))
    if part is None:
        return None
    meta = session_meta(entries)
    source = meta.get("source")
    if isinstance(source, dict) and "subagent" in source:
        return {"denied": True}  # вызов внутри субагента пока не учитывается
    if _foreign_expansion(part, run):
        return {"denied": True}
    calls: dict[str, dict] = {}
    tools: dict[str, str] = {}
    models: list[str] = []
    accounting: set[str] = set()
    last = None
    error = False
    complete = False
    interrupted = False
    for e in part:
        p = payload(e)
        stamp = _stamp(e)
        last = stamp if stamp is not None else last
        if e.get("type") == "turn_context" and p.get("turn_id") == run.get("prompt_id"):
            model = p.get("model")
            if isinstance(model, str) and model not in models:
                models.append(model)
        if e.get("type") == "token_usage_record" and p.get("turn_id") == run.get("prompt_id") \
                and p.get("thread_id", run["session"]) == run["session"]:
            rid, usage = p.get("response_id"), p.get("usage")
            if isinstance(rid, str) and isinstance(usage, dict):
                calls[rid] = usage
        if e.get("type") == "response_item" and p.get("type") in ("function_call", "custom_tool_call"):
            if isinstance(p.get("call_id"), str):
                tools[p["call_id"]] = p.get("name") if isinstance(p.get("name"), str) else ""
        if e.get("type") == "event_msg":
            typ = p.get("type")
            if typ == "token_count" and isinstance(p.get("info"), dict):
                total = p["info"].get("total_token_usage")
                if isinstance(total, dict):
                    accounting.add(json.dumps(total, sort_keys=True))
            if p.get("turn_id") == run.get("prompt_id"):
                complete = complete or typ == "task_complete"
                interrupted = interrupted or typ == "turn_aborted"
                if typ in ("task_complete", "turn_aborted"):
                    error = False  # восстановленная ошибка не делает успешный ход ошибочным
                elif typ in ("error", "task_failed"):
                    error = True
    # Несколько команд в одном ходе имеют общую границу. Распределения по скиллам нет.
    ambiguous = run.get("shared_turn", False)
    incomplete = len(accounting) > len(calls)

    def total(key: str) -> int | None:
        values = [_number(u.get(key)) for u in calls.values()]
        return sum(values) if values and not incomplete and not ambiguous and None not in values else None

    ordinary = []
    for u in calls.values():
        values = [_number(u.get(k)) for k in ("input_tokens", "cached_input_tokens", "cache_write_input_tokens")]
        ordinary.append(values[0] - values[1] - values[2]
                        if None not in values and values[0] >= values[1] + values[2] else None)
    agent_calls = sum(name.rsplit(".", 1)[-1] in ("spawn_agent", "resume_agent") for name in tools.values())
    return {
        "version": meta.get("cli_version") if isinstance(meta.get("cli_version"), str) else None, "models": models or ([run["model"]] if run.get("model") else []),
        "input": sum(ordinary) if ordinary and not incomplete and not ambiguous and None not in ordinary else None,
        "output": total("output_tokens"), "cache_read": total("cached_input_tokens"),
        "cache_write": total("cache_write_input_tokens"),
        "turns": None if ambiguous or incomplete or not calls else len(calls),
        "tools": None if ambiguous else len(tools),
        # Пока нет проверенной связи с дочерними rollout: неизвестные расход и количество
        # уникальных субагентов пусты; отсутствие вызовов субагентов — известный ноль.
        "agents": None if ambiguous or agent_calls else 0,
        "agent_tokens": None if ambiguous or agent_calls else 0,
        "pending": False, "error": error, "last": last, "cut": False,
        "completed": (complete or bool(run.get("stopped_at"))) and not interrupted,
    }
