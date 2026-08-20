---
name: review-pr
description: When the user wants to review someone's GitHub pull request, approve it, or leave feedback on it. Also use when the user mentions "review this PR", "code review", "look at this pull request", "what do you think of this PR", "approve this PR", "request changes", or pastes a GitHub pull request URL asking for an opinion.
version: 0.3.0
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
   gh pr diff <n> > /tmp/pr-<n>.diff
   ```

   Do not also run `gh pr view`, `gh pr checks`, or a per-file loop. `pr_context.sh`
   already returned all of it.

2. **Understand intent before judging code.** Read the PR description and linked issue.
   State in one line what the PR claims to do. If the description does not explain the
   change, that is the first review comment.

3. **Read the diff in context, not in isolation.** For every non-trivial hunk, open the
   full file. Reviewing only diff lines produces false positives. When several files need
   full context, run `gh pr checkout <n>` once and read locally rather than making an API
   call per file.

4. **Check CI and tests.** The `## Checks` section from step 1 already lists only the
   genuinely failing contexts. Failing checks are blocking. A behavior change with no test
   change is a finding.

5. **Apply the checklist.** Work through `references/review-checklist.md`: correctness,
   security, error handling, tests, API/back-compat, performance, readability. Skip
   categories that genuinely do not apply.

6. **Classify every finding** with a severity prefix so the author can triage:
   - `blocker:` correctness, security, data loss, breaking change.
   - `issue:` should be fixed before merge.
   - `nit:` style or taste, non-blocking.
   - `question:` you need information to judge.

7. **Read what other reviewers already said** (in the step 1 output) and do not repeat an
   existing open comment. Add signal, not volume.

8. **Decide the verdict**, which determines what happens next:

   | Findings after step 5-6 | Verdict | Action |
   | --- | --- | --- |
   | No blockers and no issues | **Clean** | Outcome A: approve, post no comments |
   | Any blocker, issue, or open question | **Needs work** | Outcome B: post findings |

   Nits alone do not make a PR "needs work". Under a clean verdict, nits are not posted to
   the PR at all; report them to the human instead (see Outcome A).

9. **Act on the verdict.** Clean goes to Outcome A, everything else to Outcome B. Post
   findings as one batched call:

   ```bash
   gh pr review <n> --comment --body-file /tmp/review-<n>.md
   ```

   For line-anchored comments, submit them in a single `/reviews` request; see
   `references/gh-commands.md`.

10. **Never merge or close a PR.** Approving is allowed only under a clean verdict
    (Outcome A); requesting changes needs the user to ask for it explicitly.

## Outcome A: the PR is correct

Use when there are no blockers and no issues. Approve the PR and leave **no review
comments on it at all**.

```bash
gh pr review <n> --approve
```

That is the entire GitHub-side action. Specifically:

- Post no summary body, no inline comments, and no nits to the PR. A correct PR gets a
  clean approval and nothing else.
- Do not open threads to note optional suggestions. If you noticed nits, they go in the
  report to the human below, not onto the PR.
- Never manufacture a concern to look thorough.

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

<Optional, chat only: any non-blocking nits I did not post to the PR.>
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

Use when there is at least one blocker, issue, or open question. Lead with the most
severe finding.

```
## Summary
<what the PR does, 1-2 lines>

**Verdict: needs changes.** <n> blocker(s), <n> issue(s). <one line on the main risk.>

## Blockers
- `path/file.ts:120` — <problem> → <concrete fix>

## Issues
- `path/file.ts:44` — <problem> → <concrete fix>

## Questions
- `path/file.ts:12` — <what you need to know to judge this>

## Optional nits
- <non-blocking suggestion>
```

Rules for this shape:

- Omit any section that is empty. Never print a header with "none" under it.
- Every finding names a file and line and proposes a concrete fix. "This feels wrong" is
  not a review comment.
- Keep the severity honest: if nothing is truly blocking, there are no blockers, and the
  verdict line should say so.
- When the only findings are questions, say **"Verdict: needs info."** rather than
  implying the code is wrong.

## Rules

- One API call per job. Use `pr_context.sh`; never loop a command per file, and never
  re-fetch data it already returned.
- Approve only under a clean verdict, and approve with no comments attached. Never merge
  or close a PR, and never request changes unless the user asked for that action.
- Never approve to be agreeable. If any category is unverified or any doubt remains, that
  is Outcome B, not an approval.
- Quote the specific line and give a concrete fix; no vague feedback.
- Be direct about severity. Do not soften a blocker into a nit, and do not inflate a nit
  into a blocker to justify a longer review.
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

| Script | Calls | Purpose |
| --- | --- | --- |
| `scripts/pr_context.sh` | 1 | Whole review context: meta, files, failing checks, reviews, threads |
