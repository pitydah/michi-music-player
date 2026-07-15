#!/usr/bin/env python3
"""Extract first clean copy from QML files with duplicate content.

Strategy: scan lines, skip everything after we see a second 
'import' block in the file body (not at the top).
"""
import re
from pathlib import Path

QML_DIR = Path("ui_qml")


def extract_first_copy(content: str) -> str:
    lines = content.splitlines()
    
    # Phase 1: collect all top-level imports (lines 0..N where line starts with "import ")
    import_end = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("import "):
            import_end = i + 1
        else:
            break
    
    # Phase 2: find the opening brace of the root item (first non-import line)
    root_start = import_end
    for i in range(import_end, len(lines)):
        if "{" in lines[i]:
            root_start = i
            break
    
    # Phase 3: track brace depth from root_start
    # Stop when we see an import statement AFTER the root has started
    depth = 0
    first_copy_end = None
    for i in range(root_start, len(lines)):
        line = lines[i]
        stripped = line.strip()
        
        # If we see import after root started, this is the second copy
        if stripped.startswith("import ") and depth == 0:
            first_copy_end = i
            break
        
        depth += line.count("{")
        depth -= line.count("}")
        
        if depth == 0 and i > root_start:
            # Root item closed
            first_copy_end = i + 1
            break
    
    if first_copy_end is None:
        return content
    
    kept = lines[:first_copy_end]
    return "\n".join(kept) + "\n"


def main():
    # Files known to have duplicate content
    files = [
        "components/AsyncStateView.qml",
        "components/BalanceSlider.qml",
        "components/CapabilityGuard.qml",
        "components/CommandPalette.qml",
        "components/ConfirmationDialog.qml",
        "components/DestructiveActionDialog.qml",
        "components/ErrorState.qml",
        "components/InlineError.qml",
        "components/JobProgressCard.qml",
        "components/KeyboardShortcutHint.qml",
        "components/LoadingState.qml",
        "components/NotificationBanner.qml",
        "components/NotificationCenter.qml",
        "components/NotificationItem.qml",
        "components/NotificationProgressItem.qml",
        "components/NotificationToast.qml",
        "components/ProgressState.qml",
        "components/ResponsivePageLayout.qml",
        "components/ResponsiveToolbar.qml",
        "components/SelectionActionBar.qml",
        "components/UnavailableState.qml",
        "pages/MixDetailPage.qml",
        "pages/MixHubPage.qml",
        "pages/devices/DevicePairingPage.qml",
        "pages/playlists/PlaylistEditorDialog.qml",
        "pages/search/SearchResultRow.qml",
    ]
    
    for rel in files:
        p = QML_DIR / rel
        if not p.exists():
            print(f"MISS {rel}")
            continue
        content = p.read_text()
        new_content = extract_first_copy(content)
        if new_content != content:
            p.write_text(new_content)
            old_lines = len(content.splitlines())
            new_lines = len(new_content.splitlines())
            print(f"FIX {rel}: {old_lines} -> {new_lines} lines")
        else:
            # Check if brace imbalance exists
            opens = content.count("{")
            closes = content.count("}")
            if opens != closes:
                content = content.rstrip()
                diff = opens - closes
                if diff > 0:
                    content += "\n" + "}" * diff + "\n"
                    p.write_text(content)
                    print(f"FIX {rel}: balanced braces (+{diff} closing)")
                else:
                    print(f"SKIP {rel}: -{closes - opens} extra closes")
            else:
                print(f"OK   {rel}")


if __name__ == "__main__":
    main()
