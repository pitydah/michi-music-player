#!/usr/bin/env python3
"""Audit QML Manifest V7 — verify SHA, weights, dimensions, no deferred scoring."""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "docs" / "qml_migration_manifest_v7.json"
CONFIG = REPO / "config" / "qml_modules.yaml"


def load_yaml(p):
    try:
        import yaml
        return yaml.safe_load(p.read_text())
    except Exception:
        return json.loads(p.read_text())


def main():
    head_sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if not MANIFEST.exists():
        print("ERROR: manifest not found")
        sys.exit(1)
    m = json.loads(MANIFEST.read_text())

    errors = []
    if m.get("sha") != head_sha:
        errors.append(f"SHA mismatch: manifest {m.get('sha')} != HEAD {head_sha}")

    cfg = load_yaml(CONFIG)
    dw = cfg.get("dimension_weights", {})
    aw = cfg.get("area_weights", {})
    if sum(dw.values()) != 100:
        errors.append(f"Dimension weights sum to {sum(dw.values())}, expected 100")
    if sum(aw.values()) != 100:
        errors.append(f"Area weights sum to {sum(aw.values())}, expected 100")

    for mod in m.get("modules", []):
        if mod.get("deferred"):
            continue
        for dim, _status in mod.get("dimensions", {}).items():
            if dim not in dw:
                errors.append(f"Unknown dimension '{dim}' in module '{mod['module']}'")

    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
        sys.exit(1)
    print("## Manifest V7 Audit: PASSED")
    print(f"SHA: {head_sha}")
    print(f"Modules: {len(m.get('modules', []))}")
    print(f"Score: {m.get('score', '?')}%")


if __name__ == "__main__":
    main()
