SETTINGS='{"autoMemoryEnabled":false,"sandbox":{"enabled":true,"autoAllowBashIfSandboxed":true}}'
ARM=(--model sonnet --effort medium --setting-sources project,local --settings "$SETTINGS" --permission-mode acceptEdits --permission-prompts none --output-format stream-json --verbose)
# LID_PLUGIN is the plugins/linked-intent-dev folder of a LID checkout at the version under test.
LID=(--plugin-dir "${LID_PLUGIN:?set LID_PLUGIN}" --add-dir "$LID_PLUGIN")
