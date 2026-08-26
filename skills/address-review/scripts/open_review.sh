#!/usr/bin/env bash
# Every open review comment on a PR, in one API call.
#
# Emits two TAB-separated sections:
#   REVIEW<TAB><author> (<state>)<TAB><review body>
#   THREAD<TAB><threadId>\t<path>:<line>[ flags]<TAB><author>: <body>
#
# Only reviews in a non-approving state are emitted (CHANGES_REQUESTED, COMMENTED,
# DISMISSED, PENDING); an APPROVED review carries no open ask. Threads are unresolved
# only unless --all is passed. A file-level comment has a null line and prints as
# <path>:0.
#
# Requires: gh (authenticated).
# Usage: open_review.sh <owner/repo> <pr-number> [--all] [--full]
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "usage: open_review.sh <owner/repo> <pr-number> [--all] [--full]" >&2
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
      reviews(first:50) { nodes { state body author { login } } }
      reviewThreads(first:100) { nodes {
        id isResolved isOutdated path line
        comments(first:10) { nodes { author { login } body } }
      } }
    }
  }
}' -F owner="$OWNER" -F name="$NAME" -F pr="$PR" --jq "
.data.repository.pullRequest as \$pr
| (
    \$pr.reviews.nodes[]
    | select(.state != \"APPROVED\")
    | select((.body // \"\") | gsub(\"\\\\s+\"; \"\") != \"\")
    | \"REVIEW\t\(.author.login) (\(.state))\t\(.body | gsub(\"\\\\s+\"; \" \") $CLIP)\"
  ),
  (
    \$pr.reviewThreads.nodes[]
    | select($FILTER)
    | .id as \$id | .path as \$path | .line as \$line
    | (if .isOutdated then \" [outdated]\" else \"\" end) as \$old
    | (if .isResolved then \" [resolved]\" else \"\" end) as \$res
    | .comments.nodes[]
    | \"THREAD\t\(\$id)\t\(\$path):\(\$line // 0)\(\$old)\(\$res)\t\(.author.login): \(.body | gsub(\"\\\\s+\"; \" \") $CLIP)\"
  )"
