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
3. **Load the open threads before auditing.** Read `## Unresolved threads` from step 1 and
   keep that list in mind for the whole review. An unresolved thread is feedback already
   visible to the author, so re-posting it adds noise and splits the discussion. A thread
   that someone **resolved** is fair game again: if the underlying problem is still in the
   code, raise it, because resolving a thread does not fix anything. See
   `references/existing-threads.md` for how to match a finding to a thread and what to do
   with a suppressed one.
4. **Understand intent before judging code.** Read the PR description and linked
   issues. State in one line what the PR claims to do. If the description does not
   explain the change, that is the first review comment.
5. **Read the diff in context, not in isolation.** For every non-trivial hunk, open the
   full file. Reviewing only diff lines produces false positives. When several files need
   full context, run `gh pr checkout <n>` once and read locally rather than making an API
   call per file.
6. **Check tests.** CI is already green by step 2, so what remains is coverage: a
   behavior change with no test change is a finding.
7. **Apply the checklist.** Work through `references/review-checklist.md`: correctness,
   security, error handling, tests, API/back-compat, performance, readability. Skip
   categories that genuinely do not apply.
8. **Classify every finding** with a severity prefix so the author can triage:

   - `[Blocker]` correctness, security, data loss, breaking change. Must be fixed.
   - `[Suggestion]` should be fixed before merge, but not dangerous.
   - `[Nitpick]` style or taste. Non-blocking, the author may decline.

   An open question counts as a blocker or a suggestion depending on what it gates: use
   `[Blocker]` when you cannot judge correctness without the answer.
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

## Outcomes

Exactly one applies. Read its file and follow it; do not read the other two.

| Condition | Outcome | Read |
| --- | --- | --- |
| Any CI check failing | **C** | `references/outcome-ci-failing.md` |
| CI green, nothing to change | **A** | `references/outcome-approve.md` |
| CI green, any finding at all | **B** | `references/outcome-request-changes.md` |

Outcome C overrides the others: a failing check ends the review whatever the diff looks
like. Between A and B, a single nitpick is enough to make it B.

## Rules

These hold for every review; the outcome-specific rules live in that outcome's file.

- One API call per job. Use `pr_context.sh`; never loop a command per file, and never
  re-fetch data it already returned.
- Failing CI ends the review before it starts, with no counts line and no code comments.
- Approve only when there is nothing to change, and approve with no comments attached.
  Any finding, down to one nitpick, is a request for changes.
- Never merge or close a PR.
- Never approve to be agreeable. If any category is unverified or any doubt remains, that
  is Outcome B, not an approval.
- A clean PR gets a clean review. Finding nothing is a valid, complete result; never
  invent findings to fill the template.
- Be direct about severity in both directions: do not soften a blocker into a nitpick, and
  do not inflate a nitpick to justify a longer review.
- Every finding names a concrete fix. "This feels wrong" is not a review comment.
- The counts in the review body must equal the findings actually posted, so a finding
  suppressed as a duplicate of an open thread is not counted.
- Never re-post a finding that an unresolved thread already covers. A thread that was
  resolved without the code changing may be raised again.
- Judge the diff against the repo's existing conventions, not your own defaults, and do
  not rewrite the author's style preferences as blockers.
- No vendor or AI attribution in review bodies.

## References

Load these on demand, not up front.

- `references/review-checklist.md` — the per-category checklist. Read at step 6, when
  actually reviewing the diff.
- `references/writing-comments.md` — placement tiers, the five-bullet comment structure,
  and committable suggestions. Read under Outcome B, before posting findings.
- `references/existing-threads.md` — how to suppress a finding another reviewer already
  has open, and when a resolved thread may be re-raised. Read at step 3.
- `references/gh-commands.md` — the review JSON payload, batched `gh`/GraphQL recipes,
  and the costly anti-patterns. Read when posting, or when a command needs changing.

One outcome file, chosen by the verdict. Never more than one:

- `references/outcome-ci-failing.md` — Outcome C, any check failing.
- `references/outcome-approve.md` — Outcome A, nothing to change.
- `references/outcome-request-changes.md` — Outcome B, any finding at all.

## Scripts

| Script                  | Calls | Purpose                                                             |
| ----------------------- | ----- | ------------------------------------------------------------------- |
| `scripts/pr_context.sh` | 1     | Whole review context: meta, files, failing checks, reviews, threads |
