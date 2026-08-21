# Review checklist

Work top to bottom. Skip a category only when it genuinely does not apply, and say so.

## Correctness

- Does the code do what the PR description claims?
- Off-by-one, boundary, and empty-collection cases.
- Null / undefined / `None` paths, and optional values unwrapped without a check.
- Concurrency: shared mutable state, races, missing locks, `await` inside a loop that
  should be batched.
- Early returns that skip cleanup.

## Security

- User input reaching a query, shell, filesystem path, or template without validation.
- Secrets, tokens, or keys added to code, tests, fixtures, or logs.
- AuthZ checks present on every new endpoint or handler, not just authN.
- New dependencies: needed, maintained, and license-compatible?
- Deserialization of untrusted data.

## Error handling

- Swallowed exceptions (`catch {}`), or errors logged then ignored.
- Error messages that leak internals to end users.
- Failure paths that leave partial state written.
- Retries without backoff or without an idempotency guarantee.

## Tests

- Behavior change with no test change is a finding.
- Tests assert on behavior, not on implementation detail.
- At least one failure-path test, not only the happy path.
- No sleeps, no dependence on test ordering, no live network calls.

## API and compatibility

- Public signature, response shape, or config key changed without a version note.
- Database migration is reversible and safe on a live table.
- Feature flag or fallback for risky behavior changes.
- Removed fields still consumed elsewhere in the repo.

## Performance

- N+1 queries or a query inside a loop.
- Unbounded reads: no pagination, no limit, whole file into memory.
- New index needed for a new query pattern.
- Only flag performance when there is a plausible real workload; otherwise it is a nit.

## Readability and maintenance

- Names describe intent; comments explain why, not what.
- Dead code, commented-out blocks, stray debug output.
- Duplicated logic that already exists in the codebase.
- Function doing several unrelated things.

## Repo hygiene

- Follows the project's own conventions (`AGENTS.md`, `CONTRIBUTING.md`, lint config).
- No unrelated formatting churn inflating the diff.
- No vendor or AI attribution in commits, comments, or PR text.
- Generated or lock files updated consistently with the source change.
