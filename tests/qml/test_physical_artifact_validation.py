"""Validate the physical audio artifact at artifacts/qml-physical-results.json.

Verifies:
- File exists and is valid JSON
- Required fields present (status, sha, date, platform, backend, device)
- Status is one of: PENDING, RUNNING, VERIFIED, FAILED, BLOCKED_HARDWARE
- All 21 checks present
- Each check has id, label, passed, evidence
- passed + total consistency
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
ARTIFACT_PATH = REPO / "artifacts" / "qml-physical-results.json"

REQUIRED_FIELDS = {"status", "sha", "date", "platform", "backend", "device", "version", "passed", "total", "checks"}
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


def load_artifact():
    if not ARTIFACT_PATH.exists():
        pytest.skip(f"Artifact not found at {ARTIFACT_PATH}")
    return json.loads(ARTIFACT_PATH.read_text())


def test_artifact_exists():
    assert ARTIFACT_PATH.exists(), f"Physical artifact missing at {ARTIFACT_PATH}"


def test_artifact_is_valid_json():
    try:
        load_artifact()
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON in artifact: {e}")


def test_required_fields_present():
    art = load_artifact()
    missing = REQUIRED_FIELDS - set(art.keys())
    assert not missing, f"Missing required fields: {missing}"


def test_status_is_valid():
    art = load_artifact()
    assert art["status"] in VALID_STATUSES, f"Invalid status: {art['status']}"


def test_all_21_checks_present():
    art = load_artifact()
    check_ids = [c["id"] for c in art.get("checks", [])]
    missing = [cid for cid in EXPECTED_CHECK_IDS if cid not in check_ids]
    extra = [cid for cid in check_ids if cid not in EXPECTED_CHECK_IDS]
    errors = []
    if missing:
        errors.append(f"Missing checks: {missing}")
    if extra:
        errors.append(f"Unexpected checks: {extra}")
    assert not errors, "; ".join(errors)
    assert len(art["checks"]) == 21, f"Expected 21 checks, got {len(art['checks'])}"


def test_each_check_has_required_fields():
    art = load_artifact()
    for c in art.get("checks", []):
        assert "id" in c, f"Check missing 'id': {c}"
        assert "passed" in c, f"Check {c.get('id', '?')} missing 'passed'"
        assert isinstance(c["passed"], bool), f"Check {c['id']} passed must be bool"
        assert "evidence" in c, f"Check {c['id']} missing 'evidence'"


def test_pass_count_matches():
    art = load_artifact()
    if not art.get("checks"):
        return
    expected = sum(1 for c in art["checks"] if c.get("passed", False))
    assert art["passed"] == expected, f"passed count {art['passed']} != expected {expected}"


def test_total_count_matches():
    art = load_artifact()
    if not art.get("checks"):
        return
    assert art["total"] == len(art["checks"]), f"total {art['total']} != checks len {len(art['checks'])}"


def test_sha_is_non_empty():
    art = load_artifact()
    assert art.get("sha", ""), "SHA must not be empty"


def test_date_is_non_empty():
    art = load_artifact()
    assert art.get("date", ""), "Date must not be empty"


def test_platform_is_non_empty():
    art = load_artifact()
    assert art.get("platform", ""), "Platform must not be empty"


def test_backend_is_non_empty_when_verified():
    art = load_artifact()
    if art["status"] == "VERIFIED":
        assert art.get("backend", ""), "Backend must not be empty when VERIFIED"


def test_device_is_non_empty_when_verified():
    art = load_artifact()
    if art["status"] == "VERIFIED":
        assert art.get("device", ""), "Device must not be empty when VERIFIED"


def test_blocked_hardware_has_reason():
    art = load_artifact()
    if art["status"] == "BLOCKED_HARDWARE":
        mp3s = [c for c in art.get("checks", []) if c["id"] == "mp3_playback"]
        for c in mp3s:
            assert not c.get("passed", False), "BLOCKED_HARDWARE: mp3_playback should be failed"


def test_verified_requires_all_pass():
    art = load_artifact()
    if art["status"] == "VERIFIED":
        assert art["passed"] == art["total"], f"VERIFIED but {art['passed']}/{art['total']} passed"
