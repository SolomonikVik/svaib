#!/usr/bin/env python3
"""
Учёт использования скиллов Claude Code и Codex: строки в `<пространство>/.svaib/usage/<хост>.md`.

    usage_log.py skill    # PreToolUse Skill — скилл вызвала модель; Agent/Task — субагенту дали SKILL.md пакета
    usage_log.py prompt   # UserPromptSubmit — `/плагин:скилл` Claude, `$скилл` Codex, следующий ход запуска
    usage_log.py stop     # Stop — ход закончен; в Codex здесь же находится скилл, прочитанный моделью
    usage_log.py end      # SessionEnd — закрывает всё открытое

Запуск — работа скилла от вызова до вызова другого скилла командой, чужой команды, паузы
дольше суток или конца сессии: конца работы скилла хост не сообщает, поэтому хвост сессии
после скилла может попасть в его запуск — строка на ход показывает, где это случилось. Строка — отрезок запуска: ход основной сессии или
субагент; у всех строк запуска общий `запуск`, у всех строк сессии — `сессия`, поэтому
строки параллельных сессий, лёгшие вперемешку, собираются обратно. Скилл, который модель
вызвала внутри открытого запуска, — вложенный: его отрезок в том же запуске. Токены строки —
только её собственные: расход запуска — сумма его строк.

Строка пишется не на Stop, а при следующем запросе или конце сессии: к Stop хост ещё не
дописал последний ответ в транскрипт, а другой Stop-хук может вернуть модель в работу в том
же ходе. Отрезок без Stop своего хода — `оборван`.

Считаются только скиллы этого плагина: имя `<плагин>:<скилл>`, `skills/<скилл>/SKILL.md` в
установленном пакете или чтение этого файла (правило самого Codex для неявного вызова) —
новые скиллы подхватываются без настроек. Вне готового пространства
(`hook_space.ready_usage_root`) обработчик выходит, не читая транскрипт и ничего не создавая.
Состояние открытых отрезков — вне пространства, файл на сессию. Сбой — stderr и код 0.
`кто` — `subject` из кэша идентичности хука карты (`space_map.read_cache`, тот же ключ, срок не
важен) на момент открытия запуска; нет записи — клетка пустая. В Codex `кто` пуст: этот кэш
привязан к аккаунту Claude.
"""
from __future__ import annotations

import contextlib
import datetime
import hashlib
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

HEADER = ("| дата | сессия | запуск | этап | скилл | версия | способ | харнес | модель | ОС | машина | кто "
          "| материал ток | ток ввод | ток вывод | кэш чтение | кэш запись | ходов | инстр | сек | исход | оценка |")
SID_RE = re.compile(r"[^A-Za-z0-9_.-]")
SLASH_RE = re.compile(r"\s*/([\w.-]+:[\w.-]+)(?:\s|$)")
FLUSH_WAIT = 2.0  # секунд ждать последний ответ хода в транскрипте
MAX_MISSES = 3  # закрытий, после которых отрезок без начала в транскрипте снимается
PENDING_TTL = 3600  # секунд ждать итог фонового субагента, прежде чем писать то, что есть
IDLE_CLOSE = 86400  # секунд паузы, после которой запуск кончен: ответ на вопрос скилла приходит и через часы
STATE_TTL = 7 * 86400  # пустые файлы состояния старше — удаляются
CLOSE_BUDGET = 5.0  # секунд на закрытие: остальное — следующему событию, до тайм-аута хука (10 с)
LOCK_WAIT = 2.0  # секунд ждать чужую блокировку файла, дальше — отказ и повтор следующим событием
ORPHAN_AGE = 3600  # секунд без движения — сессия считается закрытой без SessionEnd
LOG_LIMIT = 1_000_000  # байт лога, дальше — ротация в .1
NAME_RE = re.compile(r"^[A-Za-z0-9][\w.-]*$")
SKILL_FILE_RE = re.compile(r"""([^\s'"`;|&<>()]*[/\\]skills[/\\]([A-Za-z0-9][\w.-]*)[/\\](?:SKILL\.md|scripts[/\\]))""")
FOREIGN_SLASH_RE = re.compile(r"\s*/[A-Za-z][\w.-]*(?::[\w.-]+)?(?:\s|$)")  # команда, а не путь вроде /etc/hosts
FOREIGN_CODEX_RE = re.compile(r"\s*\$[A-Za-z][\w.-]*(?::[\w.-]+)?(?![\w:.-])")
COMMAND = "команда"
MODEL = "модель"


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


def has_state(session_id) -> bool:
    """Быстрая проверка без блокировки и без чтения транскрипта: есть ли открытые отрезки или запуск."""
    try:
        return isinstance(session_id, str) and bool(session_id) and os.path.getsize(state_path(session_id)) > 0
    except OSError:
        return False


class State(dict):
    """Состояние сессии; `save()` сохраняет его, не отпуская блокировку."""
    save = None


@contextlib.contextmanager
def state_of(session_id: str):
    """Состояние сессии под блокировкой: `runs` — открытые отрезки, `launch` — открытый запуск,
    `agents_seen` — учтённые ответы субагентов сессии. Файл не удаляется, а опустошается: удаление
    под блокировкой дало бы второму хуку старое состояние на отвязанном файле."""
    path = state_path(session_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with locked(path, "a+") as f:
        f.seek(0)
        try:
            state = json.loads(f.read() or "{}")
        except ValueError:
            state = {}
        if isinstance(state, list):  # состояние плагина 0.3: только список вызовов
            state = {"runs": state}
        state = State(state if isinstance(state, dict) else {})
        runs = state.get("runs")  # битая запись не должна ронять каждый следующий хук сессии
        state["runs"] = [r for r in runs if isinstance(r, dict) and isinstance(r.get("root"), str)] \
            if isinstance(runs, list) else []

        def save():
            f.seek(0)
            f.truncate()
            if any(state.get(k) for k in ("runs", "launch", "agents_seen", "no_flush")):
                f.write(json.dumps(state, ensure_ascii=False))
            f.flush()

        state.save = save
        try:
            yield state
        finally:  # записанное до сбоя не повторится: состояние сохраняется всегда
            save()


def sweep_state(current: str) -> None:
    """Пустые файлы старых сессий — удалить; отрезки сессии, закрытой без SessionEnd (терминал
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
                    state = json.load(f)
                runs = state if isinstance(state, list) else state.get("runs") or []
                launch = None if isinstance(state, list) else state.get("launch")
                last = runs[-1] if runs and isinstance(runs[-1], dict) else launch if isinstance(launch, dict) else {}
                sid = last.get("session")
                if not isinstance(sid, str) or sid == current:
                    continue
                transcript = last.get("transcript")
                if isinstance(transcript, str) and os.path.exists(transcript) \
                        and time.time() - os.path.getmtime(transcript) <= ORPHAN_AGE:
                    continue  # долгий ход без событий хука: сессия жива, её транскрипт растёт
                if runs:  # отрезки молчащей сессии дописать; её запуск живёт до своей паузы
                    orphan = {"session_id": sid, "transcript_path": last.get("transcript")}
                elif age > IDLE_CLOSE:  # запуск истёк, отрезков нет — состояние сессии больше не нужно
                    with state_of(sid) as st:
                        if not st["runs"] and live_launch(st, time.time()) is None:
                            st.clear()
                            st["runs"] = []
        except (OSError, ValueError, AttributeError):
            continue
    if orphan:
        close_runs(orphan, keep_launch=True)


def plugin_root() -> str:
    return os.environ.get("CLAUDE_PLUGIN_ROOT") or os.environ.get("PLUGIN_ROOT") or os.path.dirname(HOOK_DIR)


def plugin_name(root: str | None = None) -> str | None:
    try:
        with open(os.path.join(root or plugin_root(), ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
            name = json.load(f).get("name")
        return name if isinstance(name, str) else None
    except (OSError, ValueError, AttributeError):
        return None


def is_codex(ev: dict) -> bool:
    """Codex: `turn_id` во входе и rollout транскриптом. Одного поля мало — хост добавляет поля."""
    path = ev.get("transcript_path")
    return bool(ev.get("turn_id")) and isinstance(path, str) and os.path.basename(path).startswith("rollout")


def turn_key(ev: dict):
    return ev.get("turn_id") if is_codex(ev) else ev.get("prompt_id")


def plugin_skill(name) -> tuple[str, str] | None:
    """(`скилл`, путь SKILL.md) для скилла этого плагина, иначе None."""
    if not isinstance(name, str) or ":" not in name:
        return None
    prefix, _, base = name.partition(":")
    if not NAME_RE.match(base):
        return None
    path = os.path.join(plugin_root(), "skills", base, "SKILL.md")
    return (base, path) if prefix == plugin_name() and os.path.isfile(path) else None


def skill_by_file(path) -> tuple[str, str] | None:
    """Скилл по пути его `SKILL.md` или скрипта: этот пакет или другая его версия рядом в кэше хоста —
    модуль, который зовут агентом, читает инструкцию по пути из пакета, где его вызвали."""
    if not isinstance(path, str) or not path or "\0" in path:
        return None
    m = SKILL_FILE_RE.search(path)
    if not m or not NAME_RE.match(m.group(2)):
        return None
    head = m.group(1)
    base_dir = os.path.normcase(os.path.realpath(os.path.expanduser(head[:head.replace("\\", "/").rfind("/skills/")])))
    own = os.path.normcase(os.path.realpath(plugin_root()))
    same = base_dir == own or (os.path.dirname(base_dir) == os.path.dirname(own)
                               and plugin_name(base_dir) == plugin_name(own) is not None)
    skill_md = os.path.join(base_dir, "skills", m.group(2), "SKILL.md")
    return (m.group(2), skill_md) if same and os.path.isfile(skill_md) else None


def resolve_skill(kind: str, value) -> tuple[str, str] | None:
    """Адаптерам: скилл пакета по имени вызова, пути файла или тексту команды оболочки."""
    if kind == "name":
        return plugin_skill(value)
    if kind == "file":
        return skill_by_file(value)
    if kind == "command" and isinstance(value, (str, list)):
        text = value if isinstance(value, str) else " ".join(str(v) for v in value)
        for m in SKILL_FILE_RE.finditer(text):
            found = skill_by_file(m.group(1))
            if found:
                return found
    return None


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


def live_launch(state: dict, now: float) -> dict | None:
    """Открытый запуск, если пауза после его последнего хода не дольше IDLE_CLOSE."""
    launch = state.get("launch")
    if isinstance(launch, dict) and now - (launch.get("last") or launch.get("start") or 0) <= IDLE_CLOSE:
        return launch
    state["launch"] = None
    return None


def new_launch(state: dict, ev: dict, key: str, skill: tuple[str, str], plugin: str, root: str, method: str,
               harness: str | None = None) -> dict:
    sid = ev["session_id"]
    launch = {"id": hashlib.sha1(f"{sid}:{key}".encode()).hexdigest()[:8], "session": sid,
              "skill": skill[0], "skill_path": skill[1], "version": skill_version(skill[1]), "plugin": plugin,
              "method": method, "root": root, "root_real": os.path.realpath(root), "turn": 1,
              "start": time.time(), "last": time.time(), "transcript": ev.get("transcript_path"),
              "who": "" if harness == "codex" else who(root),  # кто — на момент вызова: к записи аккаунт мог смениться
              "cowork": os.environ.get("CLAUDE_CODE_IS_COWORK") == "1", "harness": harness, "key": key}
    state["launch"] = launch
    return launch


def segment_of(launch: dict, ev: dict, key: str, skill: tuple[str, str] | None = None, method: str | None = None,
               **extra) -> dict:
    """Открытый отрезок запуска: скилл запуска или вложенный."""
    skill = skill or (launch["skill"], launch["skill_path"])
    run = {"key": key, "session": launch["session"], "launch": launch["id"], "turn": launch["turn"],
           "skill": skill[0], "skill_path": skill[1], "plugin": launch["plugin"],
           "version": launch["version"] if skill[0] == launch["skill"] else skill_version(skill[1]),
           "method": method or launch["method"], "root": launch["root"], "root_real": launch["root_real"],
           "prompt_id": turn_key(ev), "start": time.time(), "transcript": ev.get("transcript_path") or launch["transcript"],
           "who": launch["who"], "cowork": launch["cowork"]}
    if launch.get("harness"):
        run["harness"] = launch["harness"]
        run["model"] = ev.get("model")
    run.update(extra)
    return run


def open_run(ev: dict, name, key: str, tool_use_id: str | None = None) -> None:
    """Вызов скилла в Claude: команда открывает новый запуск; модель — новый, если открытого нет,
    иначе вложенный отрезок того же запуска."""
    skill = plugin_skill(name)
    sid = ev.get("session_id")
    if not skill or not isinstance(sid, str) or not sid or ev.get("agent_id"):
        return  # скилл внутри субагента учитывается строкой субагента
    root = hook_space.ready_usage_root(ev)
    if not root:
        return
    with state_of(sid) as state:
        runs = state["runs"]
        # команда и сразу за ней Skill того же скилла — один отрезок; после другого скилла — новый
        same_turn = [r for r in runs if r.get("prompt_id") == turn_key(ev)]
        if any(r.get("key") == key for r in runs) or (same_turn and not same_turn[-1].get("tool_use_id")
                                                      and same_turn[-1].get("skill") == skill[0]):
            return
        launch = live_launch(state, time.time())
        method = MODEL if tool_use_id else COMMAND
        if launch is None or method == COMMAND:
            launch = new_launch(state, ev, key, skill, name.partition(":")[0], root, method)
        runs.append(segment_of(launch, ev, key, skill, method, tool_use_id=tool_use_id))
    log("open", skill=skill[0], session=sid)
    sweep_state(sid)


def open_agent_run(ev: dict) -> None:
    """Субагент получил путь к `SKILL.md` пакета — модуль зовут агентом. Открытый запуск его и так
    учтёт строкой субагента; нет запуска — субагент его открывает, отрезок начинается с этого вызова."""
    sid = ev.get("session_id")
    ti = ev.get("tool_input") if isinstance(ev.get("tool_input"), dict) else {}
    if not isinstance(sid, str) or not sid or ev.get("agent_id") or not isinstance(ti.get("prompt"), str) \
            or "SKILL.md" not in ti["prompt"]:
        return  # быстрый выход до поиска корня
    skill = resolve_skill("command", ti["prompt"])
    root = hook_space.ready_usage_root(ev) if skill else None
    if not root:
        return
    key = "tool:" + str(ev.get("tool_use_id"))
    with state_of(sid) as state:
        if live_launch(state, time.time()) or any(r.get("key") == key for r in state["runs"]):
            return
        launch = new_launch(state, ev, key, skill, plugin_name(), root, MODEL)
        state["runs"].append(segment_of(launch, ev, key, skill, MODEL, tool_use_id=ev.get("tool_use_id"), by_agent=True))
    log("open", skill=skill[0], session=sid, agent=True)
    sweep_state(sid)


def continue_launch(ev: dict, stop: bool, codex: bool = False) -> None:
    """Новый ход пользователя: следующий отрезок открытого запуска или его конец. Ход в другой
    базе запуск кончает: его работа не пишется в базу, где скилл вызвали."""
    sid = ev.get("session_id")
    if not has_state(sid):
        return
    root = None if stop else (codex_root(ev) if codex else hook_space.ready_usage_root(ev))
    with state_of(sid) as state:
        launch = live_launch(state, time.time())
        if launch is None:
            return
        if not root or os.path.realpath(root) != launch.get("root_real") or not usage_root_ready(launch):
            state["launch"] = None
            return
        if any(r.get("prompt_id") == turn_key(ev) for r in state["runs"]):
            return  # повтор события того же хода
        launch["turn"] += 1
        state["runs"].append(segment_of(launch, ev, f"turn:{turn_key(ev)}"))


def open_codex_runs(ev: dict) -> None:
    """Явные $команды скиллов этого пакета — новый запуск; без команды — следующий ход открытого."""
    if usage_codex is None or ev.get("agent_id") or not isinstance(ev.get("turn_id"), str):
        return
    sid = ev.get("session_id")
    if not isinstance(sid, str) or not sid:
        return
    own = plugin_name()
    selected = {}
    for name in re.findall(r"(?<![\w\\$])\$([A-Za-z0-9][\w.-]*(?::[\w.-]+)?)(?![\w:.-])", ev.get("prompt") or ""):
        qualified = name if ":" in name else f"{own}:{name}"
        skill = plugin_skill(qualified)
        if not skill and qualified.endswith("."):
            skill = plugin_skill(qualified.rstrip("."))  # пунктуация после команды; точное имя имеет приоритет
        if skill:
            selected[skill[0]] = skill[1]
    if not selected:  # чужая $команда в начале запроса — другая работа: запуск кончился
        continue_launch(ev, stop=bool(FOREIGN_CODEX_RE.match(ev.get("prompt") or "")), codex=True)
        return
    root = codex_root(ev)
    if not root:
        return
    with state_of(sid) as state:
        runs = state["runs"]
        launch = None
        for name, path in selected.items():
            key = f"codex:{ev['turn_id']}:{name}"
            if any(r.get("key") == key for r in runs):
                continue
            if launch is None:
                launch = new_launch(state, ev, key, (name, path), own, root, COMMAND, harness="codex")
            runs.append(segment_of(launch, ev, key, (name, path), COMMAND, shared_turn=False))
            log("open", skill=name, session=sid)
        peers = [r for r in runs if r.get("harness") == "codex" and r.get("prompt_id") == ev["turn_id"]]
        if len(peers) > 1:
            for r in peers:
                r["shared_turn"] = True  # команды могут прийти разными событиями одного хода
    sweep_state(sid)


def codex_root(ev: dict) -> str | None:
    """Готовая база Codex, совпадающая с исходным cwd сессии в rollout: смена cwd не переносит учёт."""
    root = hook_space.ready_usage_root(ev, use_claude_env=False)
    if not root:
        return None  # до чтения rollout и создания состояния
    meta = usage_codex.head_meta(ev.get("transcript_path"))
    if isinstance(meta.get("source"), dict) and "subagent" in meta["source"]:
        return None  # сессия субагента учитывается строкой субагента у родителя
    original = meta.get("cwd")
    anchored = hook_space.ready_usage_root({"cwd": original}, use_claude_env=False) if isinstance(original, str) else None
    return root if anchored and os.path.realpath(anchored) == os.path.realpath(root) else None


def open_codex_implicit(ev: dict) -> None:
    """Stop хода Codex: скиллы, которые модель прочитала сама (`SKILL.md` или скрипт пакета
    командой оболочки) — правило неявного вызова самого Codex, — и субагент, исполнивший скилл
    пакета, когда запуска нет. Отрезок начинается с этой команды или запуска субагента."""
    if usage_codex is None or ev.get("agent_id") or not isinstance(ev.get("turn_id"), str):
        return
    sid = ev.get("session_id")
    if not isinstance(sid, str) or not sid:
        return
    root = codex_root(ev)
    if not root:
        return
    entries = usage_codex.read_turn(ev.get("transcript_path"), ev["turn_id"])
    found = usage_codex.implicit_calls(entries, ev["turn_id"], resolve_skill, ev.get("transcript_path"))
    if not found:
        return
    with state_of(sid) as state:
        runs = state["runs"]
        for call_id, (name, path), by_agent, stamp in found:
            key = f"codex:{ev['turn_id']}:{call_id}"
            turn = [r for r in runs if r.get("prompt_id") == ev["turn_id"]]
            if any(r.get("key") == key for r in runs) or any(r.get("skill") == name for r in turn):
                continue  # явная команда или уже прочитанный в этом ходе скилл
            launch = live_launch(state, time.time())
            if launch is not None and by_agent:
                continue  # модуль у субагента внутри запуска — это строка субагента, а не отрезок хода
            if launch is None:
                launch = new_launch(state, ev, key, (name, path), plugin_name(), root, MODEL, harness="codex")
            for r in turn:
                r.setdefault("cut_call", call_id)  # прежний отрезок хода кончается этой командой
            runs.append(segment_of(launch, ev, key, (name, path), MODEL, from_call=call_id, shared_turn=False,
                                   start=stamp or time.time(), stopped_at=time.time()))
            log("open", skill=name, session=sid, implicit=True)


def host() -> str:
    import socket  # только при записи строки: пустой выход не платит за импорт

    raw = (socket.gethostname() or "host").split(".")[0]
    name = re.sub(r"[^a-z0-9-]+", "-", raw.lower()).strip("-")
    # имя не латиницей или `readme` (на регистронезависимой ФС совпало бы с README.md контракта)
    plain = name and name == raw.lower() and name != "readme"
    return name if plain else (name + "-" if name else "host-") + hashlib.sha1(raw.encode()).hexdigest()[:6]


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

        import space_map  # генератор карты лежит рядом с хуком; грузится только при открытии запуска

        rec = space_map.read_cache(space_map.account_email(), Path(root))
        return rec["subject"] if rec else ""  # срок не нужен: subject_id неизменен, ключ — аккаунт и база
    except Exception as e:  # noqa: BLE001 — без `кто` строка всё равно пишется
        log("who failed", error=f"{type(e).__name__}: {e}")
        return ""


def cell(value) -> str:
    return "" if value is None else " ".join(str(value).replace("|", "/").split())


def stamp_of(ts: float) -> str:
    stamp = datetime.datetime.fromtimestamp(ts).astimezone().strftime("%Y-%m-%d %H:%M%z")
    return stamp[:-2] + ":" + stamp[-2:]


def line(run: dict, sid: str, stage: str, skill: str, version, method: str, harness: str, models, m: dict,
         start: float, seconds, outcome: str) -> str:
    launch = run.get("launch") or hashlib.sha1(f"{sid}:{run.get('key')}".encode()).hexdigest()[:8]  # отрезок 0.3
    cells = [stamp_of(start), sid, launch, stage, skill, version, method, harness, " + ".join(models or []),
             os_name(), host(), run.get("who"), "", m.get("input"), m.get("output"), m.get("cache_read"),
             m.get("cache_write"), m.get("turns"), m.get("tools"), seconds, outcome, ""]
    return "| " + " | ".join(cell(c) for c in cells) + " |"


def rows(run: dict, m: dict, session_id: str) -> list[str]:
    """Строка отрезка основной сессии и строки его субагентов."""
    end = m["last"] if m["cut"] else run.get("stopped_at") or m["last"]
    harness = "cowork" if run.get("cowork") else ((run.get("harness") or "claude-code") + " " + (m["version"] or "")).strip()
    done = m.get("completed", bool(run.get("stopped_at")))
    outcome = "ошибка" if m["error"] else ("завершён" if done else "оборван")
    method = run.get("method") or (COMMAND if not run.get("tool_use_id") else MODEL)
    out = [line(run, session_id, f"ход {run.get('turn', 1)}", run["skill"], run.get("version"), method, harness,
                m["models"], m, run["start"], None if end is None else max(0, round(end - run["start"])), outcome)]
    for a in m.get("agents") or []:
        skill, version, how = run["skill"], run.get("version"), method
        if a.get("skill"):
            skill, version, how = a["skill"][0], skill_version(a["skill"][1]), MODEL
        seconds = a.get("seconds")
        if seconds is None and a.get("start") is not None and a.get("last") is not None:
            seconds = max(0, round(a["last"] - a["start"]))
        out.append(line(run, session_id, ("субагент " + (a.get("kind") or "")).strip(), skill, version, how, harness,
                        a.get("models"), a, a.get("start") or run["start"], seconds,
                        "оборван" if a.get("unfinished") else "завершён"))
    return out


def archive_name(usage: str) -> str:
    base = os.path.join(usage, f"{host()}.archive-{datetime.date.today().isoformat()}")
    path, n = base + ".md", 1
    while os.path.exists(path):
        n += 1
        path = f"{base}-{n}.md"
    return path


def append(root: str, lines) -> bool:
    """Дописать строки в таблицу машины. Файл со старой шапкой отодвигается рядом целиком
    (`<хост>.archive-<дата>.md`) и начинается новый: учёт не замолкает после смены контракта."""
    lines = [lines] if isinstance(lines, str) else list(lines)
    usage = os.path.join(root, ".svaib", "usage")
    path = os.path.join(usage, host() + ".md")
    for _ in range(2):
        stale = None
        with locked(path, "a+") as f:
            f.seek(0)
            head = f.read(4096)  # шапка — в начале файла, строки читать незачем
            if not head:
                f.write(f'---\ntitle: "usage — {host()}"\n---\n\n{HEADER}\n|' + "---|" * HEADER.count(" | ") + "---|\n")
            elif HEADER not in head:
                st = os.fstat(f.fileno())
                stale = (st.st_ino, st.st_size)
            else:
                with open(path, "rb") as raw:  # последний байт: текстовый seek мог бы встать внутрь символа
                    raw.seek(-1, os.SEEK_END)
                    if raw.read(1) != b"\n":
                        f.write("\n")
            if stale is None:
                f.write("".join(ln + "\n" for ln in lines))
                return True
        # Отодвигаем под блокировкой вне базы, одной на таблицу этой машины: две сессии не выберут
        # одно имя архива и не перенесут уже новую таблицу. Таблицу к этому моменту закрыли:
        # Windows не переименует открытый файл.
        guard = os.path.join(hook_space.state_dir(), "usage", "archive-" + hashlib.sha1(
            os.path.realpath(path).encode()).hexdigest()[:12] + ".lock")
        os.makedirs(os.path.dirname(guard), exist_ok=True)
        with locked(guard, "a+"):
            try:
                st = os.stat(path)
            except FileNotFoundError:
                continue  # уже отодвинул другой хук — пишем в новую таблицу
            if (st.st_ino, st.st_size) == stale:  # тот же файл: другой хук его ещё не отодвинул
                os.replace(path, archive_name(usage))
                log("archived", file=os.path.basename(path))
    return False


def close_runs(ev: dict, keep_prompt: str | None = None, keep_launch: bool = False) -> None:
    """Пишет строки по отрезкам прошлых ходов; отрезки хода `keep_prompt` остаются открытыми.
    Без `keep_prompt` (конец сессии) закрывается и запуск, кроме уборки чужой молчащей сессии
    (`keep_launch`): её запуск живёт до своей паузы. Отрезок снимается с учёта только после
    записи строки или явного отказа, состояние сохраняется после каждой записи — повтор безопасен."""
    sid = ev.get("session_id")
    if not has_state(sid):
        return  # быстрый выход: открытых отрезков нет, транскрипт не читаем
    with state_of(sid) as state:
        runs = state["runs"]
        if keep_prompt is None and not keep_launch:
            state["launch"] = None
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
        needles = [r.get("tool_use_id") or r.get("prompt_id") for r in closing]
        entries = adapter.read_from(transcript, needles)  # с начала самого раннего отрезка, не весь файл
        # ждём последний ответ только хода, который кончился сейчас: сверка один раз на отрезок;
        # на SessionEnd не ждём — хост даёт ему короткий тайм-аут, а транскрипт к нему дописан
        final = next((r["final"] for r in reversed(closing) if r.get("final")), None) \
            if keep_prompt and not state.get("no_flush") else None
        for r in closing:
            r["final"] = None
        deadline = time.time() + FLUSH_WAIT
        while final and not adapter.has_final_text(entries, final) and time.time() < deadline:
            time.sleep(0.1)
            entries = adapter.read_from(transcript, needles)
        if final and not adapter.has_final_text(entries, final):
            state["no_flush"] = True  # сверка у этого хоста не сходится — не платить 2 с на каждом ходе
            log("flush mismatch", session=sid)
        if adapter is usage_claude and isinstance(ev.get("prompt"), str):  # запрос этого события хост пишет в транскрипт позже хука
            entries.append({"type": "user", "promptId": ev.get("prompt_id"), "message": {"content": ev["prompt"]}})
        seen = state.setdefault("agents_seen", {})
        begun = time.time()
        for run in closing:
            if time.time() - begun > CLOSE_BUDGET:
                break  # не успеть до тайм-аута хука — оставшиеся закроет следующее событие
            try:
                outcome = close_one(run, entries, transcript, sid, final_close=keep_prompt is None, seen=seen)
            except Exception as e:  # noqa: BLE001 — один сбойный отрезок не держит остальные
                outcome = f"error: {type(e).__name__}: {e}"
            if outcome in ("write", "denied", "space changed"):
                runs.remove(run)
                launch = state.get("launch")
                if outcome == "denied" and isinstance(launch, dict) and launch.get("key") == run.get("key"):
                    state["launch"] = None  # хост отклонил вызов, открывший запуск: запуска не было
            elif outcome == "start not in transcript":
                run["misses"] = run.get("misses", 0) + 1
                if run["misses"] >= MAX_MISSES or keep_prompt is None:
                    runs.remove(run)
            elif outcome != "pending" and time.time() - run["start"] > STATE_TTL:
                runs.remove(run)  # сбой записи повторяется до недели: занятая таблица строку не теряет
            state.save()  # убийство хука по тайм-ауту не повторит уже записанные строки
            log(outcome, skill=run["skill"], session=sid)
        if keep_prompt is None and not keep_launch and not runs:
            state.clear()  # конец сессии: учтённое больше не нужно
            state["runs"] = []


def usage_root_ready(run: dict) -> bool:
    return os.path.isfile(os.path.join(run["root"], ".svaib", "usage", "README.md")) and \
        os.path.realpath(run["root"]) == run.get("root_real", os.path.realpath(run["root"]))


def close_one(run: dict, entries: list[dict], transcript: str, sid: str, final_close: bool, seen: dict) -> str:
    adapter = usage_codex if run.get("harness") == "codex" else usage_claude
    probe = dict(seen)  # учтённые ответы субагентов фиксируются только вместе с записью строки
    final = final_close or time.time() - run["start"] >= PENDING_TTL  # фон ждали час — пишем, что есть
    m = adapter.measure(entries, run, transcript, resolve=resolve_skill, final=final, seen=probe)
    if m is None:
        return "start not in transcript"
    if m.get("denied"):
        return "denied"
    if m["pending"] and not final:
        return "pending"  # фоновый субагент ещё без итога — строка подождёт следующего события
    if not usage_root_ready(run):
        return "space changed"  # путь теперь ведёт в другую базу или учёт выключен — не пишем
    if not append(run["root"], rows(run, m, sid)):
        return "header mismatch"
    seen.update(probe)
    return "write"


def mark_stopped(ev: dict) -> None:
    sid = ev.get("session_id")
    if not has_state(sid):
        return
    with state_of(sid) as state:
        for run in state["runs"]:
            if run.get("prompt_id") == turn_key(ev):
                run["stopped_at"] = time.time()  # повторный Stop того же хода сдвигает конец
                run["final"] = usage_claude.digest(ev.get("last_assistant_message") or "") \
                    if (ev.get("last_assistant_message") or "").strip() else None
        if isinstance(state.get("launch"), dict):
            state["launch"]["last"] = time.time()  # от конца хода отсчитывается пауза запуска


def run(mode: str, ev: dict) -> None:
    if mode == "skill" and ev.get("tool_name") == "Skill":
        ti = ev.get("tool_input") or {}
        open_run(ev, ti.get("skill"), "tool:" + str(ev.get("tool_use_id")), ev.get("tool_use_id"))
    elif mode == "skill" and ev.get("tool_name") in usage_claude.AGENT_TOOLS:
        open_agent_run(ev)
    elif mode == "prompt":
        close_runs(ev, keep_prompt=turn_key(ev))
        if is_codex(ev):
            open_codex_runs(ev)
            return
        text = ev.get("prompt") or ""
        m = SLASH_RE.match(text)
        if m and plugin_skill(m.group(1)):
            open_run(ev, m.group(1), "prompt:" + str(ev.get("prompt_id")))
        else:  # чужая команда — другая работа: запуск кончился
            continue_launch(ev, stop=bool(FOREIGN_SLASH_RE.match(text)))
    elif mode == "stop":
        if is_codex(ev):
            open_codex_implicit(ev)
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
