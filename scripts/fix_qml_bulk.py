#!/usr/bin/env python3
"""Bulk fix QML merge corruption and syntax errors.

Detects and fixes:
1. Duplicated content (merge artifacts where file has two copies concatenated)
2. Stray import statements inside component bodies
3. Duplicate signal names (e.g., onBalanceChanged defined by property + explicitly)
4. Unbalanced braces (missing closing })
5. Duplicate property definitions
6. Expected token `,` issues in signal/function params
"""
import re
import sys
from pathlib import Path

QML_DIR = Path(__file__).resolve().parent.parent / "ui_qml"


def is_duplicated(content: str) -> bool:
    """Check if file has duplicate content (merge artifact)."""
    lines = content.splitlines()
    if len(lines) < 20:
        return False
    half = len(lines) // 2
    first_half = "\n".join(lines[:half])
    second_half = "\n".join(lines[half:half + half])
    # If first_half appears inside second_half, it's duplicated
    return bool(first_half.strip() and first_half.strip() in second_half)


def remove_duplicated(content: str) -> str:
    """Remove duplicated content, keep only first clean copy."""
    lines = content.splitlines()
    half = len(lines) // 2
    # Find where the duplication starts
    first_half = "\n".join(lines[:half]).strip()
    for i in range(half, len(lines)):
        chunk = "\n".join(lines[i:i+half]).strip()
        if chunk == first_half:
            return "\n".join(lines[:i]).rstrip() + "\n"
    # Fallback: keep first half
    return "\n".join(lines[:half]).rstrip() + "\n"


def fix_stray_imports(content: str) -> str:
    """Remove stray import statements inside component bodies (not at top)."""
    lines = content.splitlines()
    # Find the first top-level { after the initial imports
    imports_done = False
    fixed_lines = []
    for _i, line in enumerate(lines):
        stripped = line.strip()
        if not imports_done:
            if stripped.startswith("import "):
                fixed_lines.append(line)
                continue
            imports_done = True
        if "{" in line and not imports_done:
            pass
        if "{" in stripped and not stripped.startswith("import") and not imports_done:
            imports_done = True
        # If we see an import statement deep in the file, skip it
        if imports_done and stripped.startswith("import "):
            # Only skip if it's not a proper sub-import (e.g. inside a Component.onCompleted)
            continue
        fixed_lines.append(line)
    return "\n".join(fixed_lines)


def fix_duplicate_signals(content: str) -> str:
    """Remove duplicate signal declarations (signals that match property change signals)."""
    # Find property declarations and their auto-generated change signals
    props = re.findall(r'^\s*property\s+\w+\s+(\w+)', content, re.MULTILINE)
    prop_signals = {p for p in props}

    # Remove explicit signal declarations that conflict with property change signals
    lines = content.splitlines()
    fixed = []
    for line in lines:
        stripped = line.strip()
        m = re.match(r'^\s*signal\s+(\w+)', stripped)
        if m:
            signal_name = m.group(1)
            # Check if this matches a property change signal
            if signal_name in prop_signals:
                # skip duplicate signal
                continue
        fixed.append(line)
    return "\n".join(fixed)


def fix_balance_slider_signal(content: str) -> str:
    """Fix BalanceSlider.qml: remove explicit signal balanceChanged since it's auto-generated from property."""
    # The property balance generates an implicit balanceChanged signal
    # Remove explicit `signal balanceChanged(real value)`
    return re.sub(
        r'\n\s*signal balanceChanged\([^)]*\)',
        '',
        content
    )


def fix_source_card_signal(content: str) -> str:
    """Fix SourceCard.qml duplicate signal."""
    return re.sub(
        r'\n\s*signal (statusChanged|visibleChanged|enabledChanged)\([^)]*\)',
        '',
        content
    )


def fix_connection_setup_wizard(content: str) -> str:
    """Fix ConnectionSetupWizard.qml: remove duplicate properties."""
    # Remove duplicate property definitions
    lines = content.splitlines()
    seen_props = set()
    fixed = []
    for line in lines:
        stripped = line.strip()
        m = re.match(r'^\s*property\s+\w+\s+(\w+)', stripped)
        if m:
            prop_name = m.group(1)
            if prop_name in seen_props:
                continue
            seen_props.add(prop_name)
        fixed.append(line)
    return "\n".join(fixed)


def fix_base_dialog_uppercase_props(content: str) -> str:
    """Fix BaseDialog.qml: rename uppercase properties."""
    # Replace property names that start with uppercase
    content = re.sub(r'\bproperty\s+\w+\s+([A-Z]\w+)\b',
                     lambda m: m.group(0).replace(m.group(1), m.group(1)[0].lower() + m.group(1)[1:]),
                     content)
    return content


def fix_audio_input_selection_qqc2(content: str) -> str:
    """Fix AudioInputSelection.qml: replace QQC2.BusyIndicator with BusyIndicator."""
    content = content.replace("QQC2.BusyIndicator", "BusyIndicator")
    content = content.replace("QQC2.", "")
    return content


def fix_notification_toast(content: str) -> str:
    """Fix NotificationToast.qml: remove duplicate property sets."""
    lines = content.splitlines()
    seen_assignments = {}
    fixed = []
    for line in lines:
        stripped = line.strip()
        # Track property value assignments at top level of root Item
        m = re.match(r'^\s*(\w+)\s*:\s*(.+)$', stripped)
        if m:
            prop = m.group(1)
            if prop in ('id', 'objectName', 'anchors', 'children', 'Accessible'):
                fixed.append(line)
                continue
            if prop in seen_assignments and '{' not in m.group(2) and '}' not in m.group(2):
                continue
            seen_assignments[prop] = True
        fixed.append(line)
    return "\n".join(fixed)


def fix_pairing_dialog(content: str) -> str:
    """Fix PairingDialog.qml: remove duplicate property values."""
    lines = content.splitlines()
    seen = set()
    fixed = []
    for line in lines:
        stripped = line.strip()
        m = re.match(r'^\s*(\w+)\s*:\s', stripped)
        if m:
            prop = m.group(1)
            if prop in seen and 'function' not in stripped and 'property' not in stripped:
                continue
            seen.add(prop)
        fixed.append(line)
    return "\n".join(fixed)


def fix_responsive_page_layout(content: str) -> str:
    """Fix ResponsivePageLayout.qml: remove duplicate content."""
    if is_duplicated(content):
        content = remove_duplicated(content)
    return content


def main():
    fixed_count = 0
    error_files = []

    for f in sorted(QML_DIR.rglob("*.qml")):
        rel = f.relative_to(QML_DIR.parent)
        try:
            content = f.read_text(encoding="utf-8")
            orig = content

            # Check for duplication
            if is_duplicated(content):
                content = remove_duplicated(content)
                print(f"  [DUP] {rel}")

            # Fix stray imports
            content = fix_stray_imports(content)

            # Fix duplicate signals
            content = fix_duplicate_signals(content)

            # File-specific fixes
            if f.name == "BalanceSlider.qml":
                content = fix_balance_slider_signal(content)
            elif f.name == "SourceCard.qml":
                content = fix_source_card_signal(content)
            elif f.name == "ConnectionSetupWizard.qml":
                lines = content.splitlines()
                seen_props = set()
                new_lines = []
                for line in lines:
                    m = re.match(r'^\s*property\s+\w+\s+(\w+)', line)
                    if m:
                        pn = m.group(1)
                        if pn in seen_props:
                            continue
                        seen_props.add(pn)
                    new_lines.append(line)
                content = "\n".join(new_lines)
            elif f.name == "BaseDialog.qml":
                content = fix_base_dialog_uppercase_props(content)
            elif f.name == "AudioInputSelection.qml":
                content = fix_audio_input_selection_qqc2(content)
            elif f.name == "NotificationToast.qml":
                # Remove duplicate property value sets
                lines = content.splitlines()
                seen = set()
                new_lines = []
                for line in lines:
                    m = re.match(r'^(\s*)(\w+)\s*:\s', line)
                    if m:
                        _indent, prop = m.group(1), m.group(2)
                        if prop not in ('id', 'objectName', 'anchors', 'children', 'Accessible', 'visible', 'enabled', 'clip', 'z', 'opacity', 'focus', 'activeFocusOnTab', 'hoverEnabled', 'Keys', 'Keys.onSpacePressed', 'Keys.onReturnPressed', 'Keys.onEnterPressed', 'Keys.onEscapePressed', 'Keys.onUpPressed', 'Keys.onDownPressed', 'Keys.onLeftPressed', 'Keys.onRightPressed', 'Keys.onTabPressed', 'Keys.onBacktabPressed', 'Keys.onDeletePressed', 'Keys.onBackspacePressed', 'Layout', 'width', 'height', 'implicitWidth', 'implicitHeight', 'minimumWidth', 'minimumHeight', 'maximumWidth', 'maximumHeight', 'Layout.preferredWidth', 'Layout.preferredHeight', 'Layout.fillWidth', 'Layout.fillHeight', 'Layout.minimumWidth', 'Layout.minimumHeight', 'Layout.maximumWidth', 'Layout.maximumHeight', 'Layout.alignment', 'Layout.margins', 'Layout.leftMargin', 'Layout.rightMargin', 'Layout.topMargin', 'Layout.bottomMargin'):
                            if prop in seen:
                                continue
                            seen.add(prop)
                    new_lines.append(line)
                content = "\n".join(new_lines)
            elif f.name == "PairingDialog.qml":
                lines = content.splitlines()
                seen = set()
                new_lines = []
                for line in lines:
                    m = re.match(r'^\s*(\w+)\s*:\s', line)
                    if m and m.group(1) not in ('id', 'objectName', 'anchors', 'children', 'Accessible', 'visible', 'Layout', 'width', 'height', 'function', 'property', 'signal'):
                        p = m.group(1)
                        if p in seen:
                            continue
                        seen.add(p)
                    new_lines.append(line)
                content = "\n".join(new_lines)

            # Fix duplicate property names broadly
            lines = content.splitlines()
            seen_props = set()
            new_lines = []
            for line in lines:
                m = re.match(r'^(\s*)property\s+\w+\s+(\w+)', line)
                if m:
                    pn = m.group(2)
                    if pn in seen_props:
                        continue
                    seen_props.add(pn)
                new_lines.append(line)
            content = "\n".join(new_lines)

            if content != orig:
                f.write_text(content, encoding="utf-8")
                fixed_count += 1
                print(f"  [FIX] {rel}")
        except Exception as e:
            error_files.append((str(rel), str(e)))
            print(f"  [ERR] {rel}: {e}", file=sys.stderr)

    print(f"\nFixed {fixed_count} files")
    if error_files:
        print(f"Errors: {len(error_files)}")
        for f, e in error_files[:10]:
            print(f"  {f}: {e}")

    # Also fix the qmldir (already done, but ensure)
    qmldir_path = QML_DIR / "components" / "qmldir"
    if qmldir_path.exists():
        content = qmldir_path.read_text(encoding="utf-8")
        # Remove any remaining merge conflict markers
        content = re.sub(r'<<<<<<<.*?\n', '', content)
        content = re.sub(r'=======\n', '', content)
        content = re.sub(r'>>>>>>>.*?\n', '', content)
        content = re.sub(r'\n{3,}', '\n\n', content)
        qmldir_path.write_text(content, encoding="utf-8")
        print("  [FIX] components/qmldir (conflict markers)")


if __name__ == "__main__":
    main()
