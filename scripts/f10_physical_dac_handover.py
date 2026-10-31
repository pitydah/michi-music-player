#!/usr/bin/env python3
"""AP2-F10 physical DAC handover evidence.

Switches a playing Direct PCM fixture between two real DACs and records the
observed production identity, plan, transition kind, ALSA sink and Signal
Truth at every step. Audibility is never inferred: the report is explicitly
marked REQUIRES_OPERATOR_CONFIRMATION.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dac_r110_field_suite import write_pcm_fixture  # noqa: E402

from michi.bootstrap import ApplicationContainer  # noqa: E402
from michi.domain.playback import PlaybackStatus  # noqa: E402

DEFAULT_A = "usb:152a:85dd:3-3.3.2"
DEFAULT_B = "usb:2fc6:f882:HA01"
AUDIBILITY = "REQUIRES_OPERATOR_CONFIRMATION"


def _device_rows(container) -> list[dict]:
    return list(getattr(container._aob, "devices", ()) or ())


def _device_row(container, stable_device_id: str) -> dict:
    for row in _device_rows(container):
        if row.get("stableDeviceId") == stable_device_id:
            return row
    known = ", ".join(str(row.get("stableDeviceId")) for row in _device_rows(container))
    raise SystemExit(f"device {stable_device_id!r} not found; known: {known}")


def _pump(container, seconds: float, settled=None) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        container._app.processEvents()
        time.sleep(0.02)
        if settled is not None and settled():
            container._app.processEvents()
            return True
    return False


def _snapshot(container, tag: str) -> dict:
    session = container._output_session
    playback = container._playback.state
    plan = session.plan
    binding = getattr(plan, "binding", None) if plan is not None else None
    sink = getattr(plan, "sink", None) if plan is not None else None
    transition = getattr(session, "last_transition_kind", None)
    handover = getattr(session, "handover_state", None)
    return {
        "tag": tag,
        "status": playback.status.name.lower(),
        "error": playback.error_message,
        "mode": session.mode,
        "output_state": session.state.value,
        "generation": session.generation,
        "selected_device_id": container._aob.selectedDeviceId,
        "path_mode": container._aob.selectedPathMode,
        "plan_id": getattr(plan, "plan_id", None),
        "execution_id": session.active_execution_id,
        "device_locator": getattr(binding, "locator", None),
        "sink": (f"{sink.factory}:{sink.device}" if sink is not None else None),
        "transition_kind": getattr(transition, "value", transition),
        "handover_state": getattr(handover, "value", handover),
        "handover_target": session.handover_target_family,
        "last_release_evidence": session.last_release_evidence,
        "last_handover_release_evidence": (session.last_handover_release_evidence),
        "failure_code": container._aob.lastFailureCode,
        "failure_title": container._aob.lastFailureTitle,
        "signal_truth": container._aob.signalTruthLabel,
    }


def _wait_playing(container, device: str, locator: str, timeout: float) -> bool:
    def ready() -> bool:
        state = container._playback.state
        if state.error_message:
            return True
        plan = container._output_session.plan
        binding = getattr(plan, "binding", None) if plan is not None else None
        return (
            state.status is PlaybackStatus.PLAYING
            and container._aob.selectedDeviceId == device
            and container._output_session.state.value == "running"
            and getattr(binding, "locator", None) == locator
        )

    return _pump(container, timeout, ready)


def _settle(container, timeout: float = 10.0, quiet: float = 1.0) -> bool:
    """Wait until selection, transport and output generation stop moving."""
    deadline = time.monotonic() + timeout
    last = None
    stable_since = time.monotonic()
    while time.monotonic() < deadline:
        container._app.processEvents()
        current = (
            container._aob.selectedDeviceId,
            container._aob.selectedPathMode,
            container._playback.state.status.name,
            container._playback.state.error_code,
            container._output_session.generation,
            container._output_session.state.value,
        )
        now = time.monotonic()
        if current != last:
            last = current
            stable_since = now
        elif now - stable_since >= quiet:
            return True
        time.sleep(0.02)
    return False


def _run_direction(
    container,
    *,
    source: str,
    target: str,
    source_locator: str,
    target_locator: str,
    fixture: Path,
    timeout: float,
) -> dict:
    # Each direction starts from a stopped transport. Selecting a device while
    # media is still playing opens a handover restore; issuing a new user play
    # on top of it would race two preparations, which is a separate finding.
    # This harness proves the source -> target transition, not that race.
    if container._playback.state.status is not PlaybackStatus.STOPPED:
        container._playback.stop()
        _pump(
            container,
            3.0,
            lambda: container._playback.state.status is PlaybackStatus.STOPPED,
        )
    # Do not re-select an already selected device/mode: that would schedule a
    # handover restore and race the user play this harness is about to issue.
    if container._aob.selectedDeviceId != source:
        container._aob.select_device_for_playback(source)
    if container._aob.selectedPathMode != "compatible":
        container._aob.select_path_mode("compatible")
    _settle(container)
    container._playback.load_and_play(fixture)
    source_ready = _wait_playing(container, source, source_locator, timeout)
    source_step = _snapshot(container, f"source:{source}")
    if not source_ready or source_step["status"] != "playing":
        return {
            "source": source,
            "target": target,
            "steps": [source_step],
            "result": "FAIL",
            "failure": "the source never reached RUNNING/PLAYING",
        }

    container._aob.select_device_for_playback(target)
    target_ready = _wait_playing(container, target, target_locator, timeout)
    target_step = _snapshot(container, f"target:{target}")
    failures = [
        value
        for value in (
            target_step.get("failure_code"),
            target_step.get("failure_title"),
        )
        if value
    ]
    errors = [target_step["error"]] if target_step.get("error") else []
    passed = (
        target_ready
        and target_step["status"] == "playing"
        and target_step["selected_device_id"] == target
        and target_step["output_state"] == "running"
        and target_step["device_locator"] == target_locator
        and target_step["plan_id"] != source_step["plan_id"]
        and not failures
        and not errors
    )
    result = {
        "source": source,
        "target": target,
        "steps": [source_step, target_step],
        "result": "PASS" if passed else "FAIL",
        "checks": {
            "source_playing": source_step["status"] == "playing",
            "target_playing": target_step["status"] == "playing",
            "target_selected": target_step["selected_device_id"] == target,
            "target_running": target_step["output_state"] == "running",
            "no_failure": not failures and not errors,
            "plan_changed": target_step["plan_id"] != source_step["plan_id"],
            "locator_changed": (
                target_step["device_locator"] != source_step["device_locator"]
            ),
        },
        "failures": failures + errors,
    }
    if not passed:
        result["failure"] = "target did not reach RUNNING/PLAYING on the new DAC"
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device-a", default=DEFAULT_A)
    parser.add_argument("--device-b", default=DEFAULT_B)
    parser.add_argument("--locator-a", default="")
    parser.add_argument("--locator-b", default="")
    parser.add_argument("--direction", choices=("ab", "ba", "both"), default="both")
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--seconds", type=float, default=12.0)
    parser.add_argument("--timeout", type=float, default=25.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    evidence_dir = Path(args.evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    fixture = evidence_dir / "pcm16_44100.wav"
    fixture_meta = write_pcm_fixture(fixture, rate=44100, bits=16, seconds=args.seconds)

    container = ApplicationContainer()
    container.initialize()
    reports: list[dict] = []
    exit_code = 0
    try:
        _pump(container, 1.0)
        row_a = _device_row(container, args.device_a)
        row_b = _device_row(container, args.device_b)
        for flag, row in (("locator_a", row_a), ("locator_b", row_b)):
            requested = getattr(args, flag)
            expected = str(row.get("alsaLocator") or "")
            if requested and requested != expected:
                raise SystemExit(
                    f"{flag} mismatch: requested {requested!r} but discovery "
                    f"resolved {expected!r}"
                )

        locators = {
            args.device_a: str(row_a.get("alsaLocator") or ""),
            args.device_b: str(row_b.get("alsaLocator") or ""),
        }
        directions: list[tuple[str, str]]
        if args.direction == "ab":
            directions = [(args.device_a, args.device_b)]
        elif args.direction == "ba":
            directions = [(args.device_b, args.device_a)]
        else:
            directions = [
                (args.device_a, args.device_b),
                (args.device_b, args.device_a),
            ]

        for source, target in directions:
            report = _run_direction(
                container,
                source=source,
                target=target,
                source_locator=locators[source],
                target_locator=locators[target],
                fixture=fixture,
                timeout=args.timeout,
            )
            report.update(
                {
                    "schema": "michi.f10.physical_dac_handover.v1",
                    "generated_at": datetime.now(UTC).isoformat(),
                    "fixture": fixture_meta,
                    "physical_dac": True,
                    "audibility": AUDIBILITY,
                    "certification_claim": "NONE",
                }
            )
            name = "handover_ab.json" if source == args.device_a else "handover_ba.json"
            (evidence_dir / name).write_text(
                json.dumps(report, indent=2, default=str) + "\n"
            )
            reports.append(
                {
                    "file": name,
                    "source": source,
                    "target": target,
                    "result": report["result"],
                }
            )
            if report["result"] != "PASS":
                exit_code = 1
    finally:
        try:
            container._playback.stop()
            _pump(container, 1.0)
        finally:
            container.shutdown()

    matrix = {
        "schema": "michi.f10.physical_dac_handover_matrix.v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "directions": reports,
        "result": "PASS"
        if reports and all(item["result"] == "PASS" for item in reports)
        else "FAIL",
        "physical_dac": True,
        "audibility": AUDIBILITY,
        "certification_claim": "NONE",
    }
    (evidence_dir / "handover_matrix.json").write_text(
        json.dumps(matrix, indent=2) + "\n"
    )
    print(json.dumps(matrix, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
