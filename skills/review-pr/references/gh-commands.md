# gh and GraphQL recipes

All commands assume `gh auth status` succeeds. `<n>` is the PR number, `<owner/repo>` the
repository slug. Inside a checked-out repo `gh` infers the slug; pass `-R <owner/repo>` when
it does not.

## Reading a PR

```bash
gh pr view <n> --json title,body,author,state,additions,deletions,changedFiles,labels
gh pr diff <n>                       # unified diff
gh pr diff <n> --name-only           # touched paths
gh pr checks <n>                     # CI status
gh pr checkout <n>                   # local checkout for full-file context
gh pr view <n> --json commits --jq '.commits[].messageHeadline'
```

Parse a pasted URL: `https://github.com/<owner>/<repo>/pull/<n>`.

## Existing feedback

```bash
gh pr view <n> --comments                                  # issue-level conversation
gh api repos/<owner/repo>/pulls/<n>/comments --paginate     # inline review comments
gh api repos/<owner/repo>/pulls/<n>/reviews --paginate      # review verdicts
```

Resolution state lives only in GraphQL; use `scripts/fetch_threads.sh`.

## Posting a review

```bash
gh pr review <n> --comment        --body-file /tmp/review.md
gh pr review <n> --request-changes --body-file /tmp/review.md
gh pr review <n> --approve        --body "LGTM"
```

Default to `--comment`. Never `--approve` unless the user asked.

### Inline comments on specific lines

```bash
gh api repos/<owner/repo>/pulls/<n>/reviews \
  -f event=COMMENT \
  -f body="Summary" \
  -f 'comments[][path]=src/app.ts' \
  -F 'comments[][line]=120' \
  -f 'comments[][side]=RIGHT' \
  -f 'comments[][body]=blocker: this dereferences a possibly-null value.'
```

Use `start_line` plus `line` for a multi-line range. `side=LEFT` targets the pre-change
version. The line must exist in the diff or the API rejects it.

## Threads: reply and resolve

```bash
bash scripts/fetch_threads.sh <owner/repo> <n>          # unresolved threads + threadIds
bash scripts/fetch_threads.sh <owner/repo> <n> --all    # include resolved
bash scripts/reply_thread.sh  <threadId> "Fixed in abc1234 — added the null guard."
bash scripts/resolve_thread.sh <threadId>
bash scripts/resolve_thread.sh <threadId> --undo
```

`threadId` is an opaque node ID (`PRRT_...`), not the numeric comment id.

## Pushing fixes

```bash
git add -A && git commit -m "Guard against a null session in the auth middleware" && git push
```

Never force-push a shared branch unless the user asks explicitly.

## Failure modes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `gh: Not Found` | Wrong slug or no access | Pass `-R <owner/repo>`, check `gh auth status` |
| Inline comment rejected | Line not part of the diff | Comment on a diff line, or use the summary body |
| `Resource not accessible` | Token lacks scope | `gh auth refresh -s repo` |
| Thread reply 404 | Numeric id used as `threadId` | Re-fetch node IDs via `fetch_threads.sh` |
