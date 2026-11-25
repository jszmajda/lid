#!/bin/bash
# Runs a command with CLAUDE_CODE_OAUTH_TOKEN set, without printing the token.
# The token is a subscription OAuth token from `claude setup-token`. Pass it on to docker with `-e CLAUDE_CODE_OAUTH_TOKEN` (no value).
# Where the token comes from is machine-specific: set LID_EVAL_TOKEN_CMD to a shell command that prints it,
# or put that command in local/token-cmd beside this script (git ignores local/).
HERE=$(cd "$(dirname "$0")" && pwd)
CMD=${LID_EVAL_TOKEN_CMD:-$(cat "$HERE/local/token-cmd" 2>/dev/null)}
[ -n "$CMD" ] || { echo "No token command: set LID_EVAL_TOKEN_CMD or write $HERE/local/token-cmd" >&2; exit 2; }
export CLAUDE_CODE_OAUTH_TOKEN=$(sh -c "$CMD")
exec "$@"
