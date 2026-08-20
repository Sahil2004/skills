#!/usr/bin/env bash
# One GraphQL round-trip for everything needed to review a PR:
# metadata, files with churn, CI status, existing review verdicts, unresolved threads.
# Output is compact text, not raw JSON.
# Requires: gh (authenticated). Usage: pr_context.sh <owner/repo> <pr-number>
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "usage: pr_context.sh <owner/repo> <pr-number>" >&2
  exit 1
fi

OWNER="${1%%/*}"
NAME="${1##*/}"
PR="$2"

gh api graphql -f query='
query($owner:String!, $name:String!, $pr:Int!) {
  repository(owner:$owner, name:$name) {
    pullRequest(number:$pr) {
      title state isDraft additions deletions changedFiles
      author { login }
      baseRefName headRefName body
      files(first:100) { nodes { path additions deletions } }
      reviews(last:20) { nodes { author { login } state } }
      commits(last:1) { nodes { commit { statusCheckRollup {
        state contexts(first:100) { nodes {
          ... on CheckRun { name conclusion }
          ... on StatusContext { context state }
        } } } } } }
      reviewThreads(first:100) { nodes {
        id isResolved isOutdated path line
        comments(first:1) { nodes { author { login } body } }
      } }
    }
  }
}' -F owner="$OWNER" -F name="$NAME" -F pr="$PR" --jq '
.data.repository.pullRequest as $p |
"# \($p.title)  [\($p.state)\(if $p.isDraft then " DRAFT" else "" end)] by \($p.author.login)",
"\($p.headRefName) -> \($p.baseRefName) | \($p.changedFiles) files +\($p.additions)/-\($p.deletions)",
"",
"## Description",
(($p.body // "")
 | gsub("(?s)<!--.*?-->"; "")
 | gsub("\r"; "")
 | gsub("(?s)```.*?```"; "[code block elided]")
 | gsub("\n{3,}"; "\n\n")
 | ltrimstr("\n") | rtrimstr("\n")
 | if . == "" then "(none)"
   elif (. | length) > 1200 then .[0:1200] + "\n[... description truncated, run: gh pr view <n> --json body]"
   else . end),
"",
"## Files",
($p.files.nodes[] | "\(.path) +\(.additions)/-\(.deletions)"),
"",
"## Checks",
(($p.commits.nodes[0].commit.statusCheckRollup // null) |
  if . == null then "(none)"
  else "rollup: \(.state)",
       ((.contexts.nodes
         | map(select((.conclusion // .state) as $s
               | $s != null and ([$s] | inside(["FAILURE","ERROR","TIMED_OUT","CANCELLED","ACTION_REQUIRED","STARTUP_FAILURE"])))))
        as $bad
        | (.contexts.nodes
           | map(select((.conclusion // .state) as $s
                 | $s != null and ([$s] | inside(["PENDING","IN_PROGRESS","QUEUED","WAITING","REQUESTED"])))))
          as $pending
        | if ($bad | length) == 0 then "  (no failing contexts)"
          else ($bad[] | "  FAIL \(.name // .context): \(.conclusion // .state)") end,
          (if ($pending | length) == 0 then empty
           else ($pending[] | "  PENDING \(.name // .context): \(.conclusion // .state)") end))
  end),
"",
"## Reviews",
(if ($p.reviews.nodes | length) == 0 then "(none)"
 else ($p.reviews.nodes[] | "\(.author.login): \(.state)") end),
"",
"## Unresolved threads",
(($p.reviewThreads.nodes | map(select(.isResolved | not))) as $t |
 if ($t | length) == 0 then "(none)"
 else ($t[] | "\(.id)\t\(.path):\(.line // 0)\(if .isOutdated then " [outdated]" else "" end)\t\(.comments.nodes[0].author.login): \(.comments.nodes[0].body | gsub("\\s+"; " ") | .[0:300])")
 end)'
