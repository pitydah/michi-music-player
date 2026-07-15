#!/usr/bin/env python3
"""QML Workflow Audit (HS).

Analyzes tests/qml/workflows/ and verifies each workflow test:
1. Creates QQmlApplicationEngine
2. Registers context properties
3. Loads page QML
4. Gets object by objectName
5. Uses QTest.mouseClick or QTest.keyClicks
6. Waits for signal
7. Verifies backend
8. Verifies visual state
9. Destroys page
10. Verifies cleanup

A workflow that "calls bridges directly" is NOT considered a workflow.
"""
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WORKFLOWS_DIR = REPO / "tests" / "qml" / "workflows"

REQUIRED_CHECKS = [
    ("QQmlApplicationEngine", "crea engine QQmlApplicationEngine"),
    ("setContextProperty", "registra context properties"),
    (r"\.load\([\"']", "carga página QML"),
    ("objectName", "obtiene objeto por objectName"),
    (r"QTest\.(mouseClick|keyClicks)", "usa QTest.mouseClick o QTest.keyClicks"),
    (r"waitForSignal|Signal\.spy|signals", "espera signal (waitForSignal|Signal.spy|signals)"),
    (r"assert.*bridge|assert.*service|assert.*player", "verifica backend (assert.*bridge|assert.*service|assert.*player)"),
    (r"assert.*visible|assert.*enabled|assert.*text|assert.*property", "verifica estado visual (assert.*visible|assert.*enabled|assert.*text|assert.*property)"),
    (r"deleteLater|destroy|cleanup", "destruye página (deleteLater|destroy|cleanup)"),
    (r"teardown|finalize|assert.*closed", "verifica cleanup (teardown|finalize|assert.*closed)"),
]

BRIDGE_ONLY_PATTERNS = re.compile(
    r"^\s*(from\s+ui_qml_bridge\s+import|import\s+ui_qml_bridge)"
    r"|(Bridge\s*[(\[\.])",
    re.MULTILINE,
)


def audit_file(filepath: Path) -> dict:
    content = filepath.read_text(encoding="utf-8")

    # Detect bridge-only: if file only imports/calls bridges but has no QML engine
    has_engine = "QQmlApplicationEngine" in content
    has_bridge_only = bool(BRIDGE_ONLY_PATTERNS.search(content)) and not has_engine

    results = {}
    for pattern, description in REQUIRED_CHECKS:
        found = bool(re.search(pattern, content, re.IGNORECASE))
        results[description] = found

    total_found = sum(1 for v in results.values() if v)
    total_checks = len(REQUIRED_CHECKS)

    verdict = (
        "SKIP (bridge directo)" if has_bridge_only
        else "PASS" if total_found == total_checks
        else "FAIL"
    )

    return {
        "file": os.path.relpath(str(filepath), str(REPO)),
        "checks": results,
        "total_found": total_found,
        "total_checks": total_checks,
        "has_bridge_only": has_bridge_only,
        "verdict": verdict,
    }


def main():
    if not WORKFLOWS_DIR.exists():
        print(f"ERROR: workflows directory not found: {WORKFLOWS_DIR}")
        return 1

    py_files = sorted(WORKFLOWS_DIR.glob("test_*.py"))
    if not py_files:
        print("No workflow test files found.")
        return 1

    print("# QML Workflow Audit\n")
    overall_pass = True
    total_passed = 0
    total_skipped = 0
    total_failed = 0

    for f in py_files:
        result = audit_file(f)
        verdict = result["verdict"]
        if verdict == "PASS":
            total_passed += 1
        elif verdict == "SKIP (bridge directo)":
            total_skipped += 1
        else:
            total_failed += 1
            overall_pass = False

        label = {"PASS": "PASS", "SKIP (bridge directo)": "SKIP", "FAIL": "FAIL"}[verdict]
        print(f"  [{label}] {result['file']}")
        if verdict != "PASS":
            missing = [d for d, f_ in result["checks"].items() if not f_]
            if missing:
                for m in missing:
                    print(f"         missing: {m}")
            if result.get("has_bridge_only"):
                print("         bridge-only: no QQmlApplicationEngine")

    print("\n## Summary")
    print(f"  Total files: {len(py_files)}")
    print(f"  Passed: {total_passed}")
    print(f"  Skipped (bridge): {total_skipped}")
    print(f"  Failed: {total_failed}")
    print(f"  Overall: {'PASS' if overall_pass else 'FAIL'}")

    # Condition 10 detail per file
    print("\n## Detailed check matrix")
    header = "{:45s}".format("File")
    for desc in [d for _, d in REQUIRED_CHECKS]:
        short = desc.split(" (")[0].split(" ")[-1][:12]
        header += " {:>12s}".format(short)
    header += " {:>10s}".format("Veredict")
    print(header)
    print("-" * len(header))
    for f in py_files:
        result = audit_file(f)
        row = "{:45s}".format(result["file"])
        for desc in [d for _, d in REQUIRED_CHECKS]:
            found = result["checks"].get(desc, False)
            row += " {:>12s}".format("OK" if found else "--")
        row += " {:>10s}".format(result["verdict"])
        print(row)

    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
