#!/usr/bin/env python3
"""
Карта пространства в контекст сессии (трек space-map, N2). Один скрипт, четыре события:

    inject_space_map.py first-prompt   # UserPromptSubmit: только на ПЕРВОМ промпте сессии
    inject_space_map.py post-whoami    # PostToolUse (matcher mcp__.*__whoami): персонализация
    inject_space_map.py node-enter     # PostToolUse (matcher Read|Glob|Grep|Bash): подкарта узла при входе
    inject_space_map.py compact        # SessionStart matcher=compact|clear: вернуть карту
    inject_space_map.py plain          # голый markdown в stdout (отладка; без маркера сессии)

Почему первый промпт, а не старт сессии (решение Эрика 10.09): для человека это тот же
момент — до первого ответа, но к первому промпту уже подключён MCP, а в Cowork события
SessionStart нет. SessionStart остаётся для `compact`/`clear` — единственный механизм
вернуть контекст после сжатия (PostCompact контекст добавлять не умеет).

Кто пользователь — от платформы (`whoami`), не с машины. Персонализация детерминирована
хуком PostToolUse: он получает ответ `whoami` целиком (JSON), зовёт генератор без shell,
инжектит подкарту зоны и пишет кэш (state-каталог машины, вне репозитория и Drive; ключ —
email аккаунта Claude + корень пространства; TTL 24 ч). Следующая сессия стартует
персональной картой без MCP. Кэш протух / другой аккаунт / другая база → общая карта +
короткая просьба вызвать `whoami`. Без MCP агент исходит из сведений об аккаунте.

Подкарта узла — при входе в узел (решения Эрика 10–11.09, уточнено 14.09). Узел — папка
верхнего уровня безусловно (кроме служебных, `_inbox`, `zz_archive`) **и** любая папка глубже
только при наличии `README.md` (`commercial/sales`, `customer-success/projects/e-invoicing`):
границу вложенного узла задаёт README, а не overview — узел получает подкарту независимо от
того, юнит это (полноценный объект управления с менеджмент-китом) или нет; в подкарте узел с
китом помечен «юнит», без кита — «узел» (термины — канон scaffold,
`product/methodology/scaffold/README.md`). Верхний уровень — исключение по замыслу
(измерено 11.09), не забытая проверка: обход дерева не должен обрываться на папке без README
(ревью 14.09 поднимало это как расхождение с claim — правило верно, claim неточен). Первое обращение
к пути внутри узла — Read/Glob/Grep или Bash (пути вытаскиваются из команды, команда не
выполняется) —
даёт подкарту БЛИЖАЙШЕГО к цели узла (форма C: без карт пути до него; `SVAIB_MAP_NESTED` =
`0` / `chain` — формы A/B для стенда). В подкарту входят и «Маршруты чтения» README узла
после фильтра (`SVAIB_MAP_ROUTES=0` выключает). Один раз на узел за сессию (маркер
`<state>/sessions/<sid>.node.<путь>-<hash>`), узлы зоны помечаются при доставке персональной
карты, после сжатия метки снимаются. Событие входа задаёт settings; хук читает
`hook_event_name` — на PreToolUse отдаёт тот же контекст до результата инструмента (померено
как шум, прод — PostToolUse). Отказ первого обращения (deny) померен 11.09 и отклонён —
из кода убран (история: коммит 71a7ca66).

Стабильная часть карты живёт в CLAUDE.md/AGENTS.md корня (свой заголовок раздела в каждом —
«## Карта пространства» / «## Space Map», текст — `space_map.py --print-model`) и приходит
каждый ход — хук её не дублирует; нет ни одного из двух заголовков — модель пространства
подаётся вместе с картой. HTML-комментарий-маркер снят 14.09 (решение Эрика): заголовок
надёжнее и не портит вид файла. Канон этого файла —
product/plugin/hooks/inject_space_map.py (едет клиенту сборщиком вместе с space_map.py);
копия в .claude/hooks/ репозитория svaib — установка, тест держит их равными с точностью до
подстановки путей сборщиком. Реестр скиллов в карту не входит (Claude Code показывает их в
системном промпте); стенд замера включает его через SVAIB_MAP_SKILLS=1. Генератор ищется
рядом с хуком (поставка плагином: `space_map.py`), затем в дереве репозитория — и
импортируется модулем: один процесс.

Любой сбой — stderr и код 0: деградирует автоматизация, сессия не блокируется.
Исходы пишутся в `<state>/space-map-hook.log` (строка на запуск, `ms` — от загрузки
генератора до сборки контекста; старт интерпретатора ~70 мс сверх) — чтобы неделю живой
работы было чем мерить (ревью 10.09).
"""
from __future__ import annotations

import datetime
import importlib.util
import json
import os
import re
import sys
import time

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
GENERATOR_CANDIDATES = (
    os.path.join(HOOK_DIR, "space_map.py"),                                 # поставка плагином (рядом с хуком)
    os.path.join("product", "plugin", "hooks", "space_map.py"),             # репозиторий svaib: канон плагина
)
ROOT_MARKERS = ("CLAUDE.md", "AGENTS.md")  # README.md есть у каждого узла — не маркер
# Заголовок вместо HTML-комментария (решение Эрика 14.09): ищем любой из двух в любом корневом
# файле — не привязываемся к имени файла (ревью 14.09: старый снимок мог получить чужой заголовок).
MODEL_HEADINGS = ("## Карта пространства", "## Space Map")
MARKER_TTL_DAYS = 7
SID_RE = re.compile(r"[^A-Za-z0-9_.-]")
SERVICE_DIRS = {"_templates", "_state", "node_modules", "_map"}   # как в генераторе
NOT_NODES = {"zz_archive", "_inbox"}                               # карта их узлами не считает
GLOB_CHARS = set("*?[{")
ENTER_TOOLS = ("Read", "Glob", "Grep", "Bash")   # Bash — агент читает и через cat/ls/rg: карта и там (решение Эрика 11.09)
# Codex (12.09): типизированных Read/Glob/Grep у него нет — всё чтение идёт оболочкой.
# По документации хуков Codex исполнение шелла приходит как `tool_name: "Bash"` с командой
# в `tool_input.command`, то есть совместимо с Claude; но команда завёрнута в `/bin/bash -lc`,
# и без снятия обёртки путь не разбирается. Имена ниже — страховка на code-mode, где вызов
# приходит под своим именем; незнакомый инструмент пишется в лог и входом не считается.
SHELL_TOOLS = ("exec", "shell", "local_shell", "unified_exec", "exec_command", "container.exec")
SHELL_INPUT_KEYS = ("command", "cmd", "input", "script", "code")   # где лежит текст команды
# code-mode: команда лежит внутри JS-вызова — `await tools.exec_command({cmd:"sed …"})`
JS_EXEC_RE = re.compile(r"""exec_command\s*\(\s*\{[^{}]*?(?:cmd|command)\s*:\s*(["'`])(.*?)\1""",
                        re.S)
BASH_LIST_CMDS = {"cat", "head", "tail", "sed", "less", "more", "ls", "find", "tree", "grep", "rg", "awk", "wc", "stat", "file", "cd"}
BASH_PATTERN_CMDS = {"grep", "rg"}   # первый не-флаг — паттерн, не путь
NODE_MARKER_FILE = "README.md"        # вложенный узел = папка с README.md, не с 01_overview.md (уточнение Эрика 14.09)


def nested_mode() -> str:
    """Подкарты вложенных узлов при входе (A/B/C на стенде 11.09):
    `0` — только узел верхнего уровня; `chain` — все узлы на пути сверху вниз;
    `nearest` — только ближайший к цели узел (без карт пути до него)."""
    v = os.environ.get("SVAIB_MAP_NESTED", "nearest").strip().lower()   # прод-форма C (решение Эрика 11.09)
    return {"0": "0", "off": "0", "1": "chain", "chain": "chain", "nearest": "nearest", "deepest": "nearest"}.get(v, "nearest")


NODE_LEAD = ("`map_node: {node}` — подкарта узла, сгенерирована из дерева при первом обращении к нему; "
             "адреса файлов узла бери отсюда, не угадывай. Подпапка с пометкой «узел» — вложенный узел со своей "
             "картой, с пометкой «юнит, кит: …» — ещё и полноценный менеджмент-юнит (его `02_active`, "
             "`03_metrics`, `05_decisions`…); его подкарта придёт при первом обращении к ней.")

ASK_WHOAMI = (
    "Кто пользователь и его зона ответственности — от платформы: **вызови `whoami` (MCP svaib) "
    "первым действием** — до его ответа не обращайся к пользователю по имени и не считай его владельцем "
    "пространства; персональная подкарта зоны придёт в контекст автоматически (хук), ничего "
    "копировать и запускать не нужно. Если `workspace.profile_path` в ответе пуст — спроси, где в "
    "пространстве лежит профиль пользователя, и запиши через `update_me`. Если MCP svaib недоступен — "
    "исходи из сведений об аккаунте в контексте и спроси при неясности."
)


# ---------------------------------------------------------------------------- инфраструктура

def state_dir() -> str:
    override = os.environ.get("SVAIB_STATE_DIR")  # стенд замера: свой каталог на прогон
    if override:
        return override
    if os.name == "nt":
        return os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~/AppData/Local")), "svaib")
    return os.path.expanduser("~/.local/state/svaib")


def log(outcome: str, **kv) -> None:
    try:
        os.makedirs(state_dir(), exist_ok=True)
        rec = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
               "outcome": outcome, **kv}
        with open(os.path.join(state_dir(), "space-map-hook.log"), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


def is_space_root(path: str) -> bool:
    return any(os.path.isfile(os.path.join(path, m)) for m in ROOT_MARKERS)


def find_root(start: str) -> str | None:
    """Самый ВЕРХНИЙ каталог с маркером на пути от start, не доходя до $HOME:
    у юнитов svaib тоже лежит CLAUDE.md, а в домашнем каталоге может лежать чужой."""
    home = os.path.abspath(os.path.expanduser("~"))
    cur = os.path.abspath(start)
    found = None
    while cur != home:
        if is_space_root(cur):
            found = cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return found


def resolve_root(hook_input: dict) -> str | None:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and os.path.isdir(env) and is_space_root(env):
        return os.path.abspath(env)
    return find_root(hook_input.get("cwd") or os.getcwd())


def load_generator(root: str):
    for cand in GENERATOR_CANDIDATES:
        path = cand if os.path.isabs(cand) else os.path.join(root, cand)
        if os.path.isfile(path):
            spec = importlib.util.spec_from_file_location("svaib_space_map", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    return None


def model_in_root(root: str) -> bool:
    for name in ROOT_MARKERS:
        try:
            with open(os.path.join(root, name), encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        # якорь к началу строки: голая подстрока ловила бы «### Карта пространства» (ревью 14.09)
        if any(re.search(r"^" + re.escape(h) + r"\s*$", text, re.M) for h in MODEL_HEADINGS):
            return True
    return False


# ---------------------------------------------------------------------------- маркер первого промпта

def marker_path(session_id: str) -> str:
    sid = SID_RE.sub("_", session_id)[:80]
    return os.path.join(state_dir(), "sessions", f"{sid}.first-prompt")


def marker_exists(session_id: str) -> bool:
    return os.path.exists(marker_path(session_id))


def marker_set(session_id: str) -> bool:
    """Атомарно: True — поставили мы, False — уже стоял. Ставится ПОСЛЕ успешной сборки."""
    p = marker_path(session_id)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    try:
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    os.close(fd)
    return True


def node_marker_path(session_id: str, node: str) -> str:
    import hashlib
    sid = SID_RE.sub("_", session_id)[:80]
    raw = node.strip("/")
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]
    # хеш — за пределами усечения (ревью 14.09): длинный путь резать можно, хеш — нет,
    # иначе разные узлы с общим префиксом длиннее ~50 символов делят один файл-маркер
    readable = SID_RE.sub("_", raw.replace("/", "__"))[:50]
    return os.path.join(state_dir(), "sessions", f"{sid}.node.{readable}-{digest}")


def node_marker_exists(session_id: str, node: str) -> bool:
    return os.path.exists(node_marker_path(session_id, node))


def node_marker_set(session_id: str, node: str) -> bool:
    """Атомарно, как маркер первого промпта: True — поставили мы."""
    p = node_marker_path(session_id, node)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    try:
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    os.close(fd)
    return True


def node_markers_clear(session_id: str) -> None:
    """После сжатия подкарты узлов из контекста ушли — пустить их снова."""
    sid = SID_RE.sub("_", session_id)[:80]
    d = os.path.join(state_dir(), "sessions")
    try:
        for name in os.listdir(d):
            if name.startswith(f"{sid}.node."):
                os.remove(os.path.join(d, name))
    except OSError:
        pass


def _literal_lead(pattern: str) -> str:
    lead = []
    for seg in str(pattern or "").replace("\\", "/").split("/"):
        if GLOB_CHARS & set(seg):
            break
        lead.append(seg)
    return "/".join(lead)


def bash_paths(command: str, cwd: str, root: str) -> list[str]:
    """Пути пространства в команде Bash: токены, которые существуют под корнем (файл или каталог);
    у токена с glob-символами — литеральное начало. Флаги и чужие пути отбрасываются; у grep/rg
    первый не-флаг — паттерн, не путь; голый токен без «/» (`ls clients`) считается путём только
    у команд чтения/листинга — `echo product` входом не является. Переменные и подстановки
    (`cat $FILE`, `$(pwd)/…`) не раскрываются: команда не выполняется."""
    import shlex
    try:
        toks = shlex.split(command, posix=True)
    except ValueError:
        toks = command.split()
    out = []
    cmd = ""
    skip_pattern = False
    for t in toks:
        if t in ("|", "||", "&&", ";"):
            cmd = ""
            continue
        if not cmd and not re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", t):
            cmd = os.path.basename(t)
            skip_pattern = cmd in BASH_PATTERN_CMDS
            continue
        if not t or t.startswith("-") or t in (">", ">>", "<"):
            continue
        if skip_pattern:
            skip_pattern = False
            continue
        if "/" not in t and cmd not in BASH_LIST_CMDS:
            continue
        t = _literal_lead(t) if GLOB_CHARS & set(t) else t
        if not t:
            continue
        p = os.path.abspath(os.path.join(cwd, os.path.expanduser(t)))
        if os.path.exists(p) and (p == root or p.startswith(root + os.sep)) and p not in out:
            out.append(p)
    return out


def unwrap_shell(text: str) -> str:
    """`/bin/bash -lc "sed -n '1,20p' f.md"` → `sed -n '1,20p' f.md`.

    Codex заворачивает каждый вызов в оболочку; без снятия обёртки разбор путей видит
    только `bash` и `-lc`, и вход в узел не срабатывает вовсе.
    """
    import shlex
    try:
        parts = shlex.split(text, posix=True)
    except ValueError:
        return text
    if len(parts) >= 3 and os.path.basename(parts[0]) in ("bash", "sh", "zsh", "dash"):
        for i, tok in enumerate(parts[1:], start=1):
            if tok.startswith("-") and "c" in tok.lstrip("-") and i + 1 < len(parts):
                return parts[i + 1]
    return text


def shell_text(ti: dict) -> str:
    """Текст команды из входа инструмента-оболочки.

    У Codex форма зависит от режима: прямая команда (`/bin/bash -lc "sed …"`) либо JS
    code-mode (`await tools.exec_command({cmd:"sed …"})`). Нужны пути в обоих случаях:
    из JS достаём аргумент вызова, с прямой команды снимаем обёртку оболочки, а если
    поле незнакомое — берём все строки входа и оставляем отбор путей `bash_paths`.
    """
    parts = [str(ti[k]) for k in SHELL_INPUT_KEYS if isinstance(ti.get(k), str)]
    if not parts:
        parts = [v for v in ti.values() if isinstance(v, str)]
    text = "\n".join(parts)
    inner = [m.group(2) for m in JS_EXEC_RE.finditer(text)]
    return "\n".join(unwrap_shell(t) for t in (inner or [text]))


def targets_of(hook_input: dict, root: str) -> list[str]:
    """Цели обращения: Read — file_path; Grep — path; Glob — path + литеральное начало pattern;
    Bash и инструмент-оболочка Codex — пути пространства из текста команды."""
    ti = hook_input.get("tool_input")
    if not isinstance(ti, dict):
        return []
    name = hook_input.get("tool_name") or ""
    cwd = hook_input.get("cwd") or os.getcwd()
    if name == "Bash" or name in SHELL_TOOLS:
        # один путь для обоих харнесов: у Claude команда приходит как есть, у Codex —
        # в обёртке `/bin/bash -lc "…"` либо внутри JS code-mode; `shell_text` это снимает
        return bash_paths(shell_text(ti), cwd, root)
    if name not in ENTER_TOOLS:                     # неизвестный инструмент: разобрать и запомнить
        text = shell_text(ti)
        if not text:
            log("enter-foreign-tool", tool=name, keys=sorted(ti)[:8], reason="no text in input")
            return []
        return bash_paths(text, cwd, root)
    t = target_of(hook_input)
    return [t] if t else []


def target_of(hook_input: dict) -> str | None:
    """Путь, к которому обратился инструмент: Read — file_path; Grep — path; Glob — path +
    литеральное начало pattern (агент пишет `01_company/02_team/*` без path)."""
    ti = hook_input.get("tool_input")
    if not isinstance(ti, dict):
        return None
    name = hook_input.get("tool_name") or ""
    cwd = hook_input.get("cwd") or os.getcwd()
    if name == "Read":
        target = ti.get("file_path")
    elif name in ("Glob", "Grep"):
        target = ti.get("path") or cwd
        if name == "Glob":
            lead = _literal_lead(str(ti.get("pattern") or ""))
            if lead:
                target = os.path.join(str(target), lead)
    else:
        return None
    if not target or not isinstance(target, str):
        return None
    return os.path.abspath(os.path.join(cwd, os.path.expanduser(target)))


def node_of(root: str, target: str) -> str | None:
    """Узел верхнего уровня, внутри которого лежит target; None — корень, файл корня,
    служебное, скрытое или вне пространства."""
    rel = os.path.relpath(target, root)
    first = rel.split(os.sep)[0]
    if rel.startswith("..") or first in (".", "") or first.startswith(".") \
            or first in SERVICE_DIRS or first in NOT_NODES:
        return None
    return first if os.path.isdir(os.path.join(root, first)) else None


def nodes_of(root: str, target: str) -> list[str]:
    """Узлы на пути к target сверху вниз: верхний уровень + каждая папка глубже с
    README.md (вложенный узел: commercial/sales, customer-success/projects/e-invoicing) —
    юнит это или нет, не важно, важно наличие своей карты (уточнение Эрика 14.09).
    Папка-цель (Glob/Grep по каталогу) тоже считается входом в неё."""
    top = node_of(root, target)
    if not top:
        return []
    nodes = [top]
    mode = nested_mode()
    if mode == "0":
        return nodes
    parts = os.path.relpath(target, root).split(os.sep)
    cur = os.path.join(root, top)
    for seg in parts[1:]:
        if seg.startswith(".") or seg in SERVICE_DIRS or seg in NOT_NODES:
            break
        cur = os.path.join(cur, seg)
        if not os.path.isdir(cur):
            break
        if os.path.isfile(os.path.join(cur, NODE_MARKER_FILE)):
            nodes.append(os.path.relpath(cur, root).replace(os.sep, "/"))
    return nodes[-1:] if mode == "nearest" else nodes


def gc_markers() -> None:
    d = os.path.join(state_dir(), "sessions")
    try:
        cutoff = time.time() - MARKER_TTL_DAYS * 86400
        for name in os.listdir(d):
            p = os.path.join(d, name)
            if os.path.getmtime(p) < cutoff:
                os.remove(p)
    except OSError:
        pass


# ---------------------------------------------------------------------------- сборка контекста

def map_context(gen, root: str, when: str, ask: bool) -> tuple[str, dict]:
    """Карта (персональная при свежем кэше, иначе общая) + заголовок с меткой."""
    from pathlib import Path
    base = Path(root)
    cache = gen.read_cache(gen.account_email(), base)
    no_model = model_in_root(root)
    personal = bool(cache and cache.get("fresh"))
    units = list(cache.get("units") or []) if personal else []
    body = gen.emit_text(base, focus=units, no_model=no_model,
                         no_skills=os.environ.get("SVAIB_MAP_SKILLS") != "1")
    if personal:
        zone = " · ".join(f"`{u}/`" for u in units) or "юниты не выведены"
        head = (f"## Карта пространства {when}\n\n"
                f"`map_profile: {cache['subject']}` — персональная: пользователь запомнен на этой машине "
                f"по прошлому `whoami` (профиль `{cache.get('profile_path') or '—'}`, зона: {zone}).")
        if not units:
            head += (" Юниты зоны не выведены — работай по общей карте: подкарта узла придёт "
                     "при первом обращении к его файлам.")
    else:
        head = (f"## Карта пространства {when}\n\n"
                f"`map_profile: general` — карта общая, пользователь не установлен.")
        if ask:
            head += "\n\n" + ASK_WHOAMI
    meta = {"profile": cache["subject"] if personal else "general", "units": units, "no_model": no_model}
    if body.startswith("## Карта пространства"):
        body = body.split("\n", 1)[1].lstrip("\n")  # H2 генератора — лишний, заголовок даёт хук
    return head + "\n\n" + body, meta


def personalize_context(gen, root: str, hook_input: dict) -> tuple[str, dict]:
    from pathlib import Path
    resp = hook_input.get("tool_response")
    if isinstance(resp, dict) and "content" in resp and "structuredContent" not in resp:
        resp = resp["content"]
    who = gen.parse_whoami(resp)
    text, rec = gen.personalize(Path(root), who)
    return "## Персонализация карты (после `whoami`)\n\n" + text, {"profile": who["subject"], "units": rec["units"]}


def node_context(gen, root: str, node: str) -> str:
    from pathlib import Path
    body = gen.emit_node_text(Path(root), node)
    if body.startswith("## Карта узла"):
        body = body.split("\n", 1)[1].lstrip("\n")
    return f"## Подкарта узла `{node}/` (вход в узел)\n\n" + NODE_LEAD.format(node=node) + "\n\n" + body


def emit(context: str, event: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": context}},
                     ensure_ascii=False))


EVENT = {"first-prompt": "UserPromptSubmit", "post-whoami": "PostToolUse", "node-enter": "PostToolUse",
         "compact": "SessionStart"}


MODES = ("first-prompt", "post-whoami", "node-enter", "compact", "plain")


def run(mode: str, hook_input: dict) -> None:
    sid = hook_input.get("session_id") or ""
    if mode not in MODES:
        log("skip", mode=mode, reason="unknown mode")
        print(f"inject_space_map: неизвестный режим {mode!r}; ожидается один из {MODES}", file=sys.stderr)
        return
    if mode == "first-prompt":
        if not sid:
            log("skip", mode=mode, reason="no session_id")
            return
        if marker_exists(sid):
            return
    root = resolve_root(hook_input)
    if not root:
        if mode == "node-enter":
            return  # чтение вне пространства — не наше дело, лог не засорять
        log("skip", mode=mode, reason="no root", cwd=hook_input.get("cwd"))
        print("inject_space_map: корень пространства не найден", file=sys.stderr)
        return
    nodes: list[str] = []
    event = EVENT.get(mode, "PostToolUse")
    if mode == "node-enter":
        tool = hook_input.get("tool_name") or ""
        # вход слушают чтение и поиск Claude плюс инструмент-оболочка чужого харнеса (Codex)
        if not sid or (tool not in ENTER_TOOLS and tool not in SHELL_TOOLS):
            if sid and tool and tool not in ENTER_TOOLS:
                log("enter-skip", tool=tool, reason="инструмент не слушается")
            return
        event = hook_input.get("hook_event_name") or "PostToolUse"   # событие задаёт settings: Pre или Post
        for t in targets_of(hook_input, root):
            for n in nodes_of(root, t):
                if n not in nodes and not node_marker_exists(sid, n):
                    nodes.append(n)
        if not nodes:
            return
    t0 = time.monotonic()
    gen = load_generator(root)
    if gen is None:
        log("skip", mode=mode, reason="no generator", root=root)
        print("inject_space_map: генератор карты не найден — карта не подана", file=sys.stderr)
        return
    if mode == "post-whoami":
        context, meta = personalize_context(gen, root, hook_input)
    elif mode == "node-enter":
        context, meta = "\n\n".join(node_context(gen, root, n) for n in nodes), {"node": "+".join(nodes), "event": event, "tool": tool}
    else:
        when = {"compact": "после сжатия контекста"}.get(mode, "на первом запросе сессии")
        context, meta = map_context(gen, root, when, ask=(mode != "plain"))
    if mode == "first-prompt" and not marker_set(sid):
        return  # параллельный запуск уже доставил
    if mode == "node-enter":
        won = [n for n in nodes if node_marker_set(sid, n)]
        if not won:
            return  # параллельный вызов уже доставил все подкарты
        if won != nodes:   # часть подкарт доставил параллельный вызов — отдаём только свои
            context, meta = "\n\n".join(node_context(gen, root, n) for n in won), dict(meta, node="+".join(won))
    if mode == "plain":
        print(context)
    else:
        emit(context, event)
    log("ok", mode=mode, root=root, ms=int((time.monotonic() - t0) * 1000), chars=len(context), **meta)
    if sid and mode in ("first-prompt", "post-whoami", "compact"):
        if mode == "compact":
            node_markers_clear(sid)          # подкарты узлов ушли со сжатием — пустить снова
        for u in meta.get("units") or []:    # подкарты зоны уже в контексте — при входе не дублировать
            node_marker_set(sid, u)
    if mode == "first-prompt":
        gc_markers()


def main():
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "first-prompt"
    try:
        raw = sys.stdin.read()
        hook_input = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        hook_input = {}
    try:
        run(mode, hook_input)
    except Exception as e:  # noqa: BLE001 — хук не имеет права уронить сессию
        log("error", mode=mode, error=f"{type(e).__name__}: {e}")
        print(f"inject_space_map: {type(e).__name__}: {e}", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
