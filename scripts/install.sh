#!/usr/bin/env bash
# Apply this repo's VS Code config TO the current machine.
#
#   ./scripts/install.sh              copy files into place (backs up existing)
#   ./scripts/install.sh --symlink    symlink instead, so edits flow back to the repo
#   ./scripts/install.sh --no-extensions   skip extension installation
#   ./scripts/install.sh --dry-run    show what would happen, change nothing
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

MODE="copy"
DO_EXTENSIONS=1
DRY_RUN=0

for arg in "$@"; do
    case "$arg" in
        --symlink)       MODE="symlink" ;;
        --no-extensions) DO_EXTENSIONS=0 ;;
        --dry-run)       DRY_RUN=1 ;;
        -h|--help)       sed -n '2,9p' "$0"; exit 0 ;;
        *)               die "unknown option: $arg" ;;
    esac
done

USER_DIR="$(find_user_dir)" || die "could not find the VS Code User directory. Open VS Code once, or set VSCODE_USER_DIR."
echo "Target: $USER_DIR"
[ "$DRY_RUN" -eq 1 ] && echo "(dry run — nothing will be written)"

run() {
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "  would: $*"
    else
        "$@"
    fi
}

BACKUP_DIR="$USER_DIR/.config-backup-$(date +%Y%m%d-%H%M%S)"
backed_up=0

# Move anything already in place into a timestamped backup, so a bad sync is
# always recoverable.
preserve() {
    local target="$1"
    [ -e "$target" ] || [ -L "$target" ] || return 0
    if [ "$backed_up" -eq 0 ]; then
        run mkdir -p "$BACKUP_DIR"
        backed_up=1
    fi
    run mv "$target" "$BACKUP_DIR/"
}

link_or_copy() {
    local src="$1" dest="$2"
    [ -e "$src" ] || return 0
    preserve "$dest"
    if [ "$MODE" = "symlink" ]; then
        run ln -s "$src" "$dest"
        echo "  linked $(basename "$dest")"
    else
        run cp -R "$src" "$dest"
        echo "  copied $(basename "$dest")"
    fi
}

run mkdir -p "$USER_DIR"
link_or_copy "$REPO_ROOT/vscode/settings.json"    "$USER_DIR/settings.json"
link_or_copy "$REPO_ROOT/vscode/keybindings.json" "$USER_DIR/keybindings.json"
link_or_copy "$REPO_ROOT/vscode/snippets"         "$USER_DIR/snippets"

if [ "$backed_up" -eq 1 ]; then
    echo "  previous config moved to: $BACKUP_DIR"
fi

# --- extensions --------------------------------------------------------------
if [ "$DO_EXTENSIONS" -eq 1 ]; then
    echo
    if CODE="$(find_code_cli)"; then
        installed="$("$CODE" --list-extensions 2>/dev/null | tr '[:upper:]' '[:lower:]' || true)"
        failed=()
        while IFS= read -r ext; do
            ext="${ext%%#*}"                       # strip comments
            ext="$(echo "$ext" | tr -d '[:space:]')"
            [ -z "$ext" ] && continue
            if printf '%s\n' "$installed" | grep -qx "$(echo "$ext" | tr '[:upper:]' '[:lower:]')"; then
                echo "  present  $ext"
                continue
            fi
            echo "  install  $ext"
            if [ "$DRY_RUN" -eq 0 ]; then
                "$CODE" --install-extension "$ext" --force >/dev/null 2>&1 || failed+=("$ext")
            fi
        done < "$REPO_ROOT/vscode/extensions.txt"

        if [ "${#failed[@]}" -gt 0 ]; then
            echo
            echo "  WARNING: ${#failed[@]} extension(s) failed to install:" >&2
            printf '    %s\n' "${failed[@]}" >&2
        fi
    else
        echo "  WARNING: no VS Code CLI on PATH — skipping extensions." >&2
        echo "  In VS Code run: Shell Command: Install 'code' command in PATH" >&2
    fi
fi

echo
echo "Done. Restart VS Code to pick everything up."
[ -d "$REPO_ROOT/fonts" ] && [ -n "$(ls -A "$REPO_ROOT/fonts" 2>/dev/null | grep -v '^README' || true)" ] \
    && echo "Fonts present in fonts/ — run ./scripts/install-fonts.sh to install them."
exit 0
