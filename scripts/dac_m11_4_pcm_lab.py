#!/usr/bin/env python3
"""M11.4 PCM physical-closure laboratory.

This is field tooling, not a production authority. It uses the production
ApplicationContainer and Signal Truth but never upgrades an observation into a
claim without explicit evidence. Device identity and ALSA locator are mandatory:
there are no SMSL/Kinmax/vendor defaults.

The lab writes one schema-v1 manifest per physical DAC. R24/R25/R32/R35/R36 are
the required PCM closure experiments. R27/R29/R30 and DAC-V35-120/130/140 stay
out of scope.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from michi.application.dac_pcm_closure import (
    PcmClosureEvidenceError,
    evaluate_device_manifest,
    load_manifest,
    summarize_manifests,
    summary_to_dict,
)
from michi.domain.audio_engine import AudioEngineId
from michi.domain.playback import PlaybackStatus
from michi.domain.signal_truth import signal_truth_snapshot_diagnostics


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    tmp.replace(path)


def _git_head() -> str:
    import subprocess

    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return completed.stdout.strip()


def _pump(container, seconds: float, *, settled=None) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        container._app.processEvents()
        if settled is not None and settled():
            container._app.processEvents()
            return
        time.sleep(0.02)


def _rows(container) -> list[dict[str, Any]]:
    return [dict(row) for row in container._aob.devices if not row.get("isShared")]


def _row(container, device_id: str, locator: str) -> dict[str, Any]:
    matches = [
        row for row in _rows(container) if row.get("stableDeviceId") == device_id
    ]
    if len(matches) != 1:
        raise SystemExit(
            f"expected exactly one discovered device {device_id!r}, got {len(matches)}"
        )
    row = matches[0]
    if row.get("alsaLocator") != locator:
        raise SystemExit(
            f"locator mismatch for {device_id}: requested {locator!r}, "
            f"discovery reports {row.get('alsaLocator')!r}"
        )
    if not row.get("bindingAvailable") or not row.get("available"):
        raise SystemExit(f"device is not currently playback-capable: {device_id}")
    return row


def _container(device_id: str, locator: str):
    from michi.bootstrap import ApplicationContainer

    container = ApplicationContainer()
    container.initialize()
    _pump(container, 1.0)
    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline:
        readiness = container._playback.engine_switch_readiness()
        if readiness.allowed:
            break
        container._app.processEvents()
        time.sleep(0.05)
    if not container._playback.engine_switch_readiness().allowed:
        container.shutdown()
        raise SystemExit("playback runtime did not become safe for engine selection")
    container._engine_selection_coordinator.switch_to(AudioEngineId.GSTREAMER)
    _pump(
        container,
        20.0,
        settled=lambda: (
            container._audio_engine_service.state.active_engine_id
            is AudioEngineId.GSTREAMER
        ),
    )
    if (
        container._audio_engine_service.state.active_engine_id
        is not AudioEngineId.GSTREAMER
    ):
        container.shutdown()
        raise SystemExit("GStreamer did not become the active engine")
    _row(container, device_id, locator)
    container._aob.select_device(device_id)
    return container


def _truth(container) -> dict[str, Any] | None:
    recorder = getattr(container, "_signal_truth", None)
    if recorder is None:
        return None
    snapshot = None
    with contextlib.suppress(Exception):  # field boundary: no evidence yet
        snapshot = recorder.active_snapshot
    if snapshot is None:
        try:
            snapshot = recorder.candidate_snapshot
        except Exception:  # noqa: BLE001 - field boundary
            return None
    return signal_truth_snapshot_diagnostics(snapshot)


def _play(container, media: Path, mode: str) -> dict[str, Any]:
    if not media.is_file():
        raise SystemExit(f"media fixture does not exist: {media}")
    container._aob.select_path_mode(mode)
    container._playback.load_and_play(media)
    _pump(
        container,
        15.0,
        settled=lambda: (
            container._playback.state.status is PlaybackStatus.PLAYING
            or bool(container._playback.state.error_message)
        ),
    )
    truth = _truth(container)
    return {
        "status": container._playback.state.status.value,
        "error_code": container._playback.state.error_code,
        "error_message": container._playback.state.error_message,
        "signal_truth": truth,
        "signal_truth_label": container._aob.signalTruthLabel,
        "signal_truth_reasons": list(container._aob.signalTruthReasonCodes),
    }


def _stop(container) -> None:
    container._playback.stop()
    _pump(
        container,
        5.0,
        settled=lambda: container._playback.state.status is PlaybackStatus.STOPPED,
    )


def _manifest(path: Path) -> dict[str, Any]:
    payload = load_manifest(path)
    if payload.get("execution_git_head") != _git_head():
        raise SystemExit(
            "manifest execution_git_head does not match current HEAD; "
            "create a fresh manifest before collecting physical evidence"
        )
    return payload


def _record(
    path: Path,
    *,
    experiment: str,
    status: str,
    evidence: list[str],
    facts: dict[str, Any],
) -> None:
    payload = _manifest(path)
    item = payload["experiments"][experiment]
    if item.get("status") == "PASS":
        raise SystemExit(
            f"{experiment} is already PASS; physical evidence is append-only. "
            "Create a new manifest for a new run."
        )
    item.update(
        {
            "status": status,
            "executed": status in {"PASS", "FAIL"},
            "evidence": evidence,
            "facts": facts,
            "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
    )
    payload.setdefault("events", []).append(
        {
            "experiment": experiment,
            "status": status,
            "evidence": list(evidence),
            "facts": facts,
            "captured_at": item["captured_at"],
        }
    )
    _write_json(path, payload)
    try:
        verdict = evaluate_device_manifest(payload)
    except PcmClosureEvidenceError as exc:
        raise SystemExit(f"manifest became invalid: {exc}") from exc
    print(f"{experiment}: {status}; device verdict={verdict.verdict}")


def command_inventory(args) -> int:
    from michi.bootstrap import ApplicationContainer

    container = ApplicationContainer()
    try:
        container.initialize()
        _pump(container, 1.0)
        payload = {
            "schema_version": 1,
            "execution_git_head": _git_head(),
            "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "devices": [
                {
                    key: row.get(key)
                    for key in (
                        "stableDeviceId",
                        "displayName",
                        "manufacturer",
                        "product",
                        "vendorId",
                        "productId",
                        "bcdDevice",
                        "alsaLocator",
                        "deviceCategory",
                        "playbackEndpointCount",
                        "captureCapable",
                        "available",
                        "bindingAvailable",
                        "environmentFingerprint",
                    )
                }
                for row in _rows(container)
            ],
        }
    finally:
        container.shutdown()
    if args.output:
        _write_json(args.output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def command_init(args) -> int:
    container = _container(args.device_id, args.locator)
    try:
        row = _row(container, args.device_id, args.locator)
        qualification = container._aob._qualification
        if qualification is None:
            raise SystemExit("DAC qualification authority unavailable")
        context = qualification.current_environment_context(args.device_id)
        if not context.complete_for_current_evidence:
            raise SystemExit("device-bound qenv is incomplete")
        payload = {
            "schema_version": 1,
            "execution_git_head": _git_head(),
            "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "environment_fingerprint": qualification.current_environment_fingerprint(
                args.device_id
            ),
            "environment_context": asdict(context),
            "device": {
                "label": args.label,
                "stable_device_id": args.device_id,
                "locator": args.locator,
                "vendor_id": row.get("vendorId") or "",
                "product_id": row.get("productId") or "",
                "bcd_device": row.get("bcdDevice") or "",
                "manufacturer": row.get("manufacturer") or "",
                "product": row.get("product") or "",
                "descriptor_hash": "",
                "display_name": row.get("displayName") or "",
            },
            "experiments": {
                experiment: {
                    "status": "NOT_RUN",
                    "executed": False,
                    "evidence": [],
                    "facts": {},
                }
                for experiment in ("R24", "R25", "R32", "R35", "R36")
            },
            "events": [],
            "claim_firewall": {
                "bit_perfect": False,
                "exclusive": False,
                "M11.5": "OUT_OF_SCOPE",
                "DAC-V35-120": "OUT_OF_SCOPE",
                "DAC-V35-130": "POST_STABLE",
                "DAC-V35-140": "SEPARATE_PROMOTION",
            },
        }
        _write_json(args.manifest, payload)
    finally:
        container.shutdown()
    print(f"manifest initialized: {args.manifest}")
    return 0


def command_clock(args) -> int:
    container = _container(args.device_id, args.locator)
    try:
        result = _play(container, args.media, args.mode)
        truth = result["signal_truth"] or {}
        clock = truth.get("clock") if isinstance(truth, dict) else {}
        reasons = (
            ((truth.get("verdict") or {}).get("reason_codes") or []) if truth else []
        )
        facts = {
            "sink_provides_clock": (clock or {}).get("sink_provides_clock"),
            "sink_clock_is_pipeline_clock": (clock or {}).get(
                "sink_clock_is_pipeline_clock"
            ),
            "slave_method": (clock or {}).get("slave_method"),
            "resampling_observed": "ST_RESAMPLER_PRESENT" in reasons,
            "signal_truth_state": (
                (truth.get("verdict") or {}).get("state") if truth else None
            ),
        }
        status = (
            "PASS"
            if result["status"] == PlaybackStatus.PLAYING.value
            and facts["sink_provides_clock"] is True
            and facts["sink_clock_is_pipeline_clock"] is True
            and facts["resampling_observed"] is False
            else "FAIL"
        )
        _record(
            args.manifest,
            experiment="R24",
            status=status,
            evidence=[f"runtime:{args.media}", "SignalTruth.clock"],
            facts=facts,
        )
    finally:
        with __import__("contextlib").suppress(Exception):
            _stop(container)
        container.shutdown()
    return 0


def command_transition(args) -> int:
    if len(args.media) != 7:
        raise SystemExit(
            "R25 requires seven fixtures in this order: "
            "44.1, 44.1, 48, 44.1, 96, 192, 44.1 kHz"
        )
    container = _container(args.device_id, args.locator)
    observed_rates: list[int] = []
    stale = False
    receipts: list[dict[str, Any]] = []
    try:
        previous_identity = None
        for media in args.media:
            result = _play(container, media, args.mode)
            truth = result["signal_truth"] or {}
            decoded = truth.get("decoded") if isinstance(truth, dict) else None
            identity = truth.get("identity") if isinstance(truth, dict) else None
            rate = int((decoded or {}).get("rate_hz") or 0)
            observed_rates.append(rate)
            if previous_identity is not None and identity == previous_identity:
                stale = True
            previous_identity = identity
            receipts.append(
                {
                    "media": str(media),
                    "rate_hz": rate,
                    "identity": identity,
                    "verdict": truth.get("verdict")
                    if isinstance(truth, dict)
                    else None,
                    "error": result["error_message"],
                }
            )
            _stop(container)
        edges = [
            f"{left}->{right}"
            for left, right in zip(observed_rates[:-1], observed_rates[1:], strict=True)
        ]
        first_sample_result = args.first_sample_result
        facts = {
            "transition_edges": edges,
            "first_sample_result": first_sample_result,
            "stale_generation_observed": stale,
            "receipts": receipts,
        }
        status = (
            "PASS"
            if first_sample_result == "PASS"
            and not stale
            and all(rate > 0 for rate in observed_rates)
            else "FAIL"
            if first_sample_result == "FAIL" or stale
            else "REQUIRES_OPERATOR_CONFIRMATION"
        )
        _record(
            args.manifest,
            experiment="R25",
            status=status,
            evidence=[f"runtime:{media}" for media in args.media],
            facts=facts,
        )
    finally:
        container.shutdown()
    return 0


def command_soak(args) -> int:
    if args.duration_seconds <= 0:
        raise SystemExit("--duration-seconds must be > 0")
    container = _container(args.device_id, args.locator)
    started = time.monotonic()
    errors: list[str] = []
    cycles = 0
    xrun_count = 0
    try:
        while time.monotonic() - started < args.duration_seconds:
            media = args.media[cycles % len(args.media)]
            result = _play(container, media, args.mode)
            reasons = result.get("signal_truth_reasons") or []
            if "ST_XRUN" in reasons:
                xrun_count += 1
            if result["error_message"]:
                errors.append(str(result["error_message"]))
            cycles += 1
            _stop(container)
            if errors and args.fail_fast:
                break
        duration = time.monotonic() - started
        facts = {
            "duration_seconds": duration,
            "cycles": cycles,
            "xrun_count": xrun_count,
            "runtime_error_count": len(errors),
            "errors": errors[:20],
        }
        status = (
            "PASS"
            if duration >= 28800 and not errors and xrun_count == 0
            else "FAIL"
            if errors or xrun_count
            else "REQUIRES_OPERATOR_CONFIRMATION"
        )
        _record(
            args.manifest,
            experiment="R32",
            status=status,
            evidence=[f"soak:{duration:.3f}s", *(f"runtime:{m}" for m in args.media)],
            facts=facts,
        )
    finally:
        container.shutdown()
    return 0


def command_tail(args) -> int:
    container = _container(args.device_id, args.locator)
    try:
        result = _play(container, args.media, args.mode)
        _pump(
            container,
            args.timeout_seconds,
            settled=lambda: container._playback.state.status is PlaybackStatus.STOPPED,
        )
        facts = {
            "tail_result": args.tail_result,
            "evidence_kind": args.evidence_kind,
            "playback_error": result["error_message"],
            "terminal_status": container._playback.state.status.value,
        }
        status = (
            "PASS"
            if args.tail_result == "PASS"
            and args.evidence_kind in {"capture", "operator"}
            and not result["error_message"]
            else "FAIL"
            if args.tail_result == "FAIL" or result["error_message"]
            else "REQUIRES_OPERATOR_CONFIRMATION"
        )
        _record(
            args.manifest,
            experiment="R35",
            status=status,
            evidence=[f"{args.evidence_kind}:{args.evidence_reference}"],
            facts=facts,
        )
    finally:
        container.shutdown()
    return 0


def command_xrun(args) -> int:
    if not args.inject:
        raise SystemExit("R36 is destructive fault injection; pass --inject explicitly")
    container = _container(args.device_id, args.locator)
    try:
        result = _play(container, args.media, args.mode)
        truth = result["signal_truth"] or {}
        alsa = truth.get("alsa") if isinstance(truth, dict) else None
        # The public diagnostics serializer intentionally omits proc_path.
        # Resolve it from the active recorder snapshot only inside this lab.
        snapshot = container._signal_truth.active_snapshot
        device = snapshot.device_negotiated
        if device is None:
            raise SystemExit("R36 requires active ALSA runtime evidence")
        hw_path = Path(device.proc_path)
        substream = hw_path.parent
        xrun_path = substream / "xrun_injection"
        status_path = substream / "status"
        if not xrun_path.exists():
            raise SystemExit(
                f"kernel does not expose xrun_injection for {substream}; "
                "R36 remains NOT_RUN on this environment"
            )
        before = status_path.read_text(encoding="utf-8") if status_path.exists() else ""
        xrun_path.write_text("1\n", encoding="utf-8")
        immediate = (
            status_path.read_text(encoding="utf-8") if status_path.exists() else ""
        )
        _pump(container, 2.0)
        after_truth = _truth(container) or {}
        after_reasons = (after_truth.get("verdict") or {}).get("reason_codes") or []
        after_state = (after_truth.get("verdict") or {}).get("state")
        observed = (
            "XRUN" in immediate.upper()
            or "XRUN" in before.upper()
            or "ST_XRUN" in after_reasons
        )
        false_verified = observed and after_state in {
            "direct",
            "direct_container_adapted",
        }
        facts = {
            "fault_injected": True,
            "xrun_observed": observed,
            "false_verified_after_xrun": false_verified,
            "recovery_loop_observed": False,
            "status_before": before,
            "status_immediate": immediate,
            "signal_truth_after": after_truth,
            "alsa_locator": (alsa or {}).get("locator")
            if isinstance(alsa, dict)
            else None,
        }
        status = "PASS" if observed and not false_verified else "FAIL"
        _record(
            args.manifest,
            experiment="R36",
            status=status,
            evidence=[str(xrun_path), str(status_path), f"runtime:{args.media}"],
            facts=facts,
        )
    finally:
        with __import__("contextlib").suppress(Exception):
            _stop(container)
        container.shutdown()
    return 0


def command_summary(args) -> int:
    payloads = [load_manifest(path) for path in args.manifest]
    summary = summarize_manifests(payloads)
    result = summary_to_dict(summary)
    if args.output:
        _write_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    inventory = sub.add_parser("inventory")
    inventory.add_argument("--output", type=Path)
    inventory.set_defaults(func=command_inventory)

    init = sub.add_parser("init")
    init.add_argument("--device-id", required=True)
    init.add_argument("--locator", required=True)
    init.add_argument("--label", required=True)
    init.add_argument("--manifest", type=Path, required=True)
    init.set_defaults(func=command_init)

    def common(name: str):
        command = sub.add_parser(name)
        command.add_argument("--device-id", required=True)
        command.add_argument("--locator", required=True)
        command.add_argument("--manifest", type=Path, required=True)
        command.add_argument(
            "--mode", choices=("strict", "compatible"), default="compatible"
        )
        return command

    clock = common("clock")
    clock.add_argument("--media", type=Path, required=True)
    clock.set_defaults(func=command_clock)

    transition = common("transition")
    transition.add_argument("--media", type=Path, nargs="+", required=True)
    transition.add_argument(
        "--first-sample-result",
        choices=("PASS", "FAIL", "NOT_OBSERVED"),
        default="NOT_OBSERVED",
    )
    transition.set_defaults(func=command_transition)

    soak = common("soak")
    soak.add_argument("--media", type=Path, nargs="+", required=True)
    soak.add_argument("--duration-seconds", type=float, required=True)
    soak.add_argument("--fail-fast", action="store_true")
    soak.set_defaults(func=command_soak)

    tail = common("tail")
    tail.add_argument("--media", type=Path, required=True)
    tail.add_argument(
        "--tail-result", choices=("PASS", "FAIL", "NOT_OBSERVED"), required=True
    )
    tail.add_argument("--evidence-kind", choices=("capture", "operator"), required=True)
    tail.add_argument("--evidence-reference", required=True)
    tail.add_argument("--timeout-seconds", type=float, default=30.0)
    tail.set_defaults(func=command_tail)

    xrun = common("xrun")
    xrun.add_argument("--media", type=Path, required=True)
    xrun.add_argument("--inject", action="store_true")
    xrun.set_defaults(func=command_xrun)

    summary = sub.add_parser("summary")
    summary.add_argument("--manifest", type=Path, action="append", required=True)
    summary.add_argument("--output", type=Path)
    summary.set_defaults(func=command_summary)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
