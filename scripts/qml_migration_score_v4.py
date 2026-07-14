#!/usr/bin/env python3
"""QML Migration Score V4 — multidimensional, honest, from manifest + evidence."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "docs" / "qml_migration_manifest_v4.json"

DIM_WEIGHTS = {
    "page": 8, "bridge": 8, "service": 12, "read": 6,
    "primary_action": 12, "write": 8, "errors": 7,
    "async": 6, "cancel": 5,
    "unit_tests": 9, "integration_tests": 10, "runtime_test": 8, "physical": 1,
}

DIM_MAX = sum(DIM_WEIGHTS.values())


def score_module(evidence: dict) -> tuple[float, dict]:
    score = 0.0
    details = {}
    for dim, weight in DIM_WEIGHTS.items():
        val = evidence.get(dim, False)
        if isinstance(val, (bool, list)):
            if val:
                score += weight
                details[dim] = weight
            else:
                details[dim] = 0
        elif isinstance(val, (int, float)):
            if val > 0:
                score += weight
                details[dim] = weight
            else:
                details[dim] = 0
        else:
            details[dim] = 0
    return score, details


def main():
    if not MANIFEST.exists():
        print("ERROR: manifest not found")
        return 1

    data = json.loads(MANIFEST.read_text())
    area_weights = data.get("area_weights", {})
    modules = data.get("modules", [])

    area_scores = {}

    for mod in modules:
        area = mod["area"]
        weight = mod["module_weight"]
        ev = mod["evidence"]
        s, details = score_module(ev)
        weighted = s * weight / 100.0
        area_scores[area] = area_scores.get(area, 0.0) + weighted

    print("# QML Migration Score V4\n")
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
    print(f"  {'Module':25s} {'Area':20s} {'W':>3s} {'Score':>6s} {'Status':15s}")
    print("  " + "-" * 72)
    for mod in sorted(modules, key=lambda m: (-m["module_weight"], m["module"])):
        s, _ = score_module(mod["evidence"])
        print(f"  {mod['module']:25s} {mod['area']:20s} {mod['module_weight']:3d} {s:5.1f}% {mod['status']:15s}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
