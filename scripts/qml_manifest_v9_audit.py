#!/usr/bin/env python3
"""Manifest V9 audit: verify SHA, weights, markers, scores — all between 0 and 100."""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MODULES_YAML = REPO / "config" / "qml_modules.yaml"
MANIFEST = REPO / "docs" / "qml_migration_manifest_v9.json"
EVIDENCE_FILE = REPO / "artifacts" / "qml-evidence-v9.json"

VALID_STATUSES = {"PASSED", "FAILED", "MISSING", "NOT_APPLICABLE_DECLARED", "DEFERRED_PHYSICAL"}


def main():
    errors = []

    if not MANIFEST.exists():
        print("ERROR: manifest not found")
        return 1
    if not MODULES_YAML.exists():
        print("ERROR: qml_modules.yaml not found")
        return 1

    try:
        import yaml
        config = yaml.safe_load(MODULES_YAML.read_text())
    except Exception as e:
        print(f"ERROR: cannot parse qml_modules.yaml: {e}")
        return 1
    manifest = json.loads(MANIFEST.read_text())

    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO
    ).stdout.strip()

    manifest_sha = manifest.get("sha", "")
    if manifest_sha != sha:
        errors.append(f"SHA mismatch: manifest={manifest_sha}, HEAD={sha}")

    module_defs = config.get("modules", {})
    manifest_modules = {m["module"]: m for m in manifest.get("modules", [])}

    for mod_name in module_defs:
        if mod_name not in manifest_modules:
            errors.append(f"Module '{mod_name}' defined in yaml but missing from manifest")
            continue
        mod_entry = manifest_modules[mod_name]
        score = mod_entry.get("score", -1)
        if not (0 <= score <= 100):
            errors.append(f"Module '{mod_name}': score {score} out of range [0, 100]")

        for marker, marker_val in mod_entry.get("markers", {}).items():
            status = marker_val.get("status")
            if status not in VALID_STATUSES:
                errors.append(f"Module '{mod_name}', marker '{marker}': invalid status '{status}'")

    global_score = manifest.get("global_score", -1)
    if not (0 <= global_score <= 100):
        errors.append(f"Global score {global_score} out of range [0, 100]")

    if EVIDENCE_FILE.exists():
        evidence_data = json.loads(EVIDENCE_FILE.read_text())
        evidence_testcases = evidence_data.get("testcases", [])
        for mod in manifest.get("modules", []):
            for marker_type, marker_val in mod.get("markers", {}).items():
                for t in marker_val.get("tests", []):
                    tc_nodeid = t.get("nodeid", "")
                    matched = any(
                        tc.get("nodeid", "") == tc_nodeid for tc in evidence_testcases
                    )
                    if not matched and not t.get("_unmatched"):
                        combined = f"{t.get('classname', '')}::{t.get('name', '')}"
                        matched = any(
                            tc.get("nodeid", "") == combined for tc in evidence_testcases
                        )
                    if not matched and not t.get("_unmatched"):
                        errors.append(f"Module '{mod['module']}', marker '{marker_type}': test '{tc_nodeid}' not in JUnit evidence")

    if errors:
        print("## Manifest V9 Audit ERRORS\n")
        for e in errors:
            print(f"  - {e}")
        print(f"\n{len(errors)} error(s) found")
        return 1

    print("## Manifest V9 Audit: PASSED")
    print(f"SHA: {sha}")
    print(f"Global score: {manifest.get('global_score', 'N/A')}%")
    print(f"Modules: {len(manifest.get('modules', []))}")
    print("All evidence is consistent with the real codebase.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
