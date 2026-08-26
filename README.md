# skills

Two GitHub code-review skills for coding agents, installable into Jcode, Claude Code,
Codex, Windsurf, Cursor, and opencode from one source of truth.

Between them they cover both halves of a review: producing one on someone else's pull
request, and answering the one left on yours.

| Skill | Use it when |
| --- | --- |
| [`review-pr`](skills/review-pr/) | You are reviewing **someone else's** PR and leaving feedback |
| [`address-review`](skills/address-review/) | You are answering the review on **your own** PR |

Both require `gh`, authenticated. Both hold to one API call per job: every bundled script
makes exactly one request, so a review never turns into a per-file or per-thread loop.

## review-pr

Review a pull request, then either approve it cleanly or post structured,
severity-classified feedback.

Triggers on "review PR 412", a pasted pull request URL, "is this safe to merge?", or
"approve this if it's fine".

- **One call loads everything**: metadata, file churn, CI status, existing reviews, and
  open threads come back together from `pr_context.sh`.
- **CI gates the review.** A failing check ends it immediately, before the diff is read,
  because the fix will change the diff anyway.
- **Existing threads are respected.** A finding another reviewer already has open is
  suppressed rather than re-posted. A thread resolved without the code changing is fair
  game again.
- **Every finding is classified** `[Blocker]`, `[Suggestion]` or `[Nitpick]`, and placed
  at the narrowest scope that fits: inline, on the file, or in the review body.
- **Exactly one outcome** applies, and only that outcome's file is read. A clean PR is
  approved with no comments attached; any finding at all, down to a single nitpick, is a
  request for changes.
- Never merges or closes a PR. Never approves to be agreeable: an unverified category is
  not clean.

## address-review

Work through the open review comments on your own PR: triage them all into a table, fix
everything that needs no human input, then bring the blockers and the judgement calls
back one at a time.

Triggers on "address the comments on PR 412", "reply to these threads", "what did the
reviewers say and can you fix it?", or the same request with no PR named at all.

- **Finds the PR itself** when you do not name one, from the branch in the current
  directory. Worktrees work unchanged. Missing, closed and ambiguous PRs are handled
  explicitly rather than guessed at.
- **Triage before edits.** Every comment lands in a table before any code changes:

  | comment | severity | needsChanges | anyBlockers | anyDecisions |
  | --- | --- | --- | --- | --- |

  Praise is classified first and needs no work. A blocker is something external and
  concrete; a decision is a choice with two defensible answers. Anything the codebase
  already settles is neither, and is not worth a question.
- **Clear rows run immediately** — no blockers, no decisions — ordered by severity, with
  speed only as a tiebreak. Severity always beats easiness. One worker per row where
  orchestration is available.
- **Blockers are reported while that work runs**, linked to tracked issues where a
  tracker is connected.
- **Decisions are asked one at a time**, written so someone with no context on the
  product can answer: the problem, the context, the options, the tradeoff, and a
  recommendation. Each answer dispatches its row while the next question is asked.
- **Deferred items are parked, never resolved**, and are written into the PR description
  and any linked issue at the end, naming what each one waits on.

## Install

No clone required. With Node 16+:

```bash
npx @sahil2004/skills --all                       # both skills, every agent they declare
npx @sahil2004/skills --skill review-pr           # one skill
npx @sahil2004/skills --skill address-review
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
clone instead? Use the Python installer; it symlinks by default, so edits take effect
immediately.

```bash
python3 scripts/install.py --list          # show targets and status
python3 scripts/install.py --all           # install everything, everywhere
python3 scripts/install.py --agent claude --skill address-review
python3 scripts/install.py --all --copy    # copy instead of symlink
python3 scripts/install.py --all --uninstall
```

### Install targets

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

## Using a skill

Installed skills load on their own. Describe the job in your own words and the agent
picks the skill from its trigger conditions:

> Review PR 412.

> Address the review comments.

Naming the skill directly works too, in agents that support it: `/review-pr`,
`/address-review`.

## Layout

```
skills/review-pr/SKILL.md         # review someone else's PR
skills/review-pr/references/      # checklist, comment style, one file per outcome
skills/review-pr/scripts/         # pr_context.sh

skills/address-review/SKILL.md    # answer the review on your own PR
skills/address-review/references/ # triage table, dispatch, asking decisions
skills/address-review/scripts/    # open_review.sh, reply_thread.sh, resolve_thread.sh
```

Each `SKILL.md` carries the workflow; `references/` holds the detail, loaded only when a
step needs it. Scripts stay deterministic so the agent is not left to compose GraphQL by
hand.

## Contributing

`AGENTS.md` at the repo root is the contributor guide for agents working *in* this repo.
`CLAUDE.md`, `GEMINI.md`, and `.windsurfrules` are symlinks to it, and
`.cursor/rules/repo.mdc` points at it, so every agent reads one source of truth.

Adding a skill starts from `templates/SKILL.md` via `scripts/new_skill.py`. Before
finishing any change:

```bash
python3 scripts/validate.py                # schema + lint checks
python3 scripts/install.py --all --dry-run # installer still resolves every target
python3 scripts/check_cli_parity.py        # bin/cli.js matches the Python installer
python3 scripts/test_package.py            # pack and install in a sandbox HOME
```

`.github/workflows/validate.yml` runs the same checks on every push and PR, plus
`npm pack`.
