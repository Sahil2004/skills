# Agent install targets

| Agent | Skills root | Discovery |
| --- | --- | --- |
| jcode | `~/.jcode/skills/<name>/SKILL.md` | Native skill loader; `/<name>` invokes it. |
| claude | `~/.claude/skills/<name>/SKILL.md` | Native skill loader; model-invoked by description. |
| codex | `~/.codex/skills/<name>/SKILL.md` | No native loader in older builds; `~/.codex/AGENTS.md` gets a managed index block pointing at each SKILL.md. |
| windsurf | `~/.codeium/windsurf/skills/<name>/SKILL.md` | Rules-file driven; index written to `~/.codeium/windsurf/memories/global_rules.md`. |
| cursor | `~/.cursor/skills/<name>/SKILL.md` | Index written to `~/.cursor/rules/skills.mdc`. |
| opencode | `~/.config/opencode/skills/<name>/SKILL.md` | Reads skill directories directly. |

## Managed index block

`scripts/install.py` writes, between `<!-- BEGIN managed skills index -->` and
`<!-- END managed skills index -->`, a list of installed skills with their descriptions.
Everything outside those markers is preserved, so hand-written rules are safe.

## Notes

- Symlinks keep every agent on the same source of truth. Use `--copy` only for agents
  sandboxed away from this repo path.
- Per-project installs: symlink `skills/<name>` into the project's `.<agent>/skills/`
  directory.
- Restart or start a new agent session after installing; most agents scan skills at boot.
