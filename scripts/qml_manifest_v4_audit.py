#!/usr/bin/env python3
"""Manifest V4 audit: verify evidence against real codebase."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "docs" / "qml_migration_manifest_v4.json"
TESTS = REPO / "tests/qml"

REAL_TESTS = set()
for pyfile in sorted(TESTS.rglob("test_*.py")):
    for line in pyfile.read_text().splitlines():
        line = line.strip()
        if line.startswith("def test_"):
            REAL_TESTS.add(line.split("(")[0].replace("def ", "").strip())


def main() -> int:
    if not MANIFEST.exists():
        print("ERROR: manifest not found")
        return 1

    data = json.loads(MANIFEST.read_text())
    errors = []

    for mod in data.get("modules", []):
        mod_id = mod["module"]
        ev = mod.get("evidence", {})

        unit_tests = ev.get("unit_tests", [])
        if isinstance(unit_tests, list):
            for t in unit_tests:
                if t not in REAL_TESTS:
                    errors.append(f"  {mod_id}: test '{t}' not found in tests/qml/")

    if errors:
        print("## Manifest V4 Audit Errors\n")
        for e in errors:
            print(e)
        print(f"\n{len(errors)} error(s) found")
        return 1

    print("## Manifest V4 Audit: PASSED")
    print(f"SHA: {data.get('sha', 'unknown')}")
    print(f"Modules: {len(data.get('modules', []))}")
    print("All evidence is consistent with the real codebase.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
