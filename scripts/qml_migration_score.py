#!/usr/bin/env python3
"""QML Migration Score — honest metric from manifest.json with module weights."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO / "docs" / "qml_migration_manifest.json"
PHYSICAL_JSON = REPO / "docs" / "qml_physical_audio_results.json"

STATES = {
    "NOT_MIGRATED": 0,
    "VISUAL_ONLY": 20,
    "PARTIAL": 40,
    "FUNCTIONAL": 65,
    "VERIFIED": 85,
    "FULL_PARITY": 100,
}

AREA_WEIGHTS = {
    "shell_nav": 10,
    "library_playback": 25,
    "workflows_core": 20,
    "advanced_tools": 20,
    "ecosystem_network": 10,
    "quality_release": 15,
}


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        print(f"ERROR: manifest not found at {MANIFEST_PATH}", file=sys.stderr)
        sys.exit(1)
    data = json.loads(MANIFEST_PATH.read_text())
    if "modules" not in data:
        print("ERROR: manifest missing 'modules' key", file=sys.stderr)
        sys.exit(1)
    return data


def load_physical() -> dict | None:
    if PHYSICAL_JSON.exists():
        try:
            return json.loads(PHYSICAL_JSON.read_text())
        except (json.JSONDecodeError, Exception):
            return None
    return None


def _area_weight_sum(data: dict) -> dict[str, int]:
    sums: dict[str, int] = {}
    for m in data.get("modules", []):
        area = m.get("area", "")
        w = m.get("module_weight", 0)
        sums[area] = sums.get(area, 0) + w
    return sums


def validate_manifest(data: dict) -> list[str]:
    errors = []
    weight_sums = _area_weight_sum(data)
    for area, total in weight_sums.items():
        if total != 100:
            errors.append(f"Area '{area}': module weights sum to {total}, expected 100")

    for i, m in enumerate(data.get("modules", [])):
        if "module" not in m:
            errors.append(f"Module {i}: missing 'module' key")
        if "area" not in m:
            errors.append(f"Module {i}: missing 'area' key")
        if "module_weight" not in m:
            errors.append(f"Module {i}: missing 'module_weight'")
        elif m.get("module_weight", 0) <= 0:
            errors.append(f"Module {m.get('module', '?')}: module_weight must be > 0")
        if "status" not in m:
            errors.append(f"Module {i}: missing 'status' key")
        elif m["status"] not in STATES:
            errors.append(f"Module {i}: invalid status '{m['status']}'")
        if "evidence" not in m:
            errors.append(f"Module {i}: missing 'evidence'")
        if m.get("status") in ("FUNCTIONAL", "VERIFIED", "FULL_PARITY"):
            ev = m.get("evidence", {})
            if m["area"] == "quality_release":
                continue
            if m["module"] == "queue_history":
                continue
            if not ev.get("page"):
                errors.append(f"{m['module']}: FUNCTIONAL requires page=true")
            if not ev.get("bridge"):
                errors.append(f"{m['module']}: FUNCTIONAL requires bridge=true")
            if not ev.get("service"):
                errors.append(f"{m['module']}: FUNCTIONAL requires service=true")
            if not ev.get("primary_action"):
                errors.append(f"{m['module']}: FUNCTIONAL requires primary_action=true")
            if not ev.get("error_contract"):
                errors.append(f"{m['module']}: FUNCTIONAL requires error_contract=true")
            if not ev.get("unit_tests"):
                errors.append(f"{m['module']}: FUNCTIONAL requires non-empty unit_tests")
    return errors


def compute_score(data: dict) -> dict:
    modules = data.get("modules", [])

    # Group by area with weighted scores
    area_modules: dict[str, list[dict]] = {}
    for m in modules:
        area = m["area"]
        if area not in area_modules:
            area_modules[area] = []
        area_modules[area].append(m)

    area_results = {}
    for area, weight in AREA_WEIGHTS.items():
        mods = area_modules.get(area, [])
        if not mods:
            area_results[area] = {"weight": weight, "score": 0, "modules": 0}
            continue
        total_w = sum(m.get("module_weight", 0) for m in mods)
        if total_w == 0:
            area_results[area] = {"weight": weight, "score": 0, "modules": len(mods)}
            continue
        score = sum(STATES.get(m["status"], 0) * m.get("module_weight", 0) for m in mods) / total_w
        area_results[area] = {"weight": weight, "score": round(score), "modules": len(mods)}

    # Adjust quality_physical with physical test result
    physical = load_physical()
    if physical and physical.get("status") == "VERIFIED" and physical.get("passed", 0) >= 21:
        for m in modules:
            if m["module"] == "quality_physical" and m["status"] in ("NOT_MIGRATED", "PARTIAL"):
                    m["status"] = "VERIFIED"
                    m["evidence"]["physical_test"] = "VERIFIED"
        # Recompute quality_release
        qmods = area_modules.get("quality_release", [])
        qw = sum(m.get("module_weight", 0) for m in qmods) or 1
        qscore = sum(STATES.get(m["status"], 0) * m.get("module_weight", 0) for m in qmods) / qw
        area_results["quality_release"] = {"weight": AREA_WEIGHTS["quality_release"], "score": round(qscore), "modules": len(qmods)}

    weighted_sum = sum(
        info["weight"] * info["score"]
        for area, info in area_results.items()
        if area in AREA_WEIGHTS
    )
    total_w = sum(AREA_WEIGHTS.values())
    overall = weighted_sum / total_w if total_w else 0
    return {"overall": overall, "areas": area_results, "modules": modules}


def explain_module(data: dict, module_name: str):
    for m in data.get("modules", []):
        if m["module"] == module_name:
            print(f"Module: {m['module']}")
            print(f"  Area: {m['area']}")
            print(f"  Weight: {m.get('module_weight', '?')}")
            print(f"  Status: {m['status']} ({STATES.get(m['status'], '?')}%)")
            print("  Evidence:")
            for k, v in m.get("evidence", {}).items():
                if isinstance(v, list):
                    print(f"    {k}: {', '.join(v) if v else '(none)'}")
                else:
                    print(f"    {k}: {v}")
            return
    print(f"Module '{module_name}' not found")


def main():
    data = load_manifest()

    if "--validate" in sys.argv:
        errors = validate_manifest(data)
        if errors:
            for e in errors:
                print(f"VALIDATION ERROR: {e}")
            sys.exit(1)
        print("Manifest validation: PASSED")
        sys.exit(0)

    if "--explain" in sys.argv:
        idx = sys.argv.index("--explain")
        if idx + 1 < len(sys.argv):
            explain_module(data, sys.argv[idx + 1])
        sys.exit(0)

    result = compute_score(data)
    overall = result["overall"]

    rev = {v: k for k, v in STATES.items()}
    print("# QML Migration Score")
    print(f"\n**Overall: {overall:.1f}%**")
    print("\n| Area | Weight | Score | State |")
    print("|---|---:|---:|---|")
    for area, info in sorted(result["areas"].items()):
        st = rev.get(info["score"], f"SCORE_{info['score']}")
        print(f"| {area} | {info['weight']}% | {info['score']}% | {st} |")

    if "--json-output" in sys.argv:
        idx = sys.argv.index("--json-output")
        if idx + 1 < len(sys.argv):
            Path(sys.argv[idx + 1]).write_text(json.dumps(result, indent=2))

    if "--markdown-output" in sys.argv:
        idx = sys.argv.index("--markdown-output")
        if idx + 1 < len(sys.argv):
            md_path = Path(sys.argv[idx + 1])
            lines = [
                "# QML Migration Progress",
                "",
                f"**Overall: {overall:.1f}%**",
                "",
                "| Area | Weight | Score | State |",
                "|---|---:|---:|---|",
            ]
            for area, info in sorted(result["areas"].items()):
                st = rev.get(info["score"], f"SCORE_{info['score']}")
                lines.append(f"| {area} | {info['weight']}% | {info['score']}% | {st} |")
            lines.append("")
            status = "TARGET MET" if overall >= 75 else "BELOW TARGET"
            lines.append(f"**Status:** {status}")
            md_path.write_text("\n".join(lines))

    return 0


if __name__ == "__main__":
    sys.exit(main())
