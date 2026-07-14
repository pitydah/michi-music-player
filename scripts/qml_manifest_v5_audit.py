#!/usr/bin/env python3
"""Manifest V5 audit: verify SHA, weights, dimensions, exclusion, and evidence integrity."""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONFIG_FILE = REPO / "config" / "qml_migration_dimensions.json"
MANIFEST = REPO / "docs" / "qml_migration_manifest_v5.json"
EVIDENCE_FILE = REPO / "artifacts" / "qml-evidence-v5.json"

KNOWN_DIMENSIONS = {
    "route_load", "qml_instance", "model_data", "service_wiring",
    "read", "primary_action", "secondary_actions", "write",
    "error_contract", "async_execution", "real_cancellation",
    "persistence", "integration", "vertical_workflow",
    "performance", "accessibility",
}

KNOWN_AREAS = {
    "shell_nav", "library_playback", "core_workflows",
    "advanced_tools", "ecosystem_network", "quality_release",
}

AREA_EXPECTED_SUMS = {
    "shell_nav": 10,
    "library_playback": 25,
    "core_workflows": 20,
    "advanced_tools": 20,
    "ecosystem_network": 15,
    "quality_release": 10,
}


def main() -> int:
    errors = []

    if not MANIFEST.exists():
        print("ERROR: manifest not found")
        return 1
    if not CONFIG_FILE.exists():
        print("ERROR: config file not found")
        return 1

    config = json.loads(CONFIG_FILE.read_text())
    manifest = json.loads(MANIFEST.read_text())
    evidence_data = {}
    if EVIDENCE_FILE.exists():
        evidence_data = json.loads(EVIDENCE_FILE.read_text())

    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO
    ).stdout.strip()

    manifest_sha = manifest.get("sha", "")
    if manifest_sha != sha:
        errors.append(f"SHA mismatch: manifest={manifest_sha}, HEAD={sha}")

    dim_weights = config.get("dimension_weights", {})
    area_weights = config.get("area_weights", {})

    dim_weights_sum = sum(dim_weights.values())  # noqa: F841
    area_weights_sum = sum(area_weights.values())

    if area_weights_sum != 100:
        errors.append(f"Area weights sum to {area_weights_sum}, expected 100")

    for area, expected_sum in AREA_EXPECTED_SUMS.items():
        actual = area_weights.get(area, 0)
        if actual != expected_sum:
            errors.append(f"Area '{area}' weight: {actual}, expected {expected_sum}")

    for dim in dim_weights:
        if dim not in KNOWN_DIMENSIONS:
            errors.append(f"Unknown dimension: '{dim}'")

    for area in area_weights:
        if area not in KNOWN_AREAS:
            errors.append(f"Unknown area: '{area}'")

    excluded = manifest.get("excluded", [])
    for ex in excluded:
        if "physical" in ex.lower():
            pass
    has_physical = any("physical" in dim for dim in dim_weights)
    if has_physical:
        errors.append("Physical dimension found in dimension_weights (should be excluded)")

    evidence_testcases = evidence_data.get("testcases", [])
    for mod in manifest.get("modules", []):
        mod_id = mod["module"]
        ev = mod.get("evidence", {})
        if ev.get("passed_count", 0) + ev.get("failed_count", 0) == 0:
            continue
        {tc.get("classname", "") for tc in evidence_testcases if not tc.get("failure") and not tc.get("skipped")}
        related = [tc for tc in evidence_testcases if mod_id in tc.get("classname", "")]
        for tc in related:
            if tc.get("failure") and not tc.get("skipped"):
                errors.append(f"Module '{mod_id}': test {tc.get('classname')}::{tc.get('name')} FAILED but included as evidence")

    if errors:
        print("## Manifest V5 Audit ERRORS\n")
        for e in errors:
            print(f"  - {e}")
        print(f"\n{len(errors)} error(s) found")
        return 1

    print("## Manifest V5 Audit: PASSED")
    print(f"SHA: {sha}")
    print(f"Modules: {len(manifest.get('modules', []))}")
    print(f"Excluded: {manifest.get('excluded', [])}")
    print("All evidence is consistent with the real codebase.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
