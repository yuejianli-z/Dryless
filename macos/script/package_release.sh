#!/usr/bin/env bash
set -euo pipefail

APP_NAME="DrylessMac"
DISPLAY_NAME="Dryless"
BUNDLE_ID="com.yuejianli.dryless.mac"
VERSION="${1:-0.1.0}"
MIN_SYSTEM_VERSION="14.0"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RELEASE_DIR="$ROOT_DIR/release"
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/dryless-release.XXXXXX")"
trap 'rm -rf "$WORK_DIR"' EXIT
APP_BUNDLE="$WORK_DIR/$DISPLAY_NAME.app"
APP_CONTENTS="$APP_BUNDLE/Contents"
APP_MACOS="$APP_CONTENTS/MacOS"
APP_RESOURCES="$APP_CONTENTS/Resources"
OUTPUT_APP="$RELEASE_DIR/$DISPLAY_NAME.app"

cd "$ROOT_DIR"

pkill -x "$APP_NAME" >/dev/null 2>&1 || true
rm -rf .build "$OUTPUT_APP"
mkdir -p "$RELEASE_DIR"

swift build -c release --product "$APP_NAME"
BUILD_DIR="$(swift build -c release --show-bin-path)"
BUILD_BINARY="$BUILD_DIR/$APP_NAME"
RESOURCE_BUNDLE="$BUILD_DIR/DrylessMac_DrylessMac.bundle"

test -x "$BUILD_BINARY"
test -d "$RESOURCE_BUNDLE"

strip -S "$BUILD_BINARY"
if strings -a "$BUILD_BINARY" | LC_ALL=C grep -E '/Users/|/home/|/var/folders/|/private/var/folders/' >/dev/null; then
  echo "Refusing to package a binary containing a private build path." >&2
  exit 1
fi

mkdir -p "$APP_MACOS" "$APP_RESOURCES"
cp -X "$BUILD_BINARY" "$APP_MACOS/$APP_NAME"
cp -RX "$RESOURCE_BUNDLE" "$APP_RESOURCES/"

ICON_SOURCE="$ROOT_DIR/Sources/DrylessMac/Resources/Icons/desktop-eye-sage.ico"
ICONSET_DIR="$RELEASE_DIR/Dryless.iconset"
mkdir -p "$ICONSET_DIR"
sips -s format png -z 16 16 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_16x16.png" >/dev/null
sips -s format png -z 32 32 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_16x16@2x.png" >/dev/null
sips -s format png -z 32 32 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_32x32.png" >/dev/null
sips -s format png -z 64 64 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_32x32@2x.png" >/dev/null
sips -s format png -z 128 128 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_128x128.png" >/dev/null
sips -s format png -z 256 256 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_128x128@2x.png" >/dev/null
sips -s format png -z 256 256 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_256x256.png" >/dev/null
sips -s format png -z 512 512 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_256x256@2x.png" >/dev/null
sips -s format png -z 512 512 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_512x512.png" >/dev/null
sips -s format png -z 1024 1024 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_512x512@2x.png" >/dev/null
iconutil -c icns "$ICONSET_DIR" -o "$APP_RESOURCES/Dryless.icns"
rm -rf "$ICONSET_DIR"

cat >"$APP_CONTENTS/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key>
  <string>$APP_NAME</string>
  <key>CFBundleIdentifier</key>
  <string>$BUNDLE_ID</string>
  <key>CFBundleName</key>
  <string>$DISPLAY_NAME</string>
  <key>CFBundleIconFile</key>
  <string>Dryless</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>$VERSION</string>
  <key>CFBundleVersion</key>
  <string>$VERSION</string>
  <key>LSMinimumSystemVersion</key>
  <string>$MIN_SYSTEM_VERSION</string>
  <key>NSPrincipalClass</key>
  <string>NSApplication</string>
  <key>NSCameraUsageDescription</key>
  <string>Dryless uses the camera locally to estimate blink frequency. Frames are processed in memory and are not saved or uploaded.</string>
</dict>
</plist>
PLIST

if find "$APP_BUNDLE" -iname '*demo*' -print -quit | grep -q .; then
  echo "Refusing to package demo assets in the release bundle." >&2
  exit 1
fi

xattr -cr "$APP_BUNDLE"
plutil -lint "$APP_CONTENTS/Info.plist"
codesign --force --deep --sign - "$APP_BUNDLE"
codesign --verify --deep --strict --verbose=2 "$APP_BUNDLE"

ditto --norsrc "$APP_BUNDLE" "$OUTPUT_APP"
xattr -cr "$OUTPUT_APP"
codesign --verify --deep --strict "$OUTPUT_APP"
printf 'Created %s\n' "$OUTPUT_APP"
