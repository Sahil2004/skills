# Outcome A: the PR is correct

**Condition:** CI is green and there is nothing to change at all: no blockers, no
suggestions, no nitpicks.

Approve the PR and leave **no review comments on it at all**.

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
