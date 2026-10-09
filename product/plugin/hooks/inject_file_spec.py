#!/usr/bin/env python3
"""
Спецификация файла до записи.

    inject_file_spec.py pre-write   # PreToolUse (Claude: Write|Edit|MultiEdit|Bash; Codex: apply_patch и shell)
    inject_file_spec.py compact     # SessionStart compact|clear (Claude) / PostCompact (Codex)

Агент пишет в канонический файл пространства, а спецификации этого типа в сессии ещё не было —
хук отклоняет запись и кладёт текст спецификации в причину отказа. Агент читает её и повторяет
запись уже по контракту; повторно та же спецификация не приходит. Отказ, а не добавленный
контекст: контекст приходит вместе с записью, которая к тому моменту уже выполнена.

Тип файла — по каноническому имени (KIT_RE, REFERENCE_NAMES): kit-файлы `NN_<тип>.md`, выжимка встречи
`meetings/<папка>/summary.md`, справочные файлы из спецификации `reference`. Первой идёт
`00_general.md` — общие правила читаются до спецификации типа (README папки спецификаций).
Обычно всё приходит одним отказом; не влезшее в BUDGET — следующим. Имена сравниваются без учёта
регистра: на macOS и Windows `02_Active.md` — тот же файл.

Запись оболочкой ловится базово (`bash_writes`): перенаправление, `tee`, `sed -i`/`perl -i`, получатель
`cp`/`mv`/`install`/`ln`/`rsync`, явная запись в коде интерпретатора (`open(путь, 'w')`,
`Path(путь).write_text`, `writeFile`; путь — литерал или переменная из того же скрипта),
`apply_patch` через shell. Разбор оболочки — сито, а не полный парсер. Упоминание пути в коде — в тексте замены, в
строке данных — не запись. Пути — от cwd сессии, после `cd X` в той же команде — от X; тип определяется именем. В Cowork путь VM
`/sessions/<сессия>/mnt/<папка>` переводится в путь хоста (`nav.vm_to_host`).
Inline Python разбирается статически: присваивания по порядку, конкатенация строк, списки и кортежи
путей, накопление ключей словаря и запись циклом по `.items()`. Код не исполняется; произвольные
функции и динамические выражения путей не вычисляются. Другие интерпретаторы — сито по вызовам.
Не ловятся запись через переменную оболочки, `find -exec`, скрипт-файл, пишущий сам, и чтение спецификации
агентом самим. Хук — перила для невраждебного агента, не замок.

Разбор оболочки, корень пространства и state-каталог — из соседнего `inject_space_map.py`: один
разбор на оба хука (снятие обёртки Codex, JS code-mode, имена shell-инструментов).

Спецификации ищутся: `SVAIB_FILE_SPECS` → рядом с хуком в плагине
(`../skills/space/scaffold/file-specs`) → канон в репозитории svaib. Версия структуры пространства
(`.svaib/space.json`) расходится с версией плагина (`version.txt` скилла) — отказ называет расхождение. Метки «подано» — в state-каталоге
машины (тот же, что у хука карты, и его уборка старше 7 дней), по сессии и субагенту — у субагента
свой контекст; Codex `agent_id` в событии не гарантирует, тогда субагент делит метки с сессией.
После сжатия контекста метки снимаются.

Любой сбой — stderr и код 0: запись не блокируется из-за поломки хука.
"""
from __future__ import annotations

import ast
import copy
import datetime
import json
import os
import re
import shlex
import sys
import time

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HOOK_DIR)
try:
    import inject_space_map as nav         # едет рядом: плагин, .claude/hooks, .agents/hooks
except Exception:  # noqa: BLE001 — без соседа хук молчит, запись не блокируется
    nav = None
SPEC_DIR_CANDIDATES = (
    os.path.join(HOOK_DIR, "..", "skills", "space-scaffold", "file-specs"),        # поставка плагином
    os.path.join(HOOK_DIR, "..", "skills", "space", "scaffold", "file-specs"),     # исходники до сборки
    os.path.join("product", "methodology", "space", "scaffold", "file-specs"),     # репозиторий svaib
    os.path.join("product", "methodology", "scaffold", "file-specs"),              # он же до переноса
)
# Пространство svaib, а не любой проект с CLAUDE.md: плагин ставится на пользователя и видит все его
# проекты. Служебную папку заводит миграция структуры вместе с плагином.
SPACE_MARK = ".svaib"
GENERAL = "00_general.md"
KIT_RE = re.compile(r"^\d\d_(overview|active|backlog|progress|decisions)\.md$", re.I)
REFERENCE_NAMES = {"person.md", "profile.md", "architecture.md", "setup.md", "glossary.md", "speech-aliases.md"}
SKIP_DIRS = {"_templates", "zz_archive", "node_modules"}          # шаблоны и архив — не рабочие файлы
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "apply_patch"}
# Каноническое имя где-то в тексте команды — быстрый отсев: без него оболочку не разбираем.
NAME_RE = re.compile(r"[\w./~-]*?(?:\d\d_(?:overview|active|backlog|progress|decisions)|summary|person|profile|"
                     r"architecture|setup|glossary|speech-aliases)\.md", re.I)
REDIRECTS = {">", ">>", ">|", "&>", "&>>"}
SEPARATORS = {"|", "||", "&&", ";", "&", "(", ")"}
COPY_CMDS = {"cp", "mv", "install", "ln", "rsync"}
INPLACE_CMDS = {"sed", "perl", "ruby"}
SCRIPT_CMDS = {"python", "python3", "node", "perl", "ruby", "deno", "bun"}
PREFIX_CMDS = {"sudo", "env", "command", "time", "nice", "nohup"}   # `echo x | sudo tee f` — пишет tee
# Явная запись в коде интерпретатора: аргумент — литерал пути или переменная, которой он присвоен.
_ARG = r"(?:[rbuf]{0,2}(['\"])(?P<lit>[^'\"\n]+)\1|(?P<var>[A-Za-z_]\w*))"
_MODE = r"(?:mode\s*=\s*)?[rbuf]{0,2}['\"][^'\"]*[wax+]"
WRITE_CALL_RES = (
    re.compile(r"\bopen\(\s*" + _ARG + r"\s*,\s*" + _MODE),
    re.compile(r"\bPath\(\s*" + _ARG + r"\s*\)\s*\.\s*(?:write_text|write_bytes|open\(\s*" + _MODE + ")"),
    re.compile(r"\b(?:writeFile|appendFile)(?:Sync)?\(\s*" + _ARG),
    re.compile(r"\b(?P<var>[A-Za-z_]\w*)\s*\.\s*(?:write_text|write_bytes)\("),     # p = Path('…'); p.write_text
)
PATH_ASSIGN_RE = re.compile(r"\b([A-Za-z_]\w*)\s*=\s*(?:Path\(\s*)?[rbuf]{0,2}(['\"])([^'\"\n]+)\2")
ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")   # `PYTHONUTF8=1 python3 …` — окружение перед командой
PATCH_RE = re.compile(r"^\*\*\* (?:Add|Update) File: (.+?)\s*$|^\*\*\* Move to: (.+?)\s*$", re.M)
SID_RE = re.compile(r"[^A-Za-z0-9_.-]")
# Символов во всей причине отказа. Отказ в 18 тыс. символов доходит до агента
# целиком и в Claude Code 2.1.276, и в Codex 0.154.0; жёсткий предел Claude Code — 64 КБ stdout,
# за ним отказ теряется и запись проходит. Пара «общие правила + тип» держится в BUDGET — страж в тестах.
BUDGET = 20000
# Секунд после выдачи, в которые запись того же типа считается соседним вызовом того же хода: модель
# ещё не видела отказ. Короткий отказ
# получает любая такая запись, и в тот же файл: пачка из нескольких Edit одного файла — частый вид
# соседей. Эвристика, не граница хода: сосед после долгого Bash в той же пачке пройдёт, а слишком
# быстрый повтор получит ещё один короткий отказ (~175 символов). Точная граница — новый ответ модели
# в транскрипте.
SAME_TURN = 5
MAX_NAMES = 5   # целей в тексте отказа: заплатка на сотни файлов не должна раздувать его


# ---------------------------------------------------------------------------- инфраструктура

def state_dir() -> str:
    return nav.state_dir() if nav else os.path.expanduser("~/.local/state/svaib")


def log(outcome: str, **kv) -> None:
    try:
        os.makedirs(state_dir(), exist_ok=True)
        rec = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
               "outcome": outcome, **kv}
        with open(os.path.join(state_dir(), "file-spec-hook.log"), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


def spec_dir(root: str) -> str | None:
    env = os.environ.get("SVAIB_FILE_SPECS")
    for cand in ((env,) if env else ()) + SPEC_DIR_CANDIDATES:
        path = cand if os.path.isabs(cand) else os.path.join(root, cand)
        if os.path.isfile(os.path.join(path, GENERAL)):
            return os.path.realpath(path)
    return None


def sid_part(sid: str) -> str:
    return SID_RE.sub("_", sid)[:80]           # как у хука карты


def session_key(hook_input: dict) -> str:
    sid = sid_part(hook_input.get("session_id") or "")
    agent = SID_RE.sub("_", hook_input.get("agent_id") or "")[:40]
    return f"{sid}.{agent}" if agent else sid


def marker_path(key: str, spec: str) -> str:
    return os.path.join(state_dir(), "sessions", f"{key}.spec.{SID_RE.sub('_', spec)}")


def marker_set(key: str, spec: str, call: str = "") -> None:
    """В метке — id вызова, на котором спецификация выдана: второй экземпляр хука узнаёт свой же вызов."""
    p = marker_path(key, spec)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(call)


def marker_call(key: str, spec: str) -> str:
    try:
        with open(marker_path(key, spec), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def markers_clear(sid: str) -> None:
    """Сжатие снимает метки сессии и её субагентов: спецификации ушли из контекста."""
    sid = sid_part(sid)
    d = os.path.join(state_dir(), "sessions")
    try:
        for name in os.listdir(d):
            if name.startswith(f"{sid}.") and ".spec." in name:
                os.remove(os.path.join(d, name))
    except OSError:
        pass


# ---------------------------------------------------------------------------- что пишется и чем

def is_shell(tool: str) -> bool:
    return tool == "Bash" or tool in nav.SHELL_TOOLS


def _tokens(line: str) -> list[str]:
    lex = shlex.shlex(line, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    return list(lex)


def _logical_lines(text: str) -> list[tuple[list[str], str]]:
    """Команда → логические строки (токены, тело heredoc). Строка с незакрытой кавычкой склеивается
    со следующими — многострочное сообщение коммита остаётся одним аргументом. Heredoc — по токену
    `<<` вне кавычек (`<<<` — не heredoc); его тело — данные, не команды."""
    lines, out, i = text.split("\n"), [], 0
    while i < len(lines):
        chunk, i = lines[i], i + 1
        while True:
            try:
                toks = _tokens(chunk)
                break
            except ValueError:
                if i >= len(lines):
                    toks = chunk.split()
                    break
                chunk, i = chunk + "\n" + lines[i], i + 1
        body = []
        for k, t in enumerate(toks[:-1]):
            if t == "<<":
                delim = toks[k + 1].lstrip("-")
                while i < len(lines) and lines[i].strip() != delim:
                    body.append(lines[i])
                    i += 1
                i += 1
                break
        out.append((toks, "\n".join(body)))
    return out


def _segment_writes(toks: list[str], cwd: str) -> tuple[str, list[str]]:
    """Команда простого сегмента и файлы, в которые он пишет."""
    out = []
    args = [t for t in toks if not ASSIGN_RE.match(t)] or [""]
    while len(args) > 1 and os.path.basename(args[0]) in PREFIX_CMDS:
        args = args[1:]
        while len(args) > 1 and args[0].startswith("-"):
            args = args[1:]
    cmd, rest = os.path.basename(args[0]), args[1:]
    if cmd == "git" and rest[:1] == ["mv"]:
        cmd, rest = "mv", rest[1:]
    for k, t in enumerate(toks[:-1]):
        if t in REDIRECTS and not toks[k + 1].startswith("&"):
            out.append(toks[k + 1])
    rest = [t for k, t in enumerate(rest) if t not in REDIRECTS and (k == 0 or rest[k - 1] not in REDIRECTS)]
    plain = [t for t in rest if not t.startswith("-")]
    if cmd == "tee":
        out += plain
    elif cmd in INPLACE_CMDS and any(re.match(r"^-[a-zA-Z]*i|^--in-place", t) for t in rest):
        out += plain                                   # скрипт sed тоже попадёт — отсеет spec_of
    elif cmd in COPY_CMDS and len(plain) >= 2:
        dest = plain[-1]
        if dest.endswith("/") or os.path.isdir(os.path.join(cwd, os.path.expanduser(dest))):
            out += [os.path.join(dest, os.path.basename(src.rstrip("/"))) for src in plain[:-1]]
        else:
            out.append(dest)
    return cmd, out


class _PythonPaths:
    """Статический срез путей: литералы, конкатенация, таблицы и конечные циклы.

    Содержимое файлов, функции и произвольные выражения не вычисляются. Множество строк —
    возможные значения пути; список/кортеж/словарь — таблица для распаковки и обхода.
    """

    def __init__(self):
        self.env = {}
        self.writes = []
        self.modules = {name: name for name in ("pathlib", "io", "builtins")}
        self.symbols = {"Path": "pathlib.Path", "open": "builtins.open"}

    def value(self, node):
        if isinstance(node, getattr(ast, "Index", ())):
            return self.value(node.value)     # Python 3.8 оборачивает ключ Subscript в Index
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return {node.value}
        if isinstance(node, ast.Constant) and isinstance(node.value, bytes):
            return {os.fsdecode(node.value)}
        if isinstance(node, ast.JoinedStr) and all(
                isinstance(n, ast.Constant) and isinstance(n.value, str) for n in node.values):
            return {"".join(n.value for n in node.values)}   # f-строка без подстановок — литерал
        if isinstance(node, ast.Name):
            return self.env.get(node.id)
        if isinstance(node, ast.List):
            return [self.value(n) for n in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(self.value(n) for n in node.elts)
        if isinstance(node, ast.Dict):
            return {k: self.value(v) for key, v in zip(node.keys, node.values)
                    for k in (self.value(key) or ()) if isinstance(k, str)}
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            a, b = self.value(node.left), self.value(node.right)
            if isinstance(a, set) and isinstance(b, set):
                return {x + y for x in a for y in b}
            if isinstance(a, list) and isinstance(b, list):
                return a + b
            if isinstance(a, tuple) and isinstance(b, tuple):
                return a + b
        if isinstance(node, ast.Call):
            fn = node.func
            if node.args and (isinstance(fn, ast.Name) and self.symbols.get(fn.id) == "pathlib.Path" or
                              isinstance(fn, ast.Attribute) and fn.attr == "Path" and
                              isinstance(fn.value, ast.Name) and
                              self.modules.get(fn.value.id) == "pathlib"):
                paths = {""}
                for arg in node.args:
                    parts = self.value(arg)
                    if not isinstance(parts, set):
                        return None
                    paths = {os.path.join(a, b) for a in paths for b in parts}
                return paths
            if isinstance(fn, ast.Name) and fn.id in {"list", "tuple"} and node.args:
                values = self.iterable(self.value(node.args[0]))
                return tuple(values) if fn.id == "tuple" and values is not None else values
            if isinstance(fn, ast.Name) and not node.args and not node.keywords:
                if fn.id == "dict":
                    return {}
                if fn.id == "tuple":
                    return ()
                if fn.id == "list":
                    return []
            if isinstance(fn, ast.Attribute):
                obj = self.value(fn.value)
                if isinstance(obj, dict) and not node.args and not node.keywords:
                    if fn.attr == "items":
                        return [[{k}, v] for k, v in obj.items()]
                    if fn.attr == "keys":
                        return [{k} for k in obj]
        return None

    @staticmethod
    def iterable(value):
        if isinstance(value, dict):
            return [{k} for k in value]
        return list(value) if isinstance(value, (list, tuple)) else None

    def bind(self, target, value):
        if isinstance(target, ast.Name):
            self.env[target.id] = value
        elif isinstance(target, (ast.Tuple, ast.List)):
            for i, t in enumerate(target.elts):
                self.bind(t, value[i] if isinstance(value, (list, tuple)) and i < len(value) else None)
        elif isinstance(target, ast.Subscript):
            obj, keys = self.value(target.value), self.value(target.slice)
            if isinstance(obj, dict) and isinstance(keys, set):
                for key in keys:
                    obj[key] = value

    def calls(self, expr):
        if expr is None:
            return
        pending = [expr]
        while pending:
            node = pending.pop()
            if isinstance(node, ast.Lambda):
                continue                     # определение функции само не выполняет запись
            pending.extend(ast.iter_child_nodes(node))
            if not isinstance(node, ast.Call):
                continue
            fn, path, modes = node.func, None, None
            if (isinstance(fn, ast.Name) and self.symbols.get(fn.id) in {"io.open", "builtins.open"} or
                              isinstance(fn, ast.Attribute) and fn.attr == "open" and
                              isinstance(fn.value, ast.Name) and
                              self.modules.get(fn.value.id) in {"io", "builtins"}):
                path = self.value(node.args[0]) if node.args else next(
                    (self.value(kw.value) for kw in node.keywords if kw.arg == "file"), None)
                modes = self.value(node.args[1]) if len(node.args) > 1 else None
            elif isinstance(fn, ast.Attribute):
                if fn.attr in {"write_text", "write_bytes"}:
                    path, modes = self.value(fn.value), {"w"}
                elif fn.attr == "open":
                    path = self.value(fn.value)
                    modes = self.value(node.args[0]) if node.args else None
            for kw in node.keywords:
                if kw.arg == "mode":
                    modes = self.value(kw.value)
            if isinstance(path, set) and isinstance(modes, set) and any(
                    any(c in mode for c in "wax+") for mode in modes):
                self.writes.extend(sorted(path))

    @classmethod
    def merge(cls, a, b):
        if a is b:
            return a
        if isinstance(a, set) and isinstance(b, set):
            return a | b
        if isinstance(a, dict) and isinstance(b, dict):
            return {k: cls.merge(a.get(k), b.get(k)) for k in a.keys() | b.keys()}
        if a is None:
            return b
        if b is None:
            return a
        if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
            # Сохраняем позиции: строку таблицы могут распаковать после ветвления.
            values = [cls.merge(a[i] if i < len(a) else None,
                                b[i] if i < len(b) else None)
                      for i in range(max(len(a), len(b)))]
            return tuple(values) if isinstance(a, tuple) and isinstance(b, tuple) else values
        return a if a == b else None

    def run(self, statements):
        for stmt in statements:
            if isinstance(stmt, ast.Import):
                for alias in stmt.names:
                    if alias.name in {"pathlib", "io", "builtins"}:
                        self.modules[alias.asname or alias.name] = alias.name
            elif isinstance(stmt, ast.ImportFrom) and not stmt.level:
                for alias in stmt.names:
                    symbol = f"{stmt.module}.{alias.name}"
                    if symbol in {"pathlib.Path", "io.open", "builtins.open"}:
                        self.symbols[alias.asname or alias.name] = symbol
            elif isinstance(stmt, (ast.Assign, ast.AnnAssign)):
                self.calls(stmt.value)
                value = self.value(stmt.value)
                targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
                for target in targets:
                    self.bind(target, value)
            elif isinstance(stmt, ast.AugAssign):
                self.calls(stmt.value)
                self.bind(stmt.target, self.value(ast.BinOp(
                    left=stmt.target, op=stmt.op, right=stmt.value)))
            elif isinstance(stmt, ast.Expr):
                self.calls(stmt.value)
            elif isinstance(stmt, (ast.For, ast.AsyncFor)):
                self.calls(stmt.iter)
                values = self.iterable(self.value(stmt.iter))
                # Неизвестный цикл не наследует последнее значение переменной до него.
                for value in values if values is not None else [None]:
                    self.bind(stmt.target, value)
                    self.run(stmt.body)
                self.run(stmt.orelse)
            elif isinstance(stmt, ast.If):
                self.calls(stmt.test)
                before = copy.deepcopy(self.env)
                self.run(stmt.body)
                yes = self.env
                self.env = before
                self.run(stmt.orelse)
                self.env = self.merge(yes, self.env)
            elif isinstance(stmt, ast.While):
                self.calls(stmt.test)
                before = copy.deepcopy(self.env)
                # Достаточно одного статического прохода: цикл не исполняем.
                self.run(stmt.body)
                self.env = self.merge(before, self.env)
                self.run(stmt.orelse)
            elif isinstance(stmt, (ast.Try, getattr(ast, "TryStar", ast.Try))):
                before = copy.deepcopy(self.env)
                self.run(stmt.body)
                self.run(stmt.orelse)
                possible = self.merge(before, self.env)
                outcomes = self.env
                for handler in stmt.handlers:
                    self.env = copy.deepcopy(possible)
                    if handler.name:
                        self.env[handler.name] = None
                    self.run(handler.body)
                    outcomes = self.merge(outcomes, self.env)
                self.env = outcomes
                self.run(stmt.finalbody)
            elif isinstance(stmt, getattr(ast, "Match", ())):
                self.calls(stmt.subject)
                before = copy.deepcopy(self.env)
                outcomes = before
                for case in stmt.cases:
                    self.env = copy.deepcopy(before)
                    self.calls(case.guard)
                    self.run(case.body)
                    outcomes = self.merge(outcomes, self.env)
                self.env = outcomes
            elif isinstance(stmt, (ast.With, ast.AsyncWith)):
                for item in stmt.items:
                    self.calls(item.context_expr)
                    if item.optional_vars:
                        self.bind(item.optional_vars, None)
                self.run(stmt.body)
            elif isinstance(stmt, ast.Assert):
                self.calls(stmt.test)
                self.calls(stmt.msg)


def script_writes(code: str, *, python: bool = True) -> list[str]:
    """Явные записи inline-скрипта; код не исполняется. Динамические пути не ловятся."""
    if python:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            pass
        else:
            paths = _PythonPaths()
            paths.run(tree.body)
            return list(dict.fromkeys(paths.writes))
    # Присваивания и записи читаются по порядку: одна переменная часто используется для
    # нескольких файлов. Последнее присваивание во всём скрипте не относится к ранним записям.
    events = [(m.start(), True, m) for m in PATH_ASSIGN_RE.finditer(code)]
    events += [(m.start(), False, m) for rx in WRITE_CALL_RES for m in rx.finditer(code)]
    assigned = {}
    out = []
    for _, is_assignment, m in sorted(events, key=lambda event: event[0]):
        if is_assignment:
            assigned[m.group(1)] = m.group(3)
            continue
        groups = m.groupdict()
        path = groups.get("lit") or assigned.get(groups.get("var") or "")
        if path:
            out.append(path)
    return out


def bash_writes(text: str, cwd: str) -> list[str]:
    """Файлы, в которые пишет команда оболочки. Сито, а не парсер: лишний кандидат отсеет
    `spec_of`, а ложная спецификация стоит одного отказа за сессию."""
    if not NAME_RE.search(text) and not re.search(r"\bpython3?\b", text):
        return []
    found: list[str] = []
    if "*** Begin Patch" in text:                      # Codex зовёт apply_patch и через оболочку
        found += [a or b for a, b in PATCH_RE.findall(text)]
    for toks, body in _logical_lines(text):
        seg: list[str] = []
        for t in toks + [";"]:
            if t not in SEPARATORS:
                seg.append(t)
                continue
            if seg:
                cmd, writes = _segment_writes(seg, cwd)
                if cmd in SCRIPT_CMDS:                 # код интерпретатора: только явная запись
                    flags = {"-c"} if cmd in {"python", "python3"} else {"-e", "--eval"}
                    # С -c/-e heredoc — входные данные, а не исполняемый код.
                    code = next((seg[i + 1] for i, flag in enumerate(seg[:-1]) if flag in flags),
                                body or " ".join(seg))
                    writes += script_writes(code, python=cmd in {"python", "python3"})
                found += [os.path.join(cwd, os.path.expanduser(p)) for p in writes]
                # `cd X && tee a.md`: дальше пути от X (Cowork ходит так по VM); через `|` cd не
                # действует — там подоболочка, и чужой cwd дал бы ложный отказ
                if cmd == "cd" and len(seg) > 1 and t != "|":
                    d = os.path.abspath(os.path.join(cwd, os.path.expanduser(seg[-1])))
                    if os.path.isdir(d):
                        cwd = d
            seg = []
    return found


def targets_of(hook_input: dict, root: str) -> list[str]:
    ti = hook_input.get("tool_input") or {}
    if not isinstance(ti, dict):
        ti = {"patch": str(ti)}
    tool = hook_input.get("tool_name") or ""
    cwd = hook_input.get("cwd") or root
    if tool == "apply_patch":
        # Codex: пути только в тексте заплатки, файлов может быть несколько; поле зависит от версии
        paths = [a or b for v in ti.values() if isinstance(v, str) for a, b in PATCH_RE.findall(v)]
    elif is_shell(tool):
        paths = bash_writes(nav.shell_text(ti), cwd)
    else:
        paths = [ti[k] for k in ("file_path", "path") if isinstance(ti.get(k), str)]
    out = []
    for p in paths:
        full = os.path.normpath(p if os.path.isabs(p) else os.path.join(cwd, p))
        if full not in out:
            out.append(full)
    return out


def spec_of(root: str, sdir: str, target: str) -> str | None:
    """Имя файла спецификации для цели записи или None, если файл не канонический."""
    try:
        rel = os.path.relpath(target, root)
    except ValueError:                        # Windows: другой диск — не наше пространство
        return None
    if rel == ".." or rel.startswith(".." + os.sep) or os.path.realpath(target).startswith(sdir + os.sep):
        return None
    parts = rel.split(os.sep)
    if any(p.startswith(".") or p.lower() in SKIP_DIRS for p in parts[:-1]):
        return None
    if any(a == "scaffold" and b == "templates" for a, b in zip(parts, parts[1:])):   # шаблоны в исходнике скилла
        return None
    name = parts[-1].lower()
    m = KIT_RE.match(name)
    if m:
        spec = f"{m.group(1)}.md"
    elif name == "summary.md" and len(parts) >= 3 and parts[-3].lower() == "meetings":
        spec = "meeting-summary.md"
    elif name in REFERENCE_NAMES:
        spec = "reference.md"
    else:
        return None
    return spec if os.path.isfile(os.path.join(sdir, spec)) else None


def _version(v: str) -> tuple[int, ...] | None:
    try:
        return tuple(int(x) for x in v.strip().split("."))
    except (ValueError, AttributeError):
        return None


def version_note(root: str, sdir: str) -> str:
    """Пространство и плагин разных версий структуры — строка для отказа; иначе пусто.

    Плагины у участников общего пространства обновляются каждый на своей машине, и окно, когда
    структура уже новее спецификаций, реально. Версия плагина — `version.txt` рядом с file-specs:
    в репозитории svaib её нет, и сверки нет."""
    try:
        with open(os.path.join(sdir, "..", "version.txt"), encoding="utf-8") as f:
            plugin_v = f.read().strip()
    except OSError:
        return ""
    try:                                             # файла нет — пространство версии 4.0, как в скилле scaffold
        with open(os.path.join(root, SPACE_MARK, "space.json"), encoding="utf-8") as f:
            space_v = str(json.load(f).get("scaffold_version", ""))
    except FileNotFoundError:
        space_v = "4.0"
    except (OSError, ValueError, AttributeError):
        return ""
    pv, sv = _version(plugin_v), _version(space_v)
    if not pv or not sv:
        return ""
    width = max(len(pv), len(sv))                    # 4.2 и 4.2.0 — одна версия
    pv, sv = pv + (0,) * (width - len(pv)), sv + (0,) * (width - len(sv))
    if pv == sv:
        return ""
    if sv > pv:
        return (f"Внимание: пространство версии {space_v} новее плагина ({plugin_v}) — спецификации ниже "
                "могут устареть. Скажи пользователю, что плагин svaib нужно обновить.")
    return (f"Внимание: пространство версии {space_v} отстаёт от плагина ({plugin_v}) — спецификации ниже "
            "описывают новую структуру. Предложи пользователю обновить пространство скиллом `space-scaffold`.")


def read_spec(sdir: str, spec: str) -> str:
    with open(os.path.join(sdir, spec), encoding="utf-8") as f:
        return f.read().strip()


def listed(paths: list[str]) -> str:
    shown = ", ".join(f"`{p}`" for p in paths[:MAX_NAMES])
    return shown + (f" и ещё {len(paths) - MAX_NAMES}" if len(paths) > MAX_NAMES else "")


def deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}, ensure_ascii=False))


def pre_write(hook_input: dict) -> None:
    tool = hook_input.get("tool_name") or ""
    if nav is None or not hook_input.get("session_id") or not (tool in WRITE_TOOLS or is_shell(tool)):
        return
    root = nav.resolve_root(hook_input)
    if not root or not os.path.isdir(os.path.join(root, SPACE_MARK)):
        return
    sdir = spec_dir(root)
    if not sdir:
        log("skip", reason="no specs", root=root)
        return
    key = session_key(hook_input)
    files: dict[str, list[str]] = {}          # спецификация → файлы, которые под неё пишутся
    for t in targets_of(hook_input, root):
        spec = spec_of(root, sdir, t)
        if spec:
            files.setdefault(spec, []).append(os.path.relpath(t, root))
    if not files:
        return
    pending = [s for s in [GENERAL] + list(files) if not os.path.exists(marker_path(key, s))]
    if not pending:
        fresh = [s for s in files if time.time() - os.path.getmtime(marker_path(key, s)) < SAME_TURN]
        call = hook_input.get("tool_use_id") or ""
        if fresh and call and all(marker_call(key, s) == call for s in fresh):
            # тот же вызов: хук стоит дважды (плагин и локальная копия); хост показывает один отказ
            # из двух, поэтому второй молчит, и в силе отказ со спецификацией
            log("dup-instance", specs=fresh)
            return
        if fresh:
            deny(f"Запись в {listed([f for s in fresh for f in files[s]])} остановлена: спецификация "
                 "этого типа только что выдана в отказе соседнего вызова этого же хода. Прочитай её там, "
                 "сверь правку и повтори запись.")
            log("deny-same-turn", specs=fresh)
        return

    names = listed([f for fs in files.values() for f in fs])
    kinds = ", ".join(f"`{s[:-3]}`" for s in files)
    head = (f"Запись в {names} остановлена: это канонический файл пространства (тип {kinds}), "
            "а его спецификации в этой сессии ещё не было. Прочитай спецификацию ниже, сверь с ней "
            "задуманную правку и повтори запись. Повторно эта спецификация не придёт.")
    more = "Спецификация приходит частями: следующая часть — при повторной попытке записи."
    batch, size = [], len(head) + len(more)
    for s in pending:
        part = f"## Спецификация `{s}`\n\n{read_spec(sdir, s)}"
        if batch and size + len(part) > BUDGET:
            break                             # одна спецификация больше BUDGET всё равно уходит целиком
        batch.append((s, part))
        size += len(part) + 2
    rest = pending[len(batch):]
    note = version_note(root, sdir)
    reason = "\n\n".join([head] + ([note] if note else []) + ([more] if rest else []) + [part for _, part in batch])
    for s, _ in batch:                        # метка до вывода: сбой записи метки не зациклит отказы
        marker_set(key, s, hook_input.get("tool_use_id") or "")
    deny(reason)
    log("deny", files=names, specs=[s for s, _ in batch], rest=rest, chars=len(reason))


def main():
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "pre-write"
    for stream in (sys.stdin, sys.stdout):    # Windows: консольная кодировка роняет кириллицу, отказ теряется
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    try:
        raw = sys.stdin.read()
        hook_input = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        hook_input = {}
    try:
        if mode == "pre-write":
            pre_write(hook_input)
        elif mode == "compact" and hook_input.get("session_id") and nav is not None:
            markers_clear(hook_input["session_id"])
    except Exception as e:  # noqa: BLE001 — хук не имеет права сломать запись
        log("error", mode=mode, error=f"{type(e).__name__}: {e}")
        print(f"inject_file_spec: {type(e).__name__}: {e}", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
