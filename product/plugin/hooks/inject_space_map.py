#!/usr/bin/env python3
"""
Карта пространства в контекст сессии. Один скрипт, пять событий:

    inject_space_map.py first-prompt   # UserPromptSubmit: только на ПЕРВОМ промпте сессии
    inject_space_map.py post-whoami    # PostToolUse (matcher mcp__.*__whoami): персонализация
    inject_space_map.py post-update-me # PostToolUse (matcher mcp__.*__update_me): онбординг и настройки в кэш, без вывода
    inject_space_map.py node-enter     # PostToolUse (matcher Read|Glob|Grep|Bash): подкарта узла при входе
    inject_space_map.py compact        # SessionStart matcher=compact|clear: вернуть карту
    inject_space_map.py plain          # голый markdown в stdout (отладка; без маркера сессии)

Почему первый промпт, а не старт сессии: для человека это тот же
момент — до первого ответа, но к первому промпту уже подключён MCP, а в Cowork события
SessionStart нет. SessionStart остаётся для `compact`/`clear` — единственный механизм
вернуть контекст после сжатия (PostCompact контекст добавлять не умеет).

Кто пользователь — от платформы (`whoami`), не с машины. Персонализация детерминирована
хуком PostToolUse: он получает ответ `whoami` целиком (JSON), зовёт генератор без shell,
инжектит подкарту зоны и сохраняет личность для хуков этой сессии (state-каталог машины,
вне репозитория и Drive; ключ — session_id + корень пространства). Новая сессия
начинается с общей карты и вызывает `whoami`; после сжатия карта восстанавливается
из записи текущей сессии. Без MCP личность не угадывается.

Под строкой «За клавиатурой» — ближайшие этапы онбординга («два и два»): статус `onboarding`
из записи сессии × каталог этапов скилла `onboarding` (`space_map.onboarding_block`). Ответ
`update_me` несёт итоговые статус и `preferences` — хук обновляет запись сессии.

Подкарта узла — при входе в узел. Узел — папка
верхнего уровня безусловно (кроме служебных, `_inbox`, `zz_archive`) **и** любая папка глубже
только при наличии `README.md` (`commercial/sales`, `customer-success/projects`):
границу вложенного узла задаёт README, а не overview — узел получает подкарту независимо от
того, юнит это (полноценный объект управления с менеджмент-китом) или нет; в подкарте узел с
китом помечен «юнит», без кита — «узел» (термины — канон scaffold). Верхний уровень — исключение
по замыслу, не забытая проверка: обход дерева не должен обрываться на папке без README. Первое
обращение к пути внутри узла — Read/Glob/Grep или Bash (пути вытаскиваются из команды, команда не
выполняется) —
даёт подкарту БЛИЖАЙШЕГО к цели узла (без карт пути до него; `SVAIB_MAP_NESTED` =
`0` / `chain` — другие формы для стенда). В подкарту входят и «Маршруты чтения» README узла
после фильтра (`SVAIB_MAP_ROUTES=0` выключает). Один раз на узел за сессию (маркер
`<state>/sessions/<sid>.node.<путь>-<hash>`), узлы зоны помечаются при доставке персональной
карты, после сжатия метки снимаются. Событие входа задаёт settings; хук читает
`hook_event_name` — на PreToolUse отдаёт тот же контекст до результата инструмента
(прод — PostToolUse).

Стабильная часть карты живёт в CLAUDE.md/AGENTS.md корня (свой заголовок раздела в каждом —
«## Карта пространства» / «## Space Map», текст — `space_map.py --print-model`) и приходит
каждый ход — хук её не дублирует; нет ни одного из двух заголовков — модель пространства
подаётся вместе с картой. Маркер — заголовок, а не HTML-комментарий: надёжнее и не портит вид
файла. Реестр скиллов в карту не входит (Claude Code показывает их в
системном промпте); стенд замера включает его через SVAIB_MAP_SKILLS=1. Генератор ищется
рядом с хуком (поставка плагином: `space_map.py`), затем в дереве репозитория — и
импортируется модулем: один процесс.

Любой сбой — stderr и код 0: деградирует автоматизация, сессия не блокируется.
Исходы пишутся в `<state>/space-map-hook.log` (строка на запуск, `ms` — от загрузки
генератора до сборки контекста; старт интерпретатора ~70 мс сверх) — чтобы было чем мерить
живую работу.
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
sys.path.insert(0, HOOK_DIR)
try:
    import hook_space   # корень сессии — общий с хуками спецификации и учёта
except ImportError:     # неполная поставка: сбой ловит main, сессия не падает
    hook_space = None
GENERATOR_CANDIDATES = (
    os.path.join(HOOK_DIR, "space_map.py"),                                 # поставка плагином (рядом с хуком)
    os.path.join("product", "plugin", "hooks", "space_map.py"),             # репозиторий svaib: канон плагина
)
# Заголовок вместо HTML-комментария: ищем любой из двух в любом корневом
# файле — не привязываемся к имени файла (старый снимок мог получить чужой заголовок).
MODEL_HEADINGS = ("## Карта пространства", "## Space Map")
MARKER_TTL_DAYS = 7
SID_RE = re.compile(r"[^A-Za-z0-9_.-]")
SERVICE_DIRS = {"_templates", "_state", "node_modules", "_map", "__pycache__"}   # как в генераторе
NOT_NODES = {"zz_archive", "_inbox"}                               # карта их узлами не считает
GLOB_CHARS = set("*?[{")
ENTER_TOOLS = ("Read", "Glob", "Grep", "Bash")   # Bash — агент читает и через cat/ls/rg: карта и там
# Codex: типизированных Read/Glob/Grep у него нет — всё чтение идёт оболочкой.
# По документации хуков Codex исполнение шелла приходит как `tool_name: "Bash"` с командой
# в `tool_input.command`, то есть совместимо с Claude; но команда завёрнута в `/bin/bash -lc`,
# и без снятия обёртки путь не разбирается. Имена ниже — страховка на code-mode, где вызов
# приходит под своим именем; незнакомый инструмент пишется в лог и входом не считается.
SHELL_TOOLS = ("PowerShell", "exec", "shell", "local_shell", "unified_exec", "exec_command", "container.exec",
               "mcp__workspace__bash")   # Cowork «Only on this computer»: bash в VM — MCP-инструмент
SHELL_INPUT_KEYS = ("command", "cmd", "input", "script", "code")   # где лежит текст команды
# code-mode: команда лежит внутри JS-вызова — `await tools.exec_command({cmd:"sed …"})`
JS_EXEC_RE = re.compile(r"""exec_command\s*\(\s*\{[^{}]*?(?:cmd|command)\s*:\s*(["'`])((?:\\.|(?!\1).)*?)\1""",
                        re.S)
BASH_LIST_CMDS = {"cat", "head", "tail", "sed", "less", "more", "ls", "find", "tree", "grep", "rg", "awk", "wc", "stat", "file", "cd"}
BASH_PATTERN_CMDS = {"grep", "rg"}   # первый не-флаг — паттерн, не путь
NODE_MARKER_FILE = "README.md"        # вложенный узел = папка с README.md, не с 01_overview.md


def nested_mode() -> str:
    """Подкарты вложенных узлов при входе:
    `0` — только узел верхнего уровня; `chain` — все узлы на пути сверху вниз;
    `nearest` — только ближайший к цели узел (без карт пути до него)."""
    v = os.environ.get("SVAIB_MAP_NESTED", "nearest").strip().lower()
    return {"0": "0", "off": "0", "1": "chain", "chain": "chain", "nearest": "nearest", "deepest": "nearest"}.get(v, "nearest")


NODE_LEAD = "`map_node: {node}` — адреса файлов узла бери отсюда, не угадывай."

ASK_WHOAMI = (
    "Кто пользователь и его зона ответственности — от серверной части svaib: **вызови `whoami` (MCP svaib) "
    "первым действием** — до его ответа не обращайся к пользователю по имени и не считай его владельцем "
    "пространства; персональная подкарта зоны придёт в контекст автоматически (хук), ничего "
    "копировать и запускать не нужно. Если `workspace.profile_path` в ответе пуст — спроси, где в "
    "пространстве лежит профиль пользователя, и запиши через `update_me`. Если MCP svaib недоступен — "
    "пользователя не угадывай и имя не подставляй; при неясности спроси."
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


def find_root(start: str) -> str | None:
    return hook_space.find_root(start)


def _cowork_ambiguous(count: int, total: int, folders: list[str]) -> None:
    log("skip", reason="workspace folders: .svaib in %d of %d" % (count, total), folders=folders)
    print("inject_space_map: подключено %d папок, `.svaib/` в %d — не понять, какая из них пространство"
          % (total, count), file=sys.stderr)


def resolve_root(hook_input: dict) -> str | None:
    return hook_space.resolve_root(hook_input, _cowork_ambiguous)


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
    for name in hook_space.ROOT_MARKERS:
        try:
            with open(os.path.join(root, name), encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        # якорь к началу строки: голая подстрока ловила бы «### Карта пространства»
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


def node_key(hook_input: dict) -> str:
    """Ключ меток подкарт: у субагента — свой. Хост даёт субагенту session_id родителя и agent_id
    (Claude Code и Codex, зонд 28.09); без agent_id скаут забирал подкарты у основного агента."""
    sid = SID_RE.sub("_", hook_input.get("session_id") or "")[:80]
    agent = SID_RE.sub("_", hook_input.get("agent_id") or "")[:40]
    return f"{sid}.{agent}" if agent and sid else sid


def node_marker_path(session_id: str, node: str) -> str:
    import hashlib
    sid = SID_RE.sub("_", session_id)[:121]
    raw = os.path.normcase(node).replace(os.sep, "/").strip("/")
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]
    # хеш — за пределами усечения: длинный путь резать можно, хеш — нет,
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
    """После сжатия подкарты узлов из контекста ушли — пустить их снова (и субагентам сессии)."""
    sid = SID_RE.sub("_", session_id)[:80]
    d = os.path.join(state_dir(), "sessions")
    try:
        for name in os.listdir(d):
            if name.startswith(f"{sid}.") and ".node." in name:
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


def powershell_input(ti: dict, tool: str = "") -> bool:
    """Диалект команды: имя инструмента, явная оболочка или обёртка Codex."""
    if tool == "PowerShell":
        return True
    shell = str(ti.get("shell") or "").replace("\\", "/").rsplit("/", 1)[-1].lower()
    if shell in {"pwsh", "pwsh.exe", "powershell", "powershell.exe"}:
        return True
    text = next((ti[k] for k in SHELL_INPUT_KEYS if isinstance(ti.get(k), str)), "")
    executable = re.match(r'''^\s*(?:&\s*)?(?:"([^"]+)"|'([^']+)'|([^\s"']+))''', text)
    if executable:
        name = next(value for value in executable.groups() if value is not None)
        if name.replace("\\", "/").rsplit("/", 1)[-1].lower() in {"pwsh", "pwsh.exe", "powershell", "powershell.exe"}:
            return True
        if name.replace("\\", "/").rsplit("/", 1)[-1].lower().removesuffix(".exe") in {"bash", "sh", "zsh", "dash"}:
            return False
    return os.name == "nt" and tool not in {"Bash", "mcp__workspace__bash"} and not shell


class PowerShellToken(str):
    """Текст аргумента и его синтаксическая роль: строка ';' не оператор ;."""

    def __new__(cls, value: str, *, operator: bool = False, quoted: bool = False, start: int = -1):
        token = super().__new__(cls, value)
        token.operator, token.quoted = operator, quoted
        token.start = start
        return token


def ps_operator(token: str, values) -> bool:
    return getattr(token, "operator", False) and token in values


def powershell_tokens(text: str) -> list[PowerShellToken]:
    """Буквальные аргументы PowerShell; обратный слеш — часть пути, не escape Bash.

    Подстановки не вычисляются. Одинарные кавычки удваиваются, в двойных escape — backtick.
    Это сито путей, не исполнение и не полный парсер PowerShell.
    """
    out, token, quote, quoted, token_start, i = [], [], "", False, -1, 0
    def flush():
        nonlocal quoted, token_start
        if token or quoted:
            out.append(PowerShellToken("".join(token), quoted=quoted, start=token_start))
            token.clear()
        quoted = False
        token_start = -1
    while i < len(text):
        ch = text[i]
        if ch == "`" and quote != "'" and text[i + 1:i + 2] in {"\r", "\n"}:
            i += 2
            if text[i - 1] == "\r" and text[i:i + 1] == "\n":
                i += 1
            continue
        if quote:
            if ch == quote:
                if quote == "'" and text[i:i + 2] == "''":
                    token.append("'")
                    i += 2
                    continue
                quote = ""
            elif ch == "`" and quote == '"' and i + 1 < len(text):
                i += 1
                token.append(text[i])
            else:
                token.append(ch)
        elif ch in "'\"":
            if not token:
                quoted = True
                token_start = i
            quote = ch
        elif ch == "`" and i + 1 < len(text):
            if not token:
                token_start = i
            i += 1
            token.append(text[i])
        elif ch == "#" and not token:
            end = text.find("\n", i)
            i = len(text) if end < 0 else end
            continue
        elif ch.isspace():
            flush()
            if ch == "\n":
                out.append(PowerShellToken(";", operator=True, start=i))
        elif ch in ";|&<>,()":
            flush()
            if i + 1 < len(text) and text[i + 1] == ch and ch in "|&<>":
                out.append(PowerShellToken(ch * 2, operator=True, start=i))
                i += 1
            else:
                out.append(PowerShellToken(ch, operator=True, start=i))
        else:
            if not token:
                token_start = i
            token.append(ch)
        i += 1
    flush()
    return out


def powershell_literal_arrays(tokens: list[PowerShellToken]) -> list[PowerShellToken]:
    """Снять только скобки буквальных строковых массивов, без выполнения выражений."""
    out, i = [], 0
    while i < len(tokens):
        if ps_operator(tokens[i], {"("}):
            end = i + 1
            values, expect_value = [], True
            while end < len(tokens) and not ps_operator(tokens[end], {")"}):
                token = tokens[end]
                if expect_value and token.quoted and not token.operator:
                    values.append(token)
                elif not expect_value and ps_operator(token, {","}):
                    values.append(token)
                else:
                    break
                expect_value = not expect_value
                end += 1
            if end < len(tokens) and ps_operator(tokens[end], {")"}) and values and not expect_value:
                if out and out[-1] == "@" and not out[-1].quoted:
                    out.pop()
                out.extend(values)
                i = end + 1
                continue
        out.append(tokens[i])
        i += 1
    return out


def bash_paths(command: str, cwd: str, root: str, *, powershell: bool = False) -> list[str]:
    """Пути пространства в команде Bash: токены, которые существуют под корнем (файл или каталог);
    у токена с glob-символами — литеральное начало. Флаги и чужие пути отбрасываются; у grep/rg
    первый не-флаг — паттерн, не путь; голый токен без «/» (`ls clients`) считается путём только
    у команд чтения/листинга — `echo product` входом не является. Переменные и подстановки
    (`cat $FILE`, `$(pwd)/…`) не раскрываются: команда не выполняется."""
    import shlex
    try:
        toks = powershell_literal_arrays(powershell_tokens(command)) if powershell else shlex.split(command, posix=True)
    except ValueError:
        toks = command.split()
    out = []
    cmd = ""
    skip_pattern = False
    glued = False
    locations = []
    for t in toks:
        if glued:                               # прошлый токен кончался `;` — новая команда
            cmd, glued = "", False
        separator = ps_operator(t, {"|", "||", "&&", ";", "&", "(", ")"}) if powershell else t in ("|", "||", "&&", ";")
        if separator:
            cmd = ""
            continue
        if not powershell and t.endswith(";") and len(t) > 1:
            t, glued = t[:-1], True
        if not cmd and not re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", t):
            cmd = os.path.basename(t).lower() if powershell else os.path.basename(t)
            if powershell and cmd in {"pop-location", "popd"} and locations:
                cwd = locations.pop()
            skip_pattern = cmd in BASH_PATTERN_CMDS
            continue
        redirect = ps_operator(t, {">", ">>", "<"}) if powershell else t in (">", ">>", "<")
        if not t or t.startswith("-") or redirect:
            continue
        if cmd in ({"cd", "set-location", "sl", "chdir", "push-location", "pushd"} if powershell else {"cd"}):
            d = os.path.abspath(os.path.join(cwd, os.path.expanduser(t)))
            if os.path.isdir(d):
                if powershell and cmd in {"push-location", "pushd"}:
                    locations.append(cwd)
                cwd = d
        if skip_pattern:
            skip_pattern = False
            continue
        reads = BASH_LIST_CMDS | {"get-content", "gc", "type", "get-childitem", "gci", "dir", "set-location", "sl", "chdir", "push-location", "pushd"}
        if "/" not in t and (not powershell or "\\" not in t) and cmd not in (reads if powershell else BASH_LIST_CMDS):
            continue
        t = _literal_lead(t) if GLOB_CHARS & set(t) else t
        if not t:
            continue
        p = os.path.abspath(os.path.join(cwd, os.path.expanduser(t)))
        try:
            inside = os.path.normcase(os.path.commonpath([p, root])) == os.path.normcase(root)
        except ValueError:  # другой диск Windows
            inside = False
        if os.path.exists(p) and inside and p not in out:
            out.append(p)
    return out


def unwrap_shell(text: str) -> str:
    """`/bin/bash -lc "sed -n '1,20p' f.md"` → `sed -n '1,20p' f.md`.

    Codex заворачивает каждый вызов в оболочку; без снятия обёртки разбор путей видит
    только `bash` и `-lc`, и вход в узел не срабатывает вовсе.
    """
    import shlex
    ps = powershell_tokens(text)
    if ps and ps[0] == "&":
        ps = ps[1:]
    if ps and ps[0].replace("\\", "/").rsplit("/", 1)[-1].lower() in {"powershell", "pwsh", "powershell.exe", "pwsh.exe"}:
        for i, tok in enumerate(ps[:-1]):
            if tok.lower() in {"-command", "-c"}:
                if i + 2 == len(ps):
                    return str(ps[i + 1])
                if ps[i + 1].quoted:
                    return str(ps[i + 1]) + " " + text[ps[i + 2].start:]
                return text[ps[i + 1].start:]
        return text
    try:
        parts = shlex.split(text, posix=True)
    except ValueError:
        return text
    executable = ps[0].replace("\\", "/").rsplit("/", 1)[-1].lower().removesuffix(".exe") if ps else ""
    if len(parts) >= 3 and executable in ("bash", "sh", "zsh", "dash"):
        for i, tok in enumerate(parts[1:], start=1):
            if re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", tok) and i + 1 < len(parts):
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
    inner = []
    for m in JS_EXEC_RE.finditer(text):
        quote, value = m.group(1), m.group(2)
        try:
            if quote == '"':
                value = json.loads(quote + value + quote)
            elif quote == "'":
                import ast
                value = ast.literal_eval(quote + value + quote)
            else:
                escapes = {"\\": "\\", "n": "\n", "r": "\r", "t": "\t", "`": "`"}
                value = re.sub(r"\\([\\nrt`])", lambda m: escapes[m.group(1)], value)
        except (ValueError, SyntaxError):
            pass
        inner.append(value)
    return vm_to_host("\n".join(unwrap_shell(t) for t in (inner or [text])))


def vm_to_host(text: str) -> str:
    """Cowork «Only on this computer»: bash исполняется в VM, подключённая папка там —
    `/sessions/<сессия>/mnt/<имя папки>`; хук живёт на хосте. Переводим в путь хоста
    по имени папки из CLAUDE_CODE_WORKSPACE_HOST_PATHS. Вне Cowork — без изменений."""
    if os.environ.get("CLAUDE_CODE_IS_COWORK") != "1" or "/mnt/" not in text:
        return text
    raw = (os.environ.get("CLAUDE_CODE_WORKSPACE_HOST_PATHS") or "").strip()
    folders = [raw] if os.path.isdir(raw) else raw.split("|")
    by_name: dict[str, str] = {}
    twins = set()
    for f in (x.strip().rstrip("/") for x in folders):
        if f and os.path.isdir(f):
            n = os.path.basename(f)
            if n in by_name and by_name[n] != f:
                twins.add(n)        # две папки с одним именем: путь VM неоднозначен — не переводим
            by_name[n] = f
    if twins:
        log("vm-path-ambiguous", names=sorted(twins))
    by_name = {n: f for n, f in by_name.items() if n not in twins}
    if not by_name:
        return text
    # путь VM — только с начала токена: подстрока внутри чужого пути не переводится
    rx = re.compile(r"(?<![^\s'\"`=(;&|<>])/sessions/[^/\s'\"]+/mnt/(" + "|".join(re.escape(n) for n in by_name)
                    + r")(?=[/\s'\"`;&|)]|$)")
    return rx.sub(lambda m: by_name[m.group(1)], text)


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
        return bash_paths(shell_text(ti), cwd, root, powershell=powershell_input(ti, name))
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
    try:
        rel = os.path.relpath(target, root)
    except ValueError:  # Windows: обращение на другом диске не относится к пространству
        return None
    first = rel.split(os.sep)[0]
    if rel.startswith("..") or first in (".", "") or first.startswith(".") \
            or first in SERVICE_DIRS or first in NOT_NODES:
        return None
    return first if os.path.isdir(os.path.join(root, first)) else None


def nodes_of(root: str, target: str) -> list[str]:
    """Узлы на пути к target сверху вниз: верхний уровень + каждая папка глубже с
    README.md (вложенный узел: commercial/sales, customer-success/projects) —
    юнит это или нет, не важно, важно наличие своей карты.
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

def map_context(gen, root: str, when: str, ask: bool, session_id: str = "") -> tuple[str, dict]:
    """Карта (персональная после whoami в этой сессии, иначе общая)."""
    from pathlib import Path
    base = Path(root)
    identity = gen.read_session(session_id, base)
    no_model = model_in_root(root)
    personal = bool(identity)
    units = list(identity.get("units") or []) if personal else []
    body = gen.emit_text(base, focus=units, no_model=no_model,
                         no_skills=os.environ.get("SVAIB_MAP_SKILLS") != "1")
    if personal:
        ceo = gen.is_ceo_profile(identity.get("profile_path", ""))
        zone = ("зона " + " · ".join(f"`{u}/`" for u in units)) if units else (
            "прямой маршрут к целям компании" if ceo else "management units зоны не выведены")
        head = (f"## Карта пространства {when}\n\n"
                f"{gen.who_line(identity['subject'], identity.get('name', ''))}, профиль "
                f"`{identity.get('profile_path') or '—'}`, {zone} — установлен через `whoami` в этой сессии.")
        if not units and not ceo:   # до блоков ниже: иначе фраза приклеивается к хвосту последнего из них
            head += (" Management units зоны не выведены — работай по общей карте: подкарта узла придёт "
                     "при первом обращении к его файлам.")
        head += (f"{gen.keyboard_line(identity.get('name', ''))}{gen.onboarding_block(identity)}"
                 f"{gen.preferences_line(identity.get('preferences', ''))}")
    else:
        head = (f"## Карта пространства {when}\n\n"
                f"`map_profile: general` — карта общая, пользователь не установлен.")
        if ask:
            head += "\n\n" + ASK_WHOAMI
    meta = {"profile": identity["subject"] if personal else "general", "units": units, "no_model": no_model}
    if body.startswith("## Карта пространства"):
        body = body.split("\n", 1)[1].lstrip("\n")  # H2 генератора — лишний, заголовок даёт хук
    goals = gen.goals_context(base, identity.get("profile_path", ""), units,
                              identity.get("unit_source", "")) if personal else ""
    rules = gen.space_rules(base)
    return head + ("\n\n" + goals if goals else "") + "\n\n" + body + ("\n\n" + rules if rules else ""), meta


def personalize_context(gen, root: str, hook_input: dict) -> tuple[str, dict]:
    from pathlib import Path
    who = gen.parse_whoami(hook_input.get("tool_response"))
    text, rec = gen.personalize(Path(root), who)
    try:
        gen.write_session(hook_input.get("session_id") or "", Path(root), rec)
    except OSError as exc:
        log("skip", mode="post-whoami", reason=f"session write failed: {exc}")
    return "## Персонализация карты (после `whoami`)\n\n" + text, {"profile": who["subject"], "units": rec["units"]}


def node_context(gen, root: str, node: str) -> str:
    from pathlib import Path
    body = gen.emit_node_text(Path(root), node)
    if body.startswith("## Карта узла"):
        body = body.split("\n", 1)[1].lstrip("\n")
    return f"## Подкарта узла `{node}/`\n\n" + NODE_LEAD.format(node=node) + "\n\n" + body


def emit(context: str, event: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": context}},
                     ensure_ascii=False))


EVENT = {"first-prompt": "UserPromptSubmit", "post-whoami": "PostToolUse", "node-enter": "PostToolUse",
         "compact": "SessionStart"}


MODES = ("first-prompt", "post-whoami", "post-update-me", "node-enter", "compact", "plain")
WHOAMI_RE = re.compile(r"^mcp__.+__whoami$")
UPDATE_ME_RE = re.compile(r"^mcp__.+__update_me$")


def run(mode: str, hook_input: dict) -> None:
    sid = hook_input.get("session_id") or ""
    nkey = node_key(hook_input)
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
    if mode == "node-enter" and WHOAMI_RE.match(hook_input.get("tool_name") or ""):
        # Codex: отдельной регистрации на whoami у него нет, вызов приходит сюда —
        # персонализация та же, что у Claude по matcher `mcp__.*__whoami`
        mode = "post-whoami"
    if mode == "node-enter" and UPDATE_ME_RE.match(hook_input.get("tool_name") or ""):
        mode = "post-update-me"   # то же для update_me
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
                if n not in nodes and not node_marker_exists(nkey, n):
                    nodes.append(n)
        if not nodes:
            return
    t0 = time.monotonic()
    gen = load_generator(root)
    if gen is None:
        log("skip", mode=mode, reason="no generator", root=root)
        print("inject_space_map: генератор карты не найден — карта не подана", file=sys.stderr)
        return
    if mode == "post-update-me":
        from pathlib import Path
        ok = gen.apply_update_me(Path(root), sid, hook_input.get("tool_response"))
        log("ok" if ok else "skip", mode=mode, root=root, session_updated=ok)
        return
    if mode == "post-whoami":
        context, meta = personalize_context(gen, root, hook_input)
    elif mode == "node-enter":
        context, meta = "\n\n".join(node_context(gen, root, n) for n in nodes), {"node": "+".join(nodes), "event": event, "tool": tool}
    else:
        when = {"compact": "после сжатия контекста"}.get(mode, "на первом запросе сессии")
        context, meta = map_context(gen, root, when, ask=(mode != "plain"), session_id=sid)
    if mode == "first-prompt" and not marker_set(sid):
        return  # параллельный запуск уже доставил
    if mode == "node-enter":
        won = [n for n in nodes if node_marker_set(nkey, n)]
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
            node_marker_set(nkey, u)
    if mode == "first-prompt":
        gc_markers()


def main():
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "first-prompt"
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    try:   # чтение и разбор ввода — внутри той же границы: битый байт в stdin не роняет хук
        raw = sys.stdin.read()
        run(mode, json.loads(raw) if raw.strip() else {})
    except Exception as e:  # noqa: BLE001 — хук не имеет права уронить сессию
        log("error", mode=mode, error=f"{type(e).__name__}: {e}")
        print(f"inject_space_map: {type(e).__name__}: {e}", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
