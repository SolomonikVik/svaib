"""Расход отрезка запуска скилла Codex по локальному rollout.

Граница — turn_id; внутри хода отрезок может начинаться (`from_call`) или кончаться
(`cut_call`) командой, которой модель прочитала `SKILL.md` пакета, — неявный вызов по правилу
самого Codex. token_usage_record считается по response_id; token_count — только проверка
полноты, его нарастающий итог не прибавляется. input_tokens включает оба вида кэша,
output_tokens — reasoning. Несколько явных команд одного хода не получают общий расход.
Субагент — свой rollout рядом (`rollout-*-<thread_id>.jsonl`); его расход в этом ходе —
записи с его thread_id и root_turn_id этого хода. Формат rollout не является стабильным API:
неизвестные величины остаются пустыми.
"""

from __future__ import annotations

import datetime
import glob
import hashlib
import html
import json
import os
import re


def read(path: str) -> list[dict]:
    return read_from(path, None)


def read_from(path, needles) -> list[dict]:
    """Записи с первой строки, где встретился любой из `needles` (turn_id), — многомегабайтный
    rollout на каждом ходе целиком не разбираем. Ни одного не нашли — файл целиком."""
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except (OSError, TypeError):
        return []
    found = [raw.find(str(n).encode()) for n in needles or () if n]
    found = [i for i in found if i >= 0]
    if found:
        raw = raw[raw.rfind(b"\n", 0, min(found)) + 1:]
    return _parse(raw)


def _parse(raw: bytes) -> list[dict]:
    entries = []
    for line in raw.decode("utf-8", errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict):
            entries.append(entry)
    return entries


def head_meta(path) -> dict:
    """session_meta из первых строк rollout: файл целиком ради неё не читаем."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for _ in range(5):
                line = f.readline()
                try:
                    entry = json.loads(line) if line else None
                except ValueError:
                    continue
                if isinstance(entry, dict) and entry.get("type") == "session_meta":
                    return payload(entry)
    except (OSError, TypeError):
        pass
    return {}


MARKERS = (b"SKILL.md", b"scripts", b"SubAgentActivity")


def read_turn(path, turn_id) -> list[dict]:
    """Записи rollout от первого упоминания хода — пусто, если в них нет признака скилла или
    субагента: Stop каждого хода не разбирает многомегабайтный файл целиком."""
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except (OSError, TypeError):
        return []
    at = raw.find(str(turn_id).encode()) if turn_id else -1
    if at < 0:
        return []
    chunk = raw[raw.rfind(b"\n", 0, at) + 1:]
    return _parse(chunk) if any(m in chunk for m in MARKERS) else []


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


def _slice(part: list[dict], run: dict) -> list[dict]:
    """Часть хода от команды чтения скилла (`from_call`) до следующей такой команды (`cut_call`)."""
    def at(call_id):
        return next((i for i, e in enumerate(part) if (e.get("type") == "response_item" and payload(e).get("call_id") == call_id)
                     or (isinstance(payload(e).get("item"), dict) and payload(e)["item"].get("id") == call_id)), None)
    start = at(run["from_call"]) if run.get("from_call") else 0
    end = at(run["cut_call"]) if run.get("cut_call") else None
    return part[start or 0:end if end is not None else len(part)]


SHELL_TOOLS = {"exec", "exec_command", "shell", "shell_command", "local_shell", "unified_exec"}


def _shell_text(p: dict) -> str:
    """Текст вызова инструмента оболочки; у прочих инструментов (сообщение агенту, правка файла)
    упоминание пути — не чтение, неявным вызовом не считается."""
    name = p.get("name") if isinstance(p.get("name"), str) else ""
    return _call_text(p) if name.rsplit(".", 1)[-1] in SHELL_TOOLS else ""


def _call_text(p: dict) -> str:
    value = p.get("arguments") if "arguments" in p else p.get("input")
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False) if value is not None else ""


def implicit_calls(entries: list[dict], turn_id: str, resolve, transcript_path: str | None = None) -> list[tuple]:
    """(call_id, скилл, через субагента, время записи) в порядке хода: команда, которая прочитала `SKILL.md` или запустила скрипт
    скилла пакета, и запуск субагента, который сам исполнял скилл пакета (задание субагенту в
    rollout зашифровано — скилл видно только в его собственном rollout). Первый раз на скилл."""
    part = segment(entries, turn_id) or []
    found: list = []
    names: set = set()
    for e in part:
        p = payload(e)
        skill, call_id, by_agent = None, None, False
        if e.get("type") == "response_item" and p.get("type") in ("function_call", "custom_tool_call"):
            skill, call_id = (resolve("command", _shell_text(p)) if resolve else None), p.get("call_id")
        item = p.get("item") if e.get("type") == "event_msg" else None
        if isinstance(item, dict) and item.get("type") == "SubAgentActivity" and item.get("kind") == "started":
            path = _child_rollout(transcript_path, item.get("agent_thread_id"))
            agent = measure_agent(path, item.get("agent_thread_id"), turn_id, resolve) if path else None
            skill, call_id, by_agent = (agent["skill"][:2] if agent and agent["skill"] else None), item.get("id"), True
        if skill and skill[0] not in names and isinstance(call_id, str):
            names.add(skill[0])
            found.append((call_id, skill, by_agent, _stamp(e)))
    return found


def _child_rollout(transcript_path: str, thread_id: str) -> str | None:
    if not isinstance(transcript_path, str) or not isinstance(thread_id, str) or not re.fullmatch(r"[\w-]+", thread_id):
        return None
    folder = os.path.dirname(transcript_path)
    hits = glob.glob(os.path.join(glob.escape(folder), f"rollout-*-{thread_id}.jsonl"))
    if not hits:  # субагент стартовал после полуночи — папка другого дня
        sessions = os.path.dirname(os.path.dirname(os.path.dirname(folder)))
        hits = glob.glob(os.path.join(glob.escape(sessions), "*", "*", "*", f"rollout-*-{thread_id}.jsonl"))
    return hits[0] if hits else None


def measure_agent(path: str, thread_id: str, turn_id: str, resolve=None) -> dict | None:
    """Расход субагента в ходе родителя `turn_id`. История родителя, скопированная при форке,
    не считается: только ходы субагента, чьи записи несут его thread_id и root_turn_id хода."""
    entries = read(path)
    own_turns: set = set()
    calls: dict = {}
    for e in entries:
        p = payload(e)
        if e.get("type") == "token_usage_record" and p.get("thread_id") == thread_id and p.get("root_turn_id") == turn_id:
            own_turns.add(p.get("turn_id"))
            if isinstance(p.get("response_id"), str) and isinstance(p.get("usage"), dict):
                calls[p["response_id"]] = p["usage"]
        if e.get("type") == "event_msg" and p.get("type") == "task_started" and p.get("root_turn_id") == turn_id \
                and p.get("turn_id") != turn_id:
            own_turns.add(p.get("turn_id"))
    if not own_turns:
        return None
    meta = session_meta(entries)
    spawn = ((meta.get("source") or {}).get("subagent") or {}) if isinstance(meta.get("source"), dict) else {}
    spawn = spawn.get("thread_spawn") if isinstance(spawn, dict) and isinstance(spawn.get("thread_spawn"), dict) else {}
    models: list[str] = []
    tools = 0
    skill = None
    seconds = 0.0
    finished: set = set()
    starts: list[float] = []
    current = None
    for e in entries:
        p = payload(e)
        if e.get("type") in ("turn_context", "event_msg") and p.get("turn_id"):
            current = p["turn_id"] if e.get("type") == "turn_context" or p.get("type") == "task_started" else current
        if current not in own_turns:
            continue
        if e.get("type") == "turn_context" and isinstance(p.get("model"), str) and p["model"] not in models:
            models.append(p["model"])
        if e.get("type") == "event_msg" and p.get("type") == "task_started":
            stamp = _stamp(e)
            if stamp is not None:
                starts.append(stamp)
        if e.get("type") == "event_msg" and p.get("type") in ("task_complete", "turn_aborted") and p.get("turn_id") in own_turns:
            finished.add(p["turn_id"])
            if isinstance(p.get("duration_ms"), (int, float)):
                seconds += p["duration_ms"] / 1000
        if e.get("type") == "response_item" and p.get("type") in ("function_call", "custom_tool_call"):
            tools += 1
            if skill is None and resolve:
                found = resolve("command", _shell_text(p))
                skill = (found[0], found[1], "модель") if found else None
    return {"id": thread_id, "kind": spawn.get("agent_role") or "", "skill": skill, "models": models,
            **_totals(calls), "turns": len(calls) or None, "tools": tools,
            "start": min(starts) if starts else None, "seconds": round(seconds) if finished else None,
            "unfinished": bool(own_turns - finished)}


def _foreign_expansion(part: list[dict], run: dict, resolve=None) -> bool:
    """Хост разрешил совпавшее имя в скилл другого пакета — строку не пишем.
    Вставка <skill> бывает не всегда: в 0.157.1 хост также оставляет чтение модели.
    Явная команда уже подтверждена UserPromptSubmit и проверкой пакета писателем.
    """
    for e in part:
        p = payload(e)
        if e.get("type") != "response_item" or p.get("type") != "message" or p.get("role") != "user":
            continue
        for name, path in re.findall(r"<skill>\s*<name>([^<]+)</name>\s*<path>([^<]+)</path>", _text(p)):
            path = html.unescape(path)
            if name.rsplit(":", 1)[-1] == run["skill"] and os.path.realpath(path) != os.path.realpath(run["skill_path"]) \
                    and not (resolve and resolve("file", path)):  # другая версия этого пакета в кэше — свой
                return True
    return False


def _number(value) -> int | None:
    return value if type(value) is int and value >= 0 else None


def _totals(calls: dict) -> dict:
    """Четыре вида токенов по ответам. input_tokens включает оба вида кэша — обычный ввод после
    их вычитания; неизвестная или противоречивая величина хоть в одном ответе — итог пуст."""
    def total(key: str) -> int | None:
        values = [_number(u.get(key)) for u in calls.values()]
        return sum(values) if values and None not in values else None

    ordinary = []
    for u in calls.values():
        values = [_number(u.get(k)) for k in ("input_tokens", "cached_input_tokens", "cache_write_input_tokens")]
        ordinary.append(values[0] - values[1] - values[2]
                        if None not in values and values[0] >= values[1] + values[2] else None)
    return {"input": sum(ordinary) if ordinary and None not in ordinary else None,
            "output": total("output_tokens"), "cache_read": total("cached_input_tokens"),
            "cache_write": total("cache_write_input_tokens")}


def _stamp(entry: dict) -> float | None:
    raw = entry.get("timestamp")
    try:
        return datetime.datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
    except (AttributeError, TypeError, ValueError):
        return None


def measure(entries: list[dict], run: dict, transcript_path: str, resolve=None, final: bool = False,
            seen: dict | None = None) -> dict | None:
    whole = segment(entries, run.get("prompt_id"))
    if whole is None:
        return None
    part = _slice(whole, run)
    meta = session_meta(entries) or head_meta(transcript_path)  # читали с начала хода — шапки там нет
    source = meta.get("source")
    if isinstance(source, dict) and "subagent" in source:
        return {"denied": True}  # сессия субагента учитывается строкой субагента у родителя
    if _foreign_expansion(part, run, resolve):
        return {"denied": True}
    calls: dict[str, dict] = {}
    tools: dict[str, str] = {}
    models: list[str] = []
    for e in whole:  # модель хода — из его начала, даже если отрезок начат командой посреди хода
        model = payload(e).get("model") if e.get("type") == "turn_context" and payload(e).get("turn_id") == run.get("prompt_id") else None
        if isinstance(model, str) and model not in models:
            models.append(model)
    accounting: set[str] = set()
    last = None
    error = False
    complete = False
    interrupted = False
    for e in part:
        p = payload(e)
        stamp = _stamp(e)
        last = stamp if stamp is not None else last
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

    totals = dict.fromkeys(("input", "output", "cache_read", "cache_write")) if incomplete or ambiguous else _totals(calls)
    children: list[str] = []
    for e in part:  # субагенты хода: запуск и продолжение отмечены SubAgentActivity
        item = payload(e).get("item") if e.get("type") == "event_msg" else None
        child = item.get("agent_thread_id") if isinstance(item, dict) and item.get("type") == "SubAgentActivity" else None
        if isinstance(child, str) and child not in children:
            children.append(child)
    agents: list[dict] = []
    pending = False
    seen = {} if seen is None else seen
    for child in children:
        key = f"codex:{child}:{run.get('prompt_id')}"
        if key in seen:
            continue  # расход субагента в этом ходе уже записан строкой другого отрезка
        seen[key] = 1
        path = _child_rollout(transcript_path, child)
        found = measure_agent(path, child, run.get("prompt_id"), resolve) if path else None
        if found is None:
            found = {"id": child, "kind": "", "skill": None, "models": [], "input": None, "output": None,
                     "cache_read": None, "cache_write": None, "turns": None, "tools": None, "start": None,
                     "seconds": None, "unfinished": True}  # rollout субагента нет — завершение не подтверждено
        pending = pending or (found["unfinished"] and not final)
        agents.append(found)
    return {
        "version": meta.get("cli_version") if isinstance(meta.get("cli_version"), str) else None, "models": models or ([run["model"]] if run.get("model") else []),
        **totals,
        "turns": None if ambiguous or incomplete or not calls else len(calls),
        "tools": None if ambiguous else len(tools),
        "agents": agents,
        "pending": pending, "error": error, "last": last, "cut": bool(run.get("cut_call")),
        "completed": (complete or bool(run.get("stopped_at"))) and not interrupted,
    }
