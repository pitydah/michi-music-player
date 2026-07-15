#!/usr/bin/env python3
"""Generate QML Manifest V11 from evidence."""
import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "artifacts" / "qml-evidence-v11.json"
CONFIG = REPO / "config" / "qml_modules.yaml"
OUT = REPO / "docs" / "qml_migration_manifest_v11.json"


def load_yaml(p):
    try:
        import yaml
        return yaml.safe_load(p.read_text())
    except Exception:
        return json.loads(p.read_text())


def compute_composite(score):
    if score >= 95:
        return "PARITY"
    if score >= 80:
        return "PRODUCTIVE"
    if score >= 60:
        return "PARTIAL_WORKFLOW"
    if score >= 40:
        return "READ_ONLY"
    if score >= 20:
        return "COMPILES"
    return "SCAFFOLDED"


def main():
    cfg = load_yaml(CONFIG)
    evidence = json.loads(EVIDENCE.read_text()) if EVIDENCE.exists() else {}
    modules = []
    for mc in cfg.get("modules", []):
        name = mc["module"]
        ev = evidence.get("modules", {}).get(name, {})
        score = ev.get("score", 0)
        modules.append({
            "module": name,
            "area": mc.get("area", ""),
            "weight": mc.get("module_weight", 10),
            "score": score,
            "status": compute_composite(score),
            "dimensions": {k: v["status"] for k, v in ev.get("dimensions", {}).items()},
            "deferred": mc.get("deferred", False),
        })

    manifest = {
        "version": "11.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sha": evidence.get("sha", ""),
        "score": evidence.get("score", 0),
        "area_scores": evidence.get("area_scores", {}),
        "modules": modules,
        "total_tests": evidence.get("total_tests", 0),
    }
    OUT.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(f"Manifest V11 written to {OUT}")
    print(f"Score: {manifest['score']}%")


if __name__ == "__main__":
    main()
