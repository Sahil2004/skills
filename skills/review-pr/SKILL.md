---
name: review-pr
description: When the user wants to review someone's GitHub pull request, approve it, or leave feedback on it. Also use when the user mentions "review this PR", "code review", "look at this pull request", "what do you think of this PR", "approve this PR", "request changes", or pastes a GitHub pull request URL asking for an opinion.
version: 0.1.0
agents: [all]
tags: [github, code-review, workflow]
allowed-tools: [Bash, Read, Write, Edit]
---

# Review PR

Review a GitHub pull request, then either approve it cleanly or post structured,
severity-classified feedback. A correct PR is approved with no comments attached; a PR
with findings gets those findings and no approval.

## When to use

- "Review PR 412" / a pasted `https://github.com/<org>/<repo>/pull/<n>` URL.
- "Is this PR safe to merge?" (answering "yes, nothing blocking" is a valid outcome)
- "Look over these changes and tell me what's wrong."
- "Approve this PR if it's fine."

Do not use this when the user wants to **answer** review comments already left on their own
PR; this skill produces feedback, it does not reply to it. Also skip this when the change
is not on GitHub yet (review the working tree directly) or the user only wants a PR
description.

## Prerequisites

```bash
gh auth status    # must be logged in
```

If `gh` is missing or unauthenticated, stop and tell the user; do not guess at PR content.

**Command economy is a hard requirement.** Every script here batches into a single API
call. Never poll, never loop a command per file, and never dump raw JSON into context. See
`references/gh-commands.md` for the anti-patterns to avoid.

## Workflow

1. **Load the PR in one call.** Metadata, file churn, CI status, existing reviews, and
   open threads all come back from a single request:

   ```bash
   bash scripts/pr_context.sh <owner/repo> <n>
   ```

   Then fetch the diff once and reuse it:

   ```bash
   gh pr diff <n> > /tmp/pr-<n>.diff
   ```

   Do not also run `gh pr view`, `gh pr checks`, or a per-file loop. `pr_context.sh`
   already returned all of it.

2. **Understand intent before judging code.** Read the PR description and linked issue.
   State in one line what the PR claims to do. If the description does not explain the
   change, that is the first review comment.

3. **Read the diff in context, not in isolation.** For every non-trivial hunk, open the
   full file. Reviewing only diff lines produces false positives. When several files need
   full context, run `gh pr checkout <n>` once and read locally rather than making an API
   call per file.

4. **Check CI and tests.** The `## Checks` section from step 1 already lists only the
   genuinely failing contexts. Failing checks are blocking. A behavior change with no test
   change is a finding.

5. **Apply the checklist.** Work through `references/review-checklist.md`: correctness,
   security, error handling, tests, API/back-compat, performance, readability. Skip
   categories that genuinely do not apply.

6. **Classify every finding** with a severity prefix so the author can triage:
   - `blocker:` correctness, security, data loss, breaking change. Must be fixed.
   - `suggestion:` should be fixed before merge, but not dangerous.
   - `nitpick:` style or taste. Non-blocking, the author may decline.

   An open question counts as a blocker or a suggestion depending on what it gates: use
   `blocker:` when you cannot judge correctness without the answer.

7. **Read what other reviewers already said** (in the step 1 output) and do not repeat an
   existing open comment. Add signal, not volume.

8. **Decide the verdict**, which determines what happens next:

   | Findings after step 5-6 | Verdict | Action |
   | --- | --- | --- |
   | Nothing at all | **Clean** | Outcome A: approve, post no comments |
   | Any blocker, suggestion, or nitpick | **Needs work** | Outcome B: request changes |

   Any finding at all, down to a single nitpick, means Outcome B. Only a PR with nothing
   to change is approved.

9. **Place each finding at the narrowest scope that fits**, then act on the verdict.
   See "Comment placement" below for the three tiers and the exact API calls.

10. **Never merge or close a PR.** Approve only under a clean verdict (Outcome A);
    request changes under Outcome B.

## Outcome A: the PR is correct

Use only when there is nothing to change at all: no blockers, no suggestions, no
nitpicks. Approve the PR and leave **no review comments on it at all**.

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

Include every category in the count line even when zero (`Blockers: 0, Suggestions: 2,
Nitpicks: 1`), so the author can see the shape of the review at a glance.

The body is the last resort, not a summary. A finding appears there only because there is
no line and no file to attach it to. Never restate, preview, or summarize a finding that
is already posted inline or on a file, and do not add a lead-in describing the main risk.
When every finding has a home, the body is exactly one line: the counts.

### Comment placement

| Scope of the finding | Where it goes | How |
| --- | --- | --- |
| Specific line(s) of code | Inline on those lines | `line` (+ `start_line` for a range) |
| A file as a whole | On the file | `subject_type: file`, no `line` |
| Neither: general or cross-cutting | The main review body | Bullet in the body |

Choose the narrowest tier that is truthful. Do not push a line-specific finding up into
the summary, and do not attach a general concern to an arbitrary line just to anchor it.

### Committable suggestions

When a fix is small and you can express it as the literal replacement text, use a
`suggestion` block. GitHub renders it with an "Apply suggestion" button the author can
commit in one click.

````
blocker: `user` may be nil here, so this dereferences on the logged-out path.

```suggestion
    if user == nil {
        return ErrUnauthenticated
    }
    return user.Name
```
````

Rules for suggestion blocks:

- The block replaces **exactly** the commented line range, so the range must cover every
  line you are rewriting and the replacement must be complete, compiling code.
- Match the surrounding indentation exactly; the block is inserted verbatim.
- Use one only when the fix is small and unambiguous. A refactor spanning several
  functions is described in prose, not forced into a suggestion.
- Never put a placeholder or `...` inside a suggestion block. It would be committed as-is.

### Posting it

Submit the whole review, body and all inline comments, in one call:

```bash
gh api repos/<owner/repo>/pulls/<n>/reviews --input /tmp/review-<n>.json
```

Build the payload with `event: REQUEST_CHANGES`, the count-led body, and one entry per
finding. See `references/gh-commands.md` for the full JSON shape, including the
`subject_type: file` form and suggestion-block escaping.

### Rules for this shape

- Every inline finding starts with its severity word: `blocker:`, `suggestion:`, or
  `nitpick:`.
- Every finding proposes a concrete fix. "This feels wrong" is not a review comment.
- Keep severity honest in both directions: do not soften a blocker into a nitpick, and do
  not inflate a nitpick to pad the counts.
- The counts in the body must equal the findings actually posted.
- When the only findings are open questions, request changes but phrase them as questions
  on the relevant lines rather than implying the code is wrong.

## Rules

- One API call per job. Use `pr_context.sh`; never loop a command per file, and never
  re-fetch data it already returned.
- Approve only when there is nothing to change, and approve with no comments attached.
  Any finding, down to one nitpick, is a request for changes. Never merge or close a PR.
- Never approve to be agreeable. If any category is unverified or any doubt remains, that
  is Outcome B, not an approval.
- Put every finding at the narrowest true scope: line, then file, then the review body.
- Quote the specific line and give a concrete fix; no vague feedback.
- Offer a committable `suggestion` block whenever the fix is small and unambiguous.
- Be direct about severity. Do not soften a blocker into a nitpick, and do not inflate a
  nitpick into a blocker to justify a longer review.
- The counts in the review body must match the findings actually posted.
- A clean PR gets a clean review. Finding nothing is a valid, complete result; never
  invent findings to fill the template.
- Do not rewrite the PR author's style preferences as blockers.
- Judge the diff against the repo's existing conventions, not your own defaults.
- No vendor or AI attribution in review bodies.

## References

- `references/review-checklist.md` — the full per-category review checklist.
- `references/gh-commands.md` — batched `gh`/GraphQL recipes, the inline-comment API, and
  the costly anti-patterns to avoid.

## Scripts

| Script | Calls | Purpose |
| --- | --- | --- |
| `scripts/pr_context.sh` | 1 | Whole review context: meta, files, failing checks, reviews, threads |
