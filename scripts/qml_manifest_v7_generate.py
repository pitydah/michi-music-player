#!/usr/bin/env python3
"""Generate QML manifest V7 from config and evidence."""
import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONFIG = REPO / "config" / "qml_modules.yaml"
EVIDENCE = REPO / "artifacts" / "qml-evidence-v7.json"
OUT = REPO / "docs" / "qml_migration_manifest_v7.json"


def load_yaml(p):
    try:
        import yaml
        return yaml.safe_load(p.read_text())
    except Exception:
        return json.loads(p.read_text())


def compute_composite(score: float, dims: dict) -> str:
    if score >= 95 and all(d.get("status") == "PASSED" for d in dims.values()):
        return "PARITY"
    if score >= 80:
        has_primary = any("primary_action" in k for k in dims)
        has_integration = any("integration" in k for k in dims)
        if has_primary and has_integration:
            return "PRODUCTIVE"
        return "PARTIAL_WORKFLOW"
    if score >= 40:
        return "READ_ONLY"
    if score >= 20:
        return "COMPILES"
    return "SCAFFOLDED"


def main():
    cfg = load_yaml(CONFIG)
    evidence = {}
    if EVIDENCE.exists():
        evidence = json.loads(EVIDENCE.read_text())

    modules = []
    for mod in cfg.get("modules", []):
        ev_mod = next((m for m in evidence.get("modules", []) if m["module"] == mod["module"]), {})
        score = ev_mod.get("score", 0)
        dims = ev_mod.get("dimensions", {})
        status = compute_composite(score, dims)
        modules.append({
            "module": mod["module"],
            "area": mod["area"],
            "module_weight": mod["module_weight"],
            "score": score,
            "status": status,
            "dimensions": {k: v["status"] for k, v in dims.items()},
            "widget_replacement": mod.get("widget_replacement", {}),
            "deferred": mod.get("deferred", False),
            "deferred_reason": mod.get("deferred_reason", ""),
        })

    manifest = {
        "version": "7.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sha": evidence.get("sha", ""),
        "dimension_weights": cfg.get("dimension_weights", {}),
        "area_weights": cfg.get("area_weights", {}),
        "score": evidence.get("score", 0),
        "area_scores": evidence.get("area_scores", {}),
        "modules": modules,
        "total_tests": evidence.get("total_tests", 0),
        "passed_tests": evidence.get("passed_tests", 0),
    }
    OUT.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(f"Manifest V7 written to {OUT}")
    print(f"Score: {manifest['score']}%  Modules: {len(modules)}")


if __name__ == "__main__":
    main()
