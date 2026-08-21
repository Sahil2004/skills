# Writing review comments

Loaded when posting findings under Outcome B. `outcome-request-changes.md` covers the
verdict and the review body; this file covers the shape of each individual comment.

## Placement

| Scope of the finding              | Where it goes         | How                                 |
| --------------------------------- | --------------------- | ----------------------------------- |
| Specific line(s) of code          | Inline on those lines | `line` (+ `start_line` for a range) |
| A file as a whole                 | On the file           | `subject_type: file`, no `line`     |
| Neither: general or cross-cutting | The main review body  | Bullet in the body                  |


Choose the narrowest tier that is truthful. Do not push a line-specific finding up into
the summary, and do not attach a general concern to an arbitrary line just to anchor it.

## Comment structure


Every comment placed on a line or a file opens with a bold heading naming the severity
in square braces, followed by a one-line statement of the issue, then the same five bold
bullets in this order:

```
**[Blocker] `user` may be nil on the logged-out path.**

- **What:** When nobody is signed in, `user` is empty here, and the next line asks that
  empty value for its name.
- **Why:** Asking an empty value for a field crashes the request instead of returning an
  error the caller can handle.
- **Impact:** Every logged-out visitor to this endpoint gets a 500, and the handler never
  reaches the error path that would have told them to sign in.
- **Repro:** Call `GET /api/profile` with no session cookie, or run `go test ./pkg/auth`
  after adding a case with a nil user.
- **Fix:** Return `ErrUnauthenticated` before touching `user`.
```

The heading is the whole finding in one line, so a reader skimming the Files tab knows
the severity and the problem without expanding anything. Braced label exactly as
`[Blocker]`, `[Suggestion]`, or `[Nitpick]`, and the entire heading line is bold.

Write all five for a reader who does not know this codebase:

- **What** — the problem in plain words. Name the condition that triggers it. No jargon,
  no internal shorthand, no "this violates X" without saying what X means here.
- **Why** — why it must be resolved, not merely that it is wrong. The rule or reason
  behind it, in one sentence.
- **Impact** — the concrete consequence if it ships: who hits it, what they see, what
  breaks. For a nitpick this is honestly small; say so rather than inflating it.
- **Repro** — how to see it for yourself: the exact request, command, input, or state
  that triggers it, and what you observe. Prefer something the author can run.
- **Fix** — the specific change to make. Name the function, value, or line to change.
  Pair it with a `suggestion` block whenever the fix is small enough to commit directly.

Keep each bullet to a sentence or two. If a bullet would be empty or a restatement of
another, the finding is probably not real; drop it rather than padding the shape.

Some findings cannot be run, notably style and readability nitpicks. Never invent a
repro for them. Say where it is visible instead, such as **Repro:** Read the block as a
newcomer, or **Repro:** Not runnable, visible on inspection only. A blocker that you
cannot describe how to reach deserves a second look; if nothing triggers it, it may not
be a blocker.

## Committable suggestions


When a fix is small and you can express it as the literal replacement text, use a
`suggestion` block. GitHub renders it with an "Apply suggestion" button the author can
commit in one click.

```
**[Blocker] `user` may be nil on the logged-out path.**

- **What:** When nobody is signed in, `user` is empty, and the next line asks that empty
  value for its name.
- **Why:** Asking an empty value for a field crashes the request instead of returning a
  handled error.
- **Impact:** Every logged-out visitor to this endpoint gets a 500 instead of a sign-in
  prompt.
- **Repro:** Call `GET /api/profile` with no session cookie.
- **Fix:** Return `ErrUnauthenticated` before touching `user`.

```suggestion
    if user == nil {
        return ErrUnauthenticated
    }
    return user.Name
```
```

Rules for suggestion blocks:

- The block replaces **exactly** the commented line range, so the range must cover every
  line you are rewriting and the replacement must be complete, compiling code.
- Match the surrounding indentation exactly; the block is inserted verbatim.
- Use one only when the fix is small and unambiguous. A refactor spanning several
  functions is described in prose, not forced into a suggestion.
- Never put a placeholder or `...` inside a suggestion block. It would be committed as-is.

## Rules for every placed comment

- The heading names the severity in braces and states the issue in one line; the five
  bullets follow in order: **What**, **Why**, **Impact**, **Repro**, **Fix**.
- Write for someone unfamiliar with the codebase. Plain language, no unexplained jargon.
- Every finding proposes a concrete fix. "This feels wrong" is not a review comment.
- Keep severity honest in both directions: do not soften a blocker into a nitpick, and do
  not inflate a nitpick to pad the counts.
- When the only findings are open questions, request changes but phrase them as questions
  on the relevant lines rather than implying the code is wrong.
