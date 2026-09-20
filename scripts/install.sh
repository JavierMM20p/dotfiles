#!/usr/bin/env bash
# Apply this repo's config TO the current machine.
#
#   ./scripts/install.sh                   every module
#   ./scripts/install.sh zsh kitty         only the named modules
#   ./scripts/install.sh --symlink         symlink instead of copy, so edits flow back
#   ./scripts/install.sh --no-extensions   skip VS Code extension installation
#   ./scripts/install.sh --dry-run         show what would happen, change nothing
#
# Modules: vscode zsh kitty fonts llms
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

MODE="copy"
DO_EXTENSIONS=1
DRY_RUN=0
MODULES=()

for arg in "$@"; do
    case "$arg" in
        --symlink)       MODE="symlink" ;;
        --no-extensions) DO_EXTENSIONS=0 ;;
        --dry-run)       DRY_RUN=1 ;;
        -h|--help)       sed -n '2,12p' "$0"; exit 0 ;;
        -*)              die "unknown option: $arg" ;;
        *)               is_module "$arg" || die "unknown module: $arg (known: ${ALL_MODULES[*]})"
                         MODULES+=("$arg") ;;
    esac
done

[ "${#MODULES[@]}" -eq 0 ] && MODULES=("${ALL_MODULES[@]}")

[ "$DRY_RUN" -eq 1 ] && echo "(dry run — nothing will be written)"

run() {
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "  would: $*"
    else
        "$@"
    fi
}

BACKUP_DIR="$REPO_ROOT/.config-backup-$(date +%Y%m%d-%H%M%S)"
backed_up=0

# Move anything already in place into a timestamped backup, so a bad sync is
# always recoverable. Everything lands in one directory inside the repo (it is
# gitignored) rather than scattered next to each config it displaced.
preserve() {
    local target="$1"
    [ -e "$target" ] || [ -L "$target" ] || return 0
    local dest="$BACKUP_DIR/$(basename "$target")"
    # Two modules could own same-named files; keep both.
    if [ -e "$dest" ]; then
        dest="$BACKUP_DIR/$(basename "$(dirname "$target")")-$(basename "$target")"
    fi
    if [ "$backed_up" -eq 0 ]; then
        run mkdir -p "$BACKUP_DIR"
        backed_up=1
    fi
    run mv "$target" "$dest"
}

link_or_copy() {
    local src="$1" dest="$2"
    [ -e "$src" ] || return 0
    run mkdir -p "$(dirname "$dest")"
    preserve "$dest"
    if [ "$MODE" = "symlink" ]; then
        run ln -s "$src" "$dest"
        [ "$DRY_RUN" -eq 0 ] && echo "  linked  $dest"
    else
        run cp -R "$src" "$dest"
        [ "$DRY_RUN" -eq 0 ] && echo "  copied  $dest"
    fi
    return 0
}

install_files() {
    local module="$1" mapping
    if ! mapping="$(module_files "$module")"; then
        echo "  SKIPPED: $(module_unavailable_reason "$module")" >&2
        return 0
    fi
    [ -z "$mapping" ] && return 0
    while IFS=$'\t' read -r rel target; do
        [ -z "$rel" ] && continue
        link_or_copy "$REPO_ROOT/$rel" "$target"
    done <<< "$mapping"
}

# --- VS Code extensions ------------------------------------------------------
install_extensions() {
    local ext_file="$REPO_ROOT/vscode/extensions.txt"
    [ -f "$ext_file" ] || return 0

    local code
    if ! code="$(find_code_cli)"; then
        echo "  WARNING: no VS Code CLI on PATH — skipping extensions." >&2
        echo "  In VS Code run: Shell Command: Install 'code' command in PATH" >&2
        return 0
    fi

    local installed failed=()
    installed="$("$code" --list-extensions 2>/dev/null | tr '[:upper:]' '[:lower:]' || true)"
    while IFS= read -r ext; do
        ext="${ext%%#*}"                       # strip comments
        ext="$(echo "$ext" | tr -d '[:space:]')"
        [ -z "$ext" ] && continue
        if printf '%s\n' "$installed" | grep -qx "$(echo "$ext" | tr '[:upper:]' '[:lower:]')"; then
            echo "  present $ext"
            continue
        fi
        echo "  install $ext"
        if [ "$DRY_RUN" -eq 0 ]; then
            "$code" --install-extension "$ext" --force >/dev/null 2>&1 || failed+=("$ext")
        fi
    done < "$ext_file"

    if [ "${#failed[@]}" -gt 0 ]; then
        echo "  WARNING: ${#failed[@]} extension(s) failed to install:" >&2
        printf '    %s\n' "${failed[@]}" >&2
    fi
}

# --- fonts -------------------------------------------------------------------
# Not a one-to-one file mapping like the other modules: every font file in
# fonts/ is copied into the user font directory, then the cache is refreshed.
install_fonts() {
    local src="$REPO_ROOT/fonts" dest
    [ -d "$src" ] || return 0

    case "$(uname -s)" in
        Darwin) dest="$HOME/Library/Fonts" ;;
        *)      dest="${XDG_DATA_HOME:-$HOME/.local/share}/fonts" ;;
    esac

    local count=0
    while IFS= read -r -d '' font; do
        [ "$count" -eq 0 ] && run mkdir -p "$dest"
        run cp "$font" "$dest/"
        echo "  installed $(basename "$font")"
        count=$((count + 1))
    done < <(find "$src" -type f \( -iname '*.ttf' -o -iname '*.otf' -o -iname '*.ttc' \) -print0)

    if [ "$count" -eq 0 ]; then
        echo "  no font files in fonts/ — nothing to do"
        return 0
    fi

    if command -v fc-cache >/dev/null 2>&1 && [ "$DRY_RUN" -eq 0 ]; then
        fc-cache -f "$dest" >/dev/null
        echo "  refreshed font cache"
    fi
    echo "  installed $count font file(s) to $dest"
}

for module in "${MODULES[@]}"; do
    echo
    echo "== $module"
    case "$module" in
        llms)
            llm_args=(install)
            [ "$MODE" = "symlink" ] && llm_args+=(--symlink)
            [ "$DRY_RUN" -eq 1 ] && llm_args+=(--dry-run)
            python3 "$REPO_ROOT/scripts/llms.py" "${llm_args[@]}"
            ;;
        fonts)
            install_fonts
            ;;
        vscode)
            install_files vscode
            [ "$DO_EXTENSIONS" -eq 1 ] && install_extensions
            ;;
        *)
            install_files "$module"
            ;;
    esac
done

echo
if [ "$backed_up" -eq 1 ]; then
    echo "Previous config moved to: $BACKUP_DIR"
fi
echo "Done. Restart affected apps (VS Code, kitty, Codex, Claude Code), or 'exec zsh', to pick up changes."
