"""ST-R2-01: the current R15C certification must be executable and consistent."""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/verify_michi_truth_certification_st_r2.py"
ARTIFACT = ROOT / "docs/audio/phase2/F11_SIGNAL_TRUTH_ST_R2_CERTIFICATION.json"


def _module():
    spec = importlib.util.spec_from_file_location("st_r2_certification", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pass_requires_real_executed_evidence():
    module = _module()
    artifact = {
        "cases": [
            {
                "id": "R15C-01",
                "status": "PASS",
                "category": "SOFTWARE_ORACLE",
                "evidence": [],
            }
        ]
    }
    problems = module.check_artifact(artifact)
    assert any("without executed evidence" in item for item in problems)


def test_pass_with_a_non_pass_node_is_rejected():
    module = _module()
    artifact = {
        "cases": [
            {
                "id": "R15C-01",
                "status": "PASS",
                "category": "SOFTWARE_ORACLE",
                "evidence": [{"node": "tests/x.py::test_x", "result": "SKIP"}],
            }
        ]
    }
    assert any("claims PASS with" in item for item in module.check_artifact(artifact))


def test_special_cases_keep_their_own_obligation_status():
    module = _module()
    expected = {
        "R15C-20": ("BLOCKED_NOT_IMPLEMENTED", "POLARITY_DSP_NOT_IMPLEMENTED"),
        "R15C-23": (
            "EXTERNAL_VALIDATION_REQUIRED",
            "RT_CALLBACK_AND_XRUN_REQUIRE_PHYSICAL_HOST",
        ),
        "R15C-24": (
            "BLOCKED_RUNTIME",
            "REAL_CROSSFADE_WINDOWS_REQUIRE_PLAYBACK_RUNTIME",
        ),
        "R15C-31": ("OUT_OF_SCOPE_DESKTOP", "ANDROID_USB_REQUIRES_PHYSICAL_DEVICE"),
        "R15C-32": ("OUT_OF_SCOPE_DESKTOP", "BROWSER_RUNTIME_REQUIRES_BROWSER_HOST"),
        "R15C-37": (
            "OUT_OF_SCOPE_CURRENT_PLATFORM",
            "WINDOWS_QPC_AUDIOCONTEXT_REQUIRES_WINDOWS_HOST",
        ),
    }
    for case_id, (status, category) in expected.items():
        case = module.classify_case(case_id, ["tests/x.py::test_x"], set(), {})
        assert case["status"] == status, case_id
        assert case["category"] == category, case_id
        assert case["scope"]
        assert case["evidence"] == []


def test_legacy_out_of_scope_bucket_is_rejected():
    module = _module()
    artifact = {
        "cases": [
            {
                "id": "R15C-20",
                "status": "OUT_OF_SCOPE",
                "category": "OLD",
                "evidence": [],
            }
        ]
    }
    assert any(
        "legacy OUT_OF_SCOPE" in item for item in module.check_artifact(artifact)
    )


def test_partial_oracles_keep_their_missing_evidence():
    module = _module()
    for case_id, category in (
        ("R15C-15", "COALESCING_AND_UI_LOAD_ONLY"),
        ("R15C-44", "STAGES_SCROLL_FOCUS_ONLY"),
    ):
        case = module.classify_case(
            case_id,
            ["tests/x.py::test_x"],
            {"tests/x.py::test_x"},
            {"tests/x.py::test_x": "PASS"},
        )
        assert case["status"] == "PARTIAL", case_id
        assert case["category"] == category
        assert case["missing"]
        assert case["evidence"] == [{"node": "tests/x.py::test_x", "result": "PASS"}]


def test_partial_without_missing_evidence_is_rejected():
    module = _module()
    artifact = {
        "cases": [
            {
                "id": "R15C-15",
                "status": "PARTIAL",
                "category": "COALESCING_AND_UI_LOAD_ONLY",
                "evidence": [{"node": "tests/x.py::test_x", "result": "PASS"}],
            }
        ]
    }
    assert any(
        "PARTIAL without missing evidence" in item
        for item in module.check_artifact(artifact)
    )


def test_missing_or_unexecuted_nodes_never_pass():
    module = _module()
    blocked = module.classify_case("R15C-01", ["tests/x.py::test_x"], set(), {})
    assert blocked["status"] == "BLOCKED"
    not_run = module.classify_case(
        "R15C-01", ["tests/x.py::test_x"], {"tests/x.py::test_x"}, {}
    )
    assert not_run["status"] == "NOT_RUN"


def test_current_artifact_has_no_contradictory_status():
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    module = _module()
    assert module.check_artifact(artifact) == []
    assert artifact["summary"] == {
        "total": 50,
        "pass": 42,
        "partial": 2,
        "fail": 0,
        "error": 0,
        "skip": 0,
        "not_run": 0,
        "blocked": 0,
        "blocked_not_implemented": 1,
        "external_validation_required": 1,
        "blocked_runtime": 1,
        "out_of_scope_desktop": 2,
        "out_of_scope_current_platform": 1,
        "status_counts": {
            "BLOCKED_NOT_IMPLEMENTED": 1,
            "BLOCKED_RUNTIME": 1,
            "EXTERNAL_VALIDATION_REQUIRED": 1,
            "OUT_OF_SCOPE_CURRENT_PLATFORM": 1,
            "OUT_OF_SCOPE_DESKTOP": 2,
            "PARTIAL": 2,
            "PASS": 42,
        },
    }
    assert artifact["certification"]["software_oracle"] == "PARTIAL"
    assert artifact["certification"]["product_certification"] == "NO_GO"
    assert artifact["sources"]["historical_coverage"]["status_counts"] == {
        "NOT_RUN": 46,
        "PASS": 4,
    }


def test_execution_identity_links_the_tested_worktree():
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    module = _module()
    execution = artifact["execution"]
    # CI checks out a shallow merge commit, so the recorded baseline commit is
    # not necessarily present in the local object database. The artifact still
    # has to describe a clean tree: its own diff and untracked manifest must be
    # empty, and the recorded execution SHA must be the baseline it hashed.
    assert execution["sha"] == execution["baseline_sha"]
    assert execution["dirty"] is False
    assert execution["untracked_files"] == []
    assert execution["tracked_diff_sha256"] == module.EMPTY_DIFF_SHA256
    assert re.fullmatch(r"[0-9a-f]{40}", execution["baseline_sha"])
    assert re.fullmatch(r"[0-9a-f]{64}", execution["worktree_sha256"])
    assert execution["identity_scope"]


def test_every_mapped_node_is_collectable():
    mapping = json.loads(
        (ROOT / "docs/audio/phase2/F11_SIGNAL_TRUTH_R15C_MAP_ST_R1.json").read_text(
            encoding="utf-8"
        )
    )
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "--collect-only", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    collected = {
        line.strip()
        for line in proc.stdout.splitlines()
        if line.startswith("tests/") and "::" in line
    }
    missing = {
        node for nodes in mapping.values() for node in nodes if node not in collected
    }
    assert not missing, sorted(missing)
