#!/usr/bin/env python3
"""Remove merge artifacts from QML files.

Pattern: some files have the second copy start with imports inside
the root body. We need to detect and remove:
1. Lines that are import statements in the body of the component
2. The duplicate trailing copy that follows
"""
import re
from pathlib import Path

QML_DIR = Path("ui_qml")


def clean_file(filepath: Path) -> bool:
    content = filepath.read_text(encoding="utf-8")
    lines = content.splitlines()

    # Strategy: find all lines that are "import" statements inside the component body
    # (not at the top of file). Remove those lines and everything after.

    # Find the first non-import, non-empty, non-comment line (root element start)
    first_content_idx = -1
    for i, line in enumerate(lines):
        s = line.strip()
        if s and not s.startswith("import ") and not s.startswith("#") and not s.startswith("pragma "):
            first_content_idx = i
            break

    if first_content_idx < 0:
        return False

    # Track brace depth from the root element's opening brace
    root_brace_line = -1
    for i in range(first_content_idx, len(lines)):
        if "{" in lines[i]:
            root_brace_line = i
            break

    if root_brace_line < 0:
        return False

    depth = 0
    for i in range(root_brace_line, len(lines)):
        line = lines[i]
        s = line.strip()

        # If we see an import statement when depth > 0 (inside a component body)
        # this marks the start of the second (duplicate) copy
        if s.startswith("import ") and depth > 0:
            # Remove this import line and everything after
            new_lines = lines[:i]
            # Remove trailing whitespace
            while new_lines and new_lines[-1].strip() == "":
                new_lines.pop()
            filepath.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            return True

        depth += line.count("{")
        depth -= line.count("}")

        if depth <= 0 and i > root_brace_line:
            # Root item closed at brace depth 0
            break

    # No duplicate detected
    return False


def deduplicate_properties(content: str) -> str:
    """Remove duplicate property declarations."""
    lines = content.splitlines()
    seen = set()
    result = []
    changed = False
    for line in lines:
        m = re.match(r'^(\s*)property\s+\w+\s+(\w+)', line)
        if m:
            prop_name = m.group(2)
            if prop_name in seen:
                changed = True
                continue
            seen.add(prop_name)
        result.append(line)
    if changed:
        return "\n".join(result)
    return content


def fix_balance_slider_signal(content: str) -> str:
    """Remove signal that duplicates property change signal."""
    import re
    return re.sub(r'\n\s*signal balanceChanged\([^)]*\)', '', content)


def fix_source_card(content: str) -> str:
    import re
    return re.sub(r'\n\s*signal (statusChanged|visibleChanged|enabledChanged)\([^)]*\)', '', content)


def fix_history_table(content: str) -> str:
    import re
    return re.sub(r'\n\s*signal (rowClicked|rowDoubleClicked|headerClicked|selectionChanged|sortChanged)\([^)]*\)', '', content)


def fix_history_timeline(content: str) -> str:
    import re
    return re.sub(r'\n\s*signal (itemClicked|itemDoubleClicked|filterChanged|rangeChanged|zoomChanged)\([^)]*\)', '', content)


def main():
    fixed_clean = 0
    fixed_props = 0
    fixed_signals = 0

    for f in sorted(QML_DIR.rglob("*.qml")):
        rel = f.relative_to(QML_DIR.parent)
        content = f.read_text(encoding="utf-8")
        orig = content

        # Step 1: Clean duplicate content
        if clean_file(f):
            content = f.read_text(encoding="utf-8")
            fixed_clean += 1
            print(f"  [DUP] {rel}")

        # Step 2: Deduplicate properties
        new_content = deduplicate_properties(content)
        if new_content != content:
            content = new_content
            fixed_props += 1
            print(f"  [PROP] {rel}")

        # Step 3: Fix duplicate signals
        if f.name == "BalanceSlider.qml":
            new_c = fix_balance_slider_signal(content)
            if new_c != content:
                content = new_c
                fixed_signals += 1
                print(f"  [SIG] {rel}")
        elif f.name == "SourceCard.qml":
            new_c = fix_source_card(content)
            if new_c != content:
                content = new_c
                fixed_signals += 1
                print(f"  [SIG] {rel}")
        elif f.name == "HistoryTable.qml":
            new_c = fix_history_table(content)
            if new_c != content:
                content = new_c
                fixed_signals += 1
                print(f"  [SIG] {rel}")
        elif f.name == "HistoryTimeline.qml":
            new_c = fix_history_timeline(content)
            if new_c != content:
                content = new_c
                fixed_signals += 1
                print(f"  [SIG] {rel}")

        # Step 4: Balance braces
        opens = content.count("{")
        closes = content.count("}")
        if opens != closes:
            content = content.rstrip()
            diff = opens - closes
            if diff > 0:
                content += "\n" + "}" * diff + "\n"
                print(f"  [BRACE] {rel}: +{diff} closing")
            elif diff < 0:
                # Too many closes - can't fix automatically
                print(f"  [BRACE-WARN] {rel}: {diff} extra closes")

        if content != orig:
            f.write_text(content, encoding="utf-8")

    print(f"\nCleaned: {fixed_clean}, Properties: {fixed_props}, Signals: {fixed_signals}")


if __name__ == "__main__":
    main()
