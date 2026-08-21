# Dispatching the clear rows

A row is **clear** when `anyBlockers` is `nil` and `anyDecisions` is `nil`. Clear rows
need no human input, so they start immediately: at step 5 for rows that were born clear,
and the moment a blocker lifts or a decision is answered for the rest.

## Ordering

Sort by severity first:

1. `Blocker`
2. `Suggestion`
3. `Nitpick`

Within one severity level, do the fastest first, so a one-line guard goes before a
multi-file rename of the same severity.

**Severity beats easiness, always.** Never start a nitpick while a clear blocker has not
been started. The point of easiness is to break ties inside a level, not to jump levels.

Re-sort as rows unblock. A blocker cleared during the decision interview jumps ahead of a
nitpick still sitting in the queue.

`Praise` rows never enter this queue: no work, just a resolve.

Rows where `needsChanges` is `false` never enter it either. They get a reply explaining
why no change was made, then a resolve.

## One worker per row

If an orchestration or agent-swarm capability is available, give each clear row its own
worker so independent fixes run in parallel. If none is available, do them inline in the
same order; nothing else about the process changes.

Each worker brief must carry:

- **The comment, verbatim**, plus its file and line.
- **The thread ID**, so the reply can be attributed.
- **The severity**, so the worker knows how much rigor is warranted.
- **The exact scope**: which files it may touch, and that it must not touch anything else.
- **The decision already made**, when the row was unblocked by an answer in step 7. The
  worker did not hear the conversation and will re-litigate it otherwise.
- **The project's check command**, so the worker verifies its own change.
- **Report back**: what changed, the files touched, and the check result.

Also restate the standing rules in every brief, since a worker starts with none of this
session's context:

- Scope the edit to this comment only. No opportunistic refactoring.
- Follow the repo's existing conventions, not personal defaults.
- No vendor or AI attribution in code, comments, or commit messages.

## Keeping parallel edits apart

Two workers editing one file will collide.

- Group rows that touch the same file into a single worker, ordered by severity within
  the brief.
- Assign a file to exactly one worker at a time.
- Where two rows genuinely depend on each other, that dependency is a blocker on the
  later row. Record it in `anyBlockers` and run them in sequence.
- Do not have workers commit independently. Collect the changes, run the checks once over
  the whole result, then make the commits in step 10.

## When a worker reports back

- **Done and checks pass** — mark the row done. It gets its reply and resolve at step 10.
- **Done but a check broke** — do not resolve. Either fix the fallout in scope, or say so
  in the reply and leave the thread open.
- **Blocked on something it found** — the triage missed a blocker. Move the row back,
  fill `anyBlockers`, and add it to the step 6 report.
- **Wants a judgement call** — the triage missed a decision. Move the row back, fill
  `anyDecisions`, and add it to the interview queue.

A row moving backwards out of dispatch is normal and correct. Guessing at an answer so
the row can stay in dispatch is not.
