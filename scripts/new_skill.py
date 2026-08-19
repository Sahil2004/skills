#!/usr/bin/env python3
"""Scaffold a new skill directory from templates/SKILL.md."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from skilllib import NAME_RE, REPO_ROOT, SKILLS_DIR


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: new_skill.py <skill-name> [description...]")
        return 1
    name = sys.argv[1].strip().lower()
    if not NAME_RE.match(name):
        print(f"error: '{name}' must be kebab-case (a-z, 0-9, hyphens)")
        return 1
    desc = " ".join(sys.argv[2:]) or f"When the user wants to {name.replace('-', ' ')}."

    dest = SKILLS_DIR / name
    if dest.exists():
        print(f"error: {dest} already exists")
        return 1

    template = (REPO_ROOT / "templates" / "SKILL.md").read_text(encoding="utf-8")
    text = template.replace("skill-name", name).replace("REPLACE_DESCRIPTION", desc)
    (dest / "references").mkdir(parents=True)
    (dest / "SKILL.md").write_text(text, encoding="utf-8")
    (dest / "references" / ".gitkeep").write_text("", encoding="utf-8")
    print(f"created {dest.relative_to(REPO_ROOT)}/SKILL.md")
    print("next: edit it, then run scripts/validate.py and scripts/install.py --all")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
