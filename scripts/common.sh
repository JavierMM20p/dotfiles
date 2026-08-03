#!/usr/bin/env bash
# Shared helpers: locate the VS Code CLI and the User config directory.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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

# --- User config directory ---------------------------------------------------
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

die() {
    echo "error: $*" >&2
    exit 1
}
