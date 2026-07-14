#!/usr/bin/env python3
"""Manifest V6 audit: verify SHA, weights, dimensions, composite statuses — no physical."""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONFIG_FILE = REPO / "config" / "qml_migration_dimensions.json"
MANIFEST = REPO / "docs" / "qml_migration_manifest_v6.json"
EVIDENCE_FILE = REPO / "artifacts" / "qml-evidence-v6.json"

KNOWN_DIMENSIONS = {
    "route_load", "qml_instance", "model_data", "service_wiring",
    "read", "primary_action", "secondary_actions", "write",
    "error_contract", "async_execution", "real_cancellation",
    "persistence", "integration", "vertical_workflow",
    "performance", "accessibility",
}

COMPOSITE_ORDER = [
    "NOT_IMPLEMENTED", "SCAFFOLDED", "COMPILES", "READ_ONLY",
    "PARTIAL_WORKFLOW", "PRODUCTIVE", "PARITY",
]


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
    manifest_dim_weights = manifest.get("dimension_weights", {})

    if dim_weights != manifest_dim_weights:
        errors.append("Manifest dimension_weights do not match config")

    for dim in dim_weights:
        if dim not in KNOWN_DIMENSIONS:
            errors.append(f"Unknown dimension in config: '{dim}'")

    for dim in KNOWN_DIMENSIONS:
        if dim not in dim_weights:
            errors.append(f"Missing dimension in config: '{dim}'")

    has_physical = any("physical" in dim for dim in dim_weights)
    if has_physical:
        errors.append("Physical dimension found in dimension_weights (should be excluded)")

    evidence_testcases = evidence_data.get("testcases", [])

    for mod in manifest.get("modules", []):
        mod_id = mod["module"]
        dims = mod.get("dimensions", {})
        status = mod.get("status", "")

        if status not in COMPOSITE_ORDER:
            errors.append(f"Module '{mod_id}': unknown status '{status}'")

        for dim_name, dim_val in dims.items():
            if dim_name not in KNOWN_DIMENSIONS:
                errors.append(f"Module '{mod_id}': unknown dimension '{dim_name}'")
            ds = dim_val.get("status")
            if ds not in ("PASSED", "FAILED", "MISSING", "NOT_APPLICABLE"):
                errors.append(f"Module '{mod_id}', dim '{dim_name}': invalid status '{ds}'")
            dw = dim_val.get("weight", 0)
            expected_w = dim_weights.get(dim_name, 0)
            if dw != expected_w:
                errors.append(f"Module '{mod_id}', dim '{dim_name}': weight {dw}, expected {expected_w}")

            for t in dim_val.get("tests", []):
                tc_nodeid = t.get("nodeid", "")
                matched = any(
                    tc.get("nodeid", "") == tc_nodeid
                    for tc in evidence_testcases
                )
                if not matched and not t.get("_unmatched"):
                    combined = f"{t.get('classname', '')}::{t.get('name', '')}"
                    matched = any(
                        tc.get("nodeid", "") == combined
                        for tc in evidence_testcases
                    )
                if not matched and not t.get("_unmatched"):
                    errors.append(f"Module '{mod_id}', dim '{dim_name}': test '{tc_nodeid}' not in JUnit evidence")

            if ds == "FAILED":
                failures = [t for t in dim_val.get("tests", []) if t.get("failure")]
                if not failures:
                    errors.append(f"Module '{mod_id}', dim '{dim_name}': status FAILED but no failure in tests")

    if errors:
        print("## Manifest V6 Audit ERRORS\n")
        for e in errors:
            print(f"  - {e}")
        print(f"\n{len(errors)} error(s) found")
        return 1

    print("## Manifest V6 Audit: PASSED")
    print(f"SHA: {sha}")
    print(f"Modules: {len(manifest.get('modules', []))}")
    print("All evidence is consistent with the real codebase.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
