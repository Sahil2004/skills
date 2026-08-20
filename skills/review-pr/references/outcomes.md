# Outcomes in full

Exactly one outcome applies to a review. Load the one the verdict selected; the other two
are irrelevant to that review.

- **Outcome C** — any CI check failing. Overrides the others.
- **Outcome A** — CI green and nothing to change.
- **Outcome B** — CI green and any finding at all.

## Outcome C: CI is failing

This outrules every other outcome. If any check is failing, request changes on the CI
alone and stop. Do not review the code.

```bash
gh pr review <n> --request-changes --body "$(cat <<'EOF'
CI is failing. Please get the checks green, then I will review.

- lint: FAILURE
- e2e: TIMED_OUT
EOF
)"
```

Rules for this outcome:

- Be blunt and brief. Two lines plus the list of failing checks is the whole review.
- **No counts line.** `Blockers: ...` belongs only to a review that examined the code.
- **No inline comments**, no file comments, no checklist findings, no suggestions. The
  diff has not been reviewed, and saying otherwise would be false.
- Name the failing contexts exactly as `## Checks` reported them, so the author knows
  which job to open. Do not speculate about why they failed.
- Do not approve, and do not soften this into a comment-only review.
- `PENDING` is not failing. Never gate on a check that is merely still running.
- When the author pushes a fix and asks again, start over at step 1; the diff has moved.

Tell the human in chat that the review stopped at CI and no code review was performed.

## Outcome A: the PR is correct

Use only when CI is green and there is nothing to change at all: no blockers, no
suggestions, no nitpicks. Approve the PR and leave **no review comments on it at all**.

```bash
gh pr review <n> --approve
```

That is the entire GitHub-side action. Specifically:

- Post no summary body and no inline comments. A correct PR gets a clean approval and
  nothing else.
- If you found even one nitpick worth telling the author, this is not Outcome A. Use
  Outcome B and post it.
- Never manufacture a concern to look thorough, and never suppress a real one to reach a
  clean approval.

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

<Optional, chat only: anything worth knowing that was not worth a review comment.>
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

Use when there is **any** finding, including a lone nitpick. Request changes, and put each
finding at the narrowest scope that fits it.

### Severity vocabulary

- **Blocker** — correctness, security, data loss, breaking change. Must be fixed.
- **Suggestion** — should be fixed before merge, but not dangerous.
- **Nitpick** — style or taste. Non-blocking, author may decline.

### The main comment

The body is the counts, and nothing else unless a finding fits nowhere else:

```
Blockers: 2, Suggestions: 3, Nitpicks: 1

<Only findings that fit no line and no file: PR scope, missing tests overall,
architectural concerns, missing description. One bullet each. Omit this whole
block when every finding is placed inline or on a file.>
```

Include every category in the count line even when zero, as in
`Blockers: 0, Suggestions: 2, Nitpicks: 1`, so the author can see the shape of the
review at a glance.

The body is the last resort, not a summary. A finding appears there only because there is
no line and no file to attach it to. Never restate, preview, or summarize a finding that
is already posted inline or on a file, and do not add a lead-in describing the main risk.
When every finding has a home, the body is exactly one line: the counts.

### Writing each comment

Place every finding at the narrowest scope that is truthful: a line, else the file, else
the review body. Each placed comment opens with a bold braced heading and carries five
bullets:

```
**[Blocker] `user` may be nil on the logged-out path.**

- **What:** the problem, in plain words.
- **Why:** why it must be resolved.
- **Impact:** the consequence if it ships.
- **Repro:** how to see it happen.
- **Fix:** the specific change to make.
```

Read `references/writing-comments.md` before writing them. It has the placement table,
the full bullet briefs, and the rules for committable `suggestion` blocks.

### Posting it

Submit the whole review, body and all inline comments, in one call:

```bash
gh api repos/<owner/repo>/pulls/<n>/reviews --input /tmp/review-<n>.json
```

Build the payload with `event: REQUEST_CHANGES`, the count-led body, and one entry per
finding. See `references/gh-commands.md` for the full JSON shape, including the
`subject_type: file` form and suggestion-block escaping.

#
