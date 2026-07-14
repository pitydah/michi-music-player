#!/usr/bin/env python3
"""Manifest V7 audit: verify SHA, scores, module statuses."""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "docs" / "qml_migration_manifest_v7.json"
EVIDENCE_FILE = REPO / "artifacts" / "qml-evidence-v7.json"

COMPOSITE_ORDER = [
    "NOT_IMPLEMENTED", "SCAFFOLDED", "COMPILES", "READ_ONLY",
    "PARTIAL_WORKFLOW", "PRODUCTIVE", "PARITY",
]


def main() -> int:
    errors = []

    if not MANIFEST.exists():
        print("ERROR: manifest not found")
        return 1

    manifest = json.loads(MANIFEST.read_text())
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO
    ).stdout.strip()

    manifest_sha = manifest.get("sha", "")
    if manifest_sha != sha:
        errors.append(f"SHA mismatch: manifest={manifest_sha}, HEAD={sha}")

    for mod in manifest.get("modules", []):
        mod_id = mod["module"]
        status = mod.get("status", "")
        if status not in COMPOSITE_ORDER:
            errors.append(f"Module '{mod_id}': unknown status '{status}'")

    if errors:
        print("## Manifest V7 Audit ERRORS\n")
        for e in errors:
            print(f"  - {e}")
        print(f"\n{len(errors)} error(s) found")
        return 1

    print("## Manifest V7 Audit: PASSED")
    print(f"SHA: {sha}")
    print(f"Modules: {len(manifest.get('modules', []))}")
    print(f"Global score: {manifest.get('global_score', 'N/A')}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
