#!/usr/bin/env bash
# Resolve one or more PR review threads in a single API call.
# Usage: resolve_thread.sh <threadId> [threadId...] [--undo]
# Reads thread IDs from stdin when none are given (e.g. cut -f1 from fetch_threads.sh).
set -euo pipefail

MUTATION="resolveReviewThread"
IDS=()
for arg in "$@"; do
  case "$arg" in
    --undo) MUTATION="unresolveReviewThread" ;;
    *) IDS+=("$arg") ;;
  esac
done

if [ ${#IDS[@]} -eq 0 ] && [ ! -t 0 ]; then
  while read -r line; do
    [ -n "$line" ] && IDS+=("${line%%$'\t'*}")
  done
fi

if [ ${#IDS[@]} -eq 0 ]; then
  echo "usage: resolve_thread.sh <threadId> [threadId...] [--undo]" >&2
  exit 1
fi

QUERY="mutation {"
i=0
for id in "${IDS[@]}"; do
  QUERY+=" t$i: $MUTATION(input:{threadId:\"$id\"}) { thread { id isResolved } }"
  i=$((i + 1))
done
QUERY+=" }"

gh api graphql -f query="$QUERY" --jq '.data | to_entries[] | "\(.value.thread.id)\tresolved=\(.value.thread.isResolved)"'
