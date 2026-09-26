"""DAC-V35 FINAL PCM closure — evidence semantics and multi-hardware gates."""

from __future__ import annotations

from copy import deepcopy

import pytest

from michi.application.dac_pcm_closure import (
    PHYSICAL_FAIL,
    PHYSICAL_INCOMPLETE,
    PHYSICAL_NOT_RUN,
    PHYSICAL_PASS_BOUNDED,
    PHYSICAL_PASS_MULTI_HARDWARE,
    PcmClosureEvidenceError,
    evaluate_device_manifest,
    materially_distinct,
    summarize_manifests,
)


def _manifest(
    *,
    stable_device_id: str = "usb:1111:0001:path-a",
    vendor_id: str = "1111",
    product_id: str = "0001",
    product: str = "DAC A",
):
    return {
        "schema_version": 1,
        "execution_git_head": "deadbeef",
        "environment_fingerprint": "qenv:v2:sha256:test",
        "device": {
            "stable_device_id": stable_device_id,
            "locator": "hw:CARD=DAC,DEV=0",
            "vendor_id": vendor_id,
            "product_id": product_id,
            "bcd_device": "0100",
            "manufacturer": "Vendor",
            "product": product,
            "descriptor_hash": "",
        },
        "experiments": {
            "R24": {
                "status": "PASS",
                "executed": True,
                "evidence": ["clock.json"],
                "facts": {
                    "sink_provides_clock": True,
                    "sink_clock_is_pipeline_clock": True,
                    "resampling_observed": False,
                },
            },
            "R25": {
                "status": "PASS",
                "executed": True,
                "evidence": ["transition.json"],
                "facts": {
                    "transition_edges": [
                        "44100->44100",
                        "44100->48000",
                        "48000->44100",
                        "44100->96000",
                        "96000->192000",
                        "192000->44100",
                    ],
                    "first_sample_result": "PASS",
                    "stale_generation_observed": False,
                },
            },
            "R32": {
                "status": "PASS",
                "executed": True,
                "evidence": ["soak.json"],
                "facts": {
                    "duration_seconds": 28800,
                    "xrun_count": 0,
                    "runtime_error_count": 0,
                },
            },
            "R35": {
                "status": "PASS",
                "executed": True,
                "evidence": ["tail.wav"],
                "facts": {
                    "tail_result": "PASS",
                    "evidence_kind": "capture",
                },
            },
            "R36": {
                "status": "PASS",
                "executed": True,
                "evidence": ["xrun.json"],
                "facts": {
                    "fault_injected": True,
                    "xrun_observed": True,
                    "false_verified_after_xrun": False,
                    "recovery_loop_observed": False,
                },
            },
        },
    }


def test_final_pcm_01_empty_summary_is_not_run() -> None:
    assert summarize_manifests([]).physical_verdict == PHYSICAL_NOT_RUN


def test_final_pcm_02_one_complete_device_is_bounded_pass() -> None:
    summary = summarize_manifests([_manifest()])
    assert summary.physical_verdict == PHYSICAL_PASS_BOUNDED
    assert summary.multi_hardware_proven is False
    assert summary.bit_perfect_claimed is False


def test_final_pcm_03_two_materially_distinct_devices_promote_multi_hardware() -> None:
    first = _manifest()
    second = _manifest(
        stable_device_id="usb:2222:0002:path-b",
        vendor_id="2222",
        product_id="0002",
        product="DAC B",
    )
    summary = summarize_manifests([first, second])
    assert summary.physical_verdict == PHYSICAL_PASS_MULTI_HARDWARE
    assert summary.multi_hardware_proven is True


def test_final_pcm_04_topology_only_difference_is_not_material_diversity() -> None:
    first = _manifest()
    second = _manifest(stable_device_id="usb:1111:0001:path-b")
    left = evaluate_device_manifest(first).identity
    right = evaluate_device_manifest(second).identity
    assert materially_distinct(left, right) is False
    assert (
        summarize_manifests([first, second]).physical_verdict == PHYSICAL_PASS_BOUNDED
    )


def test_final_pcm_05_not_run_experiment_keeps_device_incomplete() -> None:
    payload = _manifest()
    payload["experiments"]["R35"]["status"] = "NOT_RUN"
    payload["experiments"]["R35"]["executed"] = False
    payload["experiments"]["R35"]["evidence"] = []
    verdict = evaluate_device_manifest(payload)
    assert verdict.verdict == "INCOMPLETE"
    assert summarize_manifests([payload]).physical_verdict == PHYSICAL_INCOMPLETE


def test_final_pcm_06_nominal_pass_without_evidence_fails_closed() -> None:
    payload = _manifest()
    payload["experiments"]["R24"]["evidence"] = []
    verdict = evaluate_device_manifest(payload)
    assert verdict.verdict == "FAIL"
    assert "lacks executed=true" in verdict.reasons[0]


def test_final_pcm_07_short_soak_cannot_be_promoted_to_pass() -> None:
    payload = _manifest()
    payload["experiments"]["R32"]["facts"]["duration_seconds"] = 28799.99
    verdict = evaluate_device_manifest(payload)
    assert verdict.verdict == "FAIL"
    assert any("28800" in reason for reason in verdict.reasons)


def test_final_pcm_08_transition_matrix_requires_all_canonical_edges() -> None:
    payload = _manifest()
    payload["experiments"]["R25"]["facts"]["transition_edges"].remove("192000->44100")
    verdict = evaluate_device_manifest(payload)
    assert verdict.verdict == "FAIL"
    assert any("missing transition edges" in reason for reason in verdict.reasons)


def test_final_pcm_09_xrun_pass_forbids_false_verified_state() -> None:
    payload = _manifest()
    payload["experiments"]["R36"]["facts"]["false_verified_after_xrun"] = True
    verdict = evaluate_device_manifest(payload)
    assert verdict.verdict == "FAIL"
    assert summarize_manifests([payload]).physical_verdict == PHYSICAL_FAIL


def test_final_pcm_10_schema_and_required_experiments_are_fail_closed() -> None:
    payload = _manifest()
    del payload["experiments"]["R24"]
    with pytest.raises(PcmClosureEvidenceError, match="R24"):
        evaluate_device_manifest(payload)

    wrong = deepcopy(_manifest())
    wrong["schema_version"] = 99
    with pytest.raises(PcmClosureEvidenceError, match="schema"):
        evaluate_device_manifest(wrong)
