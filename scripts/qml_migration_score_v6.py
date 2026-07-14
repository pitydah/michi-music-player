#!/usr/bin/env python3
"""QML Migration Score V6 — weighted by dimension weights from config, with penalties."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONFIG_FILE = REPO / "config" / "qml_migration_dimensions.json"
MANIFEST = REPO / "docs" / "qml_migration_manifest_v6.json"
EVIDENCE_FILE = REPO / "artifacts" / "qml-evidence-v6.json"

PENALTY_MAP = {
    "FAILED": 0.0,
    "MISSING": 0.0,
    "NOT_APPLICABLE": 1.0,
    "PASSED": 1.0,
}


def load_config() -> dict:
    return json.loads(CONFIG_FILE.read_text())


def load_evidence() -> dict:
    if EVIDENCE_FILE.exists():
        return json.loads(EVIDENCE_FILE.read_text())
    return {"testcases": []}


def compute_module_score(dimensions: dict[str, dict]) -> float:
    total_weight = 0
    weighted_sum = 0.0
    for dim_val in dimensions.values():
        weight = dim_val.get("weight", 0)
        status = dim_val.get("status", "NOT_APPLICABLE")
        factor = PENALTY_MAP.get(status, 0.0)
        weighted_sum += weight * factor
        total_weight += weight
    if total_weight == 0:
        return 0.0
    return (weighted_sum / total_weight) * 100.0


def main() -> int:
    if not MANIFEST.exists():
        print("ERROR: manifest not found")
        return 1

    config = load_config()
    manifest = json.loads(MANIFEST.read_text())

    dim_weights = config["dimension_weights"]

    modules = manifest.get("modules", [])

    print("# QML Migration Score V6\n")
    print(f"{'Module':30s} {'Status':20s} {'Score':>6s}  {'Weighted':>8s}")
    print("  " + "-" * 68)

    total_score = 0.0
    total_module_weight = 0

    for mod in sorted(modules, key=lambda m: m["module"]):
        dims = mod.get("dimensions", {})
        score = compute_module_score(dims)
        mod_weight = sum(d.get("weight", 0) for d in dims.values())
        weighted = score * mod_weight / 100.0
        total_score += weighted
        total_module_weight += mod_weight
        print(f"  {mod['module']:30s} {mod['status']:20s} {score:5.1f}%  {weighted:7.1f}")

    print(f"\n  {'TOTAL':30s} {'':20s} {total_score:5.1f}%  (sum={total_module_weight})")
    print(f"\n## Score V6: {total_score:.1f}%")

    print("\n## Dimension weight summary")
    for dim, w in sorted(dim_weights.items(), key=lambda x: -x[1]):
        print(f"  {dim:25s} weight={w}")

    evidence = load_evidence()
    print("\n## Evidence summary")
    print(f"  Total evidence cases: {evidence.get('total_evidence', 0)}")
    print(f"  Marked tests: {evidence.get('marked_test_count', 0)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
