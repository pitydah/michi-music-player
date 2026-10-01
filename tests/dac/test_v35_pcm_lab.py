"""LAB-01..LAB-20 — fail-closed contracts for the M11.4 PCM field lab."""

from __future__ import annotations

import importlib.util
import json
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture(scope="module")
def lab():
    path = Path(__file__).parents[2] / "scripts" / "dac_m11_4_pcm_lab.py"
    spec = importlib.util.spec_from_file_location("dac_m11_4_pcm_lab", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _identity(*, plan: str = "plan-a", execution: int = 2, port: int = 3):
    return {
        "plan_id": plan,
        "execution_generation": execution,
        "port_generation": port,
        "binding_generation": 4,
        "stable_device_id": "usb:1111:2222:1-2",
    }


def _r25_run(
    delay: int, *, actual: int | None = None, first_sample_preserved: bool = True
):
    return {
        "configured_delay_ms": delay,
        "actual_hold_ms": delay if actual is None else actual,
        "edges": [
            "44100->44100",
            "44100->48000",
            "48000->44100",
            "44100->96000",
            "96000->192000",
            "192000->44100",
        ],
        "stale_generation_observed": False,
        "hidden_conversion_observed": False,
        "xrun_count": 0,
        "receipts": [
            {"error": None, "xrun_count": 0, "actual_hold_ms": delay} for _ in range(7)
        ],
        "first_sample_evidence": _first_sample(
            delay=delay, preserved=first_sample_preserved
        ),
    }


def _first_sample(*, delay: int = 0, preserved: bool = True):
    return {
        "configured_delay_ms": delay,
        "method": "capture",
        "fixture_id": "first.wav",
        "fixture_sha256": "a" * 64,
        "evidence_reference": "capture:first.wav",
        "expected_marker": "sample zero impulse",
        "observed_result": (
            "PASS: marker preserved" if preserved else "FAIL: marker truncated"
        ),
        "preserved": preserved,
    }


def _soak_facts():
    return {
        "duration_seconds": 28800,
        "xrun_count": 0,
        "runtime_error_count": 0,
        "transition_failures": 0,
        "memory_growth_kb": 1024,
        "rss_checkpoints": [{"cycle": 1, "rss_kb": 1000}],
        "pump_health": {
            "pump_alive": True,
            "alive_at_every_checkpoint": True,
            "cycles_completed": 1,
        },
        "resource_growth": {
            "observed": True,
            "unbounded": False,
            "owned_pipelines_peak": 1,
        },
        "usb_errors_observed": {
            "device_id": "usb:1111:2222:1-2",
            "sysfs_path": "/sys/bus/usb/devices/1-2",
            "topology": "1-2",
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
    }


def test_lab_01_parser_exposes_every_physical_workflow(lab) -> None:
    choices = lab.build_parser()._subparsers._group_actions[0].choices
    assert {
        "inventory",
        "init",
        "clock",
        "transition",
        "soak",
        "tail",
        "fault-prepare",
        "fault-complete",
        "xrun",
        "summary",
    } <= set(choices)


def test_lab_02_json_checkpoint_and_event_provenance_are_atomic(
    lab, tmp_path, monkeypatch
) -> None:
    target = tmp_path / "checkpoint.json"
    lab._write_json(target, {"cycle": 2})
    assert target.read_text(encoding="utf-8") == '{\n  "cycle": 2\n}\n'
    assert not target.with_suffix(".json.tmp").exists()

    payload = {
        "manifest_schema": 2,
        "evidence_execution_head": "a" * 40,
        "experiments": {"R32": {"status": "NOT_RUN"}},
        "events": [],
    }
    written = {}
    monkeypatch.setattr(lab, "_manifest", lambda _path: payload)
    monkeypatch.setattr(lab, "_git_head", lambda: "b" * 40)
    monkeypatch.setattr(
        lab,
        "evaluate_device_manifest",
        lambda _candidate: SimpleNamespace(verdict="INCOMPLETE", reasons=()),
    )
    monkeypatch.setattr(lab, "_write_json", lambda _path, value: written.update(value))
    lab._record(
        target,
        experiment="R32",
        status="REQUIRES_OPERATOR_CONFIRMATION",
        evidence=["soak:short"],
        facts={"duration_seconds": 1},
    )
    assert written["evidence_execution_head"] == "b" * 40
    assert written["events"][-1]["collected_head"] == "b" * 40

    monkeypatch.setattr(
        lab,
        "evaluate_device_manifest",
        lambda _candidate: SimpleNamespace(
            verdict="FAIL", reasons=("R32: contradiction",)
        ),
    )
    with pytest.raises(SystemExit, match="contradicted PASS"):
        lab._record(
            target,
            experiment="R32",
            status="PASS",
            evidence=["soak:8h"],
            facts={"duration_seconds": 28800},
        )


def test_lab_03_file_hash_is_calculated_from_bytes(lab, tmp_path) -> None:
    fixture = tmp_path / "fixture.wav"
    fixture.write_bytes(b"real fixture bytes")
    assert (
        lab._file_sha256(fixture)
        == "8609d943f4c8156da66d495d4c18d13c7bcaf8a9fd829a31119227904ff49d47"
    )


def test_lab_03b_manifest_identity_uses_the_usb_descriptor_digest(lab) -> None:
    identity = lab._manifest_device_identity(
        label="Reference DAC",
        device_id="usb:1111:2222:1-2",
        locator="hw:CARD=DAC,DEV=0",
        row={
            "vendorId": "1111",
            "productId": "2222",
            "bcdDevice": "0100",
            "manufacturer": "Vendor",
            "product": "DAC",
            "displayName": "Vendor DAC",
        },
        usb_descriptor_sha256="d" * 64,
    )
    assert identity["descriptor_hash"] == "d" * 64


def test_lab_04_first_sample_requires_complete_structured_evidence(
    lab, tmp_path
) -> None:
    fixture = tmp_path / "first.wav"
    fixture.write_bytes(b"impulse")
    args = Namespace(
        first_sample_method="loopback-capture",
        first_sample_fixture=fixture,
        first_sample_evidence="capture:first.wav",
        first_sample_expected_marker="impulse at sample zero",
        first_sample_observed_result="PASS: marker preserved",
    )
    evidence = lab._first_sample_evidence(args)
    assert evidence["fixture_id"] == "first.wav"
    assert evidence["fixture_sha256"] == lab._file_sha256(fixture)


def test_lab_05_incomplete_first_sample_never_becomes_evidence(lab) -> None:
    assert lab._first_sample_evidence(Namespace()) is None


def test_lab_05b_first_sample_observations_are_bound_per_delay(lab, tmp_path) -> None:
    fixture = tmp_path / "first.wav"
    fixture.write_bytes(b"impulse")
    observations = tmp_path / "first-sample.json"
    observations.write_text(
        json.dumps(
            {
                str(delay): {
                    "evidence_reference": f"capture:{delay}.wav",
                    "observed_result": (
                        "PASS: marker preserved"
                        if delay >= 250
                        else "FAIL: marker truncated"
                    ),
                }
                for delay in (0, 100, 250, 500, 1000)
            }
        ),
        encoding="utf-8",
    )
    evidence = lab._first_sample_evidence_by_delay(
        Namespace(
            first_sample_method="loopback-capture",
            first_sample_fixture=fixture,
            first_sample_expected_marker="impulse at sample zero",
            first_sample_observations=observations,
        )
    )
    assert set(evidence) == {0, 100, 250, 500, 1000}
    assert evidence[100]["preserved"] is False
    assert evidence[250]["preserved"] is True
    assert evidence[250]["configured_delay_ms"] == 250


def test_lab_06_r25_run_requires_measured_nonshortened_hold(lab) -> None:
    assert lab._r25_run_passes(_r25_run(250)) is True
    assert lab._r25_run_passes(_r25_run(250, actual=200)) is False


def test_lab_07_r25_pass_requires_the_whole_canonical_sweep(lab) -> None:
    runs = [_r25_run(delay) for delay in (0, 100, 250, 500, 1000)]
    status, minimum = lab._r25_result(runs)
    assert (status, minimum) == ("PASS", 0)
    assert lab._r25_result(runs[:-1])[0] != "PASS"


@pytest.mark.parametrize("minimum", (250, 500))
def test_lab_07b_r25_minimum_is_derived_from_per_delay_evidence(lab, minimum) -> None:
    runs = [
        _r25_run(delay, first_sample_preserved=delay >= minimum)
        for delay in (0, 100, 250, 500, 1000)
    ]
    assert lab._r25_result(runs) == ("PASS", minimum)

    # A global PASS observation cannot override a failed lower-delay marker.
    runs[0]["first_sample_evidence"]["observed_result"] = "PASS: fabricated"
    assert lab._r25_result(runs) == ("FAIL", None)


def test_lab_08_r25_runtime_error_forces_fail(lab) -> None:
    runs = [_r25_run(delay) for delay in (0, 100, 250, 500, 1000)]
    runs[2]["receipts"][0]["error"] = "backend failure"
    assert lab._r25_result(runs)[0] == "FAIL"


def test_lab_09_transition_receipt_uses_runtime_identity_and_rates(lab) -> None:
    result = {
        "status": lab.PlaybackStatus.PLAYING.value,
        "error_message": None,
        "signal_truth": {
            "identity": _identity(),
            "decoded": {"rate_hz": 48000},
            "plan": {"requested": {"rate_hz": 48000}},
            "alsa": {"rate_hz": 48000},
            "verdict": {"state": "direct_container_adapted"},
        },
    }
    receipt = lab._transition_receipt(result, previous_identity=_identity(plan="old"))
    assert receipt["failed"] is False
    assert receipt["decoded_rate_hz"] == 48000
    assert receipt["identity"] == _identity()


def test_lab_10_stale_or_missing_transition_truth_is_a_failure(lab) -> None:
    stale = {
        "status": lab.PlaybackStatus.PLAYING.value,
        "error_message": None,
        "signal_truth": {
            "identity": _identity(),
            "decoded": {"rate_hz": 44100},
            "plan": {"requested": {"rate_hz": 44100}},
            "alsa": {"rate_hz": 44100},
            "verdict": {"state": "direct"},
        },
    }
    assert lab._transition_receipt(stale, previous_identity=_identity())["failed"]
    assert lab._transition_receipt({}, previous_identity=None)["failed"]


def test_lab_11_resources_are_read_from_the_current_owned_port(lab) -> None:
    pump = SimpleNamespace(is_alive=lambda: True)
    handle = SimpleNamespace(plan_id="plan-a", generation=7)
    port = SimpleNamespace(
        _pump=pump,
        _pipeline=object(),
        _current_path=Path("song.flac"),
        _pending_path=None,
        _active_direct_handle=handle,
        _generation=9,
        _residual_bus_watches=[],
        _residual_timer_sources=[],
    )
    container = SimpleNamespace(
        _audio_engine_registry=SimpleNamespace(
            provider=lambda engine_id: SimpleNamespace(current_port=port)
        )
    )
    snapshot = lab._runtime_resource_snapshot(container)
    assert snapshot["pump_alive"] is True
    assert snapshot["owned_pipelines"] == 1
    assert snapshot["port_generation"] == 9
    # A container that cannot resolve the canonical port degrades to an honest
    # empty observation instead of inventing ownership.
    assert lab._runtime_resource_snapshot(SimpleNamespace()) == lab._empty_resources()


def test_lab_21_resync_evidence_reads_the_canonical_runtime_port(lab) -> None:
    port = SimpleNamespace(
        resync_evidence=lambda: {
            "resync_delay_ms": 250,
            "resync_actual_hold_ms": 269,
            "port_generation": 2,
            "execution_generation": 2,
            "plan_id": "plan:x",
        }
    )
    container = SimpleNamespace(
        _audio_engine_registry=SimpleNamespace(
            provider=lambda engine_id: SimpleNamespace(current_port=port)
        )
    )
    evidence = lab._port_resync_evidence(container)
    assert evidence["resync_actual_hold_ms"] == 269
    assert evidence["plan_id"] == "plan:x"
    # The lab never fabricates hold evidence for a missing runtime port.
    assert lab._port_resync_evidence(SimpleNamespace()) == {}


def test_lab_22_play_settles_only_on_playing_or_a_new_error(lab) -> None:
    def container(status, error):
        return SimpleNamespace(
            _playback=SimpleNamespace(
                state=SimpleNamespace(status=status, error_message=error)
            )
        )

    assert (
        lab._play_settled(container(lab.PlaybackStatus.PLAYING, "stale"), "stale")
        is True
    )
    # A pre-existing error is not this request's outcome.
    assert (
        lab._play_settled(container(lab.PlaybackStatus.STOPPED, "stale"), "stale")
        is False
    )
    assert (
        lab._play_settled(container(lab.PlaybackStatus.STOPPED, "fresh"), "stale")
        is True
    )
    assert lab._play_settled(container(lab.PlaybackStatus.STOPPED, None), None) is False


def test_lab_23_coordinator_is_the_productive_selection_authority(lab) -> None:
    coordinator = object()
    container = SimpleNamespace(
        _aob=SimpleNamespace(_selection_coordinator=coordinator)
    )
    assert lab._coordinator(container) is coordinator
    with pytest.raises(SystemExit):  # a missing authority is never invented
        lab._coordinator(SimpleNamespace())


def test_lab_12_usb_node_resolution_is_bound_to_device_identity(lab, tmp_path) -> None:
    node = tmp_path / "bus" / "usb" / "devices" / "1-2"
    node.mkdir(parents=True)
    (node / "idVendor").write_text("1111\n", encoding="utf-8")
    (node / "idProduct").write_text("2222\n", encoding="utf-8")
    resolved = lab._resolve_usb_sysfs_node("usb:1111:2222:1-2", sysfs_root=tmp_path)
    assert resolved == node
    assert lab._resolve_usb_sysfs_node("usb:aaaa:bbbb:1-2", sysfs_root=tmp_path) is None
    assert (
        lab._resolve_usb_sysfs_node("usb:1111:2222:../1-2", sysfs_root=tmp_path) is None
    )
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "idVendor").write_text("1111", encoding="utf-8")
    (outside / "idProduct").write_text("2222", encoding="utf-8")
    assert (
        lab._resolve_usb_sysfs_node(
            "usb:1111:2222:1-2",
            sysfs_root=tmp_path,
            explicit_path=outside,
        )
        is None
    )


def test_lab_13_usb_health_uses_documented_abi_and_device_kernel_log(
    lab, tmp_path
) -> None:
    node = tmp_path / "bus" / "usb" / "devices" / "1-2"
    node.mkdir(parents=True)
    (node / "idVendor").write_text("1111", encoding="utf-8")
    (node / "idProduct").write_text("2222", encoding="utf-8")
    (node / "busnum").write_text("1", encoding="utf-8")
    (node / "devnum").write_text("7", encoding="utf-8")
    (node / "urbnum").write_text("40", encoding="utf-8")
    baseline = lab._read_usb_health_snapshot(node)
    (node / "urbnum").write_text("75", encoding="utf-8")

    def runner(*_args, **_kwargs):
        return SimpleNamespace(
            returncode=0,
            stdout=(
                "usb 1-2: reset high-speed USB device number 7 using xhci_hcd\n"
                "usb 9-9: device descriptor read/64, error -71\n"
            ),
            stderr="",
        )

    evidence = lab._usb_health_evidence(
        "usb:1111:2222:1-2",
        node,
        baseline,
        lab._read_usb_health_snapshot(node),
        since_epoch=100.0,
        until_epoch=200.0,
        runner=runner,
    )
    assert evidence["backend"] == "linux_usb_abi_kernel_journal"
    assert evidence["binding_stable"] is True
    assert evidence["urb_progress"] is True
    assert evidence["error_count"] == 1
    assert len(evidence["error_events"]) == 1

    unavailable = lab._usb_health_evidence(
        "usb:1111:2222:1-2",
        node,
        baseline,
        {},
        since_epoch=100.0,
        until_epoch=200.0,
        runner=runner,
    )
    assert unavailable["available"] is False


def test_lab_14_soak_pass_requires_every_measured_metric(lab) -> None:
    assert lab._soak_status(_soak_facts()) == "PASS"
    incomplete = _soak_facts()
    incomplete["usb_errors_observed"]["available"] = False
    assert lab._soak_status(incomplete) == "REQUIRES_OPERATOR_CONFIRMATION"


def test_lab_15_short_clean_soak_stays_incomplete(lab) -> None:
    facts = _soak_facts()
    facts["duration_seconds"] = 7200
    assert lab._soak_status(facts) == "REQUIRES_OPERATOR_CONFIRMATION"


def test_lab_16_r35_accumulates_without_replacing_other_fixtures(lab) -> None:
    merged = lab._merge_r35_fixture(
        {"fixtures": {"end_impulse": {"result": "PASS"}}},
        "nonzero_final_samples",
        {"result": "PASS"},
    )
    assert set(merged) == {"end_impulse", "nonzero_final_samples"}


def test_lab_17_r35_pass_requires_four_valid_fixtures(lab) -> None:
    fixtures = {
        name: {"result": "PASS", "falsifier_observed": False}
        for name in lab.R35_FIXTURES
    }
    assert lab._r35_status(fixtures) == "PASS"
    fixtures.pop("end_impulse")
    assert lab._r35_status(fixtures) == "REQUIRES_OPERATOR_CONFIRMATION"


def test_lab_18_r35_capture_entry_hashes_fixture_and_artifact(lab, tmp_path) -> None:
    media = tmp_path / "tail.wav"
    capture = tmp_path / "capture.wav"
    media.write_bytes(b"fixture")
    capture.write_bytes(b"capture")
    entry = lab._r35_fixture_entry(
        media=media,
        result="PASS",
        evidence_kind="capture",
        evidence_reference=str(capture),
        method="loopback-capture",
        falsifier_observed=False,
    )
    assert entry["fixture_sha256"] == lab._file_sha256(media)
    assert entry["sha256"] == lab._file_sha256(capture)


def test_lab_19_r36_prepare_persists_the_observed_baseline(lab) -> None:
    facts = lab._r36_prepare_facts(
        case="device_failure",
        device_id="usb:1111:2222:1-2",
        locator="hw:CARD=DAC,DEV=0",
        device_generation=4,
        signal_identity=_identity(),
        playback_status="playing",
        operator_reference="operator:session-1",
        usb_instance_before={"sysfs_path": "/sys/1-2", "busnum": 1, "devnum": 5},
        suspend_success_before=10,
    )
    assert facts["state"] == "WAITING_OPERATOR_ACTION"
    assert facts["device_generation_before"] == 4
    assert facts["signal_identity_before"] == _identity()


def test_lab_20_r36_completion_derives_recovery_truth(lab) -> None:
    baseline = lab._r36_prepare_facts(
        case="device_failure",
        device_id="usb:1111:2222:1-2",
        locator="hw:CARD=DAC,DEV=0",
        device_generation=4,
        signal_identity=_identity(execution=2, port=3),
        playback_status="playing",
        operator_reference="operator:session-1",
        usb_instance_before={"sysfs_path": "/sys/1-2", "busnum": 1, "devnum": 5},
        suspend_success_before=10,
    )
    facts = lab._r36_complete_facts(
        baseline,
        after_row={
            "stableDeviceId": "usb:1111:2222:1-2",
            "alsaLocator": "hw:CARD=DAC,DEV=0",
            "available": True,
            "generation": 5,
        },
        after_result={
            "status": lab.PlaybackStatus.PLAYING.value,
            "error_message": None,
            "signal_truth": {
                "identity": _identity(execution=3, port=4),
                "verdict": {"state": "direct_container_adapted"},
            },
        },
        after_usb_instance={
            "sysfs_path": "/sys/1-2",
            "busnum": 1,
            "devnum": 6,
        },
        suspend_success_after=10,
    )
    assert facts["same_identity_after"] is True
    assert facts["generation_fresh"] is True
    assert facts["continuity_proof"] is True
    assert facts["recovery_loop_count"] == 0

    no_device_recovery = lab._r36_complete_facts(
        baseline,
        after_row={
            "stableDeviceId": "usb:1111:2222:1-2",
            "alsaLocator": "hw:CARD=DAC,DEV=0",
            "available": True,
            "generation": 4,
        },
        after_result={
            "status": lab.PlaybackStatus.PLAYING.value,
            "error_message": None,
            "signal_truth": {
                "identity": _identity(execution=99, port=99),
                "verdict": {"state": "direct_container_adapted"},
            },
        },
        after_usb_instance={
            "sysfs_path": "/sys/1-2",
            "busnum": 1,
            "devnum": 5,
        },
        suspend_success_after=10,
    )
    assert no_device_recovery["generation_fresh"] is False
    assert no_device_recovery["continuity_proof"] is False


def test_lab_20b_r36_global_pass_requires_all_accumulated_cases(lab) -> None:
    passing = {
        "incident_retained": True,
        "recovered_state_reported": True,
        "continuity_proof": True,
        "false_verified_after_incident": False,
        "generation_fresh": True,
        "recovery_loop_count": 0,
    }
    cases = {
        "induced_underrun": {
            **passing,
            "case": "induced_underrun",
            "fault_injected": True,
            "xrun_observed": True,
        }
    }
    assert lab._r36_cases_status(cases) == "REQUIRES_OPERATOR_CONFIRMATION"

    cases["suspend_resume"] = {
        **passing,
        "case": "suspend_resume",
        "mechanism_available": True,
        "operator_reference": "operator:suspend",
        "action_completed": True,
        "signal_truth_after": {},
        "suspend_success_before": 4,
        "suspend_success_after": 5,
    }
    assert lab._r36_cases_status(cases) == "REQUIRES_OPERATOR_CONFIRMATION"

    cases["device_failure"] = {
        **passing,
        "case": "device_failure",
        "mechanism_available": True,
        "operator_reference": "operator:device",
        "action_completed": True,
        "same_identity_after": True,
        "physical_reenumeration_observed": True,
    }
    assert lab._r36_cases_status(cases) == "PASS"


def test_lab_command_soak_wires_measured_facts_into_pass(
    lab, tmp_path, monkeypatch
) -> None:
    port = SimpleNamespace(
        _pump=SimpleNamespace(is_alive=lambda: True),
        _pipeline=object(),
        _current_path=Path("song.flac"),
        _pending_path=None,
        _active_direct_handle=SimpleNamespace(plan_id="plan-a", generation=1),
        _generation=1,
        _residual_bus_watches=[],
        _residual_timer_sources=[],
    )
    container = SimpleNamespace(
        _audio_engine_registry=SimpleNamespace(
            provider=lambda engine_id: SimpleNamespace(current_port=port)
        ),
        shutdown=lambda: None,
    )
    result = {
        "status": lab.PlaybackStatus.PLAYING.value,
        "error_message": None,
        "signal_truth_reasons": [],
        "signal_truth": {
            "identity": _identity(execution=1, port=1),
            "decoded": {"rate_hz": 44100},
            "plan": {"requested": {"rate_hz": 44100}},
            "alsa": {"rate_hz": 44100},
            "verdict": {"state": "direct_container_adapted"},
        },
    }
    monotonic = iter((0.0, 1.0, 2.0, 28801.0, 28801.0))
    recorded = {}
    monkeypatch.setattr(lab, "_container", lambda *_args: container)
    monkeypatch.setattr(lab, "_play", lambda *_args: result)
    monkeypatch.setattr(lab, "_stop", lambda *_args: None)
    monkeypatch.setattr(lab, "_process_rss_kb", lambda: 100000)
    monkeypatch.setattr(lab.time, "monotonic", lambda: next(monotonic))
    monkeypatch.setattr(
        lab, "_resolve_usb_sysfs_node", lambda *_args, **_kwargs: tmp_path
    )
    health_snapshots = iter(
        (
            {"busnum": 1, "devnum": 2, "urbnum": 100},
            {"busnum": 1, "devnum": 2, "urbnum": 200},
        )
    )
    monkeypatch.setattr(
        lab, "_read_usb_health_snapshot", lambda _node: next(health_snapshots)
    )
    monkeypatch.setattr(
        lab,
        "_usb_health_evidence",
        lambda *_args, **_kwargs: _soak_facts()["usb_errors_observed"],
    )
    monkeypatch.setattr(
        lab,
        "_record",
        lambda _path, **kwargs: recorded.update(kwargs),
    )
    args = Namespace(
        duration_seconds=28800,
        device_id="usb:1111:2222:1-2",
        locator="hw:CARD=DAC,DEV=0",
        media=[tmp_path / "track.wav"],
        mode="compatible",
        checkpoint_every=1,
        manifest=tmp_path / "manifest.json",
        usb_sysfs_path=None,
        fail_fast=False,
    )
    assert lab.command_soak(args) == 0
    assert recorded["status"] == "PASS"
    assert recorded["facts"]["transition_failures"] == 0
    assert recorded["facts"]["usb_errors_observed"]["error_count"] == 0


def test_lab_command_tail_accumulates_the_fourth_fixture(
    lab, tmp_path, monkeypatch
) -> None:
    media = tmp_path / "tail.wav"
    capture = tmp_path / "capture.wav"
    media.write_bytes(b"fixture")
    capture.write_bytes(b"capture")
    state = SimpleNamespace(status=lab.PlaybackStatus.STOPPED)
    container = SimpleNamespace(
        _playback=SimpleNamespace(state=state), shutdown=lambda: None
    )
    existing = {
        name: {
            "result": "PASS",
            "falsifier_observed": False,
            "playback_error": None,
        }
        for name in lab.R35_FIXTURES[:-1]
    }
    recorded = {}
    monkeypatch.setattr(lab, "_container", lambda *_args: container)
    monkeypatch.setattr(
        lab,
        "_play",
        lambda *_args: {"error_message": None},
    )
    monkeypatch.setattr(lab, "_pump", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        lab,
        "_manifest",
        lambda _path: {"experiments": {"R35": {"facts": {"fixtures": existing}}}},
    )
    monkeypatch.setattr(
        lab,
        "_record",
        lambda _path, **kwargs: recorded.update(kwargs),
    )
    args = Namespace(
        device_id="usb:1111:2222:1-2",
        locator="hw:CARD=DAC,DEV=0",
        manifest=tmp_path / "manifest.json",
        media=media,
        mode="compatible",
        timeout_seconds=1,
        fixture=lab.R35_FIXTURES[-1],
        tail_result="PASS",
        evidence_kind="capture",
        evidence_reference=str(capture),
        method="loopback-capture",
        falsifier_observed=False,
    )
    assert lab.command_tail(args) == 0
    assert recorded["status"] == "PASS"
    assert set(recorded["facts"]["fixtures"]) == set(lab.R35_FIXTURES)


def test_lab_command_fault_complete_uses_the_prepared_baseline(
    lab, tmp_path, monkeypatch
) -> None:
    baseline = lab._r36_prepare_facts(
        case="device_failure",
        device_id="usb:1111:2222:1-2",
        locator="hw:CARD=DAC,DEV=0",
        device_generation=4,
        signal_identity=_identity(execution=2, port=3),
        playback_status=lab.PlaybackStatus.PLAYING.value,
        operator_reference="operator:session-1",
        usb_instance_before={"sysfs_path": "/sys/1-2", "busnum": 1, "devnum": 5},
        suspend_success_before=10,
    )
    container = SimpleNamespace(shutdown=lambda: None)
    recorded = {}
    prior_cases = {
        case: facts
        for case, facts in {
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
                "signal_truth_after": {},
                "suspend_success_before": 1,
                "suspend_success_after": 2,
            },
        }.items()
    }
    monkeypatch.setattr(
        lab,
        "_manifest",
        lambda _path: {
            "experiments": {
                "R36": {
                    "facts": {
                        "cases": prior_cases,
                        "pending_cases": {"device_failure": baseline},
                    }
                }
            }
        },
    )
    monkeypatch.setattr(lab, "_container", lambda *_args: container)
    monkeypatch.setattr(
        lab,
        "_play",
        lambda *_args: {
            "status": lab.PlaybackStatus.PLAYING.value,
            "error_message": None,
            "signal_truth": {
                "identity": _identity(execution=3, port=4),
                "verdict": {"state": "direct_container_adapted"},
            },
        },
    )
    monkeypatch.setattr(
        lab,
        "_row",
        lambda *_args: {
            "stableDeviceId": "usb:1111:2222:1-2",
            "alsaLocator": "hw:CARD=DAC,DEV=0",
            "available": True,
            "generation": 5,
        },
    )
    monkeypatch.setattr(
        lab,
        "_record",
        lambda _path, **kwargs: recorded.update(kwargs),
    )
    monkeypatch.setattr(
        lab,
        "_usb_instance_witness",
        lambda _device_id: {
            "sysfs_path": "/sys/1-2",
            "busnum": 1,
            "devnum": 6,
        },
    )
    monkeypatch.setattr(lab, "_suspend_success_count", lambda: 10)
    args = Namespace(
        case="device_failure",
        device_id="usb:1111:2222:1-2",
        locator="hw:CARD=DAC,DEV=0",
        manifest=tmp_path / "manifest.json",
        media=tmp_path / "track.wav",
        mode="compatible",
    )
    assert lab.command_fault_complete(args) == 0
    assert recorded["status"] == "PASS"
    assert recorded["facts"]["cases"]["device_failure"]["same_identity_after"] is True


def test_lab_command_fault_complete_one_case_cannot_promote_global_pass(
    lab, tmp_path, monkeypatch
) -> None:
    baseline = lab._r36_prepare_facts(
        case="device_failure",
        device_id="usb:1111:2222:1-2",
        locator="hw:CARD=DAC,DEV=0",
        device_generation=4,
        signal_identity=_identity(execution=2, port=3),
        playback_status=lab.PlaybackStatus.PLAYING.value,
        operator_reference="operator:session-1",
        usb_instance_before={"sysfs_path": "/sys/1-2", "busnum": 1, "devnum": 5},
    )
    recorded = {}
    monkeypatch.setattr(
        lab,
        "_manifest",
        lambda _path: {
            "experiments": {
                "R36": {
                    "facts": {
                        "cases": {},
                        "pending_cases": {"device_failure": baseline},
                    }
                }
            }
        },
    )
    monkeypatch.setattr(
        lab, "_container", lambda *_args: SimpleNamespace(shutdown=lambda: None)
    )
    monkeypatch.setattr(
        lab,
        "_play",
        lambda *_args: {
            "status": lab.PlaybackStatus.PLAYING.value,
            "error_message": None,
            "signal_truth": {
                "identity": _identity(execution=3, port=4),
                "verdict": {"state": "direct_container_adapted"},
            },
        },
    )
    monkeypatch.setattr(
        lab,
        "_row",
        lambda *_args: {
            "stableDeviceId": "usb:1111:2222:1-2",
            "alsaLocator": "hw:CARD=DAC,DEV=0",
            "available": True,
            "generation": 5,
        },
    )
    monkeypatch.setattr(lab, "_record", lambda _path, **kwargs: recorded.update(kwargs))
    monkeypatch.setattr(
        lab,
        "_usb_instance_witness",
        lambda _device_id: {"sysfs_path": "/sys/1-2", "busnum": 1, "devnum": 6},
    )
    monkeypatch.setattr(lab, "_suspend_success_count", lambda: None)
    args = Namespace(
        case="device_failure",
        device_id="usb:1111:2222:1-2",
        locator="hw:CARD=DAC,DEV=0",
        manifest=tmp_path / "manifest.json",
        media=tmp_path / "track.wav",
        mode="compatible",
    )
    assert lab.command_fault_complete(args) == 0
    assert recorded["status"] == "REQUIRES_OPERATOR_CONFIRMATION"
