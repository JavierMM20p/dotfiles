#!/usr/bin/env bash
# Export the current machine's config INTO this repo.
# Run this after you change settings, keybindings, snippets, extensions,
# .zshrc, or kitty.conf.
#
#   ./scripts/backup.sh                every module
#   ./scripts/backup.sh zsh kitty      only the named modules
#
# Modules: vscode zsh kitty   (fonts are vendored by hand, never exported)
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

MODULES=()
for arg in "$@"; do
    case "$arg" in
        -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
        -*)        die "unknown option: $arg" ;;
        fonts)     die "fonts cannot be backed up — add font files to fonts/ by hand" ;;
        *)         is_module "$arg" || die "unknown module: $arg (known: ${ALL_MODULES[*]})"
                   MODULES+=("$arg") ;;
    esac
done

if [ "${#MODULES[@]}" -eq 0 ]; then
    for m in "${ALL_MODULES[@]}"; do
        [ "$m" = "fonts" ] && continue
        MODULES+=("$m")
    done
fi

# Copy one machine path back into the repo. Directories are mirrored rather
# than merged, so a file deleted locally also disappears from the repo.
export_path() {
    local source="$1" rel="$2" dest="$REPO_ROOT/$2"

    if [ ! -e "$source" ]; then
        echo "  skipped $rel (not present on this machine)"
        return 0
    fi

    mkdir -p "$(dirname "$dest")"
    if [ -d "$source" ]; then
        rm -rf "$dest"
        cp -R "$source" "$dest"
        local count
        count=$(find "$dest" -type f ! -name '.gitkeep' | wc -l | tr -d ' ')
        touch "$dest/.gitkeep"
        echo "  saved   $rel ($count file(s))"
    else
        cp "$source" "$dest"
        echo "  saved   $rel"
    fi
}

export_files() {
    local module="$1" mapping
    if ! mapping="$(module_files "$module")"; then
        echo "  SKIPPED: $(module_unavailable_reason "$module")" >&2
        return 0
    fi
    [ -z "$mapping" ] && return 0
    while IFS=$'\t' read -r rel source; do
        [ -z "$rel" ] && continue
        export_path "$source" "$rel"
    done <<< "$mapping"
}

# --- VS Code extensions ------------------------------------------------------
export_extensions() {
    local ext_file="$REPO_ROOT/vscode/extensions.txt"
    local header='# VS Code extensions — one ID per line.
# Regenerate with: ./scripts/backup.sh vscode
# Install with:    ./scripts/install.sh vscode
'
    local ids="" code
    if code="$(find_code_cli)"; then
        ids="$("$code" --list-extensions 2>/dev/null || true)"
    fi

    # Fallback: read the extensions manifest directly. Useful when the CLI is
    # unavailable (snap confinement, headless shell, remote session).
    if [ -z "$ids" ]; then
        for manifest in "$HOME/.vscode/extensions/extensions.json" \
                        "$HOME/.vscode-server/extensions/extensions.json"; do
            if [ -f "$manifest" ] && command -v python3 >/dev/null 2>&1; then
                echo "  (VS Code CLI unavailable — reading $manifest)"
                ids="$(python3 -c "
import json, sys
with open(sys.argv[1]) as fh:
    data = json.load(fh)
print('\n'.join(sorted({e['identifier']['id'] for e in data})))
" "$manifest")"
                break
            fi
        done
    fi

    if [ -n "$ids" ]; then
        { printf '%s\n' "$header"; printf '%s\n' "$ids" | sort -u; } > "$ext_file"
        echo "  saved   vscode/extensions.txt ($(printf '%s\n' "$ids" | wc -l | tr -d ' ') extensions)"
    else
        echo "  WARNING: could not list extensions; left extensions.txt unchanged" >&2
    fi
}

for module in "${MODULES[@]}"; do
    echo
    echo "== $module"
    export_files "$module"
    [ "$module" = "vscode" ] && export_extensions
done

echo
echo "Done. Review with 'git diff', then commit and push."
