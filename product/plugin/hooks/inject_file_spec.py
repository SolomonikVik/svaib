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
`Path(путь).write_text`, `writeFile`; путь — литерал или переменная с литералом из того же скрипта),
`apply_patch` через shell. Разбор — сито, а не парсер. Упоминание пути в коде — в тексте замены, в
строке данных — не запись. Пути — от cwd сессии, после `cd X` в той же команде — от X; тип определяется именем. В Cowork путь VM
`/sessions/<сессия>/mnt/<папка>` переводится в путь хоста (`nav.vm_to_host`).
Не ловятся запись через переменную, `find -exec`, скрипт-файл, пишущий сам, и чтение спецификации
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


def script_writes(code: str) -> list[str]:
    """Пути, в которые код интерпретатора пишет явно. Путь из os.path.join или f-строки не ловится."""
    assigned = {name: path for name, _, path in PATH_ASSIGN_RE.findall(code)}
    out = []
    for rx in WRITE_CALL_RES:
        for m in rx.finditer(code):
            groups = m.groupdict()
            path = groups.get("lit") or assigned.get(groups.get("var") or "")
            if path:
                out.append(path)
    return out


def bash_writes(text: str, cwd: str) -> list[str]:
    """Файлы, в которые пишет команда оболочки. Сито, а не парсер: лишний кандидат отсеет
    `spec_of`, а ложная спецификация стоит одного отказа за сессию."""
    if not NAME_RE.search(text):
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
                    writes += script_writes(" ".join(seg) + "\n" + body)
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
