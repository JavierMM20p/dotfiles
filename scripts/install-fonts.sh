#!/usr/bin/env bash
# Install every font file under fonts/ into the current user's font directory.
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

FONT_SRC="$REPO_ROOT/fonts"
[ -d "$FONT_SRC" ] || die "no fonts/ directory in this repo"

case "$(uname -s)" in
    Darwin) FONT_DEST="$HOME/Library/Fonts" ;;
    *)      FONT_DEST="${XDG_DATA_HOME:-$HOME/.local/share}/fonts" ;;
esac

mkdir -p "$FONT_DEST"

count=0
while IFS= read -r -d '' font; do
    cp "$font" "$FONT_DEST/"
    echo "  installed $(basename "$font")"
    count=$((count + 1))
done < <(find "$FONT_SRC" -type f \( -iname '*.ttf' -o -iname '*.otf' -o -iname '*.ttc' \) -print0)

if [ "$count" -eq 0 ]; then
    echo "No font files found in fonts/ — nothing to do."
    exit 0
fi

if command -v fc-cache >/dev/null 2>&1; then
    fc-cache -f "$FONT_DEST" >/dev/null
    echo "Refreshed font cache."
fi

echo "Installed $count font file(s) to $FONT_DEST"
