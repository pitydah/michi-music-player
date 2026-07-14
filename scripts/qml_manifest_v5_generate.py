#!/usr/bin/env python3
"""QML Manifest V5 Generator — based on config weights, JUnit evidence, and module markers."""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ARTIFACTS = REPO / "artifacts"
CONFIG_FILE = REPO / "config" / "qml_migration_dimensions.json"
EVIDENCE_FILE = ARTIFACTS / "qml-evidence-v5.json"
MANIFEST_PATH = REPO / "docs" / "qml_migration_manifest_v5.json"

MODULE_TEST_MAP = {
    "shell_nav": ["navigation", "app_bridge", "theme", "notification", "accessibility"],
    "library_playback": ["home", "library", "album_views", "playback", "nowplaying", "queue"],
    "core_workflows": ["history", "playlists", "mix", "lyrics", "radio", "global_search", "worker_manager", "query_executor", "job_bridge"],
    "advanced_tools": ["eq_dsp", "metadata", "smart_tagging", "audio_lab", "library_doctor", "disc_lab", "diagnostics", "michi_ai"],
    "ecosystem_network": ["connections", "home_audio", "devices_sync", "capabilities"],
    "quality_release": ["settings", "settings_schema", "settings_runtime", "output_profiles", "runtime_quality", "performance"],
}

PHYSICAL_AUDIO_EXCLUDED = "PHYSICAL_AUDIO"

MODULE_STATUS_ORDER = [
    "NOT_IMPLEMENTED", "SCAFFOLDED", "COMPILES", "READ_ONLY",
    "PARTIAL_WORKFLOW", "PRODUCTIVE", "PARITY",
]


def load_config() -> dict:
    return json.loads(CONFIG_FILE.read_text())


def load_evidence() -> dict:
    if not EVIDENCE_FILE.exists():
        return {"testcases": [], "marked_tests": []}
    return json.loads(EVIDENCE_FILE.read_text())


def get_module_for_test(classname: str, marked_tests: list) -> str | None:
    parts = classname.split(".")
    for mt in marked_tests:
        if mt.get("file", "").replace("/", ".").replace(".py", "") in classname:
            return mt.get("function", "")
    for part in parts:
        for modules in MODULE_TEST_MAP.values():
            for mod in modules:
                if mod in part or part in mod:
                    return mod
    return None


def derive_status(classname: str, testcases: list, module_id: str) -> str:
    """Assign status based on real JUnit evidence."""
    module_tests = [tc for tc in testcases if module_id in tc.get("classname", "")]
    if not module_tests:
        return "NOT_IMPLEMENTED"
    total = len(module_tests)
    passed = sum(1 for tc in module_tests if not tc.get("failure") and not tc.get("skipped"))
    failed = sum(1 for tc in module_tests if tc.get("failure"))
    if total == 0:
        return "NOT_IMPLEMENTED"
    if failed > 0 and passed == 0:
        return "SCAFFOLDED"
    if failed > 0 and passed > 0:
        return "PARTIAL_WORKFLOW"
    if passed == total and total >= 3:
        return "PRODUCTIVE"
    if passed == total:
        return "COMPILES"
    return "READ_ONLY"


def build_module_evidence(testcases: list, module_id: str, marked_tests: list) -> dict:
    module_tests = [tc for tc in testcases if module_id in tc.get("classname", "")]
    file_hits = [mt for mt in marked_tests if module_id in mt.get("file", "")]
    return {
        "test_count": len(module_tests),
        "passed_count": sum(1 for tc in module_tests if not tc.get("failure") and not tc.get("skipped")),
        "failed_count": sum(1 for tc in module_tests if tc.get("failure")),
        "skipped_count": sum(1 for tc in module_tests if tc.get("skipped")),
        "test_files": sorted(set(mt["file"] for mt in file_hits)),
    }


def main() -> int:
    config = load_config()
    evidence = load_evidence()
    testcases = evidence.get("testcases", [])
    marked_tests = evidence.get("marked_tests", [])

    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO
    ).stdout.strip()

    dimension_weights = config["dimension_weights"]
    area_weights = config["area_weights"]

    modules_list = []
    for area, mod_ids in MODULE_TEST_MAP.items():
        for mod_id in mod_ids:
            ev = build_module_evidence(testcases, mod_id, marked_tests)
            status = derive_status(None, testcases, mod_id)
            modules_list.append({
                "module": mod_id,
                "area": area,
                "module_weight": 10,
                "status": status,
                "evidence": ev,
            })

    manifest = {
        "version": "5.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sha": sha,
        "area_weights": area_weights,
        "dimension_weights": dimension_weights,
        "modules": modules_list,
        "excluded": [PHYSICAL_AUDIO_EXCLUDED],
    }

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"Manifest V5 written to {MANIFEST_PATH}")
    print(f"SHA: {sha}")
    print(f"Modules: {len(modules_list)}")
    print(f"Excluded: {manifest['excluded']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
