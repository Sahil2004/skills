---
name: review-pr
description: When the user wants to review someone's GitHub pull request, approve it, or leave feedback on it. Also use when the user mentions "review this PR", "code review", "look at this pull request", "what do you think of this PR", "approve this PR", "request changes", or pastes a GitHub pull request URL asking for an opinion.
version: 0.1.0
agents: [all]
tags: [github, code-review, workflow]
allowed-tools: [Bash, Read, Write, Edit]
---
# Review PR

Review a GitHub pull request, then either approve it cleanly or post structured,
severity-classified feedback. A correct PR is approved with no comments attached; a PR
with findings gets those findings and no approval.

## When to use

- "Review PR 412" / a pasted `https://github.com/<org>/<repo>/pull/<n>` URL.
- "Is this PR safe to merge?" (answering "yes, nothing blocking" is a valid outcome)
- "Look over these changes and tell me what's wrong."
- "Approve this PR if it's fine."

  Do not use this when the user wants to **answer** review comments already left on their own
  PR; this skill produces feedback, it does not reply to it. Also skip this when the change
  is not on GitHub yet (review the working tree directly) or the user only wants a PR
  description.

## Prerequisites

```bash
gh auth status    # must be logged in
```

If `gh` is missing or unauthenticated, stop and tell the user; do not guess at PR content.

**Command economy is a hard requirement.** Every script here batches into a single API
call. Never poll, never loop a command per file, and never dump raw JSON into context. See
`references/gh-commands.md` for the anti-patterns to avoid.

## Workflow

1. **Load the PR in one call.** Metadata, file churn, CI status, existing reviews, and
   open threads all come back from a single request:

   ```bash
   bash scripts/pr_context.sh <owner/repo> <n>
   ```

   Then fetch the diff once and reuse it:

   ```bash
   gh pr diff <n> --repo <owner/repo> > /tmp/pr-<n>.diff
   ```

   Do not also run `gh pr view`, `gh pr checks`, or a per-file loop. `pr_context.sh`
   already returned all of it.
2. **Gate on CI before reviewing anything.** Read the `## Checks` section from step 1
   first. If any context is listed `FAIL`, stop immediately: do not read the diff, do not
   run the checklist, do not classify findings. Go straight to Outcome C below. A red
   build makes a line-by-line review premature, since the fix will change the diff.
   `PENDING` contexts are not failures; review normally and note anything still running.
3. **Understand intent before judging code.** Read the PR description and linked
   issues. State in one line what the PR claims to do. If the description does not
   explain the change, that is the first review comment.
4. **Read the diff in context, not in isolation.** For every non-trivial hunk, open the
   full file. Reviewing only diff lines produces false positives. When several files need
   full context, run `gh pr checkout <n>` once and read locally rather than making an API
   call per file.
5. **Check tests.** CI is already green by step 2, so what remains is coverage: a
   behavior change with no test change is a finding.
6. **Apply the checklist.** Work through `references/review-checklist.md`: correctness,
   security, error handling, tests, API/back-compat, performance, readability. Skip
   categories that genuinely do not apply.
7. **Classify every finding** with a severity prefix so the author can triage:

   - `[Blocker]` correctness, security, data loss, breaking change. Must be fixed.
   - `[Suggestion]` should be fixed before merge, but not dangerous.
   - `[Nitpick]` style or taste. Non-blocking, the author may decline.

   An open question counts as a blocker or a suggestion depending on what it gates: use
   `[Blocker]` when you cannot judge correctness without the answer.
8. **Read what other reviewers already said** (in the step 1 output) and do not repeat an
   existing open comment. Add signal, not volume.
9. **Decide the verdict**, which determines what happens next:

   | State                               | Verdict        | Action                               |
   | ----------------------------------- | -------------- | ------------------------------------ |
   | Any CI check failing                | **Blocked**    | Outcome C: request changes, CI only  |
   | CI green, nothing at all            | **Clean**      | Outcome A: approve, post no comments |
   | CI green, any finding               | **Needs work** | Outcome B: request changes           |


   Any finding at all, down to a single nitpick, means Outcome B. Only a PR with nothing
   to change is approved.
10. **Place each finding at the narrowest scope that fits**, then act on the verdict.
    See "Comment placement" below for the three tiers and the exact API calls.
11. **Never merge or close a PR.** Approve only under a clean verdict (Outcome A);
    request changes under Outcome B.

## Outcome C: CI is failing

This outrules every other outcome. If any check is failing, request changes on the CI
alone and stop. Do not review the code.

```bash
gh pr review <n> --request-changes --body "$(cat <<'EOF'
CI is failing. Please get the checks green, then I will review.

- lint: FAILURE
- e2e: TIMED_OUT
EOF
)"
```

Rules for this outcome:

- Be blunt and brief. Two lines plus the list of failing checks is the whole review.
- **No counts line.** `Blockers: ...` belongs only to a review that examined the code.
- **No inline comments**, no file comments, no checklist findings, no suggestions. The
  diff has not been reviewed, and saying otherwise would be false.
- Name the failing contexts exactly as `## Checks` reported them, so the author knows
  which job to open. Do not speculate about why they failed.
- Do not approve, and do not soften this into a comment-only review.
- `PENDING` is not failing. Never gate on a check that is merely still running.
- When the author pushes a fix and asks again, start over at step 1; the diff has moved.

  Tell the human in chat that the review stopped at CI and no code review was performed.

## Outcome A: the PR is correct

Use only when CI is green and there is nothing to change at all: no blockers, no
suggestions, no nitpicks. Approve the PR and leave **no review comments on it at all**.

```bash
gh pr review <n> --approve
```

That is the entire GitHub-side action. Specifically:

- Post no summary body and no inline comments. A correct PR gets a clean approval and
  nothing else.
- If you found even one nitpick worth telling the author, this is not Outcome A. Use
  Outcome B and post it.
- Never manufacture a concern to look thorough, and never suppress a real one to reach a
  clean approval.

  Then tell the human, in chat, that the PR is correct and what you verified:

```
Approved PR #<n> — <title>.

The PR is correct according to everything I verified, and I checked all the cases:
- Correctness: <what you confirmed>
- Security: <what you confirmed>
- Error handling: <what you confirmed>
- Tests: <what you confirmed>
- API/compatibility: <what you confirmed>
- Performance: <what you confirmed>
- CI: <status>

<Optional, chat only: anything worth knowing that was not worth a review comment.>
```

  Rules for this shape:

- The chat report lists every checklist category from `references/review-checklist.md`
  that you examined, so "I verified all cases" is backed by specifics, not asserted bare.
- Only claim a category if you actually checked it. If something was genuinely not
  applicable, say "n/a" and why rather than dropping it silently.
- If you could not verify a category you would normally check (no local checkout, CI not
  run, generated code you cannot read), the verdict is not clean. Say what is unverified
  and use Outcome B with a question instead of approving.

## Outcome B: the PR needs changes

Use when there is **any** finding, including a lone nitpick. Request changes, and put each
finding at the narrowest scope that fits it.

### Severity vocabulary

- **Blocker** — correctness, security, data loss, breaking change. Must be fixed.
- **Suggestion** — should be fixed before merge, but not dangerous.
- **Nitpick** — style or taste. Non-blocking, author may decline.

### The main comment

The body is the counts, and nothing else unless a finding fits nowhere else:

```
Blockers: 2, Suggestions: 3, Nitpicks: 1

<Only findings that fit no line and no file: PR scope, missing tests overall,
architectural concerns, missing description. One bullet each. Omit this whole
block when every finding is placed inline or on a file.>
```

Include every category in the count line even when zero, as in
`Blockers: 0, Suggestions: 2, Nitpicks: 1`, so the author can see the shape of the
review at a glance.

The body is the last resort, not a summary. A finding appears there only because there is
no line and no file to attach it to. Never restate, preview, or summarize a finding that
is already posted inline or on a file, and do not add a lead-in describing the main risk.
When every finding has a home, the body is exactly one line: the counts.

### Comment placement


| Scope of the finding              | Where it goes         | How                                 |
| --------------------------------- | --------------------- | ----------------------------------- |
| Specific line(s) of code          | Inline on those lines | `line` (+ `start_line` for a range) |
| A file as a whole                 | On the file           | `subject_type: file`, no `line`     |
| Neither: general or cross-cutting | The main review body  | Bullet in the body                  |


Choose the narrowest tier that is truthful. Do not push a line-specific finding up into
the summary, and do not attach a general concern to an arbitrary line just to anchor it.

### Comment structure

Every comment placed on a line or a file opens with a bold heading naming the severity
in square braces, followed by a one-line statement of the issue, then the same five bold
bullets in this order:

```
**[Blocker] `user` may be nil on the logged-out path.**

- **What:** When nobody is signed in, `user` is empty here, and the next line asks that
  empty value for its name.
- **Why:** Asking an empty value for a field crashes the request instead of returning an
  error the caller can handle.
- **Impact:** Every logged-out visitor to this endpoint gets a 500, and the handler never
  reaches the error path that would have told them to sign in.
- **Repro:** Call `GET /api/profile` with no session cookie, or run `go test ./pkg/auth`
  after adding a case with a nil user.
- **Fix:** Return `ErrUnauthenticated` before touching `user`.
```

The heading is the whole finding in one line, so a reader skimming the Files tab knows
the severity and the problem without expanding anything. Braced label exactly as
`[Blocker]`, `[Suggestion]`, or `[Nitpick]`, and the entire heading line is bold.

Write all five for a reader who does not know this codebase:

- **What** — the problem in plain words. Name the condition that triggers it. No jargon,
  no internal shorthand, no "this violates X" without saying what X means here.
- **Why** — why it must be resolved, not merely that it is wrong. The rule or reason
  behind it, in one sentence.
- **Impact** — the concrete consequence if it ships: who hits it, what they see, what
  breaks. For a nitpick this is honestly small; say so rather than inflating it.
- **Repro** — how to see it for yourself: the exact request, command, input, or state
  that triggers it, and what you observe. Prefer something the author can run.
- **Fix** — the specific change to make. Name the function, value, or line to change.
  Pair it with a `suggestion` block whenever the fix is small enough to commit directly.

  Keep each bullet to a sentence or two. If a bullet would be empty or a restatement of
  another, the finding is probably not real; drop it rather than padding the shape.

  Some findings cannot be run, notably style and readability nitpicks. Never invent a
  repro for them. Say where it is visible instead, such as **Repro:** Read the block as a
  newcomer, or **Repro:** Not runnable, visible on inspection only. A blocker that you
  cannot describe how to reach deserves a second look; if nothing triggers it, it may not
  be a blocker.

### Committable suggestions

When a fix is small and you can express it as the literal replacement text, use a
`suggestion` block. GitHub renders it with an "Apply suggestion" button the author can
commit in one click.

```
**[Blocker] `user` may be nil on the logged-out path.**

- **What:** When nobody is signed in, `user` is empty, and the next line asks that empty
  value for its name.
- **Why:** Asking an empty value for a field crashes the request instead of returning a
  handled error.
- **Impact:** Every logged-out visitor to this endpoint gets a 500 instead of a sign-in
  prompt.
- **Repro:** Call `GET /api/profile` with no session cookie.
- **Fix:** Return `ErrUnauthenticated` before touching `user`.

```suggestion
    if user == nil {
        return ErrUnauthenticated
    }
    return user.Name
```
```

Rules for suggestion blocks:

- The block replaces **exactly** the commented line range, so the range must cover every
line you are rewriting and the replacement must be complete, compiling code.
- Match the surrounding indentation exactly; the block is inserted verbatim.
- Use one only when the fix is small and unambiguous. A refactor spanning several
functions is described in prose, not forced into a suggestion.
- Never put a placeholder or `...` inside a suggestion block. It would be committed as-is.

### Posting it

Submit the whole review, body and all inline comments, in one call:

```bash
gh api repos/<owner/repo>/pulls/<n>/reviews --input /tmp/review-<n>.json
```

Build the payload with `event: REQUEST_CHANGES`, the count-led body, and one entry per
finding. See `references/gh-commands.md` for the full JSON shape, including the
`subject_type: file` form and suggestion-block escaping.

### Rules for this shape

- Every placed finding opens with a bold heading, `**[Blocker] ...**`,
  `**[Suggestion] ...**`, or `**[Nitpick] ...**`, stating the issue in one line, then
  carries all five bullets: **What**, **Why**, **Impact**, **Repro**, **Fix**.
- Write for someone unfamiliar with the codebase. Plain language, no unexplained jargon.
- Every finding proposes a concrete fix. "This feels wrong" is not a review comment.
- Keep severity honest in both directions: do not soften a blocker into a nitpick, and do
  not inflate a nitpick to pad the counts.
- The counts in the body must equal the findings actually posted.
- When the only findings are open questions, request changes but phrase them as questions
  on the relevant lines rather than implying the code is wrong.

## Rules

- One API call per job. Use `pr_context.sh`; never loop a command per file, and never
  re-fetch data it already returned.
- Failing CI ends the review before it starts. Request changes on the checks alone, with
  no counts line and no code comments, and never review the diff underneath a red build.
- Approve only when there is nothing to change, and approve with no comments attached.
  Any finding, down to one nitpick, is a request for changes. Never merge or close a PR.
- Never approve to be agreeable. If any category is unverified or any doubt remains, that
  is Outcome B, not an approval.
- Put every finding at the narrowest true scope: line, then file, then the review body.
- Quote the specific line and give a concrete fix; no vague feedback.
- Offer a committable `suggestion` block whenever the fix is small and unambiguous.
- Be direct about severity. Do not soften a blocker into a nitpick, and do not inflate a
  nitpick into a blocker to justify a longer review.
- The counts in the review body must match the findings actually posted.
- A clean PR gets a clean review. Finding nothing is a valid, complete result; never
  invent findings to fill the template.
- Do not rewrite the PR author's style preferences as blockers.
- Judge the diff against the repo's existing conventions, not your own defaults.
- No vendor or AI attribution in review bodies.

## References

- `references/review-checklist.md` — the full per-category review checklist.
- `references/gh-commands.md` — batched `gh`/GraphQL recipes, the inline-comment API, and
  the costly anti-patterns to avoid.

## Scripts


| Script                  | Calls | Purpose                                                             |
| ----------------------- | ----- | ------------------------------------------------------------------- |
| `scripts/pr_context.sh` | 1     | Whole review context: meta, files, failing checks, reviews, threads |


