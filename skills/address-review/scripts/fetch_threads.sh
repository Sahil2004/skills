#!/usr/bin/env bash
# Unresolved review threads as one TAB-separated line per thread:
#   <threadId>\t<path>:<line>\t<author>: <first comment>
# Pass --all for resolved too, --full for untruncated bodies.
# Requires: gh (authenticated). Usage: fetch_threads.sh <owner/repo> <pr-number> [--all] [--full]
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "usage: fetch_threads.sh <owner/repo> <pr-number> [--all] [--full]" >&2
  exit 1
fi

OWNER="${1%%/*}"
NAME="${1##*/}"
PR="$2"
shift 2

FILTER='.isResolved | not'
CLIP='| .[0:400]'
for arg in "$@"; do
  case "$arg" in
    --all) FILTER='true' ;;
    --full) CLIP='' ;;
    *) echo "unknown option: $arg" >&2; exit 1 ;;
  esac
done

gh api graphql -f query='
query($owner:String!, $name:String!, $pr:Int!) {
  repository(owner:$owner, name:$name) {
    pullRequest(number:$pr) {
      reviewThreads(first:100) { nodes {
        id isResolved isOutdated path line
        comments(first:10) { nodes { author { login } body } }
      } }
    }
  }
}' -F owner="$OWNER" -F name="$NAME" -F pr="$PR" --jq "
.data.repository.pullRequest.reviewThreads.nodes[]
| select($FILTER)
| .id as \$id | .path as \$path | .line as \$line
| (if .isOutdated then \" [outdated]\" else \"\" end) as \$old
| (if .isResolved then \" [resolved]\" else \"\" end) as \$res
| .comments.nodes[]
| \"\(\$id)\t\(\$path):\(\$line // 0)\(\$old)\(\$res)\t\(.author.login): \(.body | gsub(\"\\\\s+\"; \" \") $CLIP)\""
