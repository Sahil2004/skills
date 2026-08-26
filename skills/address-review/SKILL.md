---
name: address-review
description: When the user wants to respond to, fix, or resolve review comments left on their own GitHub pull request. Also use when the user mentions "address review comments", "respond to reviewer", "resolve conversations", "fix the PR feedback", "reply to comments", "mark threads resolved", or asks what reviewers said on their PR.
version: 0.1.0
agents: [all]
tags: [github, code-review, workflow]
allowed-tools: Bash, Read, Write, Edit
---

# Address review

Work through the open review comments on your own pull request: triage every comment into
a table, fix everything that needs no human input, then bring the blockers and the
decisions to the human one at a time.

## When to use

- "What did the reviewers say and can you fix it?"
- "Address the comments on PR 412."
- "Reply to these threads and mark them resolved."
- "Address the review comments" with no PR named, while sitting in the branch's checkout
  or worktree.

Do not use this when the user wants to **review** someone else's PR and leave feedback.
That is the `review-pr` skill.

## Prerequisites

```bash
gh auth status    # must be logged in
```

If `gh` is missing or unauthenticated, stop and tell the user; do not guess at PR content.

**Command economy is a hard requirement.** Every script here batches into a single API
call. Never loop a command per thread, and never dump raw JSON into context.

## Workflow

The triage table is built first and drives everything after it. Do not start editing code
before the table is complete.

### 0. Identify the PR

When the user gives a PR URL or number, use it and skip to step 1.

When they do not, resolve the PR from the branch checked out in the current directory,
which works the same in a plain clone and in a `git worktree`. `gh` reads the branch of
the working directory it runs in:

```bash
gh pr view --json number,title,headRefName,url,state --jq '"\(.number)\t\(.state)\t\(.headRefName)\t\(.title)"'
```

Confirm the match before doing anything else: state the PR number, title, and branch back
to the user in one line, and carry on without waiting for a reply. Then read the slug and
number for the scripts:

```bash
gh repo view --json nameWithOwner --jq .nameWithOwner
```

Handle the ambiguous cases rather than guessing:

| Situation | Do |
| --- | --- |
| No PR for this branch | Say so and stop. Do not open one, and do not fall back to another branch's PR. |
| The PR is closed or merged | Say which, and ask whether to continue before fetching comments. |
| Several PRs share the head branch | List them with number, title, and base, and ask which one. |
| Not inside a git repo | Ask for the PR URL or number. |
| Detached HEAD | There is no branch to match. Ask for the PR URL or number. |

See `references/gh-commands.md` for the worktree details and the fallback when `gh` cannot
infer the repository.

### 1. Fetch the open review

```bash
bash scripts/open_review.sh <owner/repo> <n>
```

One call returns both kinds of open comment:

- `REVIEW` lines: the overall body of each non-approving review
  (`CHANGES_REQUESTED`, `COMMENTED`, `DISMISSED`, `PENDING`).
- `THREAD` lines: unresolved inline threads, either line-level (`path:41`) or file-level
  (`path:0`).

An **approved** review carries no open ask, so the script drops it. Resolved threads are
dropped too; pass `--all` only when you need to re-read something already closed, and
`--full` when a clipped body is genuinely ambiguous.

If the script returns nothing, there is nothing open. Say so and stop.

### 2. Fill the comment column

Put every returned comment into the table, one row per distinct ask. A single review body
that raises three separate points becomes three rows. A thread whose later comments are
just back-and-forth on one point stays one row.

| comment | severity | needsChanges | anyBlockers | anyDecisions |
| --- | --- | --- | --- | --- |

Columns:

- **comment** — the ask in your own words, plus its location: `src/auth.ts:41`,
  `src/auth.ts (file)`, or `review body (bob)`. Keep the thread ID with the row.
- **severity** — `Blocker` | `Suggestion` | `Nitpick` | `Praise`. See
  `references/triage-table.md`.
- **needsChanges** — `true` if resolving it requires a code change, else `false`.
- **anyBlockers** — `nil` when nothing blocks it, otherwise a detailed list of what does.
- **anyDecisions** — `nil` when no human choice is needed, otherwise a detailed list of
  the choices.

At this step, fill only the comment column. Leave the rest empty.

### 3. Mark the praise rows

Go through the table and find the comments that only compliment the change and ask for
nothing. Fill those rows out completely and immediately:

`severity: Praise`, `needsChanges: false`, `anyBlockers: nil`, `anyDecisions: nil`.

A comment that praises and then asks for something is not praise. Classify it by the ask.

### 4. Investigate everything else against the codebase

For each remaining row, read the actual code the comment points at, plus the code around
it, before classifying. A comment is only understood once you can say what the current
behavior is and what the reviewer wants instead.

Then fill in severity, needsChanges, anyBlockers and anyDecisions.

- A **blocker** is something outside this comment that must land first: a dependency that
  is not merged, a missing API, an unreleased upstream fix, another comment's change that
  this one sits on top of.
- A **decision** is a choice a human must make because the codebase and the PR context do
  not settle it: naming that has no precedent, a behavior tradeoff, scope, anything with
  two defensible answers.
- If the codebase or the PR discussion already answers it, it is **not** a decision.
  Follow the existing convention and record `nil`.

Show the completed table to the user before doing anything in step 5.

### 5. Dispatch the clear rows

Take every row where `anyBlockers` is `nil` and `anyDecisions` is `nil` and
`needsChanges` is `true`. These need no human input, so start them now.

Order them by severity first, `Blocker` then `Suggestion` then `Nitpick`. Within one
severity level, do the fastest first. **Severity always beats easiness**: never start a
nitpick before an unstarted blocker of the same clearance.

If an orchestration or agent-swarm capability is available, give each row its own worker
so they run in parallel. Otherwise do them inline, in the same order. See
`references/dispatch.md` for what each worker must be told and how to keep parallel edits
from colliding.

Rows where `needsChanges` is `false` need no worker. Reply directly with the explanation
and resolve.

### 6. Report the blockers while that work runs

Do not wait for the workers. While they run, list every row with a non-`nil`
`anyBlockers` to the human:

- what the comment asks for,
- exactly what is blocking it,
- what would unblock it.

If a blocker corresponds to a tracked item, link it. Check whichever tracker the user is
actually authenticated for rather than assuming:

```bash
gh issue list --search "<keywords>" --state open --limit 5
gh pr list --search "<keywords>" --state open --limit 5
```

Use the Jira or Linear tooling instead when that is what is connected. If no tracker is
available, say the blocker is untracked rather than inventing a ticket.

### 7. Ask the decisions, one at a time

After the blocker list, work through the rows with non-`nil` `anyDecisions`. Ask about
one decision, wait for the answer, then ask the next. Never batch them into a wall of
questions.

Each question must stand on its own for a reader with no context on the product:

1. **The problem** — what is wrong or undecided right now, in plain words.
2. **The context** — how the code behaves today and why the reviewer raised it.
3. **The options** — each realistic choice, with its consequence.
4. **The tradeoff** — what each option costs, and your recommendation with a reason.

No jargon, no unexplained internal names, no assumed knowledge of the PR. See
`references/asking-decisions.md` for the shape of a good question.

### 8. Act on each answer immediately

The moment a decision is answered, or the user says a blocker is now cleared, that row
becomes clear. Start it right away, in its own worker if orchestration is available,
**while you ask the next decision question**. Do not queue answered work until the end of
the interview.

Re-apply the step 5 ordering as rows unblock: a newly cleared blocker jumps ahead of an
in-queue nitpick.

### 9. Park what stays unresolved

If the user says a decision will be made later, or that a blocker stays for now, or to
ignore something, do not resolve that thread. Keep a running parked list holding the
comment, its thread ID, its severity, and exactly what it is waiting on. Carry it to the
end of the task.

### 10. Close out

When every clear row is done:

1. Run the project's checks (tests, lint, build). Never reply "fixed" without evidence.
2. Commit and push.

   ```bash
   git add -A && git commit -m "<what changed and why>" && git push
   ```

3. Reply and resolve each addressed thread in one call.

   ```bash
   bash scripts/reply_thread.sh <threadId> "Fixed in <sha> — <what changed>." --resolve
   ```

   Batch already-answered threads instead of looping:

   ```bash
   bash scripts/resolve_thread.sh <id1> <id2> <id3>
   ```

4. If the parked list from step 9 is non-empty, record it where the team will see it:
   add a section to the PR description naming each parked comment and what it waits on,
   and add the same note to the tracked issue when one exists.

   ```bash
   gh pr edit <n> --body-file <file>
   ```

5. Tell the human plainly which items are still undecided or still blocked, and that the
   PR is not fully addressed until those are settled.

## Reply style

- Say what changed and where, in one line: `Fixed in a1b2c3d — added the null guard in
  auth.ts:41.`
- Praise rows get a resolve with no reply, or a one-word acknowledgement. Do not write a
  paragraph back at a compliment.
- Disagreeing is fine, but give the reason, not just a refusal.
- No filler ("Great catch!", "Thanks so much!"). Reviewers read dozens of these.
- Never mark a thread resolved with a reply that promises a future fix.

## Rules

- When no PR is named, resolve it from the current branch or worktree and say which PR you
  picked. Never open a PR that does not exist, and never fall back to a different branch's
  PR.
- Build the whole table before changing any code. No edits during triage.
- Never resolve a thread you did not address, and never resolve another reviewer's thread
  on a disagreement.
- Never resolve a parked row. Parked means unresolved, by definition.
- Severity ordering beats easiness when choosing what to start next.
- Ask decision questions one at a time, and never let an answered decision sit idle while
  the interview continues.
- Do not invent a decision for something the codebase already settles; follow the
  existing convention instead.
- Never force-push a shared PR branch without the user explicitly asking.
- Never merge or close the PR unless the user asked for that exact action.
- One API call per job. Use the batching scripts; never loop per thread, and never
  re-fetch what `open_review.sh` already returned.
- Scope each edit to the comment that prompted it. Do not opportunistically refactor.
- No vendor or AI attribution in replies, commit messages, or PR text.

## References

Load these on demand, not up front.

- `references/triage-table.md` — how to classify severity, what counts as a real blocker
  versus a real decision, and a worked example table. Read at steps 2 to 4.
- `references/dispatch.md` — worker briefs, ordering, and avoiding collisions between
  parallel edits. Read at step 5.
- `references/asking-decisions.md` — the four-part question shape with a full example.
  Read at step 7.
- `references/gh-commands.md` — batched `gh`/GraphQL recipes for reviews, threads,
  replies, and resolution state, plus resolving the PR from the current branch or
  worktree. Read at step 0, or when a command needs changing.

## Scripts

| Script | Calls | Purpose |
| --- | --- | --- |
| `scripts/open_review.sh` | 1 | Open review bodies and unresolved threads; `--all`, `--full` |
| `scripts/reply_thread.sh` | 1 | Reply, plus `--resolve` in the same call |
| `scripts/resolve_thread.sh` | 1 | Resolve/unresolve many IDs in one mutation; reads stdin |

To review someone else's PR and leave feedback, use the `review-pr` skill.
