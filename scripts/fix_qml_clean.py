#!/usr/bin/env python3
"""Fix QML files with duplicate content (merge artifacts).

Each file listed here has TWO copies concatenated. This script
keeps only the FIRST copy and removes the duplicate.
"""
from pathlib import Path

QML_DIR = Path(__file__).resolve().parent.parent / "ui_qml"

# Each entry: (relative_path, last_line_of_first_copy, additional_closing_braces)
# The "last_line_of_first_copy" is the LAST belonging to the first copy.
# We keep lines 0..last_line_of_first_copy (inclusive), then add closing braces.

FIXES = {
    "components/CapabilityGuard.qml": (65, 1),
    "components/CommandPalette.qml": (44, 1),
    "components/InlineError.qml": (100, 2),
    "components/KeyboardShortcutHint.qml": (25, 2),
    "components/NotificationBanner.qml": (6, 5),
    "components/NotificationCenter.qml": (48, 5),
    "components/NotificationItem.qml": (97, 6),
    "components/NotificationProgressItem.qml": (184, 3),
    "components/ResponsivePageLayout.qml": (3, 1),
    "pages/devices/DevicePairingPage.qml": (122, 8),
}


def main():
    for rel, (end_line, extra_closes) in FIXES.items():
        p = QML_DIR.parent / rel
        if not p.exists():
            print(f"  [MISS] {rel}")
            continue
        content = p.read_text(encoding="utf-8")
        lines = content.splitlines()

        if len(lines) <= end_line + 1:
            print(f"  [SKIP] {rel}: only {len(lines)} lines, end_line={end_line}")
            continue

        # Keep lines 0..end_line inclusive
        kept = lines[:end_line + 1]

        # Add closing braces
        kept.append("}" * extra_closes)

        new_content = "\n".join(kept) + "\n"
        p.write_text(new_content, encoding="utf-8")
        print(f"  [FIX] {rel} (kept {len(kept)} lines, +{extra_closes} braces)")

    print("Done")


if __name__ == "__main__":
    main()
