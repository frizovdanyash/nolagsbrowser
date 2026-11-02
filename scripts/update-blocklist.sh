#!/bin/sh
set -eu

SOURCE="${BLOCKLIST_URL:-https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts}"
TARGET="${BLOCKLIST_OUT:-${XDG_DATA_HOME:-$HOME/.local/share}/nolagsbrowser/blocklist.txt}"
TMP="$(mktemp)"

cleanup() {
    rm -f "$TMP" "$TMP.raw"
}
trap cleanup EXIT

if command -v curl >/dev/null 2>&1; then
    curl -fsSL --max-time 120 "$SOURCE" -o "$TMP.raw"
elif command -v wget >/dev/null 2>&1; then
    wget -q -T 120 -O "$TMP.raw" "$SOURCE"
else
    echo "нужен curl или wget" >&2
    exit 1
fi

mkdir -p "$(dirname "$TARGET")"
{
    echo "# NoLags Browser blocklist"
    echo "# source: $SOURCE"
    echo "# updated: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    awk '
        /^[[:space:]]*#/ { next }
        NF >= 2 {
            ip = $1
            if (ip != "0.0.0.0" && ip != "127.0.0.1" && ip != "::1") next
            for (i = 2; i <= NF; i++) {
                d = tolower($i)
                if (d == "localhost" || d == "localhost.localdomain" || d == "local" || d == "broadcasthost") continue
                if (d ~ /^[a-z0-9][a-z0-9._-]*\.[a-z0-9._-]+$/ && d !~ /^\./ && d !~ /\.\./ && d !~ /^0\.0\.0\.0/) print "0.0.0.0 " d
            }
        }
    ' "$TMP.raw" | sort -u > "$TMP"
    cat "$TMP"
} > "$TARGET.new"

mv "$TARGET.new" "$TARGET"
COUNT="$(grep -c '^0.0.0.0 ' "$TARGET" || true)"
echo "$COUNT доменов записано в $TARGET"
