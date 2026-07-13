#!/usr/bin/env python3
"""Manifest V2 audit: verify evidence against real codebase."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "docs" / "qml_migration_manifest_v2.json"
UI_QML = REPO / "ui_qml"
BRIDGE = REPO / "ui_qml_bridge"
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
        ev = mod["evidence"]

        # Check page exists (relaxed matching)
        if ev.get("page"):
            variants = [mod_id, mod_id.replace("_", ""), mod_id.replace("_", " ").title().replace(" ", ""),
                         mod_id.split("_")[0], mod_id.split("_")[-1]]
            page_found = any(
                any(v.lower() in qml_file.stem.lower() for v in variants)
                for qml_file in UI_QML.rglob("*.qml")
            )
            if not page_found:
                errors.append(f"[{mod_id}] page=True but no matching .qml file found")

        # Check bridge exists (relaxed matching)
        if ev.get("bridge"):
            variants = [mod_id, mod_id.replace("_", ""), mod_id.replace("_bridge", "")]
            bridge_found = any(
                any(v.lower() in f.stem.lower() for v in variants)
                for f in BRIDGE.glob("*.py") if f.name != "__init__.py"
            )
            if not bridge_found:
                errors.append(f"[{mod_id}] bridge=True but no matching bridge file found")

        # Check test names exist
        for t in ev.get("unit_tests", []):
            if t not in REAL_TESTS:
                errors.append(f"[{mod_id}] test '{t}' declared but not found")

        # Check async/cancel claims
        if ev.get("async") and not ev.get("service"):
            errors.append(f"[{mod_id}] async=True but service=False")
        if ev.get("cancel") and not ev.get("async"):
            errors.append(f"[{mod_id}] cancel=True but async=False")

        # Check FUNCTIONAL has action or service
        if mod["status"] == "FUNCTIONAL" and not ev.get("primary_action") and not ev.get("service"):
            errors.append(f"[{mod_id}] FUNCTIONAL but no primary_action or service")

    # Verify area weights
    area_weights = data.get("area_weights", {})
    if abs(sum(area_weights.values()) - 100) > 1:
        errors.append(f"area_weights sum={sum(area_weights.values())}, expected 100")

    if errors:
        print("## Manifest V2 Audit\n")
        print(f"**Errors: {len(errors)}**\n")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("## Manifest V2 Audit\n")
    print(f"**All checks passed: {len(data['modules'])} modules, "
          f"{sum(len(m['evidence']['unit_tests']) for m in data['modules'])} tests verified**")
    return 0


if __name__ == "__main__":
    sys.exit(main())
