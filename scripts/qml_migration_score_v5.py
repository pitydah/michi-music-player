#!/usr/bin/env python3
"""QML Migration Score V5 — from config weights, evidence, and manifest."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONFIG_FILE = REPO / "config" / "qml_migration_dimensions.json"
MANIFEST = REPO / "docs" / "qml_migration_manifest_v5.json"
EVIDENCE_FILE = REPO / "artifacts" / "qml-evidence-v5.json"


def load_config() -> dict:
    return json.loads(CONFIG_FILE.read_text())


def load_evidence() -> dict:
    if EVIDENCE_FILE.exists():
        return json.loads(EVIDENCE_FILE.read_text())
    return {"testcases": []}


def score_module(evidence: dict) -> float:
    test_count = evidence.get("test_count", 0) or 0
    passed = evidence.get("passed_count", 0) or 0
    if test_count == 0:
        return 0.0
    return min(100.0, (passed / test_count) * 100.0)


def main() -> int:
    if not MANIFEST.exists():
        print("ERROR: manifest not found")
        return 1

    config = load_config()
    manifest = json.loads(MANIFEST.read_text())

    dim_weights = config["dimension_weights"]
    area_weights = config["area_weights"]
    dim_total = sum(dim_weights.values())  # noqa: F841

    excluded = manifest.get("excluded", [])  # noqa: F841

    modules = manifest.get("modules", [])

    area_scores = {}

    for mod in modules:
        area = mod["area"]
        weight = mod["module_weight"]
        ev = mod.get("evidence", {})
        s = score_module(ev)
        weighted = s * weight / 100.0
        area_scores[area] = area_scores.get(area, 0.0) + weighted

    print("# QML Migration Score V5\n")
    total = 0.0
    total_area_weight = 0

    for area, aw in sorted(area_weights.items(), key=lambda x: -x[1]):
        s = area_scores.get(area, 0.0)
        weighted = s * aw / 100.0
        total += weighted
        total_area_weight += aw
        print(f"  {area:25s}  {aw:3d}%  area_score={s:5.1f}  weighted={weighted:5.1f}")

    print(f"\n  {'TOTAL':25s}  {total_area_weight:3d}%  {'':8s}  score={total:5.1f}%")
    print(f"\nScore: {total:.1f}%")

    print("\n## Module breakdown\n")
    print(f"  {'Module':25s} {'Area':20s} {'Status':20s} {'Passed/Total':>12s} {'Score':>6s}")
    print("  " + "-" * 86)
    for mod in sorted(modules, key=lambda m: (-m.get("module_weight", 10), m["module"])):
        ev = mod.get("evidence", {})
        s = score_module(ev)
        p = ev.get("passed_count", 0)
        t = ev.get("test_count", 0)
        print(f"  {mod['module']:25s} {mod['area']:20s} {mod['status']:20s} {p}/{t:>5}  {s:5.1f}%")

    evidence = load_evidence()
    print("\n## Evidence summary")
    print(f"  Total evidence cases: {evidence.get('total_evidence', 0)}")
    print(f"  Marked tests: {evidence.get('marked_test_count', 0)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
