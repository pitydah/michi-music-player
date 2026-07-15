#!/usr/bin/env python3
"""QML Migration Score V9 — normalizado.

Score por módulo = peso_aprobado / peso_aplicable * 100.
  - peso_aprobado: suma de pesos de markers con status PASSED
  - peso_aplicable: suma de pesos de markers con status distinto de NOT_APPLICABLE_DECLARED

Global = sum(score_módulo × weight_módulo) / sum(weight_módulo)
Siempre 0-100.

NO premia: test count, archivo presente, class presente, helper marcado.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "docs" / "qml_migration_manifest_v9.json"
EVIDENCE_FILE = REPO / "artifacts" / "qml-evidence-v9.json"

SCORE_MAP = {
    "PASSED": 1.0,
    "FAILED": 0.0,
    "MISSING": 0.0,
    "NOT_APPLICABLE_DECLARED": 1.0,
    "DEFERRED_PHYSICAL": 1.0,
}


def module_normalized_score(mod: dict) -> tuple[float, float, float]:
    markers = mod.get("markers", {})
    total_applicable_weight = 0
    total_approved_weight = 0
    for minfo in markers.values():
        mw = minfo.get("weight", 0)
        status = minfo.get("status", "MISSING")
        if status == "NOT_APPLICABLE_DECLARED":
            continue
        total_applicable_weight += mw
        total_approved_weight += mw * SCORE_MAP.get(status, 0.0)
    score = (total_approved_weight / total_applicable_weight * 100) if total_applicable_weight > 0 else 100.0
    return round(score, 1), float(total_approved_weight), float(total_applicable_weight)


def main():
    if not MANIFEST.exists():
        print("ERROR: manifest not found")
        return 1

    manifest = json.loads(MANIFEST.read_text())
    modules = manifest.get("modules", [])

    print("# QML Migration Score V9 (normalizado)\n")
    print(f"{'Module':30s} {'Weight':>6s} {'Score':>6s}  {'Aprob/ Apl':>10s}")
    print("  " + "-" * 54)

    total_weighted_score = 0.0
    total_module_weight = 0

    for mod in sorted(modules, key=lambda m: m["module"]):
        weight = int(mod.get("weight", 10))
        score, approved_w, applicable_w = module_normalized_score(mod)
        total_weighted_score += score * weight / 100.0
        total_module_weight += weight
        print(f"  {mod['module']:30s} {weight:5d}  {score:5.1f}%  {int(approved_w):3d}/{int(applicable_w):<3d}")

    global_score = (total_weighted_score / total_module_weight * 100) if total_module_weight > 0 else 0.0
    print(f"\n  {'TOTAL':30s} {'':6s} {global_score:5.1f}%  (sum_weight={total_module_weight})")
    print(f"\n## Score V9: {global_score:.1f}%")

    print("\n## Module details (normalized)")
    for mod in sorted(modules, key=lambda m: -int(m.get("weight", 10))):
        score, approved_w, applicable_w = module_normalized_score(mod)
        markers = mod.get("markers", {})
        statuses = {k: v["status"] for k, v in markers.items()}
        marker_weights = {k: int(v.get("weight", 0)) for k, v in markers.items()}
        print(f"  {mod['module']:25s} w={int(mod.get('weight', 10)):2d} score={score:5.1f}% "
              f"aprob={int(approved_w)}/{int(applicable_w)} markers={statuses} mw={marker_weights}")

    if EVIDENCE_FILE.exists():
        evidence = json.loads(EVIDENCE_FILE.read_text())
        total = evidence.get("total_evidence", 0)
        passed = evidence.get("passed", 0)
        failed = evidence.get("failed", 0)
        skipped = evidence.get("skipped", 0)
        print("\n## Evidence summary")
        print(f"  Total evidence cases: {total}")
        print(f"  Passed: {passed}")
        print(f"  Failed: {failed}")
        print(f"  Skipped: {skipped}")
        marked = sum(1 for tc in evidence.get("testcases", []) if tc.get("module") or tc.get("dimension") or tc.get("route"))
        print(f"  Marked tests: {marked}")
    else:
        print("\n## Evidence file not found")

    return 0


if __name__ == "__main__":
    sys.exit(main())
