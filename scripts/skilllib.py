#!/usr/bin/env python3
"""Shared helpers: locate skills, parse SKILL.md frontmatter (no deps)."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

# agent -> install directory (expanded at use time)
AGENT_TARGETS = {
    "jcode": "~/.jcode/skills",
    "claude": "~/.claude/skills",
    "codex": "~/.codex/skills",
    "windsurf": "~/.codeium/windsurf/skills",
    "cursor": "~/.cursor/skills",
    "opencode": "~/.config/opencode/skills",
}

# agents whose primary entry point is a single rules file; we also write a pointer index
POINTER_FILES = {
    "codex": "~/.codex/AGENTS.md",
    "windsurf": "~/.codeium/windsurf/memories/global_rules.md",
    "cursor": "~/.cursor/rules/skills.mdc",
}

REQUIRED_KEYS = ("name", "description")
KNOWN_KEYS = {
    "name",
    "description",
    "version",
    "agents",
    "tags",
    "allowed-tools",
    "license",
}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


@dataclass
class Skill:
    path: Path
    meta: dict
    body: str
    errors: list = field(default_factory=list)

    @property
    def name(self) -> str:
        return str(self.meta.get("name") or self.path.name)

    @property
    def agents(self) -> list:
        value = self.meta.get("agents") or ["all"]
        if isinstance(value, str):
            value = [value]
        return [str(v).strip().lower() for v in value]

    def targets(self) -> list:
        agents = self.agents
        if "all" in agents:
            return sorted(AGENT_TARGETS)
        return [a for a in agents if a in AGENT_TARGETS]


def _scalar(raw: str):
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        return [_scalar(part) for part in inner.split(",")]
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    return raw


def parse_frontmatter(text: str):
    """Return (meta, body). Supports scalars, inline lists, and '- ' block lists."""
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text

    meta = {}
    key = None
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.lstrip().startswith("- ") and key:
            meta.setdefault(key, [])
            if not isinstance(meta[key], list):
                meta[key] = []
            meta[key].append(_scalar(line.lstrip()[2:]))
            continue
        if ":" not in line:
            continue
        key, _, raw = line.partition(":")
        key = key.strip()
        value = _scalar(raw)
        meta[key] = value if value != "" else []
    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    return meta, body


def load_skill(path: Path) -> Skill:
    skill_md = path / "SKILL.md"
    if not skill_md.is_file():
        return Skill(path, {}, "", [f"{path.name}: missing SKILL.md"])
    meta, body = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
    return Skill(path, meta, body)


def discover(names=None):
    if not SKILLS_DIR.is_dir():
        return []
    out = []
    for entry in sorted(SKILLS_DIR.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if names and entry.name not in names:
            continue
        out.append(load_skill(entry))
    return out


def expand(p: str) -> Path:
    return Path(os.path.expanduser(p))
