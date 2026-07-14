#!/usr/bin/env python3
"""Display QML Migration Score V7 from manifest."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "docs" / "qml_migration_manifest_v7.json"


def main():
    if not MANIFEST.exists():
        print("ERROR: manifest not found (run qml_manifest_v7_generate.py first)")
        return 1
    m = json.loads(MANIFEST.read_text())
    aw = m.get("area_weights", {})
    modules = m.get("modules", [])

    print("# QML Migration Score V7\n")
    area_scores = {}
    for mod in modules:
        if mod.get("deferred"):
            continue
        area = mod["area"]
        area_scores[area] = area_scores.get(area, 0) + mod["score"] * mod["module_weight"] / 100.0

    total = 0
    total_area_weight = 0
    for area, weight in sorted(aw.items(), key=lambda x: -x[1]):
        s = area_scores.get(area, 0)
        contrib = s * weight / 100.0
        total += contrib
        total_area_weight += weight
        print(f"  {area:25s}  {weight:3d}%  area_score={s:6.1f}  weighted={contrib:6.1f}")

    print(f"\n  {'TOTAL':25s}  {total_area_weight:3d}%  {'':8s}  score={total:6.1f}%")
    print(f"\nScore: {total:.1f}%\n")

    print(f"  {'Module':25s} {'Area':20s} {'W':>3s} {'Score':>6s} {'Status':15s}")
    print("  " + "-" * 72)
    for mod in sorted(modules, key=lambda m: (-m.get("module_weight", 0), m["module"])):
        status = mod.get("status", "UNKNOWN")
        if mod.get("deferred"):
            status = "DEFERRED"
        print(f"  {mod['module']:25s} {mod['area']:20s} {mod['module_weight']:3d} {mod['score']:5.1f}% {status:15s}")
    return 0


if __name__ == "__main__":
    exit(main())
