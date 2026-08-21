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
| Full file context | `gh pr checkout <n>` once, then read locally | one API content fetch per file |

## Reading a PR

`scripts/pr_context.sh` returns, from one GraphQL request:

- title, state, draft flag, author, base/head refs, churn totals
- description with HTML comments stripped and fenced code elided, clipped at 1200 chars
- every changed file with per-file `+adds/-dels`
- CI rollup plus **only the non-passing** contexts
- existing review verdicts
- unresolved threads with their `threadId`, and resolved threads (capped at 25) so a
  finding that was resolved without a fix can be re-raised

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

Resolution state exists only in GraphQL; `pr_context.sh` already reports both the
unresolved and the resolved threads, so read them from its output rather than making a
second request. See `existing-threads.md` for which findings to suppress.

## Posting a review

```bash
gh pr review <n> --approve                                    # clean verdict only
gh api repos/<owner/repo>/pulls/<n>/reviews --input review.json   # findings
```

Check CI first. If `## Checks` lists any `FAIL`, the whole review is a short
`--request-changes` naming those contexts, with no counts line and no `comments` array:

```bash
gh pr review <n> --request-changes --body "CI is failing. Please get the checks green, then I will review.

- lint: FAILURE"
```

`PENDING` contexts are still running and never trigger this.

A clean verdict is a bare `--approve` with no `--body` and no inline comments. Any finding
at all, down to a single nitpick, is `REQUEST_CHANGES` submitted as one JSON payload.

Approving signals sign-off to the author and can unblock a merge, so never approve a PR
with an unverified category.

### The single batched payload

Build the whole review as JSON and submit it once. Never post comments one at a time.

```json
{
  "event": "REQUEST_CHANGES",
  "body": "Blockers: 1, Suggestions: 1, Nitpicks: 0\n\n- The PR description does not explain the behavior change.",
  "comments": [
    {
      "path": "pkg/auth/check.go",
      "line": 20,
      "side": "RIGHT",
      "body": "**[Blocker] `user` may be nil on the logged-out path.**\n\n- **What:** When nobody is signed in, `user` is empty, and the next line asks that empty value for its name.\n- **Why:** Asking an empty value for a field crashes the request instead of returning a handled error.\n- **Impact:** Every logged-out visitor to this endpoint gets a 500 instead of a sign-in prompt.\n- **Repro:** Call `GET /api/profile` with no session cookie.\n- **Fix:** Return `ErrUnauthenticated` before touching `user`.\n\n```suggestion\n\tif user == nil {\n\t\treturn ErrUnauthenticated\n\t}\n```"
    },
    {
      "path": "pkg/auth/check.go",
      "subject_type": "file",
      "body": "**[Suggestion] No test covers the new branch in this file.**\n\n- **What:** The new logged-out branch in this file is never exercised by a test.\n- **Why:** Untested branches regress silently, and this one guards an auth path.\n- **Impact:** A later refactor can reintroduce the crash with a green build.\n- **Repro:** Run `go test ./pkg/auth -run TestCheck -cover` and see the branch uncovered.\n- **Fix:** Add a case to `TestCheck` covering a nil user."
    }
  ]
}
```

```bash
gh api repos/<owner/repo>/pulls/<n>/reviews --input /tmp/review-<n>.json
```

Generate the file with a script or heredoc rather than by hand; the bodies contain
newlines and backticks that must be JSON-escaped.

### The three placement tiers

| Scope | Fields | Notes |
| --- | --- | --- |
| Specific line | `path`, `line`, `side` | `side=RIGHT` for additions/context, `LEFT` for deletions |
| Line range | `path`, `start_line`, `start_side`, `line`, `side` | `start_line` is the first line of the range |
| Whole file | `path`, `subject_type: "file"` | Omit `line` entirely |
| General | none — goes in `body` | No `comments` entry at all |

`subject_type: "file"` attaches the comment to the file rather than a line, which is the
correct tier for "this file lacks tests" or "this whole module duplicates X".

A line-anchored comment must land on a line present in the diff, or the API rejects the
entire review with `422`.

### Committable suggestion blocks

A fenced ` ```suggestion ` block renders with an "Apply suggestion" button. The block
replaces exactly the commented line range:

````
**[Blocker] This dereferences a possibly-nil value.**

```suggestion
    if user == nil {
        return ErrUnauthenticated
    }
```
````

- Cover the full range you are rewriting with `start_line`/`line`, or the applied commit
  will be wrong.
- Reproduce the surrounding indentation exactly; the text is inserted verbatim.
- Never include a placeholder or `...`; it would be committed literally.
- In JSON, the block needs escaped newlines and literal backticks, as shown above.

### Other events

```bash
gh pr review <n> --comment --body-file /tmp/notes.md    # feedback without a verdict
```

Use `--comment` only when the user explicitly wants non-blocking notes instead of a
verdict.

## Failure modes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `gh: Not Found` | Wrong slug or no access | Pass `-R <owner/repo>`, check `gh auth status` |
| Inline comment rejected | Line not part of the diff | Comment on a diff line, or use the summary body |
| `Resource not accessible` | Token lacks scope | `gh auth refresh -s repo` |
| `FORBIDDEN` posting a review | No write access to the repo | Report findings to the user instead |
| Review rejected wholesale | One inline comment had a bad line | Drop that comment, resubmit the batch |
| `422` on a file comment | `line` sent alongside `subject_type: file` | Omit `line` for file-level comments |
| Suggestion applies wrongly | Range did not cover every rewritten line | Widen `start_line`/`line` to the full range |
