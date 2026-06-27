#!/usr/bin/env python3
"""Audit tool — measures structural debt in ui/window.py.

Usage: python tools/audit_window.py [--max-lines N]
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WINDOW_PY = os.path.join(ROOT, "ui", "window.py")


def _lines(path: str) -> list[str]:
    with open(path) as f:
        return f.readlines()


def count_lines(path: str) -> int:
    return len(_lines(path))


def count_methods(path: str) -> int:
    with open(path) as f:
        return sum(1 for line in f if re.match(r"^\s+def ", line))


def count_imports(path: str) -> int:
    lines = _lines(path)
    count = 0
    in_import = False
    for line in lines:
        stripped = line.strip()
        if re.match(r"^from |^import ", stripped) or stripped.startswith("from "):
            in_import = True
            count += 1
            continue
        if in_import and (stripped.startswith(")") or stripped == "" or not stripped.startswith("(")):
            in_import = False
    return count


def count_direct_refs(path: str, pattern: str) -> int:
    with open(path) as f:
        return sum(1 for line in f if re.search(pattern, line))


def main():
    max_lines = 4000
    for i, arg in enumerate(sys.argv[1:], start=1):
        if arg == "--max-lines" and i + 1 < len(sys.argv):
            max_lines = int(sys.argv[i + 1])

    lines = count_lines(WINDOW_PY)
    methods = count_methods(WINDOW_PY)
    imports = count_imports(WINDOW_PY)

    optional_imports = count_direct_refs(WINDOW_PY,
        r"from (recognition|sync|streaming|integrations|home_assistant|ai_assistant|audio_analysis|recommendation)")
    private_access = count_direct_refs(WINDOW_PY, r"self\._win\._")
    db_conn = count_direct_refs(WINDOW_PY, r"_db\._conn")
    views_created = count_direct_refs(WINDOW_PY, r"self\.\w+ = \w+Widget\(\)")

    print("=== ui/window.py audit ===")
    print(f"Lines:           {lines}")
    print(f"Methods:         {methods}")
    print(f"Top-level imports: {imports}")
    print(f"Optional imports:  {optional_imports}")
    print(f"_win._ accesses:   {private_access}")
    print(f"_db._conn refs:    {db_conn}")
    print(f"Widgets created directly: {views_created}")
    print(f"Max lines target: {max_lines}")

    over = lines - max_lines
    if over > 0:
        print(f"  {over} lines over target ({max_lines})")
        return 1
    print("  Within budget")
    return 0


if __name__ == "__main__":
    sys.exit(main())
