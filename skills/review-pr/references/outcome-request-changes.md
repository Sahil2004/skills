# Outcome B: the PR needs changes

**Condition:** CI is green and you have at least one finding, down to a single nitpick.

Read `writing-comments.md` alongside this file; it holds the placement tiers and the
five-bullet structure every posted comment must follow.

Request changes, and put each finding at the narrowest scope that fits it.

## Severity vocabulary

- **Blocker** — correctness, security, data loss, breaking change. Must be fixed.
- **Suggestion** — should be fixed before merge, but not dangerous.
- **Nitpick** — style or taste. Non-blocking, author may decline.

## The main comment

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

## Writing each comment

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

Read `writing-comments.md` before writing them. It has the placement table,
the full bullet briefs, and the rules for committable `suggestion` blocks.

## Findings someone already raised

Before building the payload, drop every finding that an unresolved thread already covers,
and re-raise anything whose thread was resolved without the code changing.
`existing-threads.md` has the matching table. Suppressed findings do not appear in the
counts, and if nothing survives, post no review and report the open threads in chat.

## Posting it

Submit the whole review, body and all inline comments, in one call:

```bash
gh api repos/<owner/repo>/pulls/<n>/reviews --input /tmp/review-<n>.json
```

Build the payload with `event: REQUEST_CHANGES`, the count-led body, and one entry per
finding. See `gh-commands.md` for the full JSON shape, including the
`subject_type: file` form and suggestion-block escaping.

