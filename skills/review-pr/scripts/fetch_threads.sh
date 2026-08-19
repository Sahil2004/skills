#!/usr/bin/env bash
# List review threads on a PR with resolution state.
# Unresolved only by default; pass --all to include resolved threads.
# Requires: gh (authenticated). Usage: fetch_threads.sh <owner/repo> <pr-number> [--all]
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "usage: fetch_threads.sh <owner/repo> <pr-number> [--all]" >&2
  exit 1
fi

REPO="$1"
PR="$2"
SHOW_ALL="${3:-}"
OWNER="${REPO%%/*}"
NAME="${REPO##*/}"

if [ "$SHOW_ALL" = "--all" ]; then
  FILTER='true'
else
  FILTER='.isResolved | not'
fi

gh api graphql -f query='
query($owner:String!, $name:String!, $pr:Int!) {
  repository(owner:$owner, name:$name) {
    pullRequest(number:$pr) {
      reviewThreads(first:100) {
        nodes {
          id
          isResolved
          isOutdated
          path
          line
          comments(first:20) { nodes { author { login } body } }
        }
      }
    }
  }
}' -F owner="$OWNER" -F name="$NAME" -F pr="$PR" \
  --jq ".data.repository.pullRequest.reviewThreads.nodes[]
        | select($FILTER)
        | {threadId: .id, resolved: .isResolved, outdated: .isOutdated, path, line,
           comments: [.comments.nodes[] | {author: .author.login, body}]}"
