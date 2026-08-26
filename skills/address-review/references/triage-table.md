# The triage table

The table is the whole plan. Every later step reads from it, so a wrong cell turns into
wrong work.

## Shape

| comment | severity | needsChanges | anyBlockers | anyDecisions |
| --- | --- | --- | --- | --- |

Keep the thread ID beside each row (a scratch column, or a list under the table). You
need it to reply and resolve later, and re-fetching to recover it costs a call.

## One row per ask, not per comment

- A review body that raises three separate points becomes three rows.
- A thread with eight comments arguing about one point stays one row.
- Two reviewers raising the same point on the same lines is one row; name both.

## severity

`Blocker` | `Suggestion` | `Nitpick` | `Praise`

| Severity | Meaning |
| --- | --- |
| `Blocker` | Correctness, security, data loss, a breaking change, or the reviewer said it blocks merge. |
| `Suggestion` | Should be fixed before merge, but nothing breaks if it is not. |
| `Nitpick` | Style or taste. The author may decline. |
| `Praise` | Compliments the change and asks for nothing. |

If the reviewer already prefixed a severity, use theirs. Do not downgrade a reviewer's
`[Blocker]` to a suggestion because it looks easy, and do not inflate a nitpick to make
the work look bigger.

A comment that praises and then asks for something is not `Praise`. Classify it by the
ask.

An open question from the reviewer takes the severity of what it gates: `Blocker` when
correctness cannot be judged without the answer.

## needsChanges

`true` when resolving the comment requires editing code, config, or docs in this repo.

`false` when the right response is a reply: the reviewer misread the code, the behavior
is already correct, the concern is handled elsewhere, or it is praise.

`false` does not mean "no work". A `false` row still gets a reply that explains why,
before it is resolved.

## anyBlockers

`nil` when nothing outside this comment stands in the way.

Otherwise a detailed list. A blocker is external and concrete:

- a dependency PR that is not merged,
- an API or endpoint that does not exist yet,
- an upstream bug fix that is unreleased,
- a migration or deploy that must land first,
- another row in this table whose change this one sits on top of.

Each blocker entry says what it is, why it stops this comment, and what would clear it.

Not blockers: work being large, work being unfamiliar, needing to read more code, or a
choice a human must make. That last one is a decision, not a blocker.

## anyDecisions

`nil` when the codebase and the PR discussion settle the question.

Otherwise a detailed list of the choices a human must make. A decision is real when two
answers are both defensible and nothing in the repo picks between them:

- naming with no established precedent,
- a behavior tradeoff (strict versus lenient, fail closed versus fail open),
- scope (fix here or in a follow-up),
- anything touching a product or UX judgement.

**Check before asking.** Grep for the existing convention, read neighbouring modules, read
the PR description and earlier threads. If any of those answers it, follow them and record
`nil`. Asking a question the codebase already answers wastes the human's turn.

A row can have both blockers and decisions. It stays out of dispatch until both are `nil`.

## Worked example

Reviewer left: a null-guard blocker, a naming nitpick with no precedent, a suggestion that
depends on an unmerged PR, and a compliment.

| comment | severity | needsChanges | anyBlockers | anyDecisions |
| --- | --- | --- | --- | --- |
| `src/auth.ts:41` — session may be null before `.user` is read, throws on expired cookie | Blocker | true | nil | nil |
| `src/auth.ts:12` — rename `chk` to something readable | Nitpick | true | nil | Repo has no precedent: neighbouring files use both `validateX` and `isX`. Pick one for this codebase. |
| `src/api/client.ts:88` — use the new batch endpoint instead of the loop | Suggestion | true | Batch endpoint ships in PR #418, unmerged. Calling it now 404s. Clears when #418 merges and deploys. | nil |
| review body (bob) — error handling in the middleware reads well | Praise | false | nil | nil |

Dispatch order from this table: row 1 only (the sole fully clear row). Row 3 goes to the
blocker report in step 6, row 2 to the decision interview in step 7, row 4 gets a resolve
with no work.
