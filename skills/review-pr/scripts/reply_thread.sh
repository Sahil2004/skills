#!/usr/bin/env bash
# Reply to a PR review thread, optionally resolving it in the same API call.
# Usage: reply_thread.sh <threadId> "<body>" [--resolve]
set -euo pipefail

if [ $# -lt 2 ]; then
  echo 'usage: reply_thread.sh <threadId> "<body>" [--resolve]' >&2
  exit 1
fi

THREAD="$1"
BODY="$2"

if [ "${3:-}" = "--resolve" ]; then
  gh api graphql \
    -f query='mutation($threadId:ID!, $body:String!) {
      addPullRequestReviewThreadReply(input:{pullRequestReviewThreadId:$threadId, body:$body}) { comment { url } }
      resolveReviewThread(input:{threadId:$threadId}) { thread { isResolved } }
    }' -F threadId="$THREAD" -F body="$BODY" \
    --jq '"\(.data.addPullRequestReviewThreadReply.comment.url)\tresolved=\(.data.resolveReviewThread.thread.isResolved)"'
else
  gh api graphql \
    -f query='mutation($threadId:ID!, $body:String!) {
      addPullRequestReviewThreadReply(input:{pullRequestReviewThreadId:$threadId, body:$body}) { comment { url } }
    }' -F threadId="$THREAD" -F body="$BODY" \
    --jq '.data.addPullRequestReviewThreadReply.comment.url'
fi
