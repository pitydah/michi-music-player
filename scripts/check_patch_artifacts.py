#!/usr/bin/env python3
"""check_patch_artifacts.py — fail if patch artifacts found in QML files."""
import re
import pathlib
import sys
QML_DIR = pathlib.Path(__file__).parent.parent / "ui_qml"
artifacts = []
for f in sorted(QML_DIR.rglob("*.qml")):
    content = f.read_text(errors="replace")
    if "<<<<<<<" in content:
        artifacts.append(f"{f}: contains <<<<<<< conflict marker")
    if re.search(r'^diff --git ', content, re.MULTILINE):
        artifacts.append(f"{f}: contains embedded diff header")
if artifacts:
    for a in artifacts:
        print(a)
    sys.exit(1)
print("OK: no patch artifacts found")
sys.exit(0)
