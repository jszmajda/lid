SETTINGS='{"autoMemoryEnabled":false,"sandbox":{"enabled":true,"autoAllowBashIfSandboxed":true}}'
ARM=(--model sonnet --effort medium --setting-sources project,local --settings "$SETTINGS" --permission-mode acceptEdits --permission-prompts none --output-format stream-json --verbose)
LID=(--plugin-dir /Users/jess/src/lid/plugins/linked-intent-dev --add-dir /Users/jess/src/lid/plugins/linked-intent-dev)
