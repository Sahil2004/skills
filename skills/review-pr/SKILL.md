---
name: review-pr
description: When the user wants to review someone's GitHub pull request and leave feedback. Also use when the user mentions "review this PR", "code review", "look at this pull request", "what do you think of this PR", "request changes", or pastes a GitHub pull request URL asking for an opinion.
version: 0.2.0
agents: [all]
tags: [github, code-review, workflow]
allowed-tools: [Bash, Read, Write, Edit]
---

# Review PR

Review a GitHub pull request and post structured, severity-classified feedback.

## When to use

- "Review PR 412" / a pasted `https://github.com/<org>/<repo>/pull/<n>` URL.
- "Is this PR safe to merge?"
- "Look over these changes and tell me what's wrong."

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

8. **Post the review as one batched call.** Inline comments and the summary body go up
   together:

   ```bash
   gh pr review <n> --comment --body-file /tmp/review-<n>.md
   ```

   For line-anchored comments, submit them in a single `/reviews` request; see
   `references/gh-commands.md`.

9. **Never approve on the user's behalf unless they said to.** Default to `--comment`.

## Review output shape

```
## Summary
<what the PR does, 1-2 lines> — <recommendation: approve / changes / needs info>

## Blockers
- `path/file.ts:120` — <problem> → <concrete fix>

## Issues
- ...

## Nits
- ...

## Questions
- ...
```

Every finding names a file and line and proposes a fix. "This feels wrong" is not a review
comment. Omit empty sections.

## Rules

- One API call per job. Use `pr_context.sh`; never loop a command per file, and never
  re-fetch data it already returned.
- Never approve, merge, or close a PR unless the user asked for that exact action.
- Quote the specific line and give a concrete fix; no vague feedback.
- Be direct about severity. Do not soften a blocker into a nit.
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
