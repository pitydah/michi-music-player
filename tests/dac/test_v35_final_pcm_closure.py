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
                    "runs": [
                        {
                            "edge": edge,
                            "configured_delay_ms": 0,
                            "actual_hold_ms": 1,
                            "stale_generation_observed": False,
                            "hidden_conversion_observed": False,
                        }
                        for edge in (
                            "44100->44100",
                            "44100->48000",
                            "48000->44100",
                            "44100->96000",
                            "96000->192000",
                            "192000->44100",
                        )
                    ]
                    + [
                        {
                            "edge": "44100->44100",
                            "configured_delay_ms": delay,
                            "actual_hold_ms": delay + 1,
                            "stale_generation_observed": False,
                            "hidden_conversion_observed": False,
                        }
                        for delay in (100, 250, 500, 1000)
                    ],
                    "first_sample_evidence": {
                        "method": "operator-impulse-marker",
                        "fixture_id": "start_impulse_44100",
                        "fixture_sha256": "a" * 64,
                        "evidence_reference": "operator:2026-09-27-session",
                        "expected_marker": "impulse at sample 0",
                        "observed_result": "PASS: marker preserved",
                    },
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
                    "memory_growth_kb": 4096,
                    "pump_health": {"pump_alive": True, "cycles_completed": 120},
                    "resource_growth": {"unbounded": False, "owned_pipelines": 1},
                    "usb_errors_observed": {"device_id": "usb:1111:0001:path-a"},
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
                            "falsifier_observed": False,
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
                    "case": "induced_underrun",
                    "fault_injected": True,
                    "xrun_observed": True,
                    "incident_retained": True,
                    "recovered_state_reported": True,
                    "continuity_proof": True,
                    "false_verified_after_incident": False,
                    "generation_fresh": True,
                    "recovery_loop_count": 0,
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
    facts["runs"] = [run for run in facts["runs"] if run["edge"] != "192000->44100"]
    verdict = evaluate_device_manifest(payload)
    assert verdict.verdict == "FAIL"
    assert any("missing transition edges" in reason for reason in verdict.reasons)


def test_final_pcm_09_xrun_pass_forbids_false_verified_state() -> None:
    payload = _manifest()
    payload["experiments"]["R36"]["facts"]["false_verified_after_incident"] = True
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
    # The experimental tooling program and one finalization item remain open.
    assert closure_verdict(TOOLING_OBLIGATIONS) == "INCOMPLETE"
    assert closure_verdict(FINALIZATION_OBLIGATIONS) == "INCOMPLETE"
    assert any("R25" in gap for gap in gaps)
    assert any("R32:" in gap for gap in gaps)
    assert any("R35:" in gap for gap in gaps)
    assert any("R36:" in gap for gap in gaps)
    assert any("lab_tests" in gap for gap in gaps)
    # Closed obligations must not reappear as gaps.
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
    facts.pop("first_sample_evidence")
    assert "first-sample evidence" in _reject(manifest)

    structured = _manifest()
    structured["experiments"]["R25"]["facts"]["first_sample_evidence"].pop(
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

    transitions = _manifest()
    transitions["experiments"]["R32"]["facts"]["transition_failures"] = 2
    assert "transition failures" in _reject(transitions)


def test_final_pcm_15_r36_requires_measured_recovery_facts() -> None:
    no_continuity = _manifest()
    no_continuity["experiments"]["R36"]["facts"].pop("continuity_proof")
    assert "continuity proof" in _reject(no_continuity)

    no_loop_count = _manifest()
    no_loop_count["experiments"]["R36"]["facts"].pop("recovery_loop_count")
    assert "loop count" in _reject(no_loop_count)

    stale_generation = _manifest()
    stale_generation["experiments"]["R36"]["facts"]["generation_fresh"] = False
    assert "fresh generation" in _reject(stale_generation)

    operator_without_reference = _manifest()
    operator_without_reference["experiments"]["R36"]["facts"].update(
        {
            "case": "suspend_resume",
            "mechanism_available": True,
            "action_completed": True,
        }
    )
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
