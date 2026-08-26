# Asking about a decision

A decision question goes to a human who may not have read the PR, may not know the
product, and is being interrupted. Write for that reader.

## Rules

- **One question per turn.** Ask, wait for the answer, then ask the next. Never send a
  numbered list of five decisions.
- **No jargon and no unexplained internal names.** If you must name a module, say what it
  does in the same sentence.
- **No assumed context.** Do not write "as discussed in the thread". Restate it.
- **Always recommend one option, with a reason.** A question with no recommendation pushes
  the whole judgement onto the reader.
- **Never ask what the codebase already answers.** Grep for the convention first. If a
  precedent exists, follow it and drop the row to `nil`.

## The four parts

1. **The problem** — what is undecided right now, in plain words.
2. **The context** — how the code behaves today, and why the reviewer raised it.
3. **The options** — every realistic choice, with what each one means in practice.
4. **The tradeoff** — what each costs, then your recommendation and why.

Close by naming what happens next: which option you will implement on their answer.

## Example

> **The problem**
> A reviewer wants a function renamed, and there is no house style saying what to call it.
> I need you to pick the name.
>
> **The context**
> When someone signs in, the code runs a small function that decides whether their login
> session is still valid. It is currently called `chk`, which does not say what it checks
> or what it gives back. The reviewer flagged it as unreadable. Elsewhere in this codebase
> both naming styles already exist, so there is no precedent to follow: some files use
> `validateSession` (a verb, "go do this"), others use `isSessionValid` (a question,
> "is this true").
>
> **The options**
> 1. `validateSession` — reads as a command. Matches the four files under `src/auth/`.
> 2. `isSessionValid` — reads as a yes/no question, which is what the function actually
>    returns. Matches the six files under `src/api/`.
> 3. Leave it as `chk` — no change, and the reviewer's comment stays open.
>
> **The tradeoff**
> Option 1 sits nearer this file, so a reader in this folder sees a consistent style.
> Option 2 describes the behavior more honestly, because the function answers true or
> false rather than performing an action; names that promise an action but return a
> boolean tend to get misused later. Option 3 costs nothing now but leaves an open thread
> and the same confusion for the next reader.
>
> I recommend option 2, `isSessionValid`, because the name should match what the function
> gives back, and the `src/api/` group is the larger of the two existing styles.
>
> Tell me which you want and I will rename it and reply to the thread.

## Handling the answer

- **Answered** — the row's `anyDecisions` becomes `nil`. If it is now fully clear, start
  it immediately, in its own worker where available, while you ask the next question.
  Pass the decision and the reasoning into the worker brief; the worker did not hear this
  conversation.
- **"Do it later" / "ignore for now"** — park the row. Do not resolve the thread. Record
  what it waits on for the step 10 write-up.
- **A counter-question** — answer it and re-ask. This still counts as one question in
  flight; do not move to the next decision until this one is settled or parked.
- **An option you did not list** — take it. Confirm your understanding in one line before
  dispatching, so a misread does not become a wrong edit.
