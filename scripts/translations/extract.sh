#!/bin/bash
# Extract translatable strings from QML files
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO"

TS_DIR="translations"
mkdir -p "$TS_DIR"

if which lupdate &>/dev/null; then
    lupdate ui_qml/ -ts "$TS_DIR/michi_es.ts" -source-language es
    lupdate ui_qml/ -ts "$TS_DIR/michi_en.ts" -source-language es -target-language en
    echo "Translation files updated in $TS_DIR/"
else
    echo "lupdate not found. Install Qt Linguist tools:"
    echo "  Arch: sudo pacman -S qt6-tools"
    echo "  Debian: sudo apt install qttools5-dev-tools"
    echo "  Fedora: sudo dnf install qt6-linguist"
fi
