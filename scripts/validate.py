#!/usr/bin/env python3
"""Validate every skill in this repo. Exit non-zero on error."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from skilllib import AGENT_TARGETS, KNOWN_KEYS, NAME_RE, REQUIRED_KEYS, discover

MAX_DESC = 1024
MAX_LINES = 500


def validate(skill):
    errors, warnings = [], []
    d = skill.path.name
    meta = skill.meta

    if skill.errors:
        return skill.errors, warnings
    if not meta:
        return [f"{d}: SKILL.md has no YAML frontmatter"], warnings

    for key in REQUIRED_KEYS:
        if not meta.get(key):
            errors.append(f"{d}: frontmatter missing required key '{key}'")

    name = meta.get("name")
    if name:
        if not isinstance(name, str) or not NAME_RE.match(name):
            errors.append(f"{d}: name '{name}' must be kebab-case")
        elif name != d:
            errors.append(f"{d}: name '{name}' must match directory name")

    desc = meta.get("description")
    if isinstance(desc, str):
        if len(desc) > MAX_DESC:
            errors.append(f"{d}: description longer than {MAX_DESC} chars")
        elif len(desc) < 20:
            warnings.append(f"{d}: description is very short; describe trigger conditions")
    elif desc:
        errors.append(f"{d}: description must be a single string")

    for key in meta:
        if key not in KNOWN_KEYS:
            warnings.append(f"{d}: unknown frontmatter key '{key}'")

    for agent in skill.agents:
        if agent != "all" and agent not in AGENT_TARGETS:
            errors.append(f"{d}: unknown agent '{agent}'")

    if not skill.body.strip():
        errors.append(f"{d}: SKILL.md body is empty")
    lines = skill.body.splitlines()
    if len(lines) > MAX_LINES:
        warnings.append(f"{d}: body is {len(lines)} lines; move detail into references/")

    for ref in (skill.path / "references").glob("**/*"):
        if ref.is_file() and not ref.name.startswith(".") and ref.name not in skill.body and ref.stem not in skill.body:
            warnings.append(f"{d}: references/{ref.name} is never mentioned in SKILL.md")

    return errors, warnings


def main() -> int:
    skills = discover(sys.argv[1:] or None)
    if not skills:
        print("no skills found")
        return 0

    all_errors, all_warnings = [], []
    for skill in skills:
        errors, warnings = validate(skill)
        all_errors += errors
        all_warnings += warnings
        status = "FAIL" if errors else ("warn" if warnings else "ok")
        print(f"[{status:>4}] {skill.path.name}")

    for w in all_warnings:
        print(f"  warning: {w}")
    for e in all_errors:
        print(f"  error:   {e}")

    print(f"\n{len(skills)} skill(s), {len(all_errors)} error(s), {len(all_warnings)} warning(s)")
    return 1 if all_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
