from __future__ import annotations
"""Verify structure of a physical audio artifact produced by the local runner.
The artifact is a JSON file at artifacts/qml-physical-results.json.
This test validates the schema regardless of the artifact's status value.
"""

import json
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parent.parent.parent
ARTIFACT_PATH = REPO / "artifacts" / "qml-physical-results.json"

REQUIRED_FIELDS_TOP = {
    "status", "sha", "date", "platform", "backend", "device",
    "version", "passed", "total", "checks",
}
VALID_STATUSES = {"PENDING", "RUNNING", "VERIFIED", "FAILED", "BLOCKED_HARDWARE"}

EXPECTED_CHECK_IDS = [
    "mp3_playback", "flac_playback", "wav_playback",
    "cover_display", "placeholder",
    "play", "pause", "seek", "volume", "mute",
    "next", "previous",
    "shuffle", "repeat",
    "queue", "queue_play",
    "lyrics", "radio", "radio_play",
    "eq", "settings",
]

LOCAL_RUNNER_FIELDS = {
    "backend", "sink", "output_device", "sample_rate", "format", "profile",
    "sha", "screenshots", "logs", "result",
}


def load_artifact():
    if not ARTIFACT_PATH.exists():
        pytest.skip(f"Artifact not found at {ARTIFACT_PATH}")
    try:
        return json.loads(ARTIFACT_PATH.read_text())
    except json.JSONDecodeError:
        pytest.fail("Artifact is not valid JSON")


class TestPhysicalRunnerSchema:
    def test_artifact_exists(self):
        assert ARTIFACT_PATH.exists(), f"Physical artifact missing at {ARTIFACT_PATH}"

    def test_artifact_is_valid_json(self):
        load_artifact()

    def test_required_top_fields(self):
        art = load_artifact()
        missing = REQUIRED_FIELDS_TOP - set(art.keys())
        assert not missing, f"Missing required top-level fields: {missing}"

    def test_status_valid(self):
        art = load_artifact()
        assert art["status"] in VALID_STATUSES, f"Invalid status: {art['status']}"

    def test_all_21_checks_present(self):
        art = load_artifact()
        check_ids = [c["id"] for c in art.get("checks", [])]
        missing = [cid for cid in EXPECTED_CHECK_IDS if cid not in check_ids]
        extra = [cid for cid in check_ids if cid not in EXPECTED_CHECK_IDS]
        errors = []
        if missing:
            errors.append(f"Missing: {missing}")
        if extra:
            errors.append(f"Unexpected: {extra}")
        assert not errors, "; ".join(errors)
        assert len(art["checks"]) == 21, f"Expected 21 checks, got {len(art['checks'])}"

    def test_each_check_has_required_fields(self):
        art = load_artifact()
        for c in art.get("checks", []):
            assert "id" in c, f"Check missing 'id': {c}"
            assert "passed" in c, f"Check {c.get('id', '?')} missing 'passed'"
            assert isinstance(c["passed"], bool), f"Check {c['id']} passed must be bool"
            assert "evidence" in c, f"Check {c['id']} missing 'evidence'"

    def test_pass_total_consistency(self):
        art = load_artifact()
        if art.get("checks"):
            expected_passed = sum(1 for c in art["checks"] if c.get("passed", False))
            assert art["passed"] == expected_passed, (
                f"passed {art['passed']} != computed {expected_passed}"
            )
            assert art["total"] == len(art["checks"]), (
                f"total {art['total']} != {len(art['checks'])}"
            )

    def test_sha_non_empty(self):
        art = load_artifact()
        assert art.get("sha", ""), "SHA must not be empty"

    def test_date_non_empty(self):
        art = load_artifact()
        assert art.get("date", ""), "Date must not be empty"

    def test_platform_non_empty(self):
        art = load_artifact()
        assert art.get("platform", ""), "Platform must not be empty"

    def test_backend_present(self):
        art = load_artifact()
        assert "backend" in art

    def test_device_present(self):
        art = load_artifact()
        assert "device" in art

    def test_version_present(self):
        art = load_artifact()
        assert art.get("version", ""), "Version must not be empty"

    def test_local_runner_fields(self):
        art = load_artifact()
        if art["status"] in ("VERIFIED", "FAILED"):
            for field in LOCAL_RUNNER_FIELDS:
                assert field in art, (
                    f"Missing local runner field '{field}' for status {art['status']}"
                )

    def test_screenshots_is_list(self):
        art = load_artifact()
        if "screenshots" in art:
            assert isinstance(art["screenshots"], list), "screenshots must be a list"

    def test_logs_is_list(self):
        art = load_artifact()
        if "logs" in art:
            assert isinstance(art["logs"], list), "logs must be a list"

    def test_result_individual_check_format(self):
        art = load_artifact()
        for c in art.get("checks", []):
            if "result" in c:
                assert isinstance(c["result"], str), (
                    f"Check {c.get('id', '?')} result must be string"
                )

    def test_placeholder_check_not_passed(self):
        art = load_artifact()
        for c in art.get("checks", []):
            if c["id"] == "placeholder":
                assert c.get("passed") is False, "placeholder check must not pass"
                break

    def test_evidence_is_string_or_list(self):
        art = load_artifact()
        for c in art.get("checks", []):
            ev = c.get("evidence", "")
            assert isinstance(ev, (str, list)), (
                f"Check {c['id']} evidence must be string or list"
            )
