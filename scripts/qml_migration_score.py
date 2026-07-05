#!/usr/bin/env python3
"""QML Migration Score — honest metric from manifest.json evidence.

Usage:
    python scripts/qml_migration_score.py
    python scripts/qml_migration_score.py --validate
    python scripts/qml_migration_score.py --json-output /tmp/score.json
    python scripts/qml_migration_score.py --markdown-output docs/QML_MIGRATION_PROGRESS.md
    python scripts/qml_migration_score.py --explain module_name
"""
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


def validate_manifest(data: dict) -> list[str]:
    errors = []
    for i, m in enumerate(data.get("modules", [])):
        if "module" not in m:
            errors.append(f"Module {i}: missing 'module' key")
        if "area" not in m:
            errors.append(f"Module {i}: missing 'area' key")
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
            if not ev.get("page"):
                errors.append(f"{m['module']}: FUNCTIONAL requires page=true")
            if not ev.get("bridge"):
                errors.append(f"{m['module']}: FUNCTIONAL requires bridge=true")
            if not ev.get("service"):
                errors.append(f"{m['module']}: FUNCTIONAL requires service=true")
    return errors


def compute_score(data: dict) -> dict:
    modules = data.get("modules", [])
    area_scores: dict[str, list[int]] = {}
    for m in modules:
        area = m["area"]
        if area not in area_scores:
            area_scores[area] = []
        area_scores[area].append(STATES.get(m["status"], 0))

    # Adjust quality_release with physical test
    physical = load_physical()
    if physical and physical.get("status") == "VERIFIED" and physical.get("passed", 0) >= 21 and "quality_release" in area_scores:
            area_scores["quality_release"] = [STATES["VERIFIED"]]

    area_results = {}
    weighted_sum = 0
    total_weight = 0
    for area, weight in AREA_WEIGHTS.items():
        scores = area_scores.get(area, [0])
        avg = round(sum(scores) / len(scores)) if scores else 0
        area_results[area] = {"weight": weight, "score": avg, "modules": len(scores)}
        weighted_sum += weight * avg
        total_weight += weight

    overall = weighted_sum / total_weight if total_weight else 0
    return {"overall": overall, "areas": area_results, "modules": modules}


def explain_module(data: dict, module_name: str):
    for m in data.get("modules", []):
        if m["module"] == module_name:
            print(f"Module: {m['module']}")
            print(f"  Area: {m['area']}")
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

    # Print
    print("# QML Migration Score")
    print(f"\n**Overall: {overall:.1f}%**")
    print("\n| Area | Weight | Score | State |")
    print("|---|---:|---:|---|")
    rev = {v: k for k, v in STATES.items()}
    for area, info in sorted(result["areas"].items()):
        st = rev.get(info["score"], f"SCORE_{info['score']}")
        print(f"| {area} | {info['weight']}% | {info['score']}% | {st} |")

    # JSON output
    if "--json-output" in sys.argv:
        idx = sys.argv.index("--json-output")
        if idx + 1 < len(sys.argv):
            Path(sys.argv[idx + 1]).write_text(json.dumps(result, indent=2))

    # Markdown output
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
            lines.append("**Baseline:** 64%")
            lines.append("**Target:** 75%")
            lines.append(f"**Status:** {'✅ TARGET MET' if overall >= 75 else '❌ BELOW TARGET'}")
            md_path.write_text("\n".join(lines))

    return 0


if __name__ == "__main__":
    sys.exit(main())
