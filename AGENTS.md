# AGENTS.md

Contributor guide for agents working in this repository.

This repo is the single source of truth for portable agent skills. Skills authored here
are installed into Jcode, Claude Code, Codex, Windsurf, Cursor, and opencode.

## Repository shape

```
skills/<skill-name>/SKILL.md      # required: frontmatter + instructions
skills/<skill-name>/references/   # optional: detail loaded on demand
skills/<skill-name>/scripts/      # optional: deterministic helpers
templates/SKILL.md                # starting point for a new skill
scripts/skilllib.py               # shared parsing + target table
scripts/validate.py               # schema + lint checks
scripts/install.py                # symlink/copy into agent homes
scripts/new_skill.py              # scaffold a new skill
```

## Before you finish any change

```bash
python3 scripts/validate.py
python3 scripts/install.py --all --dry-run
```

Both must pass with zero errors. CI runs the same checks.

## Adding or editing a skill

1. Scaffold with `python3 scripts/new_skill.py <kebab-name> "When the user wants ..."`.
   Do not hand-create directories; the scaffolder keeps the layout consistent.
2. `name` in frontmatter must exactly match the directory name.
3. Write `description` as trigger conditions, not a summary. It is the only text most
   agents see when deciding whether to load the skill. Include literal phrases a user
   would type.
4. Keep `SKILL.md` under ~500 lines. Move depth into `references/` and mention each
   reference file by name in the body so it is discoverable.
5. Prefer a deterministic script over prose whenever a step is mechanical.
6. One skill, one job. Split rather than growing a catch-all.

## Conventions

- Python only in `scripts/`, standard library only, no third-party dependencies.
- Any script a skill ships must run with no install step, or declare its requirements at
  the top of the file.
- Never claim capabilities an agent lacks. Declare needed tools in `allowed-tools`.
- No vendor or AI attribution anywhere: commit messages, PR text, code comments, docs.
- Commit as you go. One skill per commit where practical.

## Installer notes

- Symlinks are the default so repo edits take effect immediately. `--copy` exists for
  sandboxed agents that cannot follow links out of their home.
- For agents without a native skill loader, the installer maintains an index between
  `<!-- BEGIN managed skills index -->` and `<!-- END managed skills index -->` in that
  agent's rules file. Never edit inside those markers by hand; everything outside them is
  preserved.
- If an agent's install path is wrong, fix `AGENT_TARGETS` in `scripts/skilllib.py`
  rather than special-casing the installer.

## Testing a skill for real

Install it, start a fresh agent session, and give a prompt matching the description
without naming the skill. If it does not trigger, the description is the bug.
