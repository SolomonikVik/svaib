#!/usr/bin/env python3
"""Сверка поставки: что из плагина лежит у руководителя ещё и локальной копией.

Только читает и ничего не меняет. Сравнивает инвентарь пакета (inventory.json рядом
со скиллом) с пространством и с пользовательскими настройками агента на этой машине.
Решения — удалить, в архив или оставить — принимает руководитель, исполняет агент.

Запуск из корня пространства:
    python3 <каталог скилла>/scripts/delivery_check.py [--space .] [--json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

INVENTORY = Path(__file__).resolve().parent.parent / "inventory.json"


def sha_of(path: Path) -> str:
    """Отпечаток файла или каталога: по относительным путям и содержимому."""
    h = hashlib.sha256()
    if path.is_dir():
        for f in sorted(p for p in path.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
            h.update(str(f.relative_to(path)).encode())
            h.update(f.read_bytes())
    elif path.is_file():
        h.update(path.read_bytes())
    return h.hexdigest()[:12]


def sha_of_value(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]


def modified(path: Path) -> str:
    try:
        files = [p for p in path.rglob("*") if p.is_file()] if path.is_dir() else [path]
        ts = max((p.stat().st_mtime for p in files), default=path.stat().st_mtime)
    except OSError:
        return ""
    return dt.date.fromtimestamp(ts).isoformat()


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


class Check:
    def __init__(self, space: Path, inventory: dict, home: Path):
        self.space = space
        self.home = home
        self.inv = inventory
        self.skills = set(inventory.get("skills", []))
        self.former = inventory.get("former_names", {}).get("skills", {})
        self.agents = set(inventory.get("agents", []))
        self.hook_scripts = {h["script"] for h in inventory.get("hooks", [])}
        self.mcp = {m["name"]: m.get("url", "") for m in inventory.get("mcp", [])}
        state = read_json(space / ".svaib" / "space.json") or {}
        self.kept = state.get("kept", []) or []
        self.custom = set(state.get("custom_skills", []) or [])
        self.package = set(state.get("package_skills", []) or [])
        self.inside: list[dict] = []
        self.outside: list[dict] = []

    # ---------------------------------------------------------------- общее

    def rel(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.space))
        except ValueError:
            return "~/" + str(path.relative_to(self.home)) if str(path).startswith(str(self.home)) else str(path)

    def add(self, where: list, kind: str, name: str, path: Path, note: str, replacement, sha: str, **extra):
        item = {"kind": kind, "name": name, "path": self.rel(path), "note": note,
                "replacement": replacement, "sha": sha, "modified": modified(path) if path.exists() else ""}
        item.update(extra)
        if kind == "skill":
            if name in self.custom:
                item["record"] = "записан в custom_skills как скилл руководителя"
            elif name in self.package:
                item["record"] = "записан в package_skills: ставила наша поставка"
        for k in self.kept:
            if k.get("kind") == kind and k.get("path") == item["path"]:
                item["kept"] = "same" if k.get("sha") == sha else "changed"
        where.append(item)

    def skill_match(self, name: str):
        """(замена в плагине, пояснение) или None, если имя не наше."""
        if name in self.skills:
            return name, "то же имя, что в плагине"
        if name in self.former:
            new = self.former[name]
            return new, "прежнее имя" + ("" if new else "; замены в плагине нет")
        return None

    # ---------------------------------------------------------------- пространство

    def scan_skill_dirs(self, base: Path, where: list, scope: str):
        if not base.is_dir():
            return
        for d in sorted(base.iterdir()):
            match = self.skill_match(d.name)
            if not match:
                continue
            replacement, note = match
            extra = {}
            if d.is_symlink():
                extra["link_to"] = os.readlink(d)
                note += "; это ссылка"
            if d.name == "meeting-analysis":
                ours = (d / "references" / "summary-spec.md").is_file()
                note += "; есть references/summary-spec.md — наш прежний разбор" if ours \
                    else "; признака нашей поставки нет — может быть скиллом руководителя"
            self.add(where, "skill", d.name, d, note, replacement, sha_of(d), scope=scope, **extra)

    def scan_space(self):
        s = self.space
        self.scan_skill_dirs(s / ".claude" / "skills", self.inside, "space")
        self.scan_skill_dirs(s / ".agents" / "skills", self.inside, "space")
        arch = s / ".claude" / "skill-archives"
        if arch.is_dir():
            for f in sorted(arch.glob("*.skill")):
                match = self.skill_match(f.stem)
                if match:
                    self.add(self.inside, "skill-archive", f.stem, f,
                             "архив скилла: из него скилл ставится обратно; " + match[1], match[0], sha_of(f))
        agents = s / ".claude" / "agents"
        for name in sorted(self.agents):
            p = agents / f"{name}.md"
            if p.is_file():
                self.add(self.inside, "agent", name, p, "то же имя, что в плагине", name, sha_of(p))
        for hooks in (s / ".claude" / "hooks", s / ".agents" / "hooks"):
            for script in sorted(self.hook_scripts):
                p = hooks / script
                if p.exists():
                    self.add(self.inside, "hook", script, p, "скрипт хука из плагина", script, sha_of(p))
        for cfg in (s / ".claude" / "settings.json", s / ".claude" / "settings.local.json", s / ".codex" / "hooks.json"):
            self.scan_hook_registrations(cfg, self.inside)
        mcp = read_json(s / ".mcp.json") or {}
        for name, conf in (mcp.get("mcpServers") or {}).items():
            if self.mcp_match(name, conf):
                self.add(self.inside, "mcp", name, s / ".mcp.json", "MCP svaib прописан в пространстве",
                         name, sha_of_value(conf), key=f"mcpServers.{name}")

    def mcp_match(self, name: str, conf) -> bool:
        url = conf.get("url", "") if isinstance(conf, dict) else ""
        return name in self.mcp or (url and url in self.mcp.values())

    def scan_hook_registrations(self, cfg: Path, where: list):
        data = read_json(cfg)
        if not isinstance(data, dict):
            return
        for event, groups in (data.get("hooks") or {}).items():
            for group in groups or []:
                for h in group.get("hooks", []) if isinstance(group, dict) else []:
                    cmd = h.get("command", "") if isinstance(h, dict) else ""
                    hit = [s for s in self.hook_scripts if re.search(rf"(^|[/\\\"' ]){re.escape(s)}\b", cmd)]
                    if hit:
                        self.add(where, "hook-registration", hit[0], cfg,
                                 f"регистрация хука на {event}: хук плагина сработает дважды", hit[0],
                                 sha_of_value(h), event=event, command=cmd)

    # ---------------------------------------------------------------- машина

    def scan_machine(self):
        home = self.home
        self.scan_skill_dirs(home / ".claude" / "skills", self.outside, "user")
        self.scan_skill_dirs(home / ".agents" / "skills", self.outside, "user")
        self.scan_skill_dirs(home / ".codex" / "skills", self.outside, "user")
        self.scan_hook_registrations(home / ".claude" / "settings.json", self.outside)
        self.scan_hook_registrations(home / ".codex" / "hooks.json", self.outside)
        cj = read_json(home / ".claude.json") or {}
        for name, conf in (cj.get("mcpServers") or {}).items():
            if self.mcp_match(name, conf):
                self.add(self.outside, "mcp", name, home / ".claude.json",
                         "MCP svaib в настройках пользователя Claude Code (все проекты)", name,
                         sha_of_value(conf), remove=f"claude mcp remove {name} -s user")
        proj = (cj.get("projects") or {}).get(str(self.space)) or {}
        for name, conf in (proj.get("mcpServers") or {}).items():
            if self.mcp_match(name, conf):
                self.add(self.outside, "mcp", name, home / ".claude.json",
                         "MCP svaib в локальных настройках Claude Code для этой папки", name,
                         sha_of_value(conf), remove=f"claude mcp remove {name} -s local")
        toml = home / ".codex" / "config.toml"
        if toml.is_file():
            text = toml.read_text(encoding="utf-8", errors="replace")
            for m in re.finditer(r"^\[mcp_servers\.([\"']?)([\w.-]+)\1\]\s*$(.*?)(?=^\[|\Z)", text, re.M | re.S):
                name, body = m.group(2), m.group(3)
                url = re.search(r"^\s*url\s*=\s*[\"']([^\"']+)", body, re.M)
                if self.mcp_match(name, {"url": url.group(1) if url else ""}):
                    self.add(self.outside, "mcp", name, toml, "MCP svaib в настройках Codex (все проекты)",
                             name, sha_of_value(body.strip()), remove=f"codex mcp remove {name}")

    # ---------------------------------------------------------------- вывод

    def report(self) -> str:
        inv = self.inv
        lines = [f"Плагин {inv.get('plugin')} {inv.get('version')}: скиллов {len(self.skills)}, "
                 f"агентов {len(self.agents)}, хуков {len(self.hook_scripts)}, MCP: {', '.join(self.mcp) or 'нет'}.",
                 "Проверь в среде, что плагин работает: скиллы и MCP плагина видны среди инструментов. "
                 "Чего из плагина в среде нет — локальную копию того не снимай.", ""]
        fresh = [i for i in self.inside if i.get("kept") != "same"]
        agreed = [i for i in self.inside + self.outside if i.get("kept") == "same"]
        outside = [i for i in self.outside if i.get("kept") != "same"]
        if fresh:
            lines.append("В пространстве — решает руководитель (удалить / в архив / оставить):")
            lines += [self.line(n, i) for n, i in enumerate(fresh, 1)]
            lines.append("")
        if outside:
            lines.append("Вне пространства, на этой машине — только сообщить и дать команду:")
            lines += [self.line(n, i) for n, i in enumerate(outside, 1)]
            lines.append("")
        if agreed:
            lines.append("Согласованные дубли — оставлены по решению руководителя:")
            lines += [self.line(n, i) for n, i in enumerate(agreed, 1)]
            lines.append("")
        if not fresh and not outside:
            lines.append("Новых дублей нет" + ("; согласованные дубли сохранены." if agreed else "."))
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def line(n: int, i: dict) -> str:
        repl = i["replacement"] or "нет"
        parts = [f"{n}. {i['kind']} `{i['path']}` — {i['note']}", f"в плагине: {repl}"]
        if i.get("event"):
            parts.append(f"команда: {i['command']}")
        if i.get("link_to"):
            parts.append(f"ссылка на {i['link_to']}")
        if i.get("record"):
            parts.append(i["record"])
        if i.get("kept") == "changed":
            parts.append("ранее оставлено, но с тех пор изменилось — спросить снова")
        if i.get("remove"):
            parts.append(f"снять: `{i['remove']}`")
        if i.get("modified"):
            parts.append(f"изменён {i['modified']}")
        parts.append(f"sha {i['sha']}")
        return " · ".join(parts)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Сверка поставки: локальные копии того, что едет плагином")
    ap.add_argument("--space", default=".", help="корень пространства (по умолчанию — текущая папка)")
    ap.add_argument("--inventory", default=str(INVENTORY), help="инвентарь пакета")
    ap.add_argument("--home", default=str(Path.home()), help=argparse.SUPPRESS)
    ap.add_argument("--json", action="store_true", help="вывод в JSON")
    args = ap.parse_args(argv)

    inv = read_json(Path(args.inventory))
    if not isinstance(inv, dict):
        print(f"Инвентаря поставки нет ({args.inventory}): скилл запущен не из установленного плагина. "
              "Сверка невозможна — скажи об этом руководителю.", file=sys.stderr)
        return 1
    space = Path(args.space).resolve()
    check = Check(space, inv, Path(args.home).resolve())
    check.scan_space()
    check.scan_machine()
    if args.json:
        print(json.dumps({"plugin": inv.get("plugin"), "version": inv.get("version"),
                          "inside": check.inside, "outside": check.outside}, ensure_ascii=False, indent=2))
    else:
        sys.stdout.write(check.report())
    return 0


if __name__ == "__main__":
    sys.exit(main())
