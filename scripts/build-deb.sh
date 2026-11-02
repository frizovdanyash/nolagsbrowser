#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(python3 -c "import re,sys;print(re.search(r'APP_VERSION = \"([^\"]+)\"', open('$ROOT/src/nolags/__init__.py').read()).group(1))")"
ARCH="all"
PKG="$ROOT/build/deb/nolagsbrowser"
OUT="$ROOT/dist"

rm -rf "$ROOT/build/deb"
mkdir -p "$PKG/DEBIAN" "$PKG/usr/bin" "$PKG/usr/share/nolagsbrowser" "$OUT"

install -Dm755 "$ROOT/scripts/nolagsbrowser" "$PKG/usr/bin/nolagsbrowser"
install -Dm644 "$ROOT/data/nolagsbrowser.desktop" "$PKG/usr/share/applications/nolagsbrowser.desktop"
install -Dm644 "$ROOT/data/nolagsbrowser.1" "$PKG/usr/share/man/man1/nolagsbrowser.1"

mkdir -p "$PKG/usr/share/nolagsbrowser/src"
cp -r "$ROOT/src/nolags" "$PKG/usr/share/nolagsbrowser/src/"
find "$PKG/usr/share/nolagsbrowser" -name '__pycache__' -type d -prune -exec rm -rf {} +
find "$PKG/usr/share/nolagsbrowser" -name '*.pyc' -delete

mkdir -p "$PKG/usr/share/nolagsbrowser/assets"
cp -r "$ROOT/assets/mascot" "$PKG/usr/share/nolagsbrowser/assets/"
rm -f "$PKG/usr/share/nolagsbrowser/assets/mascot/mascot_source.png"
cp -r "$ROOT/assets/icons" "$PKG/usr/share/nolagsbrowser/assets/"

cp -r "$ROOT/data/icons" "$PKG/usr/share/nolagsbrowser/icons"
mkdir -p "$PKG/usr/share/icons"
mkdir -p "$PKG/usr/share/icons/hicolor"
cp -r "$ROOT/data/icons/"* "$PKG/usr/share/icons/hicolor/"

mkdir -p "$PKG/usr/share/doc/nolagsbrowser"
cp "$ROOT/LICENSE" "$PKG/usr/share/doc/nolagsbrowser/copyright" 2>/dev/null || true
cp "$ROOT/README.md" "$PKG/usr/share/doc/nolagsbrowser/README.md" 2>/dev/null || true

mkdir -p "$PKG/usr/share/nolagsbrowser/images"
cp "$ROOT/assets/brand/banner.png" "$PKG/usr/share/nolagsbrowser/images/banner.png" 2>/dev/null || true
cp "$ROOT/assets/mascot/mascot.png" "$PKG/usr/share/nolagsbrowser/images/mascot.png" 2>/dev/null || true

SIZE="$(du -sk --exclude=DEBIAN "$PKG" | cut -f1)"

cat > "$PKG/DEBIAN/control" <<EOF
Package: nolagsbrowser
Version: $VERSION
Architecture: $ARCH
Maintainer: Danechka <frizovdanyash@users.noreply.github.com>
Installed-Size: $SIZE
Depends: python3 (>= 3.9), python3-gi, python3-gi-cairo, gir1.2-gtk-3.0, gir1.2-webkit2-4.1
Recommends: sqlite3, fonts-noto-core, fonts-dejavu-core
Suggests: xdg-utils
Section: web
Priority: optional
Homepage: https://github.com/frizovdanyash/nolagsbrowser
Description: lightweight web browser built on WebKitGTK
 NoLags Browser is a compact GTK3 browser focused on memory usage:
 background tabs can be suspended to release RAM, memory can be trimmed
 manually, and the interface stays out of the way. It ships with history,
 bookmarks, downloads, notes, a start page with a mascot, tracker blocking,
 reader mode and a hosts-list generator.
EOF

cat > "$PKG/DEBIAN/md5sums" <<EOF
EOF
(cd "$PKG" && find usr -type f -exec md5sum {} + | sed 's|  | |' > DEBIAN/md5sums)

install -m755 "$ROOT/debian/postinst" "$PKG/DEBIAN/postinst"
install -m755 "$ROOT/debian/postrm" "$PKG/DEBIAN/postrm"

DEB="$OUT/nolagsbrowser_${VERSION}_${ARCH}.deb"
dpkg-deb --root-owner-group -Zxz --build "$PKG" "$DEB" >/dev/null
echo "$DEB"
