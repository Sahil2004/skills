---
name: review-pr
description: When the user wants to review a GitHub pull request, or respond to and resolve review comments left on their own PR. Also use when the user mentions "review this PR", "code review", "PR feedback", "address review comments", "resolve conversations", "reply to reviewer", or pastes a GitHub pull request URL.
version: 0.1.0
agents: [all]
tags: [github, code-review, workflow]
allowed-tools: [Bash, Read, Write, Edit]
---

# Review PR

Run a GitHub pull request through one of two jobs: produce a review of someone else's PR,
or answer and resolve the review comments sitting on your own PR.

## When to use

- "Review PR 412" / a pasted `https://github.com/<org>/<repo>/pull/<n>` URL.
- "What did the reviewers say and can you fix it?"
- "Reply to these comments and mark them resolved."

Do not use this when the change is not on GitHub yet (review the working tree directly) or
when the user only wants a commit message or PR description.

## Mode selection

Ask nothing if it is obvious; infer from the request.

| Signal | Mode |
| --- | --- |
| "review", "look at this PR", no existing review threads for the user | **Mode A: review** |
| "address", "respond", "resolve", "fix the comments", PR is authored by the user | **Mode B: respond** |

If both apply, do Mode A first, then offer Mode B.

## Prerequisites

```bash
gh auth status                      # must be logged in
gh pr view <n> --json number,title,state,author,headRefName,baseRefName
```

If `gh` is missing or unauthenticated, stop and tell the user; do not guess at PR content.

---

## Mode A: reviewing a PR

1. **Load the PR.**

   ```bash
   gh pr view <n> --json title,body,author,additions,deletions,changedFiles,labels
   gh pr diff <n> > /tmp/pr-<n>.diff
   gh pr view <n> --json files --jq '.files[].path'
   ```

2. **Understand intent before judging code.** Read the PR description and linked issue.
   State in one line what the PR claims to do. If the description does not explain the
   change, that is the first review comment.

3. **Read the diff in context, not in isolation.** For every non-trivial hunk, open the
   full file (`gh pr checkout <n>` when local context is needed). Reviewing only diff
   lines produces false positives.

4. **Check CI and tests.**

   ```bash
   gh pr checks <n>
   ```

   Failing checks are blocking. A behavior change with no test change is a finding.

5. **Apply the checklist.** Work through `references/review-checklist.md`: correctness,
   security, error handling, tests, API/back-compat, performance, readability. Skip
   categories that genuinely do not apply.

6. **Classify every finding** with a severity prefix so the author can triage:
   - `blocker:` correctness, security, data loss, breaking change.
   - `issue:` should be fixed before merge.
   - `nit:` style or taste, non-blocking.
   - `question:` you need information to judge.

7. **Post the review.** Prefer inline comments on the exact lines, one summary body.

   ```bash
   gh pr review <n> --comment --body-file /tmp/review-<n>.md
   # or, when explicitly asked:
   gh pr review <n> --request-changes --body-file /tmp/review-<n>.md
   gh pr review <n> --approve --body "..."
   ```

   Line-anchored comments use the API; see `references/gh-commands.md`.

8. **Never approve on the user's behalf unless they said to.** Default to `--comment`.

### Review output shape

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
comment.

---

## Mode B: responding to and resolving reviews

1. **Fetch every open thread**, including inline ones and their resolution state:

   ```bash
   bash scripts/fetch_threads.sh <owner/repo> <n>
   ```

   This prints each unresolved thread with its `threadId`, file, line, author, and body.

2. **Group the comments** into: (a) will fix, (b) already correct / needs explanation,
   (c) out of scope / follow-up. Show the user this grouping before making edits when the
   comment count is large or any change is risky.

3. **Fix code first, reply second.** For each "will fix" thread, make the edit, keep the
   change minimal and scoped to the comment. Do not opportunistically refactor.

4. **Run the project's checks** after edits (tests, lint, build). Do not reply "fixed"
   without evidence.

5. **Commit and push.**

   ```bash
   git add -A && git commit -m "<what changed and why>" && git push
   ```

   Reference the reviewer's point in the message body, not the commit subject.

6. **Reply to each thread**, then resolve only the ones actually addressed:

   ```bash
   bash scripts/reply_thread.sh <threadId> "Fixed in <sha> — <one line on what changed>."
   bash scripts/resolve_thread.sh <threadId>
   ```

7. **Leave disagreements open.** If you did not make a change, reply with the reasoning
   and leave the thread unresolved for the reviewer to close.

8. **Summarize** back to the user: threads addressed, threads left open and why, commits
   pushed.

## Rules

- Never resolve a thread you did not address, and never resolve another reviewer's thread
  on a disagreement.
- Never force-push a shared PR branch without the user explicitly asking.
- Never approve, merge, or close a PR unless the user asked for that exact action.
- Quote the specific line and give a concrete fix; no vague feedback.
- Be direct about severity. Do not soften a blocker into a nit.
- No vendor or AI attribution in review bodies, replies, or commit messages.
- Do not rewrite the PR author's style preferences as blockers.

## References

- `references/review-checklist.md` — the full per-category review checklist.
- `references/gh-commands.md` — `gh` and GraphQL recipes for threads, inline comments,
  and resolution state.
