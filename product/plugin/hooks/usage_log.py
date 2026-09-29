#!/usr/bin/env python3
"""
Учёт использования скиллов Claude Code и Codex: строка в `<пространство>/.svaib/usage/<хост>.md` на вызов.

    usage_log.py skill    # PreToolUse matcher Skill — скилл вызвала модель
    usage_log.py prompt   # UserPromptSubmit — `/плагин:скилл` Claude, `$скилл` Codex; закрывает прошлые вызовы
    usage_log.py stop     # Stop — ход закончен, вызовы хода помечаются завершёнными
    usage_log.py end      # SessionEnd — закрывает всё открытое

Строка — вызов скилла до конца хода, в котором он вызван; следующие ходы многоходового скилла
пока не учитываются, поэтому `этап` пуст. Пишется строка не на Stop, а при следующем запросе
или конце сессии: к Stop хост ещё не дописал последний ответ в транскрипт, а другой Stop-хук
может вернуть модель в работу в том же ходе. Вызов без Stop своего хода — `оборван`.

Считаются только скиллы этого плагина: имя `<плагин>:<скилл>` и `skills/<скилл>/SKILL.md` в
установленном пакете — новые скиллы подхватываются без настроек. Вне готового пространства
(`hook_space.ready_usage_root`) обработчик выходит, не читая транскрипт и ничего не создавая.
Состояние открытых вызовов — вне пространства, файл на сессию. Сбой — stderr и код 0.
`кто` — `subject` из кэша идентичности хука карты (`space_map.read_cache`, тот же ключ, срок не
важен) на момент вызова скилла, хранится в состоянии вызова; нет записи — клетка пустая.
В Codex `кто` пуст: этот кэш привязан к аккаунту Claude. Только явные команды;
несколько команд одного хода получают строки без распределения общего расхода.
"""
from __future__ import annotations

import contextlib
import datetime
import json
import os
import re
import sys
import time

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HOOK_DIR)
try:
    import hook_space
    import usage_claude
except ImportError:  # неполная поставка: main выходит с кодом 0
    hook_space = usage_claude = None

try:
    import usage_codex
except ImportError:
    usage_codex = None  # отсутствие нового адаптера не отключает учёт Claude

try:
    import fcntl
    msvcrt = None
except ImportError:  # Windows
    fcntl = None
    import msvcrt

HEADER = ("| дата | скилл | версия | этап | харнес | модель | ОС | машина | кто | материал ток | ток ввод "
          "| ток вывод | кэш чтение | кэш запись | ходов | инстр | субаг | субаг ток | сек | исход | прогон | оценка |")
SID_RE = re.compile(r"[^A-Za-z0-9_.-]")
SLASH_RE = re.compile(r"\s*/([\w.-]+:[\w.-]+)(?:\s|$)")
FLUSH_WAIT = 2.0  # секунд ждать последний ответ хода в транскрипте
MAX_MISSES = 3  # закрытий, после которых вызов без начала в транскрипте снимается
PENDING_TTL = 3600  # секунд ждать итог фонового субагента, прежде чем писать строку без его токенов
STATE_TTL = 7 * 86400  # пустые файлы состояния старше — удаляются
CLOSE_BUDGET = 5.0  # секунд на закрытие: остальное — следующему событию, до тайм-аута хука (10 с)
LOCK_WAIT = 2.0  # секунд ждать чужую блокировку файла, дальше — отказ и повтор следующим событием
ORPHAN_AGE = 3600  # секунд без движения — сессия считается закрытой без SessionEnd
LOG_LIMIT = 1_000_000  # байт лога, дальше — ротация в .1
NAME_RE = re.compile(r"^[A-Za-z0-9][\w.-]*$")


def log(outcome: str, **kv) -> None:
    try:
        os.makedirs(hook_space.state_dir(), exist_ok=True)
        rec = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "outcome": outcome, **kv}
        path = os.path.join(hook_space.state_dir(), "usage-hook.log")
        if os.path.exists(path) and os.path.getsize(path) > LOG_LIMIT:
            os.replace(path, path + ".1")
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


@contextlib.contextmanager
def locked(path: str, mode: str):
    """Исключительная блокировка файла на время работы; снимается закрытием."""
    with open(path, mode, encoding="utf-8") as f:
        deadline = time.time() + LOCK_WAIT
        while True:  # без бесконечного ожидания: хук убьют по тайм-ауту посреди записи
            try:
                if fcntl:
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                else:
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                if time.time() > deadline:
                    raise TimeoutError(f"блокировка {os.path.basename(path)} занята")
                time.sleep(0.05)
        yield f


def state_path(session_id: str) -> str:
    return os.path.join(hook_space.state_dir(), "usage", SID_RE.sub("_", session_id)[:80] + ".json")


def has_runs(session_id) -> bool:
    """Быстрая проверка без блокировки и без чтения транскрипта: есть ли открытые вызовы."""
    try:
        return isinstance(session_id, str) and bool(session_id) and os.path.getsize(state_path(session_id)) > 0
    except OSError:
        return False


@contextlib.contextmanager
def runs_of(session_id: str):
    """Открытые вызовы сессии под блокировкой. Файл не удаляется, а опустошается: удаление
    под блокировкой дало бы второму хуку старый список на отвязанном файле."""
    path = state_path(session_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with locked(path, "a+") as f:
        f.seek(0)
        try:
            runs = json.loads(f.read() or "[]")
        except ValueError:
            runs = []
        try:
            yield runs
        finally:  # записанное до сбоя не повторится: состояние сохраняется всегда
            f.seek(0)
            f.truncate()
            if runs:
                f.write(json.dumps(runs, ensure_ascii=False))


def sweep_state(current: str) -> None:
    """Пустые файлы старых сессий — удалить; вызовы сессии, закрытой без SessionEnd (терминал
    закрыли, процесс убит), — дописать. Одна такая сессия за раз: хук не должен тормозить."""
    folder = os.path.join(hook_space.state_dir(), "usage")
    try:
        names = os.listdir(folder)
    except OSError:
        return
    orphan = None
    for name in names:
        path = os.path.join(folder, name)
        try:
            age = time.time() - os.path.getmtime(path)
            size = os.path.getsize(path)
            if name.endswith(".json") and size == 0 and age > STATE_TTL:
                os.remove(path)
            elif name.endswith(".json") and size and age > ORPHAN_AGE and orphan is None:
                with open(path, encoding="utf-8") as f:
                    runs = json.load(f)
                sid = runs[0].get("session") if runs and isinstance(runs[0], dict) else None
                if isinstance(sid, str) and sid != current:
                    orphan = {"session_id": sid, "transcript_path": runs[-1].get("transcript")}
        except (OSError, ValueError, AttributeError):
            continue
    if orphan:
        close_runs(orphan)


def plugin_root() -> str:
    return os.environ.get("CLAUDE_PLUGIN_ROOT") or os.environ.get("PLUGIN_ROOT") or os.path.dirname(HOOK_DIR)


def turn_key(ev: dict):
    return ev.get("turn_id") or ev.get("prompt_id")


def open_codex_runs(ev: dict) -> None:
    """Только явные $команды скиллов этого пакета. Чтение SKILL.md вызовом не считаем."""
    if usage_codex is None or ev.get("agent_id") or not isinstance(ev.get("turn_id"), str):
        return
    sid = ev.get("session_id")
    if not isinstance(sid, str) or not sid:
        return
    root = hook_space.ready_usage_root(ev, use_claude_env=False)
    if not root:
        return  # до чтения rollout и создания состояния
    try:
        with open(os.path.join(plugin_root(), ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
            own = json.load(f).get("name")
    except (OSError, ValueError, AttributeError):
        return
    selected = {}
    for name in re.findall(r"(?<![\w\\$])\$([A-Za-z0-9][\w.-]*(?::[\w.-]+)?)(?![\w:.-])", ev.get("prompt") or ""):
        qualified = name if ":" in name else f"{own}:{name}"
        skill = plugin_skill(qualified)
        if not skill and qualified.endswith("."):
            skill = plugin_skill(qualified.rstrip("."))  # пунктуация после команды; точное имя имеет приоритет
        if skill:
            selected[skill[0]] = skill[1]
    if not selected:
        return
    entries = usage_codex.read(ev.get("transcript_path"))
    meta = usage_codex.session_meta(entries)
    if isinstance(meta.get("source"), dict) and "subagent" in meta["source"]:
        return
    # Якорь Codex — исходный cwd сессии в rollout. Смена cwd не переносит учёт в другую базу.
    original = meta.get("cwd")
    anchored = hook_space.ready_usage_root({"cwd": original}, use_claude_env=False) if isinstance(original, str) else None
    if not anchored or os.path.realpath(anchored) != os.path.realpath(root):
        return
    # Кэш карты привязан к аккаунту Claude, не Codex: чужую идентичность не переносим.
    subject = ""
    with runs_of(sid) as runs:
        for name, path in selected.items():
            key = f"codex:{ev['turn_id']}:{name}"
            if any(r.get("key") == key for r in runs):
                continue
            runs.append({"key": key, "session": sid, "skill": name, "plugin": own,
                         "skill_path": path, "version": skill_version(path),
                         "root": root, "root_real": os.path.realpath(root), "prompt_id": ev['turn_id'],
                         "start": time.time(), "transcript": ev.get("transcript_path"),
                         "harness": "codex", "model": ev.get("model"), "who": subject,
                         "shared_turn": False})
            log("open", skill=name, session=sid)
        peers = [r for r in runs if r.get("harness") == "codex" and r.get("prompt_id") == ev["turn_id"]]
        if len(peers) > 1:
            for r in peers:
                r["shared_turn"] = True  # команды могут прийти разными событиями одного хода
    sweep_state(sid)


def plugin_skill(name) -> tuple[str, str] | None:
    """(`скилл`, путь SKILL.md) для скилла этого плагина, иначе None."""
    if not isinstance(name, str) or ":" not in name:
        return None
    prefix, _, base = name.partition(":")
    if not NAME_RE.match(base):
        return None
    try:
        with open(os.path.join(plugin_root(), ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
            own = json.load(f).get("name")
    except (OSError, ValueError, AttributeError):
        return None
    path = os.path.join(plugin_root(), "skills", base, "SKILL.md")
    return (base, path) if prefix == own and os.path.isfile(path) else None


def skill_version(path: str) -> str:
    """Версия из шапки SKILL.md; версию плагина за неё не выдаём."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read(4000)
    except OSError:
        return ""
    head = text.split("\n---", 1)[0] if text.startswith("---") else ""
    m = re.search(r"^\s*version:\s*[\"']?([^\"'\s]+)", head, re.M)
    return m.group(1) if m else ""


def open_run(ev: dict, name, key: str, tool_use_id: str | None = None) -> None:
    skill = plugin_skill(name)
    sid = ev.get("session_id")
    if not skill or not isinstance(sid, str) or not sid or ev.get("agent_id"):
        return  # скилл внутри субагента: его ход в транскрипте субагента — пока не считаем
    root = hook_space.ready_usage_root(ev)
    if not root:
        return
    run = {"key": key, "session": sid, "skill": skill[0], "plugin": name.partition(":")[0],
           "version": skill_version(skill[1]), "root": root, "root_real": os.path.realpath(root),
           "prompt_id": ev.get("prompt_id"), "tool_use_id": tool_use_id, "start": time.time(),
           "transcript": ev.get("transcript_path"), "cowork": os.environ.get("CLAUDE_CODE_IS_COWORK") == "1"}
    with runs_of(sid) as runs:
        # команда и сразу за ней Skill того же скилла — один вызов; после другого скилла — новый
        same_turn = [r for r in runs if r.get("prompt_id") == run["prompt_id"]]
        if any(r.get("key") == key for r in runs) or (same_turn and not same_turn[-1].get("tool_use_id")
                                                      and same_turn[-1].get("skill") == skill[0]):
            return
        run["who"] = who(root)  # кто запустил — на момент вызова: к записи строки аккаунт мог смениться
        runs.append(run)
    log("open", skill=skill[0], session=sid)
    sweep_state(sid)


def host() -> str:
    import hashlib
    import socket  # только при записи строки: пустой выход не платит за импорт

    raw = (socket.gethostname() or "host").split(".")[0]
    name = re.sub(r"[^a-z0-9-]+", "-", raw.lower()).strip("-")
    # имя не латиницей: у разных машин должны быть разные файлы
    return name if name and name == raw.lower() else (name + "-" if name else "host-") + hashlib.sha1(raw.encode()).hexdigest()[:6]


def os_name() -> str:
    import platform  # platform тянет subprocess: ~15 мс на каждом хуке

    system = platform.system()
    if system == "Darwin":
        return ("macOS " + platform.mac_ver()[0]).strip()
    if system == "Linux":
        return "Linux " + ".".join(platform.release().split(".")[:2])
    return f"{system} {platform.release()}".strip()


def who(root: str) -> str:
    """`subject` пользователя из кэша хука карты: ключ — email аккаунта Claude и корень базы.
    Нет записи, чужой корень, другой аккаунт, сбой — пусто: человека не угадываем."""
    try:
        from pathlib import Path

        import space_map  # генератор карты лежит рядом с хуком; грузится только при открытии вызова

        rec = space_map.read_cache(space_map.account_email(), Path(root))
        return rec["subject"] if rec else ""  # срок не нужен: subject_id неизменен, ключ — аккаунт и база
    except Exception as e:  # noqa: BLE001 — без `кто` строка всё равно пишется
        log("who failed", error=f"{type(e).__name__}: {e}")
        return ""


def cell(value) -> str:
    return "" if value is None else " ".join(str(value).replace("|", "/").split())


def row(run: dict, m: dict, session_id: str) -> str:
    start = datetime.datetime.fromtimestamp(run["start"]).astimezone()
    stamp = start.strftime("%Y-%m-%d %H:%M%z")
    end = (m["last"] if m["cut"] else run.get("stopped_at") or m["last"]) or run["start"]
    harness = "cowork" if run.get("cowork") else ((run.get("harness") or "claude-code") + " " + (m["version"] or "")).strip()
    done = m.get("completed", bool(run.get("stopped_at")))
    outcome = "ошибка" if m["error"] else ("завершён" if done else "оборван")
    cells = [stamp[:-2] + ":" + stamp[-2:], run["skill"], run.get("version"), "", harness, " + ".join(m["models"]),
             os_name(), host(), run.get("who"), "", m["input"], m["output"], m["cache_read"], m["cache_write"],
             m["turns"], m["tools"], m["agents"], m["agent_tokens"], max(0, round(end - run["start"])), outcome,
             session_id[:8], ""]
    return "| " + " | ".join(cell(c) for c in cells) + " |"


def append(root: str, line: str) -> bool:
    usage = os.path.join(root, ".svaib", "usage")
    path = os.path.join(usage, host() + ".md")
    with locked(path, "a+") as f:
        f.seek(0)
        head = f.read(4096)  # шапка — в начале файла, строки читать незачем
        if not head:
            f.write(f'---\ntitle: "usage — {host()}"\n---\n\n{HEADER}\n|' + "---|" * HEADER.count(" | ") + "---|\n")
        elif HEADER not in head:
            return False  # чужая шапка: не дописываем в таблицу другого формата
        else:
            with open(path, "rb") as raw:  # последний байт: текстовый seek мог бы встать внутрь символа
                raw.seek(-1, os.SEEK_END)
                if raw.read(1) != b"\n":
                    f.write("\n")
        f.write(line + "\n")
    return True


def close_runs(ev: dict, keep_prompt: str | None = None) -> None:
    """Пишет строки по вызовам прошлых ходов; вызовы хода `keep_prompt` остаются открытыми.
    Вызов снимается с учёта только после записи строки или явного отказа — повтор безопасен."""
    sid = ev.get("session_id")
    if not has_runs(sid):
        return  # быстрый выход: открытых вызовов нет, транскрипт не читаем
    with runs_of(sid) as runs:
        closing = [r for r in runs if keep_prompt is None or r.get("prompt_id") != keep_prompt]
        for run in list(closing):
            if not usage_root_ready(run):
                closing.remove(run)
                runs.remove(run)
                log("space changed", skill=run["skill"], session=sid)
        if not closing:
            return  # учёт выключен или корень изменён: rollout не читаем
        transcript = ev.get("transcript_path") or closing[-1].get("transcript") or ""
        adapter = usage_codex if closing[-1].get("harness") == "codex" else usage_claude
        if adapter is None:
            return  # неполная поставка: состояние дождётся исправленного адаптера
        entries = adapter.read(transcript)
        # ждём последний ответ только хода, который кончился сейчас: сверка один раз на вызов;
        # на SessionEnd не ждём — хост даёт ему короткий тайм-аут, а транскрипт к нему дописан
        final = next((r["final"] for r in reversed(closing) if r.get("final")), None) if keep_prompt else None
        for r in closing:
            r["final"] = None
        deadline = time.time() + FLUSH_WAIT
        while final and not adapter.has_final_text(entries, final) and time.time() < deadline:
            time.sleep(0.1)
            entries = adapter.read(transcript)
        if adapter is usage_claude and isinstance(ev.get("prompt"), str):  # запрос этого события хост пишет в транскрипт позже хука
            entries.append({"type": "user", "promptId": ev.get("prompt_id"), "message": {"content": ev["prompt"]}})
        begun = time.time()
        for run in closing:
            if time.time() - begun > CLOSE_BUDGET:
                break  # не успеть до тайм-аута хука — оставшиеся закроет следующее событие
            try:
                outcome = close_one(run, entries, transcript, sid, final_close=keep_prompt is None)
            except Exception as e:  # noqa: BLE001 — один сбойный вызов не держит остальные
                outcome = f"error: {type(e).__name__}: {e}"
            if outcome in ("write", "denied", "header mismatch", "space changed"):
                runs.remove(run)
            elif outcome != "pending":
                run["misses"] = run.get("misses", 0) + 1
                # сбой записи на SessionEnd не теряет строку: вызов дозакроет уборка сирот
                if run["misses"] >= MAX_MISSES or (keep_prompt is None and outcome == "start not in transcript"):
                    runs.remove(run)
            log(outcome, skill=run["skill"], session=sid)


def usage_root_ready(run: dict) -> bool:
    return os.path.isfile(os.path.join(run["root"], ".svaib", "usage", "README.md")) and \
        os.path.realpath(run["root"]) == run.get("root_real", os.path.realpath(run["root"]))


def close_one(run: dict, entries: list[dict], transcript: str, sid: str, final_close: bool) -> str:
    adapter = usage_codex if run.get("harness") == "codex" else usage_claude
    m = adapter.measure(entries, run, transcript)
    if m is None:
        return "start not in transcript"
    if m.get("denied"):
        return "denied"
    if m["pending"] and not final_close and time.time() - run["start"] < PENDING_TTL:
        return "pending"  # фоновый субагент ещё без итога — строка подождёт следующего события
    if not usage_root_ready(run):
        return "space changed"  # путь теперь ведёт в другую базу или учёт выключен — не пишем
    return "write" if append(run["root"], row(run, m, sid)) else "header mismatch"


def mark_stopped(ev: dict) -> None:
    sid = ev.get("session_id")
    if not has_runs(sid):
        return
    with runs_of(sid) as runs:
        for run in runs:
            if run.get("prompt_id") == turn_key(ev):
                run["stopped_at"] = time.time()  # повторный Stop того же хода сдвигает конец
                run["final"] = usage_claude.digest(ev.get("last_assistant_message") or "") \
                    if (ev.get("last_assistant_message") or "").strip() else None


def run(mode: str, ev: dict) -> None:
    if mode == "skill" and ev.get("tool_name") == "Skill":
        ti = ev.get("tool_input") or {}
        open_run(ev, ti.get("skill"), "tool:" + str(ev.get("tool_use_id")), ev.get("tool_use_id"))
    elif mode == "prompt":
        close_runs(ev, keep_prompt=turn_key(ev))
        if ev.get("turn_id"):
            open_codex_runs(ev)
            return
        m = SLASH_RE.match(ev.get("prompt") or "")
        if m:
            open_run(ev, m.group(1), "prompt:" + str(ev.get("prompt_id")))
    elif mode == "stop":
        mark_stopped(ev)
    elif mode == "end":
        close_runs(ev)


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if hook_space is None or usage_claude is None:
        print("usage_log: нет hook_space.py или usage_claude.py рядом с хуком", file=sys.stderr)
        sys.exit(0)
    try:
        raw = sys.stdin.read()
        ev = json.loads(raw) if raw.strip() else {}
        if isinstance(ev, dict):
            run(mode, ev)
    except Exception as e:  # noqa: BLE001 — учёт не имеет права уронить сессию
        log("error", mode=mode, error=f"{type(e).__name__}: {e}")
        print(f"usage_log: {type(e).__name__}: {e}", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
