# gh and GraphQL recipes

All commands assume `gh auth status` succeeds. `<n>` is the PR number, `<owner/repo>` the
repository slug. Inside a checked-out repo `gh` infers the slug; pass `-R <owner/repo>` when
it does not.

**Rule: one API call per job.** The bundled scripts each make exactly one request. Prefer
them over the multi-command REST sequences below.

## Cost table

| Job | Do this (1 call) | Not this |
| --- | --- | --- |
| Review context | `scripts/pr_context.sh <owner/repo> <n>` | `gh pr view` + `gh pr checks` + `gh pr view --json files` |
| Read threads | `scripts/fetch_threads.sh <owner/repo> <n>` | `gh api .../comments --paginate` then a REST call per thread |
| Reply + resolve | `scripts/reply_thread.sh <id> "..." --resolve` | reply call, then a separate resolve call |
| Close N threads | `scripts/resolve_thread.sh <id1> <id2> <id3>` | a `for` loop calling resolve N times |
| Full file context | `gh pr checkout <n>` once, then read locally | one API content fetch per file |

## Reading a PR

`scripts/pr_context.sh` returns, from one GraphQL request:

- title, state, draft flag, author, base/head refs, churn totals
- description with HTML comments stripped and fenced code elided, clipped at 1200 chars
- every changed file with per-file `+adds/-dels`
- CI rollup plus **only the non-passing** contexts
- existing review verdicts
- unresolved threads with their `threadId`

Then fetch the diff once and reuse the file:

```bash
gh pr diff <n> > /tmp/pr-<n>.diff     # reuse this; do not re-request per file
gh pr checkout <n>                    # once, when several files need full context
```

Parse a pasted URL: `https://github.com/<owner>/<repo>/pull/<n>`.

If you need the untruncated description: `gh pr view <n> --json body --jq .body`.

## Narrow REST reads

Only when `pr_context.sh` does not cover the need. Always pass `--jq` so raw JSON never
lands in context.

```bash
gh pr view <n> --comments                                    # issue-level conversation
gh api repos/<owner/repo>/pulls/<n>/comments --paginate \
  --jq '.[] | "\(.path):\(.line) \(.user.login): \(.body)"'   # inline comments, flattened
gh pr view <n> --json commits --jq '.commits[].messageHeadline'
```

Resolution state exists only in GraphQL; REST cannot tell you if a thread is resolved.

## Posting a review

```bash
gh pr review <n> --comment         --body-file /tmp/review.md
gh pr review <n> --request-changes --body-file /tmp/review.md
gh pr review <n> --approve         --body "LGTM"
```

Default to `--comment`. Never `--approve` unless the user asked.

### Inline comments: batch them into one review

Submit every inline comment with the summary in a single call. Do not post them one by one.

```bash
gh api repos/<owner/repo>/pulls/<n>/reviews \
  -f event=COMMENT \
  -f body="Summary" \
  -f 'comments[][path]=src/app.ts' \
  -F 'comments[][line]=120' \
  -f 'comments[][side]=RIGHT' \
  -f 'comments[][body]=blocker: this dereferences a possibly-null value.' \
  -f 'comments[][path]=src/db.ts' \
  -F 'comments[][line]=44' \
  -f 'comments[][body]=issue: query inside a loop, N+1.'
```

Use `start_line` with `line` for a multi-line range. `side=LEFT` targets the pre-change
version. The line must exist in the diff or the API rejects the whole review.

For many comments, build the payload as JSON and send it once:

```bash
gh api repos/<owner/repo>/pulls/<n>/reviews --input /tmp/review.json
```

## Threads: reply and resolve

```bash
bash scripts/fetch_threads.sh <owner/repo> <n>                 # unresolved, TAB-separated
bash scripts/fetch_threads.sh <owner/repo> <n> --all --full    # everything, unclipped
bash scripts/reply_thread.sh <threadId> "Fixed in abc1234 — added the null guard." --resolve
bash scripts/resolve_thread.sh <id1> <id2> <id3>               # one batched mutation
bash scripts/resolve_thread.sh <threadId> --undo
```

`resolve_thread.sh` also reads IDs from stdin, so it chains directly:

```bash
bash scripts/fetch_threads.sh <owner/repo> <n> | cut -f1 | bash scripts/resolve_thread.sh
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
| `FORBIDDEN` on resolve | No write access to the repo | Reply only; leave resolution to a maintainer |
| Batched mutation partly null | Some IDs invalid | Check the `errors[].path` alias (`t0`, `t1`) to see which |
