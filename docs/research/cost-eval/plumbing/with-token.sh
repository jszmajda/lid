#!/bin/bash
# Runs a command with CLAUDE_CODE_OAUTH_TOKEN set from the maintainer's secrets file, without printing it.
# The token is a subscription OAuth token from `claude setup-token`. Pass it to docker with `-e CLAUDE_CODE_OAUTH_TOKEN` (no value).
export CLAUDE_CODE_OAUTH_TOKEN=$(/Users/jess/.local/share/uv/python/cpython-3.12-macos-aarch64-none/bin/python3.12 -I -c 'import tomllib,os; print(tomllib.load(open(os.path.expanduser("~/.config/stonks/secrets.toml"),"rb"))["secrets"]["anthropic_auth"])')
exec "$@"
