#!/usr/bin/env python3
"""Install skills from this repo into agent skill directories.

Default is symlink so repo edits take effect immediately. Use --copy for
environments where symlinks are awkward (some sandboxes, Windows).
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from skilllib import AGENT_TARGETS, POINTER_FILES, discover, expand, load_skill

BEGIN = "<!-- BEGIN managed skills index -->"
END = "<!-- END managed skills index -->"


def link(skill_path: Path, dest: Path, copy: bool, force: bool, dry: bool) -> str:
    if dest.is_symlink() or dest.exists():
        already = dest.is_symlink() and dest.resolve() == skill_path.resolve()
        if already and not copy:
            return "up-to-date"
        if not force:
            return "exists (use --force)"
        if not dry:
            if dest.is_dir() and not dest.is_symlink():
                shutil.rmtree(dest)
            else:
                dest.unlink()
    if dry:
        return "would install"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if copy:
        shutil.copytree(skill_path, dest)
    else:
        dest.symlink_to(skill_path, target_is_directory=True)
    return "installed"


def remove(dest: Path, dry: bool) -> str:
    if not dest.exists() and not dest.is_symlink():
        return "absent"
    if dry:
        return "would remove"
    if dest.is_dir() and not dest.is_symlink():
        shutil.rmtree(dest)
    else:
        dest.unlink()
    return "removed"


def installed_skills(agent: str):
    """Every skill currently present under the agent's skills root.

    The index must describe what is on disk, not what this run touched.
    Building it from the current run makes `--skill one` drop every other
    already-installed skill out of the managed block while its files stay
    in place, leaving it installed but invisible.
    """
    root = expand(AGENT_TARGETS[agent])
    if not root.is_dir():
        return []
    out = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if not (entry / "SKILL.md").is_file():
            continue
        skill = load_skill(entry)
        if skill.meta.get("name"):
            out.append(skill)
    return out


def write_pointer(agent: str, skills, dry: bool) -> str:
    target = expand(POINTER_FILES[agent])
    root = expand(AGENT_TARGETS[agent])
    lines = [BEGIN, "", "## Available skills", "",
             f"Skill instructions live in `{root}/<name>/SKILL.md`.",
             "Read the matching SKILL.md in full before acting on its topic.", ""]
    for s in skills:
        desc = s.meta.get("description", "")
        lines.append(f"- **{s.name}** — {desc}")
    lines += ["", END, ""]
    block = "\n".join(lines)

    existing = target.read_text(encoding="utf-8") if target.is_file() else ""
    if BEGIN in existing and END in existing:
        head, _, rest = existing.partition(BEGIN)
        _, _, tail = rest.partition(END)
        new = head + block + tail.lstrip("\n")
    else:
        new = (existing.rstrip() + "\n\n" if existing.strip() else "") + block
    if new == existing:
        return "up-to-date"
    if dry:
        return "would update"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(new, encoding="utf-8")
    return "updated"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--agent", action="append", help="target agent (repeatable)")
    p.add_argument("--skill", action="append", help="skill name (repeatable)")
    p.add_argument("--all", action="store_true", help="all skills, all declared agents")
    p.add_argument("--list", action="store_true", help="show skills and targets")
    p.add_argument("--copy", action="store_true", help="copy instead of symlink")
    p.add_argument("--force", action="store_true", help="overwrite existing entries")
    p.add_argument("--uninstall", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    skills = discover(set(args.skill) if args.skill else None)
    if not skills:
        print("no matching skills")
        return 1

    if args.list:
        print("targets:")
        for agent, path in AGENT_TARGETS.items():
            print(f"  {agent:<9} {path}  ({'present' if expand(path).exists() else 'missing'})")
        print("\nskills:")
        for s in skills:
            print(f"  {s.name:<24} agents={','.join(s.agents)}")
        return 0

    if not (args.all or args.agent or args.skill):
        p.error("pass --all, --agent, --skill, or --list")

    wanted = set(a.lower() for a in args.agent) if args.agent else None
    touched = {}
    for s in skills:
        for agent in s.targets():
            if wanted and agent not in wanted:
                continue
            dest = expand(AGENT_TARGETS[agent]) / s.name
            if args.uninstall:
                status = remove(dest, args.dry_run)
            else:
                status = link(s.path, dest, args.copy, args.force, args.dry_run)
                touched.setdefault(agent, []).append(s)
            print(f"{agent:<9} {s.name:<24} {status}")

    for agent, installed in touched.items():
        if agent in POINTER_FILES:
            # Index everything on disk, plus what this run installs. The union
            # matters for --dry-run, where nothing has been written yet.
            listed = {s.name: s for s in installed_skills(agent)}
            for s in installed:
                listed.setdefault(s.name, s)
            entries = [listed[n] for n in sorted(listed)]
            print(f"{agent:<9} {'(pointer index)':<24} {write_pointer(agent, entries, args.dry_run)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
