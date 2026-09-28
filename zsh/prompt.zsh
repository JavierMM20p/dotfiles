# ============================================================
# PROMPT
#
# One line: user, directory, git branch, virtualenv, cursor.
#
#   javier ~/work/api main* (.venv) ❯
#
# Built on zsh's own vcs_info, so it needs no framework or
# plugin. Sourced from .zshrc.
# ============================================================

autoload -Uz vcs_info add-zsh-hook colors
colors

setopt PROMPT_SUBST

zstyle ':vcs_info:*' enable git

# Comparing the work tree against the index on every prompt is what
# makes the dirty marker possible; it is also the slow part in a very
# large repo. Set this to false there if the prompt starts to lag.
zstyle ':vcs_info:git:*' check-for-changes true

zstyle ':vcs_info:git:*' unstagedstr '%F{yellow}*%f'
zstyle ':vcs_info:git:*' stagedstr   '%F{yellow}+%f'
zstyle ':vcs_info:git:*' formats       ' %F{magenta}%b%f%u%c'
zstyle ':vcs_info:git:*' actionformats ' %F{magenta}%b%f %F{red}(%a)%f'

# check-for-changes only looks at tracked files, so a repo holding
# nothing but new files would otherwise read as clean.
zstyle ':vcs_info:git*+set-message:*' hooks git-untracked
+vi-git-untracked() {
    [[ -n ${hook_com[unstaged]} ]] && return
    command git ls-files --others --exclude-standard --directory \
        --no-empty-directory 2>/dev/null | read -r && \
        hook_com[unstaged]='%F{yellow}*%f'
}

# Stop `activate` from prepending its own name; this prompt shows it.
export VIRTUAL_ENV_DISABLE_PROMPT=1

_prompt_precmd() {
    vcs_info
    if [[ -n $VIRTUAL_ENV ]]; then
        _prompt_venv=" %F{green}(${VIRTUAL_ENV:t})%f"
    else
        _prompt_venv=""
    fi
}
add-zsh-hook precmd _prompt_precmd

PROMPT='%F{cyan}%n%f %F{blue}%B%~%b%f${vcs_info_msg_0_}${_prompt_venv} %(?.%F{yellow}.%F{red})❯%f '
