"""DAC-V35 FINAL PCM closure — evidence semantics and multi-hardware gates."""

from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
from copy import deepcopy
from pathlib import Path

import pytest

from michi.application.dac_pcm_closure import (
    PASSING_DEVICE_VERDICT,
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


def _r32_records(total: int = 120, *, fail_index: int | None = None) -> list[dict]:
    return [
        {
            "failed": index == fail_index,
            "error": None,
            "status": 2,
            "decoded_rate_hz": 44100,
            "requested_rate_hz": 44100,
            "negotiated_rate_hz": 44100,
            "identity": {
                "plan_id": f"plan:{index:04d}",
                "execution_generation": index + 1,
                "port_generation": index + 1,
            },
            "signal_truth_state": "direct_container_adapted",
            "stale_identity": False,
        }
        for index in range(total)
    ]


def _write_sidecar(path: Path, records: list[dict]) -> str:
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sample_of(records: list[dict]) -> list[dict]:
    head = records[:32]
    tail = records[-32:]
    sample: list[dict] = []
    seen: set[int] = set()
    for record in (*head, *tail):
        if id(record) not in seen:
            seen.add(id(record))
            sample.append(record)
    return sample


def _build_r32_sidecar() -> dict:
    """One real, complete sidecar artifact matching the lab's sample rule."""

    directory = Path(tempfile.mkdtemp(prefix="r32-closure-sidecar-"))
    path = directory / "soak-receipts-fixture.jsonl.gz"
    records = _r32_records()
    return {
        "path": str(path),
        "sha256": _write_sidecar(path, records),
        "total": len(records),
        "sample": _sample_of(records),
    }


_R32_SIDECAR = _build_r32_sidecar()


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
                    "runs": [
                        {
                            "edges": [
                                "44100->44100",
                                "44100->48000",
                                "48000->44100",
                                "44100->96000",
                                "96000->192000",
                                "192000->44100",
                            ],
                            "configured_delay_ms": delay,
                            "actual_hold_ms": delay + 1 if delay else 0,
                            "stale_generation_observed": False,
                            "hidden_conversion_observed": False,
                            "xrun_count": 0,
                            "receipts": [
                                {
                                    "error": None,
                                    "xrun_count": 0,
                                    "actual_hold_ms": delay + 1 if delay else 0,
                                }
                                for _ in range(7)
                            ],
                            "first_sample_evidence": {
                                "configured_delay_ms": delay,
                                "method": "operator-impulse-marker",
                                "fixture_id": "start_impulse_44100",
                                "fixture_sha256": "a" * 64,
                                "evidence_reference": (
                                    f"operator:2026-09-27-session:{delay}ms"
                                ),
                                "expected_marker": "impulse at sample 0",
                                "observed_result": "PASS: marker preserved",
                                "preserved": True,
                            },
                        }
                        for delay in (0, 100, 250, 500, 1000)
                    ],
                    "minimal_delay_that_preserves_first_content": 0,
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
                    "transition_failures": 0,
                    "receipts_total": _R32_SIDECAR["total"],
                    "receipts_failed": 0,
                    "receipts_sample": deepcopy(_R32_SIDECAR["sample"]),
                    "receipts_sample_limit": 64,
                    "receipts_file": _R32_SIDECAR["path"],
                    "receipts_file_sha256": _R32_SIDECAR["sha256"],
                    "rss_baseline_kb": 100000,
                    "rss_peak_kb": 104096,
                    "rss_final_kb": 104096,
                    "memory_growth_kb": 4096,
                    "pump_health": {
                        "pump_alive": True,
                        "alive_at_every_checkpoint": True,
                        "cycles_completed": 120,
                    },
                    "resource_growth": {
                        "observed": True,
                        "unbounded": False,
                        "owned_pipelines_peak": 1,
                    },
                    "usb_errors_observed": {
                        "device_id": stable_device_id,
                        "sysfs_path": (
                            "/sys/bus/usb/devices/"
                            + stable_device_id.rsplit(":", 1)[-1]
                        ),
                        "topology": stable_device_id.rsplit(":", 1)[-1],
                        "backend": "linux_usb_abi_kernel_journal",
                        "available": True,
                        "baseline": {"busnum": 1, "devnum": 2, "urbnum": 100},
                        "final": {"busnum": 1, "devnum": 2, "urbnum": 200},
                        "binding_stable": True,
                        "urb_progress": True,
                        "kernel_log_available": True,
                        "observation_start_epoch": 100.0,
                        "observation_end_epoch": 200.0,
                        "error_events": [],
                        "error_count": 0,
                    },
                    "rss_checkpoints": [{"cycle": 20, "rss_kb": 100000}],
                },
            },
            "R35": {
                "status": "PASS",
                "executed": True,
                "evidence": ["tail.wav"],
                "facts": {
                    "fixtures": {
                        name: {
                            "result": "PASS",
                            "evidence_kind": "operator",
                            "evidence_reference": "operator:tail-session",
                            "method": "operator-listening-tail-check",
                            "fixture_sha256": "d" * 64,
                            "falsifier_observed": False,
                            "playback_error": None,
                            "terminal_status": 1,
                        }
                        for name in (
                            "nonzero_final_samples",
                            "end_impulse",
                            "same_tuple_two_track_boundary",
                            "different_tuple_two_track_boundary",
                        )
                    }
                },
            },
            "R36": {
                "status": "PASS",
                "executed": True,
                "evidence": ["xrun.json"],
                "facts": {
                    "cases": {
                        "induced_underrun": {
                            "case": "induced_underrun",
                            "fault_injected": True,
                            "xrun_observed": True,
                            "incident_retained": True,
                            "recovered_state_reported": True,
                            "continuity_proof": True,
                            "false_verified_after_incident": False,
                            "generation_fresh": True,
                            "recovery_loop_count": 0,
                            "signal_truth_after": {"verdict": {"state": "unknown"}},
                        },
                        "suspend_resume": {
                            "case": "suspend_resume",
                            "mechanism_available": True,
                            "operator_reference": "operator:suspend",
                            "action_completed": True,
                            "incident_retained": True,
                            "recovered_state_reported": True,
                            "continuity_proof": True,
                            "false_verified_after_incident": False,
                            "generation_fresh": True,
                            "recovery_loop_count": 0,
                            "signal_truth_after": {
                                "verdict": {"state": "direct_container_adapted"}
                            },
                            "suspend_success_before": 10,
                            "suspend_success_after": 11,
                        },
                        "device_failure": {
                            "case": "device_failure",
                            "mechanism_available": True,
                            "operator_reference": "operator:device-failure",
                            "action_completed": True,
                            "incident_retained": True,
                            "recovered_state_reported": True,
                            "continuity_proof": True,
                            "false_verified_after_incident": False,
                            "generation_fresh": True,
                            "recovery_loop_count": 0,
                            "same_identity_after": True,
                            "physical_reenumeration_observed": True,
                            "signal_truth_after": {
                                "verdict": {"state": "direct_container_adapted"}
                            },
                        },
                    },
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
    facts = payload["experiments"]["R25"]["facts"]
    # One delay missing a canonical edge is not a valid sweep.
    facts["runs"][0]["edges"] = [
        edge for edge in facts["runs"][0]["edges"] if edge != "192000->44100"
    ]
    assert "misses canonical edges" in _reject(payload)

    # A minimum that disagrees with the recorded runs is rejected too.
    mismatched = _manifest()
    mismatched["experiments"]["R25"]["facts"]["runs"][0]["actual_hold_ms"] = 0
    mismatched["experiments"]["R25"]["facts"][
        "minimal_delay_that_preserves_first_content"
    ] = 100
    assert "disagrees with the sweep" in _reject(mismatched)


def test_final_pcm_09_xrun_pass_forbids_false_verified_state() -> None:
    payload = _manifest()
    payload["experiments"]["R36"]["facts"]["cases"]["induced_underrun"][
        "false_verified_after_incident"
    ] = True
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


# ── Provenance and append-only gates ─────────────────────────────────────


def _v2_manifest(**kwargs):
    payload = _manifest(**kwargs)
    payload.pop("execution_git_head")
    payload.update(
        {
            "manifest_schema": 2,
            "implementation_head": "a" * 40,
            "evidence_execution_head": "a" * 40,
            "manifest_created_at": "2026-09-26T00:00:00-0300",
        }
    )
    return payload


def test_fc_11_manifest_binds_to_its_execution_head_not_the_current_tree() -> None:
    """A committed manifest is never stale by construction."""
    payload = _v2_manifest()
    verify_manifest = evaluate_device_manifest(payload)
    assert verify_manifest.implementation_head == "a" * 40
    assert verify_manifest.evidence_execution_head == "a" * 40
    assert verify_manifest.manifest_created_at == "2026-09-26T00:00:00-0300"
    # The manifest claims a head that cannot be the current tree by definition;
    # loading it must still succeed because provenance is internal.
    assert payload["implementation_head"] != "b" * 40


def test_fc_12_manifest_without_provenance_or_with_drift_is_rejected() -> None:
    payload = _v2_manifest()
    payload.pop("implementation_head")
    with pytest.raises(PcmClosureEvidenceError):
        evaluate_device_manifest(payload)

    drifted = _v2_manifest()
    drifted["evidence_execution_head"] = "c" * 40
    with pytest.raises(PcmClosureEvidenceError):
        evaluate_device_manifest(drifted)

    malformed = _v2_manifest()
    malformed["implementation_head"] = "short"
    with pytest.raises(PcmClosureEvidenceError):
        evaluate_device_manifest(malformed)

    contradicted = _v2_manifest()
    contradicted["execution_git_head"] = "d" * 40
    with pytest.raises(PcmClosureEvidenceError):
        evaluate_device_manifest(contradicted)

    malformed_descriptor = _v2_manifest()
    malformed_descriptor["device"]["descriptor_hash"] = "not-a-digest"
    with pytest.raises(PcmClosureEvidenceError, match="descriptor_hash"):
        evaluate_device_manifest(malformed_descriptor)


def test_fc_13_provenance_contradiction_between_levels_is_rejected() -> None:
    """A manifest whose top level disagrees with its events is not coherent."""
    import copy

    coherent = _v2_manifest()
    coherent["events"] = [
        {
            "experiment": "R24",
            "status": "PASS",
            "collected_head": "b" * 40,
        }
    ]
    coherent["evidence_execution_head"] = "b" * 40
    # The manifest-level execution head matches its last event.
    assert evaluate_device_manifest(coherent).evidence_execution_head == "b" * 40

    contradictory = copy.deepcopy(coherent)
    contradictory["evidence_execution_head"] = "a" * 40
    with pytest.raises(PcmClosureEvidenceError):
        evaluate_device_manifest(contradictory)

    missing_event_head = copy.deepcopy(coherent)
    missing_event_head["events"][0].pop("collected_head")
    with pytest.raises(PcmClosureEvidenceError):
        evaluate_device_manifest(missing_event_head)


def test_fc_14_verifier_verdicts_come_from_obligations_not_green_gates() -> None:
    """Green gates must not be reported as full closure; gaps stay explicit."""
    from michi.application.dac_pcm_closure import (
        FINALIZATION_OBLIGATIONS,
        IMPLEMENTATION_OBLIGATIONS,
        TOOLING_OBLIGATIONS,
        closure_gaps,
        closure_verdict,
    )

    gaps = (
        closure_gaps(IMPLEMENTATION_OBLIGATIONS)
        + closure_gaps(TOOLING_OBLIGATIONS)
        + closure_gaps(FINALIZATION_OBLIGATIONS)
    )

    # Implementation closure is complete: the resync hold, the EOS replay and
    # the recovery/handover contracts are implemented and gated.
    assert closure_verdict(IMPLEMENTATION_OBLIGATIONS) == "COMPLETE"
    assert closure_verdict(TOOLING_OBLIGATIONS) == "COMPLETE"
    assert closure_verdict(FINALIZATION_OBLIGATIONS) == "COMPLETE"
    assert gaps == ()
    assert not any("resync_timing_safety" in gap for gap in gaps)
    assert not any("resync_eos_replay" in gap for gap in gaps)
    assert not any("lab_semantic_checks" in gap for gap in gaps)
    assert not any("finalization_wiring" in gap for gap in gaps)
    assert not any("docs_reconciled" in gap for gap in gaps)


def _reject(manifest: dict) -> str:
    """A contradicted nominal PASS must never be promoted to a pass verdict."""
    verdict = evaluate_device_manifest(manifest)
    assert verdict.verdict in {"INCOMPLETE", "FAIL"}, verdict.verdict
    return " ".join(verdict.reasons)


def test_final_pcm_11_nominal_pass_is_rejected_without_structured_facts() -> None:
    manifest = _manifest()
    manifest["experiments"]["R25"] = {
        "status": "PASS",
        "executed": True,
        "evidence": ["transition.json"],
    }
    assert "structured facts" in _reject(manifest)


def test_final_pcm_12_first_sample_evidence_must_be_structured() -> None:
    manifest = _manifest()
    facts = manifest["experiments"]["R25"]["facts"]
    facts["runs"][0].pop("first_sample_evidence")
    assert "first-sample evidence" in _reject(manifest)

    structured = _manifest()
    structured["experiments"]["R25"]["facts"]["runs"][0]["first_sample_evidence"].pop(
        "fixture_sha256"
    )
    assert "fixture_sha256" in _reject(structured)

    incomplete = _manifest()
    incomplete["experiments"]["R25"]["facts"]["runs"] = [
        run
        for run in incomplete["experiments"]["R25"]["facts"]["runs"]
        if run["configured_delay_ms"] != 250
    ]
    assert "sweep delays" in _reject(incomplete)

    unobserved = _manifest()
    unobserved["experiments"]["R25"]["facts"]["runs"][0].pop("actual_hold_ms")
    assert "actual hold" in _reject(unobserved)


def test_final_pcm_13_r35_requires_every_canonical_fixture() -> None:
    for missing in (
        "nonzero_final_samples",
        "end_impulse",
        "same_tuple_two_track_boundary",
        "different_tuple_two_track_boundary",
    ):
        manifest = _manifest()
        manifest["experiments"]["R35"]["facts"]["fixtures"].pop(missing)
        assert "all four canonical fixtures" in _reject(manifest)


def test_final_pcm_14_r32_requires_memory_pump_and_device_bound_usb() -> None:
    no_growth = _manifest()
    no_growth["experiments"]["R32"]["facts"].pop("memory_growth_kb")
    assert "memory-growth trend" in _reject(no_growth)

    no_pump = _manifest()
    no_pump["experiments"]["R32"]["facts"]["pump_health"] = {"pump_alive": False}
    assert "pump health" in _reject(no_pump)

    unattached_usb = _manifest()
    unattached_usb["experiments"]["R32"]["facts"]["usb_errors_observed"] = {}
    assert "not bound to the tested device" in _reject(unattached_usb)

    wrong_device = _manifest()
    wrong_device["experiments"]["R32"]["facts"]["usb_errors_observed"]["device_id"] = (
        "usb:ffff:ffff:other"
    )
    assert "different tested device" in _reject(wrong_device)

    transitions = _manifest()
    transitions["experiments"]["R32"]["facts"]["transition_failures"] = 2
    assert "transition failures" in _reject(transitions)

    stale_receipt = _manifest()
    stale_receipt["experiments"]["R32"]["facts"]["receipts_sample"][0]["failed"] = True
    assert "receipt sample" in _reject(stale_receipt)

    no_journal = _manifest()
    no_journal["experiments"]["R32"]["facts"]["usb_errors_observed"][
        "kernel_log_available"
    ] = False
    assert "kernel log" in _reject(no_journal)

    usb_delta = _manifest()
    usb_delta["experiments"]["R32"]["facts"]["usb_errors_observed"]["error_count"] = 1
    usb_delta["experiments"]["R32"]["facts"]["usb_errors_observed"]["error_events"] = [
        "usb 1-2: reset high-speed USB device"
    ]
    assert "USB errors" in _reject(usb_delta)

    no_progress = _manifest()
    no_progress["experiments"]["R32"]["facts"]["usb_errors_observed"][
        "urb_progress"
    ] = False
    assert "URB progress" in _reject(no_progress)

    false_binding = _manifest()
    false_binding["experiments"]["R32"]["facts"]["usb_errors_observed"]["final"][
        "devnum"
    ] = 3
    assert "contradict stable binding" in _reject(false_binding)

    false_progress = _manifest()
    false_progress["experiments"]["R32"]["facts"]["usb_errors_observed"]["final"][
        "urbnum"
    ] = 100
    assert "contradict URB progress" in _reject(false_progress)

    no_window = _manifest()
    no_window["experiments"]["R32"]["facts"]["usb_errors_observed"].pop(
        "observation_end_epoch"
    )
    assert "observation window" in _reject(no_window)

    dead_checkpoint = _manifest()
    dead_checkpoint["experiments"]["R32"]["facts"]["pump_health"][
        "alive_at_every_checkpoint"
    ] = False
    assert "every checkpoint" in _reject(dead_checkpoint)


def test_final_pcm_15_r36_requires_measured_recovery_facts() -> None:
    no_continuity = _manifest()
    no_continuity["experiments"]["R36"]["facts"]["cases"]["induced_underrun"].pop(
        "continuity_proof"
    )
    assert "continuity proof" in _reject(no_continuity)

    no_loop_count = _manifest()
    no_loop_count["experiments"]["R36"]["facts"]["cases"]["induced_underrun"].pop(
        "recovery_loop_count"
    )
    assert "loop count" in _reject(no_loop_count)

    stale_generation = _manifest()
    stale_generation["experiments"]["R36"]["facts"]["cases"]["induced_underrun"][
        "generation_fresh"
    ] = False
    assert "fresh generation" in _reject(stale_generation)

    operator_without_reference = _manifest()
    operator_without_reference["experiments"]["R36"]["facts"]["cases"][
        "suspend_resume"
    ]["operator_reference"] = ""
    assert "operator reference" in _reject(operator_without_reference)


def test_final_pcm_16_r35_capture_artifact_must_exist_and_match_hash(tmp_path) -> None:
    artifact = tmp_path / "tail-capture.wav"
    artifact.write_bytes(b"captured tail")
    import hashlib

    good = _manifest()
    for entry in good["experiments"]["R35"]["facts"]["fixtures"].values():
        entry.update(
            {
                "evidence_kind": "capture",
                "artifact": str(artifact),
                "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            }
        )
    assert evaluate_device_manifest(good).verdict == "PASS"

    missing = _manifest()
    for entry in missing["experiments"]["R35"]["facts"]["fixtures"].values():
        entry.update(
            {
                "evidence_kind": "capture",
                "artifact": str(tmp_path / "absent.wav"),
                "sha256": "b" * 64,
            }
        )
    assert "capture artifact is missing" in _reject(missing)

    mismatch = _manifest()
    for entry in mismatch["experiments"]["R35"]["facts"]["fixtures"].values():
        entry.update(
            {
                "evidence_kind": "capture",
                "artifact": str(artifact),
                "sha256": "c" * 64,
            }
        )
    assert "hash mismatch" in _reject(mismatch)


def test_final_pcm_17_r35_fixture_hash_and_method_are_mandatory() -> None:
    no_fixture_hash = _manifest()
    no_fixture_hash["experiments"]["R35"]["facts"]["fixtures"]["end_impulse"].pop(
        "fixture_sha256"
    )
    assert "fixture sha256" in _reject(no_fixture_hash)

    no_method = _manifest()
    no_method["experiments"]["R35"]["facts"]["fixtures"]["end_impulse"]["method"] = ""
    assert "measurement method" in _reject(no_method)

    playback_error = _manifest()
    playback_error["experiments"]["R35"]["facts"]["fixtures"]["end_impulse"][
        "playback_error"
    ] = "backend failed"
    assert "playback error" in _reject(playback_error)


def test_final_pcm_18_r36_cases_have_case_specific_recovery_proof() -> None:
    device_failure = _manifest()
    device_failure["experiments"]["R36"]["facts"]["cases"]["device_failure"][
        "same_identity_after"
    ] = False
    assert "same stable identity" in _reject(device_failure)

    suspend = _manifest()
    suspend["experiments"]["R36"]["facts"]["cases"]["suspend_resume"][
        "signal_truth_after"
    ] = None
    assert "post-recovery Signal Truth" in _reject(suspend)

    no_suspend_witness = _manifest()
    no_suspend_witness["experiments"]["R36"]["facts"]["cases"]["suspend_resume"].pop(
        "suspend_success_after"
    )
    assert "kernel suspend-success witness" in _reject(no_suspend_witness)

    recovered_device = _manifest()
    assert evaluate_device_manifest(recovered_device).verdict == "PASS"


def test_final_pcm_19_r36_one_passing_case_cannot_promote_global_pass() -> None:
    manifest = _manifest()
    cases = manifest["experiments"]["R36"]["facts"]["cases"]
    manifest["experiments"]["R36"]["facts"]["cases"] = {
        "induced_underrun": cases["induced_underrun"]
    }
    assert "missing cumulative cases" in _reject(manifest)


@pytest.mark.parametrize("minimum", (250, 500))
def test_final_pcm_20_r25_accepts_a_nonzero_evidence_derived_minimum(minimum) -> None:
    manifest = _manifest()
    facts = manifest["experiments"]["R25"]["facts"]
    for run in facts["runs"]:
        preserved = run["configured_delay_ms"] >= minimum
        run["first_sample_evidence"]["preserved"] = preserved
        run["first_sample_evidence"]["observed_result"] = (
            "PASS: marker preserved" if preserved else "FAIL: marker truncated"
        )
    facts["minimal_delay_that_preserves_first_content"] = minimum
    assert evaluate_device_manifest(manifest).verdict == "PASS"


class TestR32SidecarArtifactVerification:
    """WU1: the R32 verdict must prove the recorded artifact, not its shape."""

    @staticmethod
    def _facts(payload: dict) -> dict:
        return payload["experiments"]["R32"]["facts"]

    def _assert_artifact_rejected(self, payload: dict, expected: str) -> None:
        verdict = evaluate_device_manifest(payload)
        assert verdict.verdict != PASSING_DEVICE_VERDICT
        assert any(expected in reason for reason in verdict.reasons), verdict.reasons

    def test_valid_artifact_is_still_accepted(self) -> None:
        assert evaluate_device_manifest(_manifest()).verdict == PASSING_DEVICE_VERDICT

    def test_missing_artifact_fails_closed(self, tmp_path) -> None:
        payload = _manifest()
        self._facts(payload)["receipts_file"] = str(tmp_path / "missing.jsonl.gz")
        self._assert_artifact_rejected(payload, "sidecar artifact")

    def test_wrong_digest_is_rejected(self) -> None:
        payload = _manifest()
        self._facts(payload)["receipts_file_sha256"] = "f" * 64
        self._assert_artifact_rejected(payload, "digest")

    def test_corrupt_gzip_is_rejected(self, tmp_path) -> None:
        path = tmp_path / "corrupt.jsonl.gz"
        path.write_bytes(b"definitely not a gzip stream")
        payload = _manifest()
        facts = self._facts(payload)
        facts["receipts_file"] = str(path)
        facts["receipts_file_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        self._assert_artifact_rejected(payload, "unreadable or truncated")

    def test_invalid_json_record_is_rejected(self, tmp_path) -> None:
        path = tmp_path / "invalid.jsonl.gz"
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            handle.write(json.dumps(_R32_SIDECAR["sample"][0], sort_keys=True) + "\n")
            handle.write("this line is not json\n")
        payload = _manifest()
        facts = self._facts(payload)
        facts["receipts_file"] = str(path)
        facts["receipts_file_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        self._assert_artifact_rejected(payload, "JSON")

    def test_receipt_count_mismatch_is_rejected(self) -> None:
        payload = _manifest()
        self._facts(payload)["receipts_total"] = _R32_SIDECAR["total"] + 1
        self._assert_artifact_rejected(payload, "count does not match")

    def test_failed_count_mismatch_is_rejected(self, tmp_path) -> None:
        records = _r32_records(fail_index=60)
        path = tmp_path / "one-failure.jsonl.gz"
        payload = _manifest()
        facts = self._facts(payload)
        facts["receipts_file"] = str(path)
        facts["receipts_file_sha256"] = _write_sidecar(path, records)
        facts["receipts_total"] = len(records)
        facts["receipts_sample"] = _sample_of(records)
        # the manifest still claims zero failures while the artifact has one
        self._assert_artifact_rejected(payload, "failed-receipt count")

    def test_truncated_completed_artifact_is_rejected(self, tmp_path) -> None:
        data = Path(_R32_SIDECAR["path"]).read_bytes()
        path = tmp_path / "truncated.jsonl.gz"
        path.write_bytes(data[: len(data) - 40])
        payload = _manifest()
        facts = self._facts(payload)
        facts["receipts_file"] = str(path)
        facts["receipts_file_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        self._assert_artifact_rejected(payload, "sidecar")

    def test_partial_aborted_artifact_cannot_pass(self, tmp_path) -> None:
        data = Path(_R32_SIDECAR["path"]).read_bytes()
        path = tmp_path / "partial.jsonl.gz"
        path.write_bytes(data[: len(data) - 40])
        payload = _manifest()
        facts = self._facts(payload)
        facts["receipts_file"] = str(path)
        facts["receipts_file_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        # an explicit partial label must never satisfy a PASS
        facts["receipts_partial"] = True
        self._assert_artifact_rejected(payload, "sidecar")

    def test_sample_disagreement_with_artifact_is_rejected(self) -> None:
        payload = _manifest()
        sample = self._facts(payload)["receipts_sample"]
        sample[0] = dict(
            sample[0],
            identity={
                "plan_id": "plan:zzzz",
                "execution_generation": 999,
                "port_generation": 999,
            },
        )
        self._assert_artifact_rejected(payload, "sample is inconsistent")

    def test_large_artifact_is_streamed_and_accepted(self, tmp_path) -> None:
        records = _r32_records(total=5000)
        path = tmp_path / "large.jsonl.gz"
        payload = _manifest()
        facts = self._facts(payload)
        facts["receipts_file"] = str(path)
        facts["receipts_file_sha256"] = _write_sidecar(path, records)
        facts["receipts_total"] = len(records)
        facts["receipts_sample"] = _sample_of(records)
        assert evaluate_device_manifest(payload).verdict == PASSING_DEVICE_VERDICT
