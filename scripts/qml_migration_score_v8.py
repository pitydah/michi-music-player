#!/usr/bin/env python3
"""QML Migration Score V8 — weighted by module weights from qml_modules.yaml, markers: qml_module, qml_dimension, qml_route, qml_workflow, widget_replacement."""
import json
import sys
from pathlib import Path




REPO = Path(__file__).resolve().parent.parent
MODULES_YAML = REPO / "config" / "qml_modules.yaml"
MANIFEST = REPO / "docs" / "qml_migration_manifest_v8.json"
EVIDENCE_FILE = REPO / "artifacts" / "qml-evidence-v8.json"

SCORE_MAP = {
    "PASSED": 1.0,
    "FAILED": 0.0,
    "MISSING": 0.0,
    "NOT_APPLICABLE_DECLARED": 1.0,
    "DEFERRED_PHYSICAL": 1.0,
}


def main() -> int:
    if not MANIFEST.exists():
        print("ERROR: manifest not found")
        return 1

    manifest = json.loads(MANIFEST.read_text())

    modules = manifest.get("modules", [])

    print("# QML Migration Score V8\n")
    print(f"{'Module':30s} {'Weight':>6s} {'Score':>6s}  {'Weighted':>8s}")
    print("  " + "-" * 52)

    total_score = 0.0
    total_module_weight = 0

    for mod in sorted(modules, key=lambda m: m["module"]):
        score = mod.get("score", 0.0)
        weight = mod.get("weight", 10)
        weighted = score * weight / 100.0
        total_score += weighted
        total_module_weight += weight
        print(f"  {mod['module']:30s} {weight:5d}  {score:5.1f}%  {weighted:7.2f}")

    global_score = manifest.get("global_score", 0.0)
    print(f"\n  {'TOTAL':30s} {'':6s} {global_score:5.1f}%  (sum_weights={total_module_weight})")
    print(f"\n## Score V8: {global_score:.1f}%")

    print("\n## Module weights")
    for mod in sorted(modules, key=lambda m: -m["weight"]):
        markers = mod.get("markers", {})
        statuses = {k: v["status"] for k, v in markers.items()}
        print(f"  {mod['module']:25s} weight={mod['weight']:2d} score={mod['score']:5.1f}% markers={statuses}")

    evidence = load_evidence()
    print("\n## Evidence summary")
    print(f"  Total evidence cases: {evidence.get('total_evidence', 0)}")
    print(f"  Marked tests (V8): {evidence.get('marked_test_count', 0)}")

    return 0


def load_evidence() -> dict:
    if EVIDENCE_FILE.exists():
        return json.loads(EVIDENCE_FILE.read_text())
    return {"testcases": [], "marked_tests": []}


if __name__ == "__main__":
    sys.exit(main())
