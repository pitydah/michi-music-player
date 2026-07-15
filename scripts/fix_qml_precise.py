#!/usr/bin/env python3
"""Precise QML fix: remove only duplicate property value assignments and duplicate properties."""
import re
from pathlib import Path

QML_DIR = Path(__file__).resolve().parent.parent / "ui_qml"


def has_duplicate_content(content: str) -> bool:
    """Check if file has clearly duplicated content (two copies)."""
    lines = content.splitlines()
    if len(lines) < 30:
        return False
    # Look for consecutive import statements in the middle of file
    import_blocks = 0
    in_block = False
    for i, line in enumerate(lines):
        if line.strip().startswith("import "):
            if not in_block and i > 5:
                import_blocks += 1
            in_block = True
        else:
            in_block = False
    return import_blocks >= 2


def remove_duplicate_properties(content: str) -> str:
    """Remove duplicate property definitions."""
    lines = content.splitlines()
    seen_props = set()
    result = []
    for line in lines:
        m = re.match(r'^(\s*)property\s+\w+\s+(\w+)', line)
        if m:
            prop_name = m.group(2)
            if prop_name in seen_props:
                continue
            seen_props.add(prop_name)
        result.append(line)
    return "\n".join(result)


def fix_balance_slider(content: str) -> str:
    # Remove explicit signal balanceChanged since property balance auto-generates it
    return re.sub(r'\n\s*signal balanceChanged\([^)]*\)', '', content)


def fix_source_card(content: str) -> str:
    # Remove explicit signal declarations that conflict with property change signals
    return re.sub(r'\n\s*signal (statusChanged|visibleChanged|enabledChanged)\([^)]*\)', '', content)


def fix_history_table(content: str) -> str:
    # Remove duplicate signal declarations
    return re.sub(r'\n\s*signal (rowClicked|rowDoubleClicked|headerClicked|selectionChanged|sortChanged)\([^)]*\)', '', content)


def fix_history_timeline(content: str) -> str:
    return re.sub(r'\n\s*signal (itemClicked|itemDoubleClicked|filterChanged|rangeChanged|zoomChanged)\([^)]*\)', '', content)


def main():
    for f in sorted(QML_DIR.rglob("*.qml")):
        content = f.read_text(encoding="utf-8")
        orig = content
        rel = f.relative_to(QML_DIR.parent)

        # Fix duplicate properties
        content = remove_duplicate_properties(content)

        # File-specific fixes
        if f.name == "BalanceSlider.qml":
            content = fix_balance_slider(content)
        elif f.name == "SourceCard.qml":
            content = fix_source_card(content)
        elif f.name == "HistoryTable.qml":
            content = fix_history_table(content)
        elif f.name == "HistoryTimeline.qml":
            content = fix_history_timeline(content)

        if content != orig:
            f.write_text(content, encoding="utf-8")
            print(f"  [FIX] {rel}")

    # Fix re-created files (already done)
    print("Done")


if __name__ == "__main__":
    main()
