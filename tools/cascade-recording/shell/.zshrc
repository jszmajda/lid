# @spec CASCADE-REC-012, CASCADE-REC-013
# Startup for the shell a take records: a plain prompt, no history file, and
# a `claude` that runs Claude Code configured by the take.
unsetopt prompt_sp
setopt interactive_comments
unset HISTFILE
PROMPT='$ '
alias grep='grep --color=auto'

claude() {
  command claude --plugin-dir "$LID_PLUGIN" --setting-sources project \
    --model "$LID_MODEL" --effort "$LID_EFFORT" --permission-mode auto "$@"
}
