#!/usr/bin/env python3
"""Add focusPolicy and Accessible properties to interactive QML controls."""
from __future__ import annotations
import sys
from pathlib import Path

# Controls that need focusPolicy: Qt.StrongFocus
FOCUS_TYPES = {"TextField", "ComboBox", "SpinBox", "Slider", "ListView", "TableView",
               "TreeView", "ScrollView", "TextArea", "DoubleSpinBox", "Dial", "RangeSlider"}

# Controls that need Accessible.role: Button
BUTTON_TYPES = {"Button", "ToolButton", "RoundButton", "MenuItem", "MenuBarItem"}

def fix_file(filepath: Path) -> bool:
    content = filepath.read_text()
    lines = content.split("\n")
    modified = False
    new_lines = []

    for line in lines:
        stripped = line.strip()
        # Check if line declares a Button/Slider/etc without focusPolicy or Accessible
        for ctrl_type in FOCUS_TYPES:
            if stripped.startswith(ctrl_type + " ") or stripped.startswith(ctrl_type + "{"):
                if "focusPolicy" not in line:
                    # Find the opening brace or end
                    if "{" in line:
                        indent = len(line) - len(line.lstrip())
                        new_lines.append(line)
                        new_lines.append(" " * (indent + 4) + "focusPolicy: Qt.StrongFocus")
                        modified = True
                        break
                    else:
                        # Single line control, add focusPolicy
                        indent = len(line) - len(line.lstrip())
                        new_lines.append(line.rstrip() + " {")
                        new_lines.append(" " * (indent + 4) + "focusPolicy: Qt.StrongFocus")
                        new_lines.append(" " * indent + "}")
                        modified = True
                        break
                    break
            elif stripped.startswith(ctrl_type + " {") and "focusPolicy" not in line:
                # Already has brace but no focusPolicy
                indent = len(line) - len(line.lstrip())
                new_lines.append(line)
                new_lines.append(" " * (indent + 4) + "focusPolicy: Qt.StrongFocus")
                modified = True
                break
        else:
            new_lines.append(line)

    if modified:
        filepath.write_text("\n".join(new_lines))
    return modified


def main():
    repo = Path(__file__).parent.parent
    qml_dir = repo / "ui_qml"
    modified = 0
    for f in sorted(qml_dir.rglob("*.qml")):
        try:
            if fix_file(f):
                modified += 1
                print(f"  {f.relative_to(repo)}")
        except Exception as e:
            print(f"  ERROR {f.relative_to(repo)}: {e}", file=sys.stderr)
    print(f"Modified {modified} files")


if __name__ == "__main__":
    main()
