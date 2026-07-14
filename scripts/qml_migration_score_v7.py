#!/usr/bin/env python3
"""QML Migration Score V7 — normalized module scores with area weights."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "docs" / "qml_migration_manifest_v7.json"
EVIDENCE_FILE = REPO / "artifacts" / "qml-evidence-v7.json"


def compute_module_score(dimensions: dict[str, dict]) -> float:
    total_weight = 0
    weighted_sum = 0.0
    factor_map = {"PASSED": 1.0, "FAILED": 0.0, "NOT_APPLICABLE": 1.0}
    for dim_val in dimensions.values():
        weight = dim_val.get("weight", 0)
        status = dim_val.get("status", "NOT_APPLICABLE")
        factor = factor_map.get(status, 0.0)
        weighted_sum += weight * factor
        total_weight += weight
    if total_weight == 0:
        return 0.0
    return (weighted_sum / total_weight) * 100.0


def main() -> int:
    if not MANIFEST.exists():
        print("ERROR: manifest not found")
        return 1

    manifest = json.loads(MANIFEST.read_text())

    modules = manifest.get("modules", [])

    print("# QML Migration Score V7\n")
    print(f"{'Module':30s} {'Area':20s} {'Status':20s} {'Score':>6s}")
    print("  " + "-" * 80)

    total_score = 0.0
    total_module_weight = 0

    for mod in sorted(modules, key=lambda m: m["module"]):
        dims = mod.get("dimensions", {})
        score = compute_module_score(dims)
        mod_weight = mod.get("module_weight", 10)
        weighted = score * mod_weight / 100.0
        total_score += weighted
        total_module_weight += mod_weight
        print(f"  {mod['module']:30s} {mod.get('area', ''):20s} {mod['status']:20s} {score:5.1f}%")

    print(f"\n  TOTAL {'':30s} {'':20s} {'':20s} {total_score:5.1f}%  (sum weight={total_module_weight})")
    print(f"\n## Score V7: {total_score:.1f}%")

    evidence = {}
    if EVIDENCE_FILE.exists():
        evidence = json.loads(EVIDENCE_FILE.read_text())
    print("\n## Evidence summary")
    print(f"  Total evidence cases: {evidence.get('total_evidence', 0)}")
    print(f"  Global score: {evidence.get('global_score', 'N/A')}%")

    return 0


if __name__ == "__main__":
    sys.exit(main())
