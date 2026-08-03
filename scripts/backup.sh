#!/usr/bin/env bash
# Export the current machine's VS Code config INTO this repo.
# Run this after you change settings, keybindings, snippets, or extensions.
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

USER_DIR="$(find_user_dir)" || die "could not find the VS Code User directory. Set VSCODE_USER_DIR and retry."
echo "Reading config from: $USER_DIR"

mkdir -p "$REPO_ROOT/vscode/snippets"

# --- settings + keybindings --------------------------------------------------
for file in settings.json keybindings.json; do
    if [ -f "$USER_DIR/$file" ]; then
        cp "$USER_DIR/$file" "$REPO_ROOT/vscode/$file"
        echo "  saved $file"
    else
        echo "  skipped $file (not present on this machine)"
    fi
done

# --- snippets ----------------------------------------------------------------
# Mirror the directory so snippets deleted locally also disappear from the repo.
if [ -d "$USER_DIR/snippets" ]; then
    rm -rf "$REPO_ROOT/vscode/snippets"
    cp -R "$USER_DIR/snippets" "$REPO_ROOT/vscode/snippets"
    touch "$REPO_ROOT/vscode/snippets/.gitkeep"
    count=$(find "$REPO_ROOT/vscode/snippets" -type f ! -name '.gitkeep' | wc -l | tr -d ' ')
    echo "  saved snippets ($count file(s))"
fi

# --- extensions --------------------------------------------------------------
EXT_FILE="$REPO_ROOT/vscode/extensions.txt"
HEADER='# VS Code extensions — one ID per line.
# Regenerate with: ./scripts/backup.sh
# Install with:    ./scripts/install.sh
'

extension_ids=""
if CODE="$(find_code_cli)"; then
    extension_ids="$("$CODE" --list-extensions 2>/dev/null || true)"
fi

# Fallback: read the extensions manifest directly. Useful when the CLI is
# unavailable (snap confinement, headless shell, remote session).
if [ -z "$extension_ids" ]; then
    for manifest in "$HOME/.vscode/extensions/extensions.json" \
                    "$HOME/.vscode-server/extensions/extensions.json"; do
        if [ -f "$manifest" ] && command -v python3 >/dev/null 2>&1; then
            echo "  (VS Code CLI unavailable — reading $manifest)"
            extension_ids="$(python3 -c "
import json, sys
with open(sys.argv[1]) as fh:
    data = json.load(fh)
print('\n'.join(sorted({e['identifier']['id'] for e in data})))
" "$manifest")"
            break
        fi
    done
fi

if [ -n "$extension_ids" ]; then
    { printf '%s\n' "$HEADER"; printf '%s\n' "$extension_ids" | sort -u; } > "$EXT_FILE"
    echo "  saved extensions.txt ($(printf '%s\n' "$extension_ids" | wc -l | tr -d ' ') extensions)"
else
    echo "  WARNING: could not list extensions; left extensions.txt unchanged" >&2
fi

echo
echo "Done. Review with 'git diff', then commit and push."
