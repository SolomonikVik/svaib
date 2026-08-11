#!/usr/bin/env python3
"""Preflight базы и карта встреч для пайплайна meeting-analysis (spine-contracts §5).

Два независимых блока:

1. `check_canon` — минимум, без которого пайплайн не стартует: корневой README
   существует · `01_company/` существует · runs-dir доступен для записи. Всё.
   Линтером базы preflight не работает, клиентские конвенции не парсит.
2. `build_meetings_map` — детерминированная карта мест хранения встреч: все
   каталоги `meetings/` базы плюс вырезанные фиксированные секции их `README.md`
   и корневого README. Карта подаётся узлу `locate-context` на вход: место
   протокола выбирает LLM по карте, код только собирает и валидирует.

Вызывается из `meeting_spine.py start` как библиотека и как самостоятельный CLI.
Stdlib-only, Python 3.9+.
"""

from __future__ import annotations

import argparse
import errno
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

RUNS_ENV = "SVAIB_RUNS_DIR"

README_NAME = "README.md"
COMPANY_DIRNAME = "01_company"
MEETINGS_DIRNAME = "meetings"

# Секции README, которые карта вырезает дословно. Заголовки фиксированы каноном
# scaffold (product/methodology/scaffold/02_readme-spec.md) — резка по точному H2.
ROOT_SECTIONS = ("Содержимое папки", "Маршруты чтения", "Маршруты записи", "Правила работы")
MEETINGS_SECTIONS = ("Содержимое папки", "Маршруты записи")

# Обход базы: служебное, архивное и шаблонное не смотрим; глубину ограничиваем.
SCAN_SKIP = {"zz_archive", "_templates", "_private", ".git", "node_modules", "__pycache__"}
SCAN_DEPTH = 6


def error(code: str, message: str, **extra: Any) -> Dict[str, Any]:
    item = {"code": code, "message": message}
    item.update(extra)
    return item


def default_runs_root() -> Path:
    """Платформенный runs-root (решение B№6, 30.07). Дубль meeting_spine.default_runs_root:
    скрипт самодостаточен для preflight на развёртывании — импортировать spine нельзя.
    """
    if os.name == "nt":
        # Симметрично XDG: относительный LOCALAPPDATA дал бы runs-root от cwd.
        local = os.environ.get("LOCALAPPDATA")
        if local and Path(local).expanduser().is_absolute():
            return Path(local).expanduser() / "svaib" / "runs"
        return Path.home() / "AppData" / "Local" / "svaib" / "runs"
    state = os.environ.get("XDG_STATE_HOME")
    if state:
        path = Path(state).expanduser()
        if path.is_absolute():
            return path / "svaib" / "runs"
    return Path.home() / ".local" / "state" / "svaib" / "runs"


def runs_root() -> Path:
    raw = os.environ.get(RUNS_ENV)
    if raw:
        return Path(raw).expanduser()
    return default_runs_root()


# --------------------------------------------------------------------------- #
# Карта встреч
# --------------------------------------------------------------------------- #

def cut_sections(text: str, headings: Any) -> Dict[str, str]:
    """Режет текст по точным H2. Возвращает {заголовок: тело секции}.

    Отсутствующей секции в результате нет. Содержимое не разбирается и не
    нормализуется — как есть текстом: его читает LLM, не парсер. Повтор
    заголовка — берётся первая секция.
    """
    wanted = {"## " + name: name for name in headings}
    found: Dict[str, str] = {}
    current: Optional[str] = None
    buffer: List[str] = []

    def close() -> None:
        if current is not None:
            found.setdefault(current, "\n".join(buffer).strip("\n"))

    for line in text.splitlines():
        if line.startswith("## "):
            close()
            current = wanted.get(line.strip())
            buffer = []
            continue
        if current is not None:
            buffer.append(line)
    close()
    return found


def read_sections(path: Path, headings: Any) -> Tuple[Dict[str, str], Optional[str]]:
    """Секции README + код нечитаемости (`None` — прочитан нормально).

    Битая кодировка или недоступный файл не роняют карту и вместе с ней весь
    `start`: секции пустые, факт нечитаемости уезжает в карту явно. `utf-8-sig`
    снимает BOM, в остальном равен utf-8.
    """
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    try:
        # чтение с дескриптора после O_NOFOLLOW: закрывает check→read гонку
        # подмены README symlink'ом между проверкой и чтением (Codex v3)
        fd = os.open(str(path), os.O_RDONLY | nofollow)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                return {}, "unreadable"
            raw = os.read(fd, 4 * 1024 * 1024)
        finally:
            os.close(fd)
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return {}, "not_utf8"
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            return {}, "readme_symlink"
        return {}, "unreadable"
    return cut_sections(text, headings), None


def inside_base(base: Path, path: Path) -> bool:
    """Резолвнутый путь лежит внутри базы — защита от выхода по symlink."""
    try:
        resolved = path.resolve()
    except OSError:
        return False
    return resolved == base or base in resolved.parents


def read_readme(base: Path, readme: Path, headings: Any) -> Tuple[Optional[bool], Dict[str, str], Optional[str]]:
    """(есть ли README, секции, код проблемы) с confinement-проверкой файла.

    README-symlink или файл, резолвящийся за пределы базы, в карту не читается:
    иначе внешний текст попал бы к LLM как доверенное содержимое базы.
    """
    if not readme.is_file():
        return False, {}, None
    if readme.is_symlink() or not inside_base(base, readme):
        return False, {}, "readme_symlink"
    sections, problem = read_sections(readme, headings)
    return True, sections, problem


def iter_meetings_dirs(base: Path) -> Tuple[List[Path], bool, List[str]]:
    """Все каталоги `meetings/` базы: обход в глубину до SCAN_DEPTH, без SCAN_SKIP.

    Symlink-каталоги не обходим и в карту не берём. Обрезание глубиной и
    недоступные каталоги возвращаются наверх, а не проглатываются молча.
    """
    base_depth = len(base.parts)
    found: List[Path] = []
    unreadable: List[str] = []
    truncated = False

    def on_error(exc: OSError) -> None:
        target = getattr(exc, "filename", None)
        if not target:
            return
        try:
            unreadable.append(Path(target).relative_to(base).as_posix())
        except ValueError:
            unreadable.append(str(target))

    for root, dirs, _files in os.walk(base, onerror=on_error):
        root_path = Path(root)
        # сначала фильтр, потом решение об обрезании: skip-каталоги и symlink на
        # границе глубины — не «потерянная» часть карты (kimi v2 L1: ложный truncated)
        dirs[:] = sorted(
            name for name in dirs
            if name not in SCAN_SKIP and not (root_path / name).is_symlink()
        )
        if len(root_path.parts) - base_depth >= SCAN_DEPTH:
            truncated = truncated or bool(dirs)
            dirs[:] = []
            continue
        if MEETINGS_DIRNAME in dirs:
            found.append(root_path / MEETINGS_DIRNAME)
            # внутрь meetings не спускаемся: подпапки-типы отдаёт meetings_entry
            dirs.remove(MEETINGS_DIRNAME)
    return sorted(found), truncated, sorted(set(unreadable))


def meetings_entry(base: Path, path: Path) -> Dict[str, Any]:
    rel = path.relative_to(base).as_posix()
    node = path.parent.relative_to(base).as_posix()
    has_readme, sections, problem = read_readme(base, path / README_NAME, MEETINGS_SECTIONS)
    try:
        subdirs = sorted(
            child.name for child in path.iterdir()
            if child.is_dir() and not child.is_symlink() and child.name not in SCAN_SKIP
        )
    except OSError:
        subdirs = []
    return {
        "path": rel,
        "node": "" if node == "." else node,
        "readme": "{}/{}".format(rel, README_NAME) if has_readme else None,
        "readme_error": problem,
        "sections": sections,
        "subdirs": subdirs,
    }


def build_meetings_map(base: Path) -> Dict[str, Any]:
    """Карта мест хранения встреч базы — вход узла locate-context.

    Отсутствие README у `meetings/` — не ошибка: `readme: null`, `sections: {}`.
    Отсутствие каталогов `meetings/` вовсе — тоже не ошибка: пустой список,
    решение (спросить пользователя / предложить create) принимает узел.
    Нечитаемый README — тоже не ошибка, но и не тишина: `readme_error`.
    Symlink наружу в карту не попадает; обрезание глубиной и недоступные
    каталоги видны в `scan.truncated` / `scan.unreadable`.
    """
    base = Path(base).expanduser().resolve()
    has_root, sections, problem = read_readme(base, base / README_NAME, ROOT_SECTIONS)
    dirs, truncated, unreadable = iter_meetings_dirs(base)
    return {
        "base": str(base),
        "root_readme": {
            "path": README_NAME if has_root else None,
            "readme_error": problem,
            "sections": sections,
        },
        "meetings_dirs": [meetings_entry(base, path) for path in dirs],
        "scan": {
            "max_depth": SCAN_DEPTH,
            "skipped": sorted(SCAN_SKIP),
            "truncated": truncated,
            "unreadable": unreadable,
        },
    }


# --------------------------------------------------------------------------- #
# Preflight
# --------------------------------------------------------------------------- #

def check_canon(base: Path, runs_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Три проверки минимума. Возвращает {"ok", "base", "errors"}."""
    base = Path(base).expanduser().resolve()
    runs_dir = Path(runs_dir).expanduser() if runs_dir else runs_root()
    errors: List[Dict[str, Any]] = []

    if not base.is_dir():
        return {
            "ok": False,
            "base": str(base),
            "errors": [error("base_missing", "корень базы не существует или не каталог")],
        }

    if not (base / README_NAME).is_file():
        errors.append(error("readme_missing", "нет корневого README.md"))

    if not (base / COMPANY_DIRNAME).is_dir():
        errors.append(error("company_dir_missing", "нет каталога `01_company/`"))

    try:
        runs_dir.mkdir(parents=True, exist_ok=True)
        if not os.access(runs_dir, os.W_OK):
            raise PermissionError(str(runs_dir))
    except OSError:
        errors.append(error(
            "runs_dir_not_writable",
            "каталог runs недоступен для записи",
            path=str(runs_dir),
        ))

    return {"ok": not errors, "base": str(base), "errors": errors}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_canon.py",
        description="Preflight базы и карта встреч для meeting-analysis",
    )
    parser.add_argument("--base", help="корень базы (по умолчанию — текущий каталог)")
    parser.add_argument("--runs-dir", help="корень runs (по умолчанию $SVAIB_RUNS_DIR либо "
                                           "платформенный state-каталог svaib/runs)")
    parser.add_argument("--json", action="store_true", help="машинный вывод")
    parser.add_argument("--map", action="store_true",
                        help="вывести карту встреч (JSON) вместо результата проверки; код возврата — по проверке")
    args = parser.parse_args(argv)

    base = Path(args.base).expanduser() if args.base else Path.cwd()
    runs_dir = Path(args.runs_dir).expanduser() if args.runs_dir else None
    result = check_canon(base, runs_dir)

    if args.map:
        print(json.dumps(build_meetings_map(base), ensure_ascii=False, indent=2))
    elif args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["ok"]:
        found = build_meetings_map(base)["meetings_dirs"]
        print("Preflight базы в порядке: README, 01_company/, runs-dir")
        print("Карта встреч: каталогов meetings/ — {}".format(len(found)))
    else:
        print("База не готова к пайплайну:", file=sys.stderr)
        for item in result["errors"]:
            print("  [{}] {}".format(item["code"], item["message"]), file=sys.stderr)

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
