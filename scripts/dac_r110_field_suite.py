"""DAC-V35-110 physical PCM qualification harness (field evidence plumbing).

Runs ONE bounded scenario against the REAL selected DAC through the production
container and writes machine-readable evidence. It never fabricates a physical
claim: audibility is reported as REQUIRES_OPERATOR_CONFIRMATION unless the
operator records it.

Scenarios:
    shared       Shared path baseline (GStreamer engine)
    strict       Strict Direct over a tuple matrix
    compatible   Compatible Direct (bounded container widening)
    transitions  bounded runtime mode transitions
    restart      engine/device/policy persistence across container restarts
    stress       bounded sequential cycles

Usage:
    python scripts/dac_r110_field_suite.py --scenario strict \
        --evidence-dir evidence/dac-v35-110/<dir>
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import time
import wave
from pathlib import Path

MAX_AMPLITUDE_16 = 2**12  # conservative level: never full-scale
MAX_AMPLITUDE_24 = 2**20


def write_pcm_fixture(
    path: Path, *, rate: int, bits: int, seconds: float = 12.0
) -> dict:
    """Deterministic low-level stereo tone fixture (never full-scale)."""
    frames = bytearray()
    total = int(rate * seconds)
    amplitude = MAX_AMPLITUDE_16 if bits == 16 else MAX_AMPLITUDE_24
    for index in range(total):
        sample = int(amplitude * math.sin(2 * math.pi * 440 * index / rate))
        if bits == 16:
            frames.extend(struct.pack("<hh", sample, sample))
        else:
            packed = sample.to_bytes(4, "little", signed=True)[:3]
            frames.extend(packed + packed)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(bits // 8)
        handle.setframerate(rate)
        handle.writeframes(bytes(frames))
    import hashlib

    return {
        "path": str(path),
        "rate_hz": rate,
        "bits": bits,
        "channels": 2,
        "seconds": seconds,
        "amplitude": amplitude,
        "sha256": hashlib.sha256(frames).hexdigest(),
    }


def _signal_truth_diagnostics(container) -> dict | None:
    """R110 §11/§13: normalized Signal Truth view from the domain authority."""
    from michi.domain.signal_truth import signal_truth_snapshot_diagnostics

    recorder = getattr(container, "_signal_truth", None)
    if recorder is None:
        return None
    snapshot = None
    try:
        snapshot = recorder.active_snapshot
    except Exception:  # noqa: BLE001 — recorder boundary
        snapshot = None
    if snapshot is None:
        try:
            snapshot = recorder.candidate_snapshot
        except Exception:  # noqa: BLE001 — recorder boundary
            snapshot = None
    if snapshot is None:
        return None
    return signal_truth_snapshot_diagnostics(snapshot)


def _execution_git_head() -> str:
    """R110 §24: derive the executed SHA from the repository, never hand-enter."""
    import subprocess

    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=15,
        ).stdout.strip()
    except Exception:  # noqa: BLE001 — provenance boundary
        return ""


def _validate_device(container, *, device_id: str, locator: str) -> None:
    """R110 §23: never trust hardcoded physical defaults."""
    rows = [
        row for row in container._aob.devices if row.get("stableDeviceId") == device_id
    ]
    if not rows:
        raise SystemExit(f"device not present after rediscovery: {device_id}")
    current = rows[0].get("alsaLocator")
    if current != locator:
        raise SystemExit(
            f"locator mismatch: requested {locator!r} but discovery resolved "
            f"{current!r}; aborting the physical run"
        )
    if not rows[0].get("bindingAvailable"):
        raise SystemExit(f"device binding unavailable: {device_id}")


def _source_section(fixture: dict) -> dict:
    """R110 §15: fixture truth is immutable and runtime never overwrites it."""
    return {
        "path": str(fixture.get("path")),
        "sha256": fixture.get("sha256"),
        "format_family": "PCM",
        "rate_hz": fixture.get("rate_hz"),
        "channels": fixture.get("channels"),
        "significant_bits": fixture.get("bits"),
        "seconds": fixture.get("seconds"),
        "amplitude": fixture.get("amplitude"),
    }


def _capture(container, extra: dict | None = None) -> dict:
    state = container._playback.state
    plan = container._output_session.plan
    plan_facts = None
    if plan is not None:
        plan_facts = {
            "plan_id": plan.plan_id,
            "requested_pcm": {
                "rate_hz": plan.requested_pcm.rate_hz,
                "format": plan.requested_pcm.transport_format,
                "channels": plan.requested_pcm.channels,
                "significant_bits": plan.requested_pcm.significant_bits,
            },
            "carrier_adaptation": plan.carrier_adaptation,
            "decision_codes": list(plan.decision_codes),
            "sink": f"{plan.sink.factory}:{plan.sink.device}",
            "binding_locator": plan.binding.locator,
            "volume_policy": plan.volume_policy.value,
        }
    return {
        "playback_status": state.status.value,
        "file_path": str(state.file_path) if state.file_path else None,
        "error_code": state.error_code,
        "error_message": state.error_message,
        "output_mode": container._output_session.mode,
        "output_state": container._output_session.state.value,
        "plan": plan_facts,
        "direct_handle": container._direct_output_lifecycle.handle is not None
        if hasattr(container._direct_output_lifecycle, "handle")
        else None,
        "signal_truth_diagnostics": _signal_truth_diagnostics(container),
        "signal_truth_label": container._aob.signalTruthLabel,
        "signal_truth_reasons": list(container._aob.signalTruthReasonCodes),
        "format": container._aob.currentFormat,
        "channels": container._aob.currentChannels,
        "significant_bits": container._aob.significantBits,
        "source_rate": container._aob.currentSourceRate,
        "device_rate": container._aob.currentDeviceRate,
        "failure_code": container._aob.lastFailureCode,
        "failure_title": container._aob.lastFailureTitle,
        "failure_display": container._aob.lastFailureDisplay,
        "selected_device": container._aob.selectedDeviceId,
        "selected_path_mode": container._aob.selectedPathMode,
        "active_engine": container._audio_engine_service.state.active_engine_id.value,
        "receipt": extra or {},
    }


def _pump(container, seconds: float, *, settled=None) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        container._app.processEvents()
        time.sleep(0.02)
        if settled is not None and settled():
            container._app.processEvents()
            return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--device-id", default="usb:152a:85dd:3-3.3.2")
    parser.add_argument("--locator", default="hw:CARD=AUDIO,DEV=0")
    args = parser.parse_args()

    from michi.bootstrap import ApplicationContainer
    from michi.domain.audio_engine import AudioEngineId
    from michi.domain.playback import PlaybackStatus

    evidence_dir = Path(args.evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    fixtures_dir = evidence_dir / "fixtures"
    fixtures_dir.mkdir(exist_ok=True)

    try:
        from michi.application.dac_qualification_service import (
            default_environment_fingerprint,
        )

        _env_fingerprint = default_environment_fingerprint()
    except Exception:  # noqa: BLE001 — provenance boundary, never mask the run
        _env_fingerprint = ""

    report: dict = {
        "schema_version": 2,
        "execution_git_head": _execution_git_head(),
        "environment_fingerprint": _env_fingerprint,
        "experiment": f"R110 field scenario: {args.scenario}",
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "device_id": args.device_id,
        "locator": args.locator,
        "observations": [],
        "audible": "REQUIRES_OPERATOR_CONFIRMATION",
    }

    if args.scenario in {"restart", "stress"}:
        report["fixtures"] = {
            "16_44100": write_pcm_fixture(
                evidence_dir / "fixtures" / "pcm16_44100.wav", rate=44_100, bits=16
            ),
            "24_44100": write_pcm_fixture(
                evidence_dir / "fixtures" / "pcm24_44100.wav", rate=44_100, bits=24
            ),
        }
    if args.scenario in {"shared", "strict", "compatible", "transitions"}:
        fixtures = {
            key: write_pcm_fixture(
                fixtures_dir / f"pcm{key.split('_')[0]}_{key.split('_')[1]}.wav",
                rate=int(key.split("_")[1]),
                bits=int(key.split("_")[0]),
            )
            for key in (
                "16_44100",
                "16_48000",
                "16_96000",
                "24_44100",
                "24_48000",
                "24_96000",
                "24_192000",
            )
        }
        report["fixtures"] = fixtures

    if args.scenario == "shared":
        selection = ["shared"]
    elif args.scenario == "strict":
        selection = ["strict"] * 7
    elif args.scenario == "transitions":
        selection = ["shared", "strict", "shared", "compatible", "shared"]
    else:
        selection = ["compatible"] * 4

    if args.scenario == "restart":
        cycles = []
        for index in range(3):
            cycle_container = ApplicationContainer()
            entry: dict = {"cycle": index + 1}
            try:
                cycle_container.initialize()
                entry["selected_device"] = cycle_container._aob.selectedDeviceId
                entry["selected_path_mode"] = cycle_container._aob.selectedPathMode
                entry["active_engine"] = (
                    cycle_container._audio_engine_service.state.active_engine_id.value
                )
                entry["playback_status_after_boot"] = (
                    cycle_container._playback.state.status.value
                )
                entry["autoplay_fabricated"] = (
                    cycle_container._playback.state.status.value == 2
                )
                entry["error_message"] = cycle_container._playback.state.error_message
                deadline = time.monotonic() + 12.0
                while time.monotonic() < deadline:
                    cycle_container._app.processEvents()
                    if cycle_container._audio_engine_service.state.active_engine_id:
                        break
                    time.sleep(0.05)
            finally:
                cycle_container.shutdown()
            entry["shutdown_clean"] = True
            cycles.append(entry)
        report["observations"] = cycles
        (evidence_dir / "restart_matrix.json").write_text(
            json.dumps(report, indent=2, default=str), encoding="utf-8"
        )
        print(f"evidence written: {evidence_dir / 'restart_matrix.json'}")
        for cycle in cycles:
            print(
                "cycle",
                cycle["cycle"],
                "| engine",
                cycle["active_engine"],
                "| mode",
                cycle["selected_path_mode"],
                "| device",
                cycle["selected_device"] or "(none)",
                "| status after boot",
                cycle["playback_status_after_boot"],
                "| shutdown clean",
                cycle["shutdown_clean"],
            )
        return 0

    container = ApplicationContainer()
    try:
        container.initialize()
        # The persisted session snapshot triggers a startup restore; the engine
        # switch requires quiescence, so wait (bounded) for the container to
        # settle instead of forcing the transition.
        deadline = time.monotonic() + 15.0
        while time.monotonic() < deadline:
            readiness = container._playback.engine_switch_readiness()
            if readiness.allowed:
                break
            container._app.processEvents()
            time.sleep(0.05)
        report["engine_switch_ready"] = (
            container._playback.engine_switch_readiness().allowed
        )
        container._engine_selection_coordinator.switch_to(AudioEngineId.GSTREAMER)
        # The switch is asynchronous: wait (bounded) for the lease to release
        # and for the engine to become active before issuing playback intents.
        switch_deadline = time.monotonic() + 20.0
        while time.monotonic() < switch_deadline:
            container._app.processEvents()
            if (
                container._audio_engine_service.state.active_engine_id
                is AudioEngineId.GSTREAMER
            ):
                break
            time.sleep(0.05)
        report["active_engine_after_switch"] = (
            container._audio_engine_service.state.active_engine_id.value
        )
        _validate_device(container, device_id=args.device_id, locator=args.locator)
        container._aob.select_device(args.device_id)

        if args.scenario == "stress":
            failures: list[dict] = []
            media16 = Path(report["fixtures"]["16_44100"]["path"])
            media24 = Path(report["fixtures"]["24_44100"]["path"])
            cycles: list[dict] = []

            def run_cycle(index: int, mode: str, media: Path, kind: str) -> None:
                entry = {"iteration": index, "kind": kind, "mode": mode}
                try:
                    container._aob.select_path_mode(mode)
                    container._playback.load_and_play(media)
                    deadline = time.monotonic() + 8.0
                    while time.monotonic() < deadline:
                        container._app.processEvents()
                        if container._playback.state.status is PlaybackStatus.PLAYING:
                            break
                        if container._playback.state.error_message:
                            break
                        time.sleep(0.02)
                    entry["status"] = container._playback.state.status.value
                    entry["error"] = container._playback.state.error_message
                    entry["output_mode"] = container._output_session.mode
                    container._playback.stop()
                    deadline = time.monotonic() + 3.0
                    while time.monotonic() < deadline:
                        container._app.processEvents()
                        if container._playback.state.status is PlaybackStatus.STOPPED:
                            break
                        time.sleep(0.02)
                    entry["stopped"] = (
                        container._playback.state.status is PlaybackStatus.STOPPED
                    )
                except Exception as exc:  # noqa: BLE001 — recorded as field evidence
                    entry["exception"] = f"{type(exc).__name__}: {exc}"
                    failures.append(entry)
                cycles.append(entry)

            for index in range(10):
                run_cycle(index + 1, "shared", media16, "sequential_load_stop")
            for index in range(10):
                run_cycle(index + 11, "shared", media16, "stop_play_cycle")
            for index in range(5):
                run_cycle(index + 21, "compatible", media24, "mode_transition")
                run_cycle(index + 21, "shared", media16, "mode_transition")
            report["observations"] = cycles
            report["failures"] = failures
            (evidence_dir / "stress_matrix.json").write_text(
                json.dumps(report, indent=2, default=str), encoding="utf-8"
            )
            played = [c for c in cycles if c.get("status") == 2]
            stopped = [c for c in cycles if c.get("stopped")]
            print(f"evidence written: {evidence_dir / 'stress_matrix.json'}")
            print(
                f"cycles={len(cycles)} played={len(played)} "
                f"stopped={len(stopped)} failures={len(failures)}"
            )
            return 0

        if args.scenario == "shared":
            container._aob.select_path_mode("shared")
            targets = ["16_44100"]
        elif args.scenario == "strict":
            targets = [
                "16_44100",
                "16_48000",
                "16_96000",
                "24_44100",
                "24_48000",
                "24_96000",
                "24_192000",
            ]
        elif args.scenario == "transitions":
            targets = ["16_44100", "16_44100", "24_44100", "24_44100", "16_44100"]
        else:
            targets = ["16_44100", "16_48000", "16_96000", "24_44100"]

        for mode, key in zip(selection, targets, strict=True):
            container._aob.select_path_mode(mode)
            media = Path(report["fixtures"][key]["path"])
            container._playback.load_and_play(media)
            # Capture WHILE the intent is live: wait (bounded) for PLAYING or
            # for a contained failure, never after the fixture has ended.
            deadline = time.monotonic() + 12.0
            while time.monotonic() < deadline:
                container._app.processEvents()
                state = container._playback.state
                if state.status is PlaybackStatus.PLAYING or state.error_message:
                    break
                time.sleep(0.02)
            container._app.processEvents()
            captured = _capture(container, {"mode": mode, "fixture": key})
            entry = {
                "source": _source_section(report["fixtures"][key]),
                "request": {
                    "mode": mode,
                    "fixture": key,
                    "requested_rate_hz": report["fixtures"][key].get("rate_hz"),
                    "requested_significant_bits": report["fixtures"][key].get("bits"),
                    "requested_channels": report["fixtures"][key].get("channels"),
                },
                "playback": {
                    "status": captured.get("playback_status"),
                    "file_path": captured.get("file_path"),
                    "error_code": captured.get("error_code"),
                    "error_message": captured.get("error_message"),
                },
                "output": {
                    "mode": captured.get("output_mode"),
                    "state": captured.get("output_state"),
                    "selected_device": captured.get("selected_device"),
                    "selected_path_mode": captured.get("selected_path_mode"),
                    "failure_code": captured.get("failure_code"),
                    "failure_title": captured.get("failure_title"),
                    "failure_display": captured.get("failure_display"),
                    "active_engine": captured.get("active_engine"),
                },
                "plan": captured.get("plan"),
                "signal_truth": captured.get("signal_truth_diagnostics"),
                "receipt": {
                    "mode": mode,
                    "fixture": key,
                    "label": captured.get("signal_truth_label"),
                    "reasons": captured.get("signal_truth_reasons"),
                },
            }
            report["observations"].append(entry)
            container._playback.stop()
            _pump(container, 1.0)

        report["after_cycles"] = _capture(container)
    finally:
        container.shutdown()

    (evidence_dir / f"{args.scenario}_matrix.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8"
    )
    print(f"evidence written: {evidence_dir / (args.scenario + '_matrix.json')}")
    for entry in report["observations"]:
        plan = entry.get("plan") or {}
        print(
            entry["receipt"]["fixture"],
            entry["receipt"]["mode"],
            "|",
            entry["playback"]["status"],
            "|",
            (plan.get("requested_pcm") or {}).get("format"),
            (plan.get("carrier_adaptation") or "-"),
            "|",
            entry["playback"]["error_code"] or "ok",
            "|",
            entry["output"]["failure_title"] or "-",
        )
    print()
    print("FIELD OBSERVATION REQUIRED")
    print()
    print("Test:")
    print(f"  scenario={args.scenario} on {args.device_id} ({args.locator})")
    print()
    print("Expected:")
    print("  audible low-level 440 Hz tone during each cycle; stable playback")
    print()
    print("Please record:")
    print("  PASS | FAIL | NOT_OBSERVED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
