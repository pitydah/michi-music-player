#!/usr/bin/env python3
"""Audit that core, audio, and ui_qml_bridge don't import QtWidgets."""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROTECTED_DIRS = ['core', 'audio', 'ui_qml_bridge', 'library', 'streaming', 'sync', 'metadata', 'lyrics', 'recognition', 'sources']
EXCEPTIONS = []


def audit():
    issues = []
    for directory in PROTECTED_DIRS:
        dir_path = os.path.join(PROJECT_ROOT, directory)
        if not os.path.isdir(dir_path):
            print(f"Skipping {directory}: directory not found")
            continue
        for root, _dirs, files in os.walk(dir_path):
            for f in files:
                if not f.endswith('.py') or f.startswith('__'):
                    continue
                path = os.path.join(root, f)
                relative = os.path.relpath(path, PROJECT_ROOT)
                if any(relative.startswith(exc) for exc in EXCEPTIONS):
                    continue
                with open(path) as fh:
                    content = fh.read()
                if 'from PySide6.QtWidgets' in content or 'import PySide6.QtWidgets' in content:
                    issues.append(f"{relative}: imports QtWidgets")

    if issues:
        for i in issues:
            print(f"ISSUE: {i}")
        sys.exit(1)
    else:
        print("OK: No QtWidgets imports in core/audio/bridge/library layers")
        sys.exit(0)


if __name__ == "__main__":
    audit()
