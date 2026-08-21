# Findings that someone already raised

Read this at step 3, before auditing the diff, and again when deciding what to post.
`pr_context.sh` already returned every thread under `## Unresolved threads`, one per line:

```
PRRT_kwDO...	pkg/auth/check.go:20	octocat: [Blocker] `user` may be nil on the logged-out path...
```

Each line is `threadId`, `path:line`, the first comment's author, and the opening of that
comment. Threads marked `[outdated]` point at a line the author has since rewritten.

A second section, `## Resolved threads`, lists the same fields for threads someone marked
resolved, capped at 25 with a `[... N more]` note when a PR has more. Both sections come
from the same request; do not fetch the threads again.

`line` is `0` when GitHub no longer maps the thread to a line, which is normal for an
outdated thread. Use the path and the quoted text to locate it.

## The rule

**Unresolved thread + same underlying problem = do not post it.** The author can already
see that feedback in the Files tab. Posting a second copy splits the conversation, so a
reply on one thread does not answer the other, and it inflates your counts with feedback
that is not yours.

**Resolved thread is not a fixed problem.** Anyone with write access can resolve a thread,
including the author, and resolving changes no code. If a thread was resolved but the
problem is still in the diff in front of you, raise it as a fresh finding. Say in the
comment that it was raised before and resolved without a fix, so the author sees it is a
repeat rather than a new opinion:

```
**[Blocker] `user` may still be nil on the logged-out path.**

- **What:** ... (the normal five bullets)
...
- **Fix:** Return `ErrUnauthenticated` before touching `user`. This was raised in an
  earlier thread that was resolved, but the code is unchanged.
```

## Matching a finding to a thread

Match on the underlying problem, not on wording. The same defect described in different
words is still the same finding.

| Situation | Do |
| --- | --- |
| Unresolved thread, same problem, same place | Suppress. Post nothing. |
| Unresolved thread, same problem, code moved to another line | Suppress. It is the same defect. |
| Unresolved `[outdated]` thread, and the rewrite fixed it | Suppress. Nothing to say. |
| Unresolved `[outdated]` thread, and the rewrite did **not** fix it | Post it. The old thread is anchored to code that no longer exists, so it is effectively invisible. |
| Unresolved thread on the same line, **different** problem | Post it. Proximity is not duplication. |
| Unresolved thread, and you have material to add (a repro, a worse consequence, a concrete fix they did not give) | Post it, and open by naming what is new. Do not restate their point. |
| Resolved thread, problem still present | Post it, noting it was resolved without a fix. |
| Resolved thread, problem actually fixed | Nothing to post. |

When you cannot tell whether two findings are the same, treat them as the same and
suppress. A missed duplicate costs the author more than a missed nitpick.

## Effect on the verdict

Suppressed findings are **not** yours, so they do not count.

- They are excluded from the `Blockers: X, Suggestions: Y, Nitpicks: Z` line, which must
  equal the comments you actually post.
- They do not by themselves make the PR Outcome B. If every finding you had was already
  raised in an open thread, you have found nothing new.
- But an unresolved blocker from another reviewer still means the PR is not correct, so
  it is not Outcome A either. Do not approve on top of someone else's open blocker.
  Post no review; tell the human in chat that the open threads already cover it and name
  them.

Say which findings you suppressed in your chat report, so the human knows the short
review is deduplication and not a shallow pass:

```
Suppressed 2 findings already open: octocat on check.go:20 (nil user), the missing-test
thread on parser.go. Posted 1 new blocker.
```
