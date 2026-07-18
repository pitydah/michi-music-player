#!/bin/bash
# Compile translation files to .qm
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO"

TS_DIR="translations"

if which lrelease &>/dev/null; then
    for ts in "$TS_DIR"/*.ts; do
        lrelease "$ts"
        echo "Compiled: $ts"
    done
else
    echo "lrelease not found. Install Qt Linguist tools."
    exit 1
fi
