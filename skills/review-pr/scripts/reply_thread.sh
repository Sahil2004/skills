#!/usr/bin/env bash
# Reply to a PR review thread. Usage: reply_thread.sh <threadId> "<body>"
set -euo pipefail

if [ $# -lt 2 ]; then
  echo 'usage: reply_thread.sh <threadId> "<body>"' >&2
  exit 1
fi

gh api graphql -f query='
mutation($threadId:ID!, $body:String!) {
  addPullRequestReviewThreadReply(input:{pullRequestReviewThreadId:$threadId, body:$body}) {
    comment { url }
  }
}' -F threadId="$1" -F body="$2" --jq '.data.addPullRequestReviewThreadReply.comment.url'
