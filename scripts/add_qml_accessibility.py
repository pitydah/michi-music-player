#!/usr/bin/env python3
"""Add objectName, Accessible.role, Accessible.name, focus to root Item of QML pages."""
from __future__ import annotations
import re
import sys
from pathlib import Path


def add_accessibility(filepath: Path) -> bool:
    content = filepath.read_text()
    lines = content.split("\n")
    modified = False
    # Find root Item/Page/Pane line
    root_pattern = re.compile(r"^(Item|Page|Pane|Rectangle)\s*\{")
    accessible_role = '    Accessible.role: Accessible.Pane'
    accessible_name = f'    Accessible.name: "{_make_name(filepath)}"'
    object_name = f'    objectName: "{_make_objname(filepath)}"'
    focus_line = '    focus: true'

    added = 0
    new_lines = []
    in_root = False
    for line in lines:
        new_lines.append(line)
        if root_pattern.match(line.strip()) and not in_root:
            in_root = True
            # Check if accessibility already exists
            following = "\n".join(lines[lines.index(line)+1:lines.index(line)+8]) if lines.index(line) < len(lines) - 1 else ""
            if "Accessible.role" not in following:
                new_lines.append(accessible_role)
                added += 1
            if "Accessible.name" not in following:
                new_lines.append(accessible_name)
                added += 1
            if "objectName" not in following:
                new_lines.append(object_name)
                added += 1
            if "focus:" not in following:
                new_lines.append(focus_line)
                added += 1
    if added > 0:
        filepath.write_text("\n".join(new_lines))
        return True
    return False


def _make_name(path: Path) -> str:
    name = path.stem.replace("Page", "").replace("Dialog", "").replace("Panel", "")
    # camelCase to Title With Spaces
    result = re.sub(r'([a-z])([A-Z])', r'\1 \2', name).strip()
    return result or path.stem


def _make_objname(path: Path) -> str:
    name = path.stem[0].lower() + path.stem[1:] if path.stem else ""
    return name


def main():
    repo = Path(__file__).parent.parent
    qml_dir = repo / "ui_qml"
    modified = 0
    for f in sorted(qml_dir.rglob("*.qml")):
        try:
            if add_accessibility(f):
                modified += 1
                print(f"  {f.relative_to(repo)}")
        except Exception as e:
            print(f"  ERROR {f.relative_to(repo)}: {e}", file=sys.stderr)
    print(f"Modified {modified} files")


if __name__ == "__main__":
    main()
