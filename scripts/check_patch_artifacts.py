#!/usr/bin/env python3
"""check_patch_artifacts.py — fail if patch artifacts found in QML or Python files.

Detects:
  - <<<<<<< conflict markers
  - ======= conflict separators
  - >>>>>>> conflict markers
  - @@ hunk headers (outside valid QML/Python)
  - diff --git headers
  - rejected hunks comments
  - .rej files anywhere
  - .orig files anywhere
"""
import re
import pathlib
import sys

REPO_DIR = pathlib.Path(__file__).parent.parent
SEARCH_DIRS = ["ui_qml", "ui_qml_bridge", "core", "audio", "tests", "scripts"]
EXTENSIONS = (".qml", ".py")

artifacts = []

# 1. Stray .rej / .orig files
for ext in (".rej", ".orig"):
    for f in sorted(REPO_DIR.rglob(f"*{ext}")):
        parts = f.relative_to(REPO_DIR).parts
        if any(p.startswith(".") or p == "__pycache__" for p in parts):
            continue
        artifacts.append(f"{f}: stray {ext} file")

# 2. Check source files for embedded patch markers
# Self-test files that intentionally contain conflict markers as test data
SELF_TEST_FILES = {
    REPO_DIR / "tests" / "test_no_merge_conflicts.py",
    REPO_DIR / "scripts" / "check_patch_artifacts.py",
}

for search_dir in SEARCH_DIRS:
    target = REPO_DIR / search_dir
    if not target.exists():
        continue
    for f in sorted(target.rglob("*")):
        if f.suffix not in EXTENSIONS:
            continue
        if f in SELF_TEST_FILES:
            continue
        parts = f.relative_to(REPO_DIR).parts
        if any(p.startswith(".") or p == "__pycache__" for p in parts):
            continue
        try:
            content = f.read_text(errors="replace")
        except Exception:
            continue

        if "<<<<<<<" in content:
            artifacts.append(f"{f}: contains <<<<<<< conflict marker")
        if "=======" in content and re.search(r'^<<<<<<< |^>>>>>>> ', content, re.MULTILINE):
            artifacts.append(f"{f}: contains ======= separator (likely merge conflict)")
        if ">>>>>>>" in content:
            artifacts.append(f"{f}: contains >>>>>>> conflict marker")
        if re.search(r'^diff --git ', content, re.MULTILINE):
            artifacts.append(f"{f}: contains embedded diff header")
        if "rejected hunk" in content.lower():
            artifacts.append(f"{f}: contains rejected hunk comment")
        # @@ hunk headers: only flag if outside valid context
        if re.search(r'^@@ -\d+,\d+ \+\d+,\d+ @@', content, re.MULTILINE):
            artifacts.append(f"{f}: contains @@ hunk header (patch artifact)")

if artifacts:
    for a in artifacts:
        print(a)
    sys.exit(1)

print("OK: no patch artifacts found")
sys.exit(0)
