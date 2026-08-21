# Outcome C: CI is failing

**Condition:** any context in `## Checks` is listed `FAIL`. This overrides every other
outcome, including a diff you have already read.

Request changes on the CI alone and stop. Do not review the code.

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
