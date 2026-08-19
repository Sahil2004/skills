---
name: skill-authoring
description: When the user wants to create, edit, review, or debug an agent skill in this repo. Also use when the user mentions "write a skill", "SKILL.md", "skill frontmatter", "install skills", or "skill not triggering".
version: 0.1.0
agents: [all]
tags: [meta, tooling]
allowed-tools: [Bash, Read, Write, Edit]
---

# Skill authoring

Produce a portable skill that installs cleanly into Jcode, Claude Code, Codex, Windsurf,
Cursor, and opencode from this single repo.

## When to use

- Creating a new skill or restructuring an existing one.
- A skill exists but the agent never invokes it (description problem).
- Installing or uninstalling skills across agent homes.

Do not use this when the task is ordinary coding with no skill artifact involved.

## Workflow

1. **Scaffold.**

   ```bash
   python3 scripts/new_skill.py <skill-name> "When the user wants ..."
   ```

2. **Write the description first.** It is the only text most agents see when deciding
   whether to load the skill. Format: `When the user wants <goal>. Also use when the user
   mentions "<phrase>", "<phrase>".` Include the words a user would actually type.

3. **Write the body.** Sections: purpose, when to use (plus a negative case), numbered
   workflow, hard rules, references. Commands beat prose. Keep it under ~500 lines and
   move depth into `references/`, mentioning each file by name so it is discoverable.

4. **Validate.**

   ```bash
   python3 scripts/validate.py
   ```

5. **Install and verify.**

   ```bash
   python3 scripts/install.py --all --force
   python3 scripts/install.py --list
   ```

   Confirm the symlink resolves back to this repo, then start a fresh agent session and
   check the skill appears.

6. **Commit.** One skill per commit where practical.

## Rules

- `name` must be kebab-case and identical to the directory name.
- One skill, one job. Split rather than growing a catch-all.
- Never claim capabilities the agent lacks; state required tools in `allowed-tools`.
- No vendor or AI attribution in any generated output.
- Scripts under `scripts/` inside a skill must run with no third-party dependencies, or
  declare them explicitly at the top of the file.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| Skill never triggers | Description is a summary, not triggers | Rewrite with "When the user wants..." and literal keywords |
| Not listed by an agent | Wrong install root | `scripts/install.py --list`, check the path exists |
| Stale content | Directory was copied, not linked | Reinstall without `--copy` |
| Validation error on name | Directory renamed | Keep `name` and directory in sync |

## References

- `references/agent-targets.md` — per-agent install paths and discovery quirks.
