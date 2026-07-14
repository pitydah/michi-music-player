"""Verify that VERIFIED status requires exactly 21/21 checks passed.

Only VERIFIED with 21/21 delivers physical points.
Any other state (PENDING, RUNNING, FAILED, BLOCKED_HARDWARE) does not count.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parent.parent.parent
ARTIFACT_PATH = REPO / "artifacts" / "qml-physical-results.json"


def load_artifact():
    if not ARTIFACT_PATH.exists():
        pytest.skip(f"Artifact not found at {ARTIFACT_PATH}")
    try:
        return json.loads(ARTIFACT_PATH.read_text())
    except json.JSONDecodeError:
        pytest.fail("Artifact is not valid JSON")


class TestPhysicalVerifiedRequires21:
    def test_artifact_exists(self):
        assert ARTIFACT_PATH.exists(), (
            "Physical artifact must exist to verify physical points."
        )

    def test_verified_requires_all_21_passed(self):
        art = load_artifact()
        if art["status"] == "VERIFIED":
            assert art["passed"] == 21, (
                f"VERIFIED requires 21/21 passed, got {art['passed']}/{art['total']}"
            )
            assert art["total"] == 21, (
                f"VERIFIED requires total=21, got {art['total']}"
            )
            for c in art.get("checks", []):
                assert c.get("passed") is True, (
                    f"VERIFIED but check '{c.get('id', '?')}' is not passed"
                )
                assert c.get("evidence"), (
                    f"VERIFIED but check '{c.get('id', '?')}' has no evidence"
                )

    def test_blocked_hardware_cannot_be_verified(self):
        art = load_artifact()
        if art["status"] == "BLOCKED_HARDWARE":
            assert art["passed"] < 21, (
                f"BLOCKED_HARDWARE should not have 21/21 (got {art['passed']})"
            )

    def test_failed_not_verified(self):
        art = load_artifact()
        if art["status"] == "FAILED":
            assert art["passed"] < 21, (
                f"FAILED should not have 21/21 (got {art['passed']})"
            )

    def test_pending_not_verified(self):
        art = load_artifact()
        if art["status"] == "PENDING":
            assert art["passed"] == 0, (
                f"PENDING should have 0 passed, got {art['passed']}"
            )

    def test_running_not_verified(self):
        art = load_artifact()
        if art["status"] == "RUNNING":
            assert art["total"] == 21, (
                f"RUNNING should report total=21, got {art['total']}"
            )

    def test_verified_has_backend(self):
        art = load_artifact()
        if art["status"] == "VERIFIED":
            assert art.get("backend", ""), "VERIFIED must have non-empty backend"

    def test_verified_has_device(self):
        art = load_artifact()
        if art["status"] == "VERIFIED":
            assert art.get("device", ""), "VERIFIED must have non-empty device"

    def test_verified_has_sink(self):
        art = load_artifact()
        if art["status"] == "VERIFIED":
            assert art.get("sink", ""), "VERIFIED must have non-empty sink"

    def test_verified_has_sample_rate(self):
        art = load_artifact()
        if art["status"] == "VERIFIED":
            assert art.get("sample_rate", ""), "VERIFIED must have non-empty sample_rate"

    def test_verified_has_format(self):
        art = load_artifact()
        if art["status"] == "VERIFIED":
            assert art.get("format", ""), "VERIFIED must have non-empty format"

    def test_verified_has_profile(self):
        art = load_artifact()
        if art["status"] == "VERIFIED":
            assert art.get("profile", ""), "VERIFIED must have non-empty profile"

    def test_all_checks_present_in_verified(self):
        art = load_artifact()
        if art["status"] == "VERIFIED":
            expected_ids = [
                "mp3_playback", "flac_playback", "wav_playback",
                "cover_display", "placeholder",
                "play", "pause", "seek", "volume", "mute",
                "next", "previous",
                "shuffle", "repeat",
                "queue", "queue_play",
                "lyrics", "radio", "radio_play",
                "eq", "settings",
            ]
            check_ids = [c["id"] for c in art["checks"]]
            for eid in expected_ids:
                assert eid in check_ids, f"VERIFIED missing check '{eid}'"

    def test_verified_each_check_has_result(self):
        art = load_artifact()
        if art["status"] == "VERIFIED":
            for c in art["checks"]:
                assert "result" in c, (
                    f"VERIFIED check '{c.get('id', '?')}' missing 'result'"
                )
                assert isinstance(c["result"], str), (
                    f"VERIFIED check '{c.get('id', '?')}' result not string"
                )
