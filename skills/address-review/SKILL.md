---
name: address-review
description: When the user wants to respond to, fix, or resolve review comments left on their own GitHub pull request. Also use when the user mentions "address review comments", "respond to reviewer", "resolve conversations", "fix the PR feedback", "reply to comments", "mark threads resolved", or asks what reviewers said on their PR.
version: 0.1.0
agents: [all]
tags: [github, code-review, workflow]
allowed-tools: Bash, Read, Write, Edit
---

# Address review

Work through the review comments on your own pull request: fix the code, reply to each
thread, and resolve only what was genuinely addressed.

## When to use

- "What did the reviewers say and can you fix it?"
- "Address the comments on PR 412."
- "Reply to these threads and mark them resolved."

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

1. **Fetch every open thread** in one call, with resolution state:

   ```bash
   bash scripts/fetch_threads.sh <owner/repo> <n>
   ```

   One TAB-separated line per comment: `<threadId>  <path>:<line>  <author>: <body>`,
   bodies clipped to 400 chars. Add `--full` only when a clipped comment is genuinely
   ambiguous, `--all` to include resolved threads. Pipe with `cut -f1` for bare IDs.

2. **Group the comments** into: (a) will fix, (b) already correct / needs explanation,
   (c) out of scope / follow-up. Show the user this grouping before making edits when the
   comment count is large or any change is risky.

3. **Fix code first, reply second.** For each "will fix" thread, make the edit, keeping
   the change minimal and scoped to the comment. Do not opportunistically refactor. If a
   comment is ambiguous, ask the reviewer in the thread rather than guessing at a rewrite.

4. **Run the project's checks** after edits (tests, lint, build). Do not reply "fixed"
   without evidence. If a fix breaks something else, say so in the reply instead of
   silently reverting.

5. **Commit and push.**

   ```bash
   git add -A && git commit -m "<what changed and why>" && git push
   ```

   Reference the reviewer's point in the message body, not the commit subject.

6. **Reply and resolve in one call per thread.** `--resolve` performs the reply and the
   resolution in a single request, so use it for anything you actually fixed:

   ```bash
   bash scripts/reply_thread.sh <threadId> "Fixed in <sha> — <what changed>." --resolve
   ```

   Omit `--resolve` when you are only explaining. To close out several already-answered
   threads, batch them into one mutation instead of looping:

   ```bash
   bash scripts/resolve_thread.sh <id1> <id2> <id3>
   ```

7. **Leave disagreements open.** If you did not make a change, reply with the reasoning
   and leave the thread unresolved for the reviewer to close.

8. **Summarize** back to the user: threads addressed, threads left open and why, commits
   pushed.

## Reply style

- Say what changed and where, in one line: `Fixed in a1b2c3d — added the null guard in
  auth.ts:41.`
- Disagreeing is fine, but give the reason, not just a refusal.
- No filler ("Great catch!", "Thanks so much!"). Reviewers read dozens of these.
- Never mark a thread resolved with a reply that promises a future fix.

## Rules

- Never resolve a thread you did not address, and never resolve another reviewer's thread
  on a disagreement.
- Never force-push a shared PR branch without the user explicitly asking.
- Never merge or close the PR unless the user asked for that exact action.
- One API call per job. Use the batching scripts; never loop per thread, and never
  re-fetch what `fetch_threads.sh` already returned.
- Scope each edit to the comment that prompted it.
- No vendor or AI attribution in replies or commit messages.

## References

- `references/gh-commands.md` — batched `gh`/GraphQL recipes for threads, replies, and
  resolution state.

## Scripts

| Script | Calls | Purpose |
| --- | --- | --- |
| `scripts/fetch_threads.sh` | 1 | Threads as TAB lines; `--all`, `--full` |
| `scripts/reply_thread.sh` | 1 | Reply, plus `--resolve` in the same call |
| `scripts/resolve_thread.sh` | 1 | Resolve/unresolve many IDs in one mutation; reads stdin |

To review someone else's PR and leave feedback, use the `review-pr` skill.
