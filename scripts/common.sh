#!/usr/bin/env bash
# Shared helpers: the module registry, plus locating machine-specific paths.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Every module this repo knows how to install or back up.
ALL_MODULES=(vscode zsh kitty fonts llms)

die() {
    echo "error: $*" >&2
    exit 1
}

is_module() {
    local candidate="$1"
    for m in "${ALL_MODULES[@]}"; do
        [ "$m" = "$candidate" ] && return 0
    done
    return 1
}

# --- VS Code CLI -------------------------------------------------------------
find_code_cli() {
    if [ -n "${CODE_CLI:-}" ]; then
        echo "$CODE_CLI"
        return 0
    fi
    for candidate in code code-insiders codium; do
        if command -v "$candidate" >/dev/null 2>&1; then
            echo "$candidate"
            return 0
        fi
    done
    # macOS app bundle, not always on PATH
    local mac_cli="/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"
    if [ -x "$mac_cli" ]; then
        echo "$mac_cli"
        return 0
    fi
    return 1
}

# --- VS Code User config directory -------------------------------------------
# Override with VSCODE_USER_DIR if you use a portable/flatpak/insiders install.
find_user_dir() {
    if [ -n "${VSCODE_USER_DIR:-}" ]; then
        echo "$VSCODE_USER_DIR"
        return 0
    fi
    local candidates=(
        "$HOME/.config/Code/User"
        "$HOME/Library/Application Support/Code/User"
        "${APPDATA:-}/Code/User"
        "$HOME/.config/Code - Insiders/User"
        "$HOME/.var/app/com.visualstudio.code/config/Code/User"
        "$HOME/.config/VSCodium/User"
    )
    for dir in "${candidates[@]}"; do
        if [ -d "$dir" ]; then
            echo "$dir"
            return 0
        fi
    done
    return 1
}

xdg_config_home() {
    echo "${XDG_CONFIG_HOME:-$HOME/.config}"
}

# --- Module file map ---------------------------------------------------------
# Prints one "<repo-relative path>\t<absolute path on this machine>" line per
# file the module owns. Both install.sh and backup.sh walk this, in opposite
# directions, so a module only ever declares its paths once.
#
# `fonts` is installed specially and never exported. `llms` has its own handler
# because it merges settings and maps shared content to multiple destinations.
module_files() {
    case "$1" in
        vscode)
            local user_dir
            user_dir="$(find_user_dir)" || return 1
            printf '%s\t%s\n' \
                "vscode/settings.json"    "$user_dir/settings.json" \
                "vscode/keybindings.json" "$user_dir/keybindings.json" \
                "vscode/snippets"         "$user_dir/snippets"
            ;;
        zsh)
            printf '%s\t%s\n' "zsh/zshrc" "$HOME/.zshrc"
            ;;
        kitty)
            printf '%s\t%s\n' "kitty/kitty.conf" "$(xdg_config_home)/kitty/kitty.conf"
            ;;
        fonts|llms)
            return 0
            ;;
        *)
            die "unknown module: $1"
            ;;
    esac
}

# Human-readable reason a module cannot be resolved on this machine.
module_unavailable_reason() {
    case "$1" in
        vscode) echo "could not find the VS Code User directory — open VS Code once, or set VSCODE_USER_DIR" ;;
        *)      echo "unavailable on this machine" ;;
    esac
}
