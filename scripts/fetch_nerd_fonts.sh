#!/usr/bin/env bash
# Fetch the official Nerd Fonts font-patcher (not vendored into git).
#
# Pins release tag v3.4.0 of https://github.com/ryanoasis/nerd-fonts via the
# official FontPatcher.zip asset (font-patcher + src/glyphs/ + name_parser +
# glyphnames.json). The full nerd-fonts repo is multi-GB of pre-patched fonts;
# the zip is the supported patcher distribution (~3 MB).
#
# Usage:
#   ./scripts/fetch_nerd_fonts.sh
#
# Writes:
#   build/nerd-fonts/          extracted patcher tree
#   build/nerd_fonts_version.txt
set -euo pipefail

TAG="v3.4.0"
# Nerd Fonts release version (must match font-patcher header "Nerd Fonts Version").
EXPECTED_VERSION="3.4.0"
# font-patcher script_version embedded in the same release.
EXPECTED_SCRIPT_VERSION="4.20.3"
# sha256 of https://github.com/ryanoasis/nerd-fonts/releases/download/v3.4.0/FontPatcher.zip
EXPECTED_SHA256="a8f11e511ed7c69e96680858c06b50a643ea7752e26d5cd13dd5e5cc53ab1760"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIR="$ROOT/build/nerd-fonts"
VERSION_FILE="$ROOT/build/nerd_fonts_version.txt"
URL="https://github.com/ryanoasis/nerd-fonts/releases/download/${TAG}/FontPatcher.zip"
ZIP="${TMPDIR:-/tmp}/FontPatcher-${TAG}.zip"

if [ -f "$DIR/font-patcher" ]; then
  # Already present; still verify the pinned version string.
  FOUND=$(grep -E '^# Nerd Fonts Version:' "$DIR/font-patcher" | head -1 | awk '{print $NF}')
  if [ "$FOUND" != "$EXPECTED_VERSION" ]; then
    echo "ERROR: existing $DIR/font-patcher is version $FOUND, expected $EXPECTED_VERSION" >&2
    echo "Remove $DIR and re-run this script." >&2
    exit 1
  fi
  echo "nerd-fonts patcher already at $DIR (version $FOUND)"
  echo "$TAG $EXPECTED_VERSION script=$EXPECTED_SCRIPT_VERSION sha256=$EXPECTED_SHA256" >"$VERSION_FILE"
  exit 0
fi

echo "Downloading FontPatcher.zip ($TAG)..."
curl -fsSL -o "$ZIP" "$URL"
ACTUAL_SHA256=$(shasum -a 256 "$ZIP" | awk '{print $1}')
if [ "$ACTUAL_SHA256" != "$EXPECTED_SHA256" ]; then
  echo "ERROR: sha256 mismatch for FontPatcher.zip" >&2
  echo "  expected $EXPECTED_SHA256" >&2
  echo "  got      $ACTUAL_SHA256" >&2
  exit 1
fi

rm -rf "$DIR"
mkdir -p "$DIR"
unzip -q "$ZIP" -d "$DIR"

if [ ! -f "$DIR/font-patcher" ]; then
  echo "ERROR: font-patcher missing after extract into $DIR" >&2
  exit 1
fi
if [ ! -d "$DIR/src/glyphs" ]; then
  echo "ERROR: src/glyphs missing after extract into $DIR" >&2
  exit 1
fi

FOUND=$(grep -E '^# Nerd Fonts Version:' "$DIR/font-patcher" | head -1 | awk '{print $NF}')
if [ "$FOUND" != "$EXPECTED_VERSION" ]; then
  echo "ERROR: extracted font-patcher is version $FOUND, expected $EXPECTED_VERSION" >&2
  exit 1
fi

echo "$TAG $EXPECTED_VERSION script=$EXPECTED_SCRIPT_VERSION sha256=$EXPECTED_SHA256" >"$VERSION_FILE"
echo "nerd-fonts patcher $TAG ($EXPECTED_VERSION / script $EXPECTED_SCRIPT_VERSION) -> $DIR"
echo "recorded $VERSION_FILE"
