# skills

Portable agent skills: one source of truth, installable into Claude Code, Codex,
Windsurf, Cursor, and any other agent that reads Markdown instructions.

## Layout

```
skills/<skill-name>/SKILL.md      # required: frontmatter + instructions
skills/<skill-name>/references/   # optional: docs loaded on demand
skills/<skill-name>/scripts/      # optional: deterministic helpers
templates/SKILL.md                # starting point for a new skill
scripts/validate.py               # schema + lint checks
scripts/install.py                # symlink/copy skills into agent homes
scripts/new_skill.py              # scaffold a new skill
scripts/check_cli_parity.py       # keep bin/cli.js in step with the installer
bin/cli.js                        # dependency-free npm/npx installer
package.json                      # npm packaging
```

## Agent instructions

`AGENTS.md` at the repo root is the contributor guide for agents working *in* this repo.
`CLAUDE.md`, `GEMINI.md`, and `.windsurfrules` are symlinks to it, and
`.cursor/rules/repo.mdc` points at it, so every agent reads one source of truth.

Do not confuse this with `skills/` — those are the portable skills this repo ships to
other projects.

## SKILL.md format

YAML frontmatter, then Markdown body:

```yaml
---
name: my-skill              # kebab-case, matches directory name
description: When the user wants X. Also use when the user mentions "x", "y".
version: 0.1.0
agents: [claude, codex, windsurf, cursor]   # or [all]
tags: [category]
allowed-tools: [Bash, Read, Write]   # optional hint
---
```

`description` is the routing signal: write it as trigger conditions, not a summary.

## Install

No clone required. With Node 16+:

```bash
npx @sahil2004/skills --all                       # every skill, every agent it declares
npx @sahil2004/skills --skill review-pr           # one skill
npx @sahil2004/skills --agent claude --all        # one agent
npx @sahil2004/skills --list                      # show skills and target directories
npx @sahil2004/skills --all --dry-run             # preview without writing
npx @sahil2004/skills --all --uninstall           # remove
```

Straight from GitHub, without the registry:

```bash
npx github:Sahil2004/skills --all
```

The npm CLI copies files, so an install survives npm clearing its cache. Working in a
clone instead? Use the Python installer below; it symlinks by default, so edits take
effect immediately.

## Usage

```bash
python3 scripts/new_skill.py my-skill      # scaffold
python3 scripts/validate.py                # validate all skills
python3 scripts/install.py --list          # show targets and status
python3 scripts/install.py --all           # install everything, everywhere
python3 scripts/install.py --agent claude --skill my-skill
python3 scripts/install.py --all --copy    # copy instead of symlink
python3 scripts/install.py --all --uninstall
python3 scripts/check_cli_parity.py        # bin/cli.js matches the Python installer
```

Symlinks are the default so edits in this repo take effect immediately.

## Install targets

| Agent | Path |
| --- | --- |
| jcode | `~/.jcode/skills/<name>` |
| claude | `~/.claude/skills/<name>` |
| codex | `~/.codex/skills/<name>` |
| windsurf | `~/.codeium/windsurf/skills/<name>` |
| cursor | `~/.cursor/skills/<name>` |
| opencode | `~/.config/opencode/skills/<name>` |

Agents that only read a single rules file (older Codex/Windsurf/Cursor) also get a
generated pointer file listing installed skills, so they can discover and open them.

## Writing good skills

- Trigger-first description; include the words a user would actually say.
- Keep `SKILL.md` under ~500 lines; push detail into `references/`.
- Prefer deterministic scripts over prose when a step is mechanical.
- No agent-vendor attribution anywhere in output.

## CI

`.github/workflows/validate.yml` runs on every push and PR: skill validation, the
installer listing, the CLI parity check, a dry-run install, and `npm pack`.
