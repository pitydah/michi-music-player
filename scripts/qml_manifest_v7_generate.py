#!/usr/bin/env python3
"""QML Manifest V7 Generator — dimensions, module scores, composite statuses from V7 evidence."""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ARTIFACTS = REPO / "artifacts"
EVIDENCE_FILE = ARTIFACTS / "qml-evidence-v7.json"
MANIFEST_PATH = REPO / "docs" / "qml_migration_manifest_v7.json"


def load_evidence() -> dict:
    if not EVIDENCE_FILE.exists():
        return {"modules": [], "global_score": 0}
    return json.loads(EVIDENCE_FILE.read_text())


def main() -> int:
    evidence = load_evidence()

    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO
    ).stdout.strip()

    manifest = {
        "version": "7.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sha": sha,
        "global_score": evidence.get("global_score", 0),
        "modules": evidence.get("modules", []),
    }

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"Manifest V7 written to {MANIFEST_PATH}")
    print(f"SHA: {sha}")
    print(f"Modules: {len(manifest['modules'])}")
    print(f"Global score V7: {manifest['global_score']:.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
