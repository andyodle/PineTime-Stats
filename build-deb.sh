#!/bin/bash
# Install dependencies and create Debian package

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/output"
PKG_DIR="pinetime-stats-1.0"

echo "Creating package directory structure..."
rm -rf "$PKG_DIR"
mkdir -p "$OUTPUT_DIR"
mkdir -p "$PKG_DIR/DEBIAN"
mkdir -p "$PKG_DIR/usr/bin"
mkdir -p "$PKG_DIR/usr/share/applications"
mkdir -p "$PKG_DIR/usr/share/pixmap"

echo "Installing application..."
mkdir -p "$PKG_DIR/usr/share/pinetime-stats"
mkdir -p "$PKG_DIR/usr/share/metainfo"
mkdir -p "$PKG_DIR/usr/share/icons/hicolor/48x48/apps"
cp -r main.py ble db ui "$PKG_DIR/usr/share/pinetime-stats/"
cp pinetime-stats.desktop "$PKG_DIR/usr/share/applications/"
if [ -d "icons" ]; then
    cp icons/*.png "$PKG_DIR/usr/share/icons/hicolor/48x48/apps/" 2>/dev/null || true
fi
ln -sf /usr/share/pinetime-stats/main.py "$PKG_DIR/usr/bin/pinetime-stats"

echo "Creating control file..."
cat > "$PKG_DIR/DEBIAN/control" << 'EOF'
Package: pinetime-stats
Version: 1.0
Section: utils
Priority: optional
Architecture: all
Depends: python3, python3-pyqt6, bluez
Maintainer: PineTime Stats Team
Description: PineTime Step Tracking Dashboard
 A desktop application for tracking steps and heart rate data
 from the PineTime smartwatch running InfiniTime firmware.
EOF

cat > "$PKG_DIR/DEBIAN/postinst" << 'EOF'
#!/bin/bash
update-desktop-database /usr/share/applications || true
gtk-update-icon-cache -f /usr/share/icons/hicolor 2>/dev/null || true
EOF

chmod 755 "$PKG_DIR/DEBIAN/postinst"

cat > "$PKG_DIR/DEBIAN/prerm" << 'EOF'
#!/bin/bash
update-desktop-database /usr/share/applications || true
gtk-update-icon-cache -f /usr/share/icons/hicolor 2>/dev/null || true
rm -rf /usr/share/pinetime-stats
EOF

chmod 755 "$PKG_DIR/DEBIAN/prerm"

cat > "$PKG_DIR/DEBIAN/postrm" << 'EOF'
#!/bin/bash
rm -rf /usr/share/pinetime-stats
update-desktop-database /usr/share/applications 2>/dev/null || true
gtk-update-icon-cache -f /usr/share/icons/hicolor 2>/dev/null || true
EOF

chmod 755 "$PKG_DIR/DEBIAN/postrm"

echo "Creating Debian package..."
dpkg-deb --build "$PKG_DIR" "$OUTPUT_DIR/$PKG_DIR.deb"

echo ""
echo "========================================"
echo "Package created: $OUTPUT_DIR/$PKG_DIR.deb"
echo ""
echo "To install, run:"
echo "  sudo dpkg -i $OUTPUT_DIR/$PKG_DIR.deb"
echo "  sudo apt-get install -y -f"
echo "========================================"