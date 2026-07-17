#!/usr/bin/env python3
"""Audit bridge contracts against actual service implementations."""
import os
import sys

BRIDGE_DIR = os.path.join(os.path.dirname(__file__), '..', 'ui_qml_bridge')
SERVICE_DIRS = ['core', 'audio']


def audit():
    issues = []
    for f in sorted(os.listdir(BRIDGE_DIR)):
        if not f.endswith('_bridge.py') or f.startswith('__'):
            continue
        path = os.path.join(BRIDGE_DIR, f)
        with open(path) as fh:
            content = fh.read()
        if 'sqlite3.connect' in content:
            issues.append(f"{f}: direct SQLite connection detected")
        if '= Service(' in content or 'Service()' in content:
            issues.append(f"{f}: direct service construction detected")
    return issues


if __name__ == '__main__':
    issues = audit()
    if issues:
        for i in issues:
            print(f"ISSUE: {i}")
        sys.exit(1)
    else:
        print("OK: All bridge contracts clean")
        sys.exit(0)
