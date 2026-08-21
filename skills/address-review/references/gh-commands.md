# gh and GraphQL recipes: reviews and threads

All commands assume `gh auth status` succeeds. `<n>` is the PR number, `<owner/repo>` the
repository slug. Inside a checked-out repo `gh` infers the slug; pass `-R <owner/repo>` when
it does not.

**Rule: one API call per job.** The bundled scripts each make exactly one request.

## Cost table

| Job | Do this (1 call) | Not this |
| --- | --- | --- |
| Read the open review | `scripts/open_review.sh <owner/repo> <n>` | `gh pr view` plus `gh api .../comments --paginate` plus a call per thread |
| Reply + resolve | `scripts/reply_thread.sh <id> "..." --resolve` | reply call, then a separate resolve call |
| Close N threads | `scripts/resolve_thread.sh <id1> <id2> <id3>` | a `for` loop calling resolve N times |

## Reading the open review

```bash
bash scripts/open_review.sh <owner/repo> <n>                 # open review bodies + unresolved threads
bash scripts/open_review.sh <owner/repo> <n> --all           # include resolved threads
bash scripts/open_review.sh <owner/repo> <n> --all --full    # unclipped bodies
```

Two line types, both TAB-separated:

| Type | Columns |
| --- | --- |
| `REVIEW` | `REVIEW`, `<author> (<state>)`, `<review body>` |
| `THREAD` | `THREAD`, `<threadId>`, `<path>:<line>[ flags]`, `<author>: <body>` |

Split them without a second call:

```bash
bash scripts/open_review.sh <owner/repo> <n> > /tmp/review-<n>.tsv
grep '^REVIEW' /tmp/review-<n>.tsv
grep '^THREAD' /tmp/review-<n>.tsv | cut -f2      # bare thread IDs
```

Details that matter for triage:

- **Approved reviews are dropped.** `APPROVED` carries no open ask. States kept are
  `CHANGES_REQUESTED`, `COMMENTED`, `DISMISSED` and `PENDING`.
- **An empty review body is dropped** too: an approval-less review with only inline
  comments already appears as `THREAD` lines.
- **File-level comments** have no line and print as `<path>:0`. They apply to the whole
  file, not to line zero.
- **Flags**: `[outdated]` means the code moved under the comment, `[resolved]` appears
  only under `--all`. An `[outdated]` thread points at a line that no longer exists; read
  the surrounding code before assuming the comment is stale, then say so in the reply.
- Resolution state exists only in GraphQL; REST cannot tell you whether a thread is
  resolved.

The issue-level conversation (not inline, not part of a review) is separate:

```bash
gh pr view <n> --comments
```

## Finding a blocker's tracked issue

Search before claiming a blocker is untracked. Both are one call:

```bash
gh issue list --search "<keywords>" --state open --limit 5
gh pr list   --search "<keywords>" --state open --limit 5
```

Use the Jira or Linear tooling instead when that is the tracker the user is authenticated
for. If nothing is connected, report the blocker as untracked rather than inventing a
ticket reference.

## Replying and resolving

```bash
bash scripts/reply_thread.sh <threadId> "Fixed in abc1234 - added the null guard."
bash scripts/reply_thread.sh <threadId> "Fixed in abc1234 — added the null guard." --resolve
bash scripts/resolve_thread.sh <id1> <id2> <id3>
bash scripts/resolve_thread.sh <threadId> --undo
```

`resolve_thread.sh` also reads IDs from stdin, so it chains directly:

```bash
grep '^THREAD' /tmp/review-<n>.tsv | cut -f2 | sort -u | bash scripts/resolve_thread.sh
```

Only pipe every ID like that when you have genuinely addressed every thread. Never include
a parked row.

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

## Recording parked items on the PR

`--body-file` replaces the whole description, so read the current one, append, and write
back:

```bash
gh pr view <n> --json body --jq .body > /tmp/pr-<n>.md
# append the parked section, then:
gh pr edit <n> --body-file /tmp/pr-<n>.md
```

To leave the same note on a linked issue:

```bash
gh issue comment <issue> --body "<parked items and what each waits on>"
```

## Failure modes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `gh: Not Found` | Wrong slug or no access | Pass `-R <owner/repo>`, check `gh auth status` |
| `Resource not accessible` | Token lacks scope | `gh auth refresh -s repo` |
| Script prints nothing | No open review and no unresolved thread | Nothing to address; say so and stop |
| Thread reply 404 | Numeric id used as `threadId` | Re-fetch node IDs via `open_review.sh` |
| `FORBIDDEN` on resolve | No write access to the repo | Reply only; leave resolution to a maintainer |
| Batched mutation partly null | Some IDs invalid | Check the `errors[].path` alias (`t0`, `t1`) to see which |
| Reply lands on the wrong code | Thread is `[outdated]` | Re-read the current file before replying |
| PR description overwritten | `--body-file` used without reading the old body | Restore from the PR's edit history, then append instead |
