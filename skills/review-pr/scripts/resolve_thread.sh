#!/usr/bin/env bash
# Resolve (or with --undo, unresolve) a PR review thread.
# Usage: resolve_thread.sh <threadId> [--undo]
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: resolve_thread.sh <threadId> [--undo]" >&2
  exit 1
fi

if [ "${2:-}" = "--undo" ]; then
  gh api graphql -f query='
  mutation($threadId:ID!) {
    unresolveReviewThread(input:{threadId:$threadId}) { thread { isResolved } }
  }' -F threadId="$1" --jq '.data.unresolveReviewThread.thread.isResolved'
else
  gh api graphql -f query='
  mutation($threadId:ID!) {
    resolveReviewThread(input:{threadId:$threadId}) { thread { isResolved } }
  }' -F threadId="$1" --jq '.data.resolveReviewThread.thread.isResolved'
fi
