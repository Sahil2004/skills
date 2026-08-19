# gh and GraphQL recipes: review threads

All commands assume `gh auth status` succeeds. `<n>` is the PR number, `<owner/repo>` the
repository slug. Inside a checked-out repo `gh` infers the slug; pass `-R <owner/repo>` when
it does not.

**Rule: one API call per job.** The bundled scripts each make exactly one request.

## Cost table

| Job | Do this (1 call) | Not this |
| --- | --- | --- |
| Read threads | `scripts/fetch_threads.sh <owner/repo> <n>` | `gh api .../comments --paginate` then a call per thread |
| Reply + resolve | `scripts/reply_thread.sh <id> "..." --resolve` | reply call, then a separate resolve call |
| Close N threads | `scripts/resolve_thread.sh <id1> <id2> <id3>` | a `for` loop calling resolve N times |

## Reading threads

```bash
bash scripts/fetch_threads.sh <owner/repo> <n>                 # unresolved, TAB-separated
bash scripts/fetch_threads.sh <owner/repo> <n> --all           # include resolved
bash scripts/fetch_threads.sh <owner/repo> <n> --all --full    # unclipped bodies
```

Output columns: `<threadId>\t<path>:<line>[ flags]\t<author>: <body>`. Flags are
`[outdated]` when the code moved under the comment, `[resolved]` under `--all`.

An `[outdated]` thread points at a line that no longer exists; read the surrounding code
before assuming the comment is stale, then say so explicitly in the reply.

Resolution state exists only in GraphQL; REST cannot tell you whether a thread is resolved.

```bash
gh pr view <n> --comments      # issue-level conversation, not inline threads
```

## Replying and resolving

```bash
bash scripts/reply_thread.sh <threadId> "Fixed in abc1234 - added the null guard."
bash scripts/reply_thread.sh <threadId> "Fixed in abc1234 — added the null guard." --resolve
bash scripts/resolve_thread.sh <id1> <id2> <id3>
bash scripts/resolve_thread.sh <threadId> --undo
```

`resolve_thread.sh` also reads IDs from stdin, so it chains directly:

```bash
bash scripts/fetch_threads.sh <owner/repo> <n> | cut -f1 | bash scripts/resolve_thread.sh
```

Only pipe every ID like that when you have genuinely addressed every thread.

`threadId` is an opaque node ID (`PRRT_...`), not the numeric comment id.

## Pushing fixes

```bash
git add -A && git commit -m "Guard against a null session in the auth middleware" && git push
```

Never force-push a shared branch unless the user asks explicitly. Get the pushed SHA to
quote in replies:

```bash
git rev-parse --short HEAD
```

## Failure modes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `gh: Not Found` | Wrong slug or no access | Pass `-R <owner/repo>`, check `gh auth status` |
| `Resource not accessible` | Token lacks scope | `gh auth refresh -s repo` |
| Thread reply 404 | Numeric id used as `threadId` | Re-fetch node IDs via `fetch_threads.sh` |
| `FORBIDDEN` on resolve | No write access to the repo | Reply only; leave resolution to a maintainer |
| Batched mutation partly null | Some IDs invalid | Check the `errors[].path` alias (`t0`, `t1`) to see which |
| Reply lands on the wrong code | Thread is `[outdated]` | Re-read the current file before replying |
