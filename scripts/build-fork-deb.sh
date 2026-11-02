#!/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FORK="$ROOT/third-party/luakit-fork"
VERSION="2.0.0"
BUILD="$ROOT/build"
STAGE="$BUILD/stage"
OUT="$ROOT/dist/nolagsbrowser_${VERSION}_amd64.deb"

rm -rf "$BUILD"
mkdir -p "$STAGE/DEBIAN" "$ROOT/dist"

make -C "$FORK" -j"$(nproc)"
make -C "$FORK" install DESTDIR="$STAGE" PREFIX=/usr XDGPREFIX=/etc/xdg > /dev/null

install -m755 "$FORK/luakit" "$STAGE/usr/bin/nolagsbrowser"
rm -f "$STAGE/usr/bin/luakit"

install -m644 "$ROOT/assets/icons/nolagsbrowser.svg" "$STAGE/usr/share/pixmaps/nolagsbrowser.svg"
install -m644 "$ROOT/assets/icon.png" "$STAGE/usr/share/pixmaps/nolagsbrowser.png"
mkdir -p "$STAGE/usr/share/icons/hicolor/scalable/apps" "$STAGE/usr/share/icons/hicolor/256x256/apps"
install -m644 "$ROOT/assets/icons/nolagsbrowser.svg" "$STAGE/usr/share/icons/hicolor/scalable/apps/nolagsbrowser.svg"
install -m644 "$ROOT/assets/icon.png" "$STAGE/usr/share/icons/hicolor/256x256/apps/nolagsbrowser.png"

install -m644 "$ROOT/assets/mascot/mascot.png" "$STAGE/usr/share/luakit/resources/nolags-mascot.png"
convert "$ROOT/assets/mascot/mascot.png" -resize 96x96 "$STAGE/usr/share/luakit/resources/nolags-mascot-96.png"
convert "$ROOT/assets/mascot/mascot.png" -resize 48x48 "$STAGE/usr/share/luakit/resources/nolags-mascot-48.png"

mkdir -p "$STAGE/usr/share/applications"
cat > "$STAGE/usr/share/applications/nolagsbrowser.desktop" <<'EOF'
[Desktop Entry]
Name=NoLags Browser
Comment=Лёгкий браузер для слабых ПК
GenericName=Web Browser
Exec=nolagsbrowser %u
Icon=nolagsbrowser
Terminal=false
Type=Application
Categories=Network;WebBrowser;
Keywords=browser;web;internet;nolags;
MimeType=text/html;text/xml;application/xhtml+xml;x-scheme-handler/http;x-scheme-handler/https;
StartupNotify=true
EOF

install -d "$STAGE/usr/share/man/man1"
gzip -9 -c "$FORK/luakit.1" > "$STAGE/usr/share/man/man1/nolagsbrowser.1.gz"

cat > "$STAGE/DEBIAN/control" <<EOF
Package: nolagsbrowser
Version: ${VERSION}
Section: web
Priority: optional
Architecture: amd64
Depends: libwebkit2gtk-4.1-0, libgtk-3-0, libsoup-3.0-0, libluajit-5.1-2 | liblua5.1-0, lua-filesystem, libsqlite3-0, libgstreamer1.0-0
Recommends: gstreamer1.0-plugins-good, gstreamer1.0-libav
Maintainer: Danechka <frizovdanyash@users.noreply.github.com>
Installed-Size: 6000
Homepage: https://github.com/frizovdanyash/nolagsbrowser
Description: NoLags Browser
 Lightweight WebKitGTK browser forked from luakit, tuned for low-memory
 machines. Includes a branded panel with mascot, tab bar, address bar and
 ad-blocking.
EOF

cat > "$STAGE/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = "configure" ]; then
  command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database -q /usr/share/applications || true
  command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi
exit 0
EOF

cat > "$STAGE/DEBIAN/postrm" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = "remove" ] || [ "$1" = "purge" ]; then
  command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database -q /usr/share/applications || true
fi
exit 0
EOF

chmod 755 "$STAGE/DEBIAN/postinst" "$STAGE/DEBIAN/postrm"

dpkg-deb --build --root-owner-group "$STAGE" "$OUT"
echo "built: $OUT"
