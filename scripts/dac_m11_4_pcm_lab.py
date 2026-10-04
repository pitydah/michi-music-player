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
import copy
import gzip
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from collections import deque
from dataclasses import asdict
from pathlib import Path
from typing import Any

from michi.application.dac_pcm_closure import (
    R25_HOLD_TOLERANCE_MS,
    R25_SWEEP_DELAYS,
    R32_MAX_MEMORY_GROWTH_KB,
    R35_REQUIRED_FIXTURES,
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


SOAK_RECEIPTS_SAMPLE_LIMIT = 64
"""Bounded receipt sample kept in the manifest facts (first + last half)."""


def _git_head() -> str:
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


def _current_direct_port(container):
    """The one current GStreamer port through the canonical engine registry.

    The production container exposes the canonical engine registry, and the
    provider owns the current port. Reading it through that authority keeps the
    lab observational; a container that cannot resolve the port yields None and
    the caller degrades to an honest empty observation.
    """
    try:
        registry = getattr(container, "_audio_engine_registry", None)
        if registry is None:
            return None
        provider = registry.provider(AudioEngineId.GSTREAMER)
        return provider.current_port
    except Exception:  # noqa: BLE001 - observational boundary
        return None


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


def _play_settled(container, previous_error: str | None) -> bool:
    """One media play is settled by PLAYING or by a NEW typed failure.

    A pre-existing error (for example a refused startup resume published before
    this request) is not this request's outcome and must never be read as one:
    the receipt records the state observed after the pump.
    """
    state = container._playback.state
    if state.status is PlaybackStatus.PLAYING:
        return True
    current = state.error_message
    return bool(current) and current != previous_error


def _play(container, media: Path, mode: str) -> dict[str, Any]:
    if not media.is_file():
        raise SystemExit(f"media fixture does not exist: {media}")
    container._aob.select_path_mode(mode)
    previous_error = container._playback.state.error_message
    container._playback.load_and_play(media)
    _pump(
        container,
        15.0,
        settled=lambda: _play_settled(container, previous_error),
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
    """Load a manifest and prove it is internally valid.

    Deliberately does NOT compare the recorded head with the current HEAD: a
    manifest is committed after the run that produced it, so that comparison
    would make every archived manifest stale by construction. Provenance is
    bound inside the manifest instead (implementation_head /
    evidence_execution_head / manifest_created_at).
    """
    payload = load_manifest(path)
    try:
        evaluate_device_manifest(payload)
    except PcmClosureEvidenceError as exc:
        raise SystemExit(f"manifest is invalid: {exc}") from exc
    return payload


def _record(
    path: Path,
    *,
    experiment: str,
    status: str,
    evidence: list[str],
    facts: dict[str, Any],
) -> None:
    """Append one observation with validate-before-write provenance.

    The candidate is a deep copy: the observation is applied to the candidate,
    the candidate is validated semantically, and only a valid candidate replaces
    the evidence file atomically. An invalid observation therefore cannot mutate
    the stored evidence at all.
    """
    payload = _manifest(path)
    item = payload["experiments"][experiment]
    if item.get("status") == "PASS":
        raise SystemExit(
            f"{experiment} is already PASS; physical evidence is append-only. "
            "Create a new manifest for a new run."
        )
    candidate = copy.deepcopy(payload)
    captured_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    collected_head = _git_head()
    candidate["experiments"][experiment].update(
        {
            "status": status,
            "executed": status in {"PASS", "FAIL"},
            "evidence": list(evidence),
            "facts": dict(facts),
            "captured_at": captured_at,
        }
    )
    candidate.setdefault("events", []).append(
        {
            "experiment": experiment,
            "status": status,
            "evidence": list(evidence),
            "facts": dict(facts),
            "captured_at": captured_at,
            "collected_head": collected_head,
        }
    )
    if candidate.get("manifest_schema") == 2:
        candidate["evidence_execution_head"] = collected_head
    try:
        verdict = evaluate_device_manifest(candidate)
    except PcmClosureEvidenceError as exc:
        raise SystemExit(
            f"refusing invalid observation; stored manifest unchanged: {exc}"
        ) from exc
    contradictions = [
        reason for reason in verdict.reasons if reason.startswith(f"{experiment}:")
    ]
    if status == "PASS" and contradictions:
        raise SystemExit(
            "refusing contradicted PASS; stored manifest unchanged: "
            + "; ".join(contradictions)
        )
    _write_json(path, candidate)
    print(f"{experiment}: {status}; device verdict={verdict.verdict}")


def _file_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _process_rss_kb() -> int | None:
    """Best-effort resident set of this lab process (R32 memory evidence)."""
    try:
        status = Path("/proc/self/status").read_text(encoding="utf-8")
    except OSError:
        return None
    for line in status.splitlines():
        if line.startswith("VmRSS:"):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                return int(parts[1])
    return None


def _empty_resources() -> dict[str, Any]:
    """The honest empty observation: the lab never invents runtime ownership."""

    return {
        "port_exists": False,
        "pump_alive": False,
        "owned_pipelines": 0,
        "current_path": None,
        "pending_path": None,
        "direct_plan_id": None,
        "direct_execution_generation": None,
        "port_generation": None,
        "residual_bus_watches": 0,
        "residual_timer_sources": 0,
    }


def _runtime_resource_snapshot(container) -> dict[str, Any]:
    """Observe R32 ownership from the provider's one current port."""

    try:
        port = _current_direct_port(container)
    except Exception:  # noqa: BLE001 - observational boundary
        return _empty_resources()
    if port is None:
        return _empty_resources()
    pump = getattr(port, "_pump", None)
    handle = getattr(port, "_active_direct_handle", None)
    pipeline = getattr(port, "_pipeline", None)
    return {
        "port_exists": True,
        "pump_alive": bool(pump is not None and pump.is_alive()),
        "owned_pipelines": 1 if pipeline is not None else 0,
        "current_path": str(getattr(port, "_current_path", None) or "") or None,
        "pending_path": str(getattr(port, "_pending_path", None) or "") or None,
        "direct_plan_id": getattr(handle, "plan_id", None),
        "direct_execution_generation": getattr(handle, "generation", None),
        "port_generation": getattr(port, "_generation", None),
        "residual_bus_watches": len(getattr(port, "_residual_bus_watches", ()) or ()),
        "residual_timer_sources": len(
            getattr(port, "_residual_timer_sources", ()) or ()
        ),
    }


def _pump_alive(container) -> bool:
    return bool(_runtime_resource_snapshot(container)["pump_alive"])


def _checkpoint_path(args, cycle: int) -> Path:
    base = Path(args.manifest).parent / "checkpoints"
    base.mkdir(parents=True, exist_ok=True)
    return base / f"soak-cycle-{cycle:06d}.json"


def _resolve_usb_sysfs_node(
    stable_device_id: str,
    *,
    sysfs_root: Path = Path("/sys"),
    explicit_path: Path | None = None,
) -> Path | None:
    """Resolve one USB node and verify it against the tested stable identity."""

    parts = stable_device_id.split(":", 3)
    if len(parts) != 4 or parts[0] != "usb":
        return None
    vendor, product, identity = (part.casefold() for part in parts[1:])
    if not re.fullmatch(r"[0-9a-z][0-9a-z.\-]*", identity):
        return None
    devices = sysfs_root / "bus" / "usb" / "devices"
    candidates: list[Path]
    if explicit_path is not None:
        explicit = (
            explicit_path if explicit_path.is_absolute() else Path.cwd() / explicit_path
        )
        try:
            relative = explicit.relative_to(devices)
        except ValueError:
            return None
        # The explicit path must name exactly one device entry. Real sysfs
        # device entries are symlinks whose resolved target lives under
        # /sys/devices, so containment is checked on the presented path and
        # any traversal component is rejected.
        if len(relative.parts) != 1:
            return None
        candidates = [devices / relative.parts[0]]
    else:
        direct = devices / identity
        candidates = [direct] if direct.is_dir() else sorted(devices.glob("*"))
    for node in candidates:
        try:
            observed_vendor = (node / "idVendor").read_text(encoding="utf-8").strip()
            observed_product = (node / "idProduct").read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if (
            observed_vendor.casefold() != vendor
            or observed_product.casefold() != product
        ):
            continue
        if node.name == identity:
            return node
        serial = ""
        with contextlib.suppress(OSError):
            serial = (node / "serial").read_text(encoding="utf-8").strip()
        if serial and serial.casefold() == identity:
            return node
    return None


def _read_usb_health_snapshot(node: Path | None) -> dict[str, int]:
    """Read documented generic USB ABI witnesses from one bound device node."""

    if node is None:
        return {}
    values: dict[str, int] = {}
    for name in ("busnum", "devnum", "urbnum"):
        try:
            values[name] = int((node / name).read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return {}
    return values


_USB_KERNEL_ERROR = re.compile(
    r"\b(error|failed|failure|timeout|timed out|stall|xacterr|babble|"
    r"reset\s+(?:full-speed|high-speed|super(?:speed)?|low-speed)?\s*usb\s+device|"
    r"disconnect|not responding|cannot)\b",
    re.IGNORECASE,
)


def _usb_health_evidence(
    stable_device_id: str,
    node: Path | None,
    baseline: dict[str, int],
    final: dict[str, int],
    *,
    since_epoch: float,
    until_epoch: float,
    runner=None,
) -> dict[str, Any]:
    """Combine documented USB ABI progress with device-bound kernel diagnostics."""

    if runner is None:
        runner = subprocess.run
    topology = node.name if node is not None else ""
    kernel_log_available = False
    journal_error: str | None = None
    output = ""
    try:
        completed = runner(
            [
                "journalctl",
                "--dmesg",
                "--no-pager",
                "--output=cat",
                "--since",
                f"@{since_epoch:.6f}",
                "--until",
                f"@{until_epoch:.6f}",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        kernel_log_available = completed.returncode == 0
        output = completed.stdout if kernel_log_available else ""
        if not kernel_log_available:
            journal_error = (completed.stderr or "journalctl failed").strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        journal_error = str(exc)

    device_pattern = (
        re.compile(rf"\b(?:usb|snd-usb-audio)\s+{re.escape(topology)}(?=[:\s])", re.I)
        if topology
        else None
    )
    relevant = [
        line.strip()
        for line in output.splitlines()
        if line.strip() and device_pattern is not None and device_pattern.search(line)
    ]
    errors = [line for line in relevant if _USB_KERNEL_ERROR.search(line)]
    complete_snapshots = set(baseline) == {"busnum", "devnum", "urbnum"} and set(
        final
    ) == {"busnum", "devnum", "urbnum"}
    binding_stable = bool(
        complete_snapshots
        and baseline["busnum"] == final["busnum"]
        and baseline["devnum"] == final["devnum"]
    )
    urb_progress = bool(complete_snapshots and baseline["urbnum"] != final["urbnum"])
    return {
        "device_id": stable_device_id,
        "sysfs_path": str(node) if node is not None else None,
        "topology": topology or None,
        "backend": "linux_usb_abi_kernel_journal",
        "available": bool(
            node is not None
            and complete_snapshots
            and kernel_log_available
            and until_epoch > since_epoch
        ),
        "baseline": dict(baseline),
        "final": dict(final),
        "binding_stable": binding_stable,
        "urb_progress": urb_progress,
        "kernel_log_available": kernel_log_available,
        "journal_error": journal_error,
        "observation_start_epoch": since_epoch,
        "observation_end_epoch": until_epoch,
        "relevant_event_count": len(relevant),
        "error_events": errors,
        "error_count": len(errors),
    }


def _usb_instance_witness(stable_device_id: str) -> dict[str, Any] | None:
    """Persistent USB enumeration witness usable across lab processes."""

    node = _resolve_usb_sysfs_node(stable_device_id)
    if node is None:
        return None
    values: dict[str, Any] = {"sysfs_path": str(node)}
    for name in ("busnum", "devnum"):
        try:
            values[name] = int((node / name).read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return None
    return values


def _suspend_success_count(
    path: Path = Path("/sys/power/suspend_stats/success"),
) -> int | None:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _coordinator(container):
    """The ONE productive output-selection coordinator the app itself uses.

    The bridge owns the canonical coordinator wired by the composition root;
    the lab drives that same authority instead of reconstructing a second
    selection graph from container internals.
    """

    coordinator = getattr(
        getattr(container, "_aob", None), "_selection_coordinator", None
    )
    if coordinator is None:
        raise SystemExit("output selection coordinator is unavailable")
    return coordinator


def command_inventory(args) -> int:
    from michi.bootstrap import ApplicationContainer

    container = ApplicationContainer()
    try:
        container.initialize()
        _pump(container, 1.0)
        collected_head = _git_head()
        payload = {
            "schema_version": 1,
            "manifest_schema": 2,
            "implementation_head": collected_head,
            "evidence_execution_head": collected_head,
            "manifest_created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
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
        collected_head = _git_head()
        created_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        payload = {
            "schema_version": 1,
            "manifest_schema": 2,
            "implementation_head": collected_head,
            "evidence_execution_head": collected_head,
            "manifest_created_at": created_at,
            "captured_at": created_at,
            "environment_fingerprint": qualification.current_environment_fingerprint(
                args.device_id
            ),
            "environment_context": asdict(context),
            "device": _manifest_device_identity(
                label=args.label,
                device_id=args.device_id,
                locator=args.locator,
                row=row,
                usb_descriptor_sha256=context.usb_descriptor_sha256,
            ),
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


def _manifest_device_identity(
    *,
    label: str,
    device_id: str,
    locator: str,
    row: dict[str, Any],
    usb_descriptor_sha256: str | None,
) -> dict[str, Any]:
    """Project device identity without dropping descriptor provenance."""

    return {
        "label": label,
        "stable_device_id": device_id,
        "locator": locator,
        "vendor_id": row.get("vendorId") or "",
        "product_id": row.get("productId") or "",
        "bcd_device": row.get("bcdDevice") or "",
        "manufacturer": row.get("manufacturer") or "",
        "product": row.get("product") or "",
        "descriptor_hash": usb_descriptor_sha256 or "",
        "display_name": row.get("displayName") or "",
    }


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


R25_DELAYS = (0, 100, 250, 500, 1000)
R25_MEDIA_ORDER = (0, 0, 48000, 44100, 96000, 192000, 44100)
R25_REQUIRED_EDGES = (
    "44100->44100",
    "44100->48000",
    "48000->44100",
    "44100->96000",
    "96000->192000",
    "192000->44100",
)


def _r25_runtime_passes(run: dict[str, Any]) -> bool:
    hold = run.get("actual_hold_ms")
    receipts = run.get("receipts")
    return bool(
        isinstance(hold, int)
        and hold >= 0
        and hold + R25_HOLD_TOLERANCE_MS >= run.get("configured_delay_ms", -1)
        and set(run.get("edges") or ()) == set(R25_REQUIRED_EDGES)
        and run.get("stale_generation_observed") is False
        and run.get("hidden_conversion_observed") is False
        and int(run.get("xrun_count", 0) or 0) == 0
        and isinstance(receipts, list)
        and len(receipts) == len(R25_MEDIA_ORDER)
        and all(isinstance(receipt, dict) for receipt in receipts)
        and not any(
            receipt.get("error") or int(receipt.get("xrun_count", 0) or 0)
            for receipt in receipts
        )
        and all(
            isinstance(receipt.get("actual_hold_ms"), int)
            and receipt["actual_hold_ms"] + R25_HOLD_TOLERANCE_MS
            >= run.get("configured_delay_ms", -1)
            for receipt in receipts
        )
    )


def _r25_run_passes(run: dict[str, Any]) -> bool:
    evidence = run.get("first_sample_evidence")
    return bool(
        _r25_runtime_passes(run)
        and isinstance(evidence, dict)
        and evidence.get("configured_delay_ms") == run.get("configured_delay_ms")
        and evidence.get("preserved") is True
        and str(evidence.get("observed_result") or "").upper().startswith("PASS")
    )


def _r25_result(runs: list[dict[str, Any]]) -> tuple[str, int | None]:
    """Derive R25 status and minimum; never promote a partial sweep."""

    delays = [run.get("configured_delay_ms") for run in runs]
    malformed = any(
        not isinstance(run, dict)
        or not isinstance(run.get("receipts"), list)
        or not all(isinstance(receipt, dict) for receipt in run.get("receipts", ()))
        or any(
            receipt.get("error") or int(receipt.get("xrun_count", 0) or 0)
            for receipt in run.get("receipts", ())
        )
        or run.get("stale_generation_observed") is True
        or run.get("hidden_conversion_observed") is True
        for run in runs
    )
    if malformed:
        return "FAIL", None
    canonical = (
        len(runs) == len(R25_SWEEP_DELAYS)
        and len(set(delays)) == len(R25_SWEEP_DELAYS)
        and set(delays) == set(R25_SWEEP_DELAYS)
    )
    if not canonical:
        return "REQUIRES_OPERATOR_CONFIRMATION", None
    evidence_complete = all(
        isinstance(run.get("first_sample_evidence"), dict)
        and run["first_sample_evidence"].get("configured_delay_ms")
        == run["configured_delay_ms"]
        and isinstance(run["first_sample_evidence"].get("preserved"), bool)
        and re.fullmatch(
            r"[0-9a-f]{64}",
            str(run["first_sample_evidence"].get("fixture_sha256") or ""),
        )
        is not None
        and all(
            isinstance(run["first_sample_evidence"].get(field), str)
            and bool(run["first_sample_evidence"][field].strip())
            for field in (
                "method",
                "fixture_id",
                "fixture_sha256",
                "evidence_reference",
                "expected_marker",
                "observed_result",
            )
        )
        for run in runs
    )
    if not evidence_complete:
        return "REQUIRES_OPERATOR_CONFIRMATION", None
    contradictory_evidence = any(
        run["first_sample_evidence"]["preserved"]
        != str(run["first_sample_evidence"]["observed_result"])
        .upper()
        .startswith("PASS")
        for run in runs
    )
    if contradictory_evidence:
        return "FAIL", None
    runtime_passes = all(_r25_runtime_passes(run) for run in runs)
    if not runtime_passes:
        return "FAIL", None
    passing = sorted(
        int(run["configured_delay_ms"])
        for run in runs
        if run["first_sample_evidence"]["preserved"] is True
    )
    minimum = passing[0] if passing else None
    if minimum is None:
        return "FAIL", None
    if any(
        run["first_sample_evidence"]["preserved"]
        != (run["configured_delay_ms"] >= minimum)
        for run in runs
    ):
        return "FAIL", None
    return "PASS", minimum


def _port_resync_evidence(container) -> dict[str, Any]:
    """Measured hold evidence from the runtime, when the port exposes it."""
    try:
        port = _current_direct_port(container)
        evidence = getattr(port, "resync_evidence", None)
        if callable(evidence):
            payload = evidence()
            return payload if isinstance(payload, dict) else {}
    except Exception:  # noqa: BLE001 - observational boundary
        pass
    return {}


def _first_sample_evidence(
    args,
    *,
    delay_ms: int | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Structured first-sample evidence, or None when it is not complete.

    A nominal ``--first-sample-result PASS`` is never enough: the identity of the
    fixture and the measurement method travel with the observation, and the
    fixture hash is computed here from the file itself.
    """
    method = getattr(args, "first_sample_method", None)
    fixture = getattr(args, "first_sample_fixture", None)
    observation = observation or {}
    reference = observation.get("evidence_reference") or getattr(
        args, "first_sample_evidence", None
    )
    marker = getattr(args, "first_sample_expected_marker", None)
    observed = observation.get("observed_result") or getattr(
        args, "first_sample_observed_result", None
    )
    if not all((method, fixture, reference, marker, observed)):
        return None
    path = Path(fixture)
    if not path.is_file():
        raise SystemExit(f"first-sample fixture does not exist: {path}")
    result = {
        "method": str(method),
        "fixture_id": path.name,
        "fixture_sha256": _file_sha256(path),
        "evidence_reference": str(reference),
        "expected_marker": str(marker),
        "observed_result": str(observed),
        "preserved": str(observed).upper().startswith("PASS"),
    }
    if delay_ms is not None:
        result["configured_delay_ms"] = delay_ms
    return result


def _first_sample_evidence_by_delay(args) -> dict[int, dict[str, Any]]:
    path = getattr(args, "first_sample_observations", None)
    if path is None:
        return {}
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"invalid first-sample observations: {exc}") from exc
    if not isinstance(raw, dict):
        raise SystemExit("first-sample observations must be a JSON object by delay")
    result: dict[int, dict[str, Any]] = {}
    for delay in R25_DELAYS:
        observation = raw.get(str(delay))
        if not isinstance(observation, dict):
            continue
        evidence = _first_sample_evidence(args, delay_ms=delay, observation=observation)
        if evidence is not None:
            result[delay] = evidence
    return result


def _wip_heartbeat(
    args, phase: str, detail: str = "", *, wip_dir: Path | None = None
) -> None:
    """Durable progress for the external supervisor, emitted by the sweep path."""
    run_dir = os.environ.get("M11_4_RUN_DIR")
    if not run_dir:
        return
    evidence = _evidence_module()
    with contextlib.suppress(Exception):
        evidence.atomic_write_json(
            Path(run_dir) / "progress.json",
            {
                "monotonic_ns": evidence.monotonic_ns(),
                "wall_time_utc": evidence.utc_now_iso(),
                "phase": phase,
                "detail": detail,
                "wip_dir": str(
                    wip_dir if wip_dir is not None else _transition_wip_dir(args)
                ),
            },
        )


def _run_r25_delay(
    container,
    args,
    delay_ms: int,
    first_sample_evidence: dict[str, Any] | None,
) -> dict[str, Any]:
    """One delay of the canonical sweep: the full media sequence, measured."""
    coordinator = _coordinator(container)
    coordinator.select_path_mode(args.mode)
    coordinator.set_resync_delay_ms(delay_ms)
    receipts: list[dict[str, Any]] = []
    stale = False
    hidden = False
    previous_identity = None
    measured: dict[str, Any] = {}
    measured_holds: list[int] = []
    for media in args.media:
        _wip_heartbeat(args, "r25-delay", f"{delay_ms}ms {Path(media).name}")
        result = _play(container, media, args.mode)
        truth = result.get("signal_truth") or {}
        decoded = truth.get("decoded") if isinstance(truth, dict) else None
        identity = truth.get("identity") if isinstance(truth, dict) else None
        rate = int((decoded or {}).get("rate_hz") or 0)
        reasons = result.get("signal_truth_reasons") or []
        if previous_identity is not None and identity == previous_identity:
            stale = True
        if any("CONTAINER_TRANSFORM_UNOBSERVED" in str(reason) for reason in reasons):
            hidden = True
        previous_identity = identity
        evidence = _port_resync_evidence(container)
        if evidence:
            measured = evidence
        actual = evidence.get("resync_actual_hold_ms")
        actual_hold = (
            int(actual) if isinstance(actual, int) else (0 if delay_ms == 0 else None)
        )
        if isinstance(actual_hold, int):
            measured_holds.append(actual_hold)
        receipts.append(
            {
                "media": str(media),
                "source_rate_hz": rate,
                "signal_truth_state": (
                    (truth.get("verdict") or {}).get("state")
                    if isinstance(truth, dict)
                    else None
                ),
                "signal_truth_identity": identity,
                "requested_tuple": (
                    (truth.get("plan") or {}).get("requested")
                    if isinstance(truth, dict)
                    else None
                ),
                "negotiated_tuple": (
                    truth.get("negotiated") or truth.get("alsa")
                    if isinstance(truth, dict)
                    else None
                ),
                "xrun_count": 1 if "ST_XRUN" in reasons else 0,
                "error": result.get("error_message"),
                "actual_hold_ms": actual_hold,
            }
        )
        _stop(container)
    rates = [int(receipt["source_rate_hz"]) for receipt in receipts]
    edges = [
        f"{left}->{right}" for left, right in zip(rates[:-1], rates[1:], strict=True)
    ]
    return {
        "configured_delay_ms": delay_ms,
        "actual_hold_ms": (
            min(measured_holds)
            if len(measured_holds) == len(receipts) and measured_holds
            else None
        ),
        "edges": edges,
        "port_generation": measured.get("port_generation"),
        "execution_generation": measured.get("execution_generation"),
        "plan_id": measured.get("plan_id"),
        "stale_generation_observed": stale,
        "hidden_conversion_observed": hidden,
        "xrun_count": sum(
            int(receipt.get("xrun_count", 0) or 0) for receipt in receipts
        ),
        "receipts": receipts,
        "first_sample_evidence": copy.deepcopy(first_sample_evidence),
    }


def _evidence_module():
    spec = importlib.util.spec_from_file_location(
        "m11_4_evidence", Path(__file__).resolve().parent / "m11_4_evidence.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["m11_4_evidence"] = module
    spec.loader.exec_module(module)
    return module


def _transition_wip_dir(args) -> Path:
    explicit = getattr(args, "wip_dir", None)
    if explicit is not None:
        return Path(explicit)
    run_dir = os.environ.get("M11_4_RUN_DIR")
    if run_dir:
        return Path(run_dir) / "r25"
    evidence = _evidence_module()
    return evidence.STATE_ROOT / "r25-wip" / time.strftime("%Y%m%dT%H%M%S") / "r25"


def _r25_wip_meta(container, args) -> dict[str, Any]:
    qualification = getattr(getattr(container, "_aob", None), "_qualification", None)
    fingerprint = None
    if qualification is not None:
        with contextlib.suppress(Exception):
            fingerprint = qualification.current_environment_fingerprint(args.device_id)
    return {
        "schema_version": 1,
        "experiment": "R25",
        "device_id": args.device_id,
        "locator": args.locator,
        "environment_fingerprint": fingerprint,
        "implementation_head": _git_head(),
        "fixture_sha256": {
            str(media): _file_sha256(Path(media)) for media in args.media
        },
        "canonical_delays": list(R25_DELAYS),
        "first_sample_inputs_sha256": (
            _file_sha256(Path(args.first_sample_observations))
            if Path(args.first_sample_observations).is_file()
            else None
        ),
        "first_sample_fixture_sha256": _file_sha256(Path(args.first_sample_fixture)),
        "first_sample_method": args.first_sample_method,
        "first_sample_expected_marker": args.first_sample_expected_marker,
        "created_wallclock_utc": _evidence_module().utc_now_iso(),
    }


def _r25_wip_mismatch(previous: dict[str, Any], current: dict[str, Any]) -> str | None:
    checks = (
        ("device_id", "device identity"),
        ("locator", "ALSA locator"),
        ("environment_fingerprint", "environment fingerprint"),
        ("implementation_head", "implementation HEAD"),
        ("fixture_sha256", "fixture hashes"),
        ("canonical_delays", "canonical R25 contract"),
        ("first_sample_inputs_sha256", "operator observation inputs"),
        ("first_sample_fixture_sha256", "first-sample fixture"),
        ("first_sample_method", "first-sample method"),
        ("first_sample_expected_marker", "first-sample marker"),
    )
    for key, label in checks:
        if previous.get(key) != current.get(key):
            return f"{label} changed ({key})"
    return None


def command_transition(args) -> int:
    if len(args.media) != 7:
        raise SystemExit(
            "R25 requires seven fixtures in this order: "
            "44.1, 44.1, 48, 44.1, 96, 192, 44.1 kHz"
        )
    evidence = _evidence_module()
    first_sample_by_delay = _first_sample_evidence_by_delay(args)
    wip_dir = _transition_wip_dir(args)
    wip_dir.mkdir(parents=True, exist_ok=True)
    journal = evidence.EventJournal(wip_dir / "journal.jsonl")
    container = _container(args.device_id, args.locator)
    runs: list[dict[str, Any]] = []
    sealed: dict[int, dict[str, Any]] = {}
    try:
        meta = _r25_wip_meta(container, args)
        meta_path = wip_dir / "wip-meta.json"
        if getattr(args, "resume", False) and meta_path.is_file():
            previous = json.loads(meta_path.read_text(encoding="utf-8"))
            mismatch = _r25_wip_mismatch(previous, meta)
            if mismatch:
                raise SystemExit(f"STOP_R25_WIP_PROVENANCE_MISMATCH: {mismatch}")
            for delay in R25_DELAYS:
                record_path = wip_dir / f"delay-{delay:04d}.json"
                if record_path.is_file():
                    sealed[delay] = json.loads(record_path.read_text(encoding="utf-8"))
        evidence.atomic_write_json(meta_path, meta)
        journal.append(
            "R25_SWEEP_START",
            {"delays": list(R25_DELAYS), "resumed_delays": sorted(sealed)},
        )
        _wip_heartbeat(args, "r25-sweep", "start")
        for delay in R25_DELAYS:
            if delay in sealed:
                runs.append(sealed[delay]["run"])
                journal.append("R25_DELAY_RECOVERED", {"delay_ms": delay})
                continue
            _wip_heartbeat(args, "r25-delay-start", f"{delay}ms")
            run = _run_r25_delay(
                container, args, delay, first_sample_by_delay.get(delay)
            )
            runs.append(run)
            evidence.atomic_write_json(
                wip_dir / f"delay-{delay:04d}.json",
                {
                    "schema_version": 1,
                    "delay_ms": delay,
                    "run": run,
                    "first_sample_evidence": first_sample_by_delay.get(delay),
                    "sealed_wallclock_utc": evidence.utc_now_iso(),
                },
            )
            journal.append(
                "R25_DELAY_SEALED",
                {"delay_ms": delay, "receipts": len(run["receipts"])},
            )
    finally:
        container.shutdown()

    status, minimal = _r25_result(runs)
    any_stale = any(run["stale_generation_observed"] for run in runs)
    any_hidden = any(run["hidden_conversion_observed"] for run in runs)
    any_xrun = any(receipt["xrun_count"] for run in runs for receipt in run["receipts"])
    facts = {
        "runs": runs,
        "transition_edges": sorted({edge for run in runs for edge in run["edges"]}),
        "first_sample_evidence_by_delay": {
            str(delay): copy.deepcopy(first_sample_by_delay[delay])
            for delay in sorted(first_sample_by_delay)
        },
        "first_sample_result": "PASS" if status == "PASS" else "NOT_PROVEN",
        "minimal_delay_that_preserves_first_content": minimal,
        "stale_generation_observed": any_stale,
        "hidden_conversion_observed": any_hidden,
        "xrun_count": any_xrun,
    }
    _record(
        args.manifest,
        experiment="R25",
        status=status,
        evidence=[f"runtime:{media}" for media in args.media]
        + [f"sweep_delay:{delay}ms" for delay in R25_DELAYS],
        facts=facts,
    )
    return 0


def _transition_receipt(
    result: dict[str, Any], *, previous_identity: dict[str, Any] | None
) -> dict[str, Any]:
    """Classify one load from productive Signal Truth, never filenames."""

    truth = result.get("signal_truth")
    truth = truth if isinstance(truth, dict) else {}
    identity = truth.get("identity")
    identity = identity if isinstance(identity, dict) else None
    decoded = truth.get("decoded")
    requested = (truth.get("plan") or {}).get("requested")
    negotiated = truth.get("alsa")
    decoded_rate = (decoded or {}).get("rate_hz") if isinstance(decoded, dict) else None
    requested_rate = (
        (requested or {}).get("rate_hz") if isinstance(requested, dict) else None
    )
    negotiated_rate = (
        (negotiated or {}).get("rate_hz") if isinstance(negotiated, dict) else None
    )
    verdict = truth.get("verdict")
    state = (verdict or {}).get("state") if isinstance(verdict, dict) else None
    generations_valid = bool(
        identity
        and isinstance(identity.get("execution_generation"), int)
        and isinstance(identity.get("port_generation"), int)
    )
    rates_valid = bool(
        isinstance(decoded_rate, int)
        and decoded_rate > 0
        and requested_rate == decoded_rate
        and negotiated_rate == decoded_rate
    )
    stale = previous_identity is not None and identity == previous_identity
    failed = bool(
        result.get("error_message")
        or result.get("status") != PlaybackStatus.PLAYING.value
        or state not in {"direct", "direct_container_adapted"}
        or not generations_valid
        or not rates_valid
        or stale
    )
    return {
        "failed": failed,
        "error": result.get("error_message"),
        "status": result.get("status"),
        "decoded_rate_hz": decoded_rate,
        "requested_rate_hz": requested_rate,
        "negotiated_rate_hz": negotiated_rate,
        "identity": identity,
        "signal_truth_state": state,
        "stale_identity": stale,
    }


def _soak_status(facts: dict[str, Any]) -> str:
    hard_failure = bool(
        int(facts.get("xrun_count", 0) or 0)
        or int(facts.get("runtime_error_count", 0) or 0)
        or int(facts.get("transition_failures", 0) or 0)
    )
    if hard_failure:
        return "FAIL"
    if float(facts.get("duration_seconds", 0) or 0) < 28800:
        return "REQUIRES_OPERATOR_CONFIRMATION"
    growth = facts.get("memory_growth_kb")
    checkpoints = facts.get("rss_checkpoints")
    pump = facts.get("pump_health")
    resources = facts.get("resource_growth")
    usb = facts.get("usb_errors_observed")
    measured = bool(
        isinstance(growth, (int, float))
        and isinstance(checkpoints, list)
        and checkpoints
        and isinstance(pump, dict)
        and isinstance(resources, dict)
        and resources.get("observed") is True
        and isinstance(usb, dict)
        and usb.get("available") is True
        and bool(usb.get("device_id"))
        and bool(usb.get("sysfs_path"))
        and usb.get("backend") == "linux_usb_abi_kernel_journal"
        and usb.get("kernel_log_available") is True
    )
    if not measured:
        return "REQUIRES_OPERATOR_CONFIRMATION"
    failed = bool(
        growth > R32_MAX_MEMORY_GROWTH_KB
        or pump.get("pump_alive") is not True
        or pump.get("alive_at_every_checkpoint") is not True
        or int(pump.get("cycles_completed", 0) or 0) <= 0
        or resources.get("unbounded") is not False
        or usb.get("binding_stable") is not True
        or usb.get("urb_progress") is not True
        or int(usb.get("error_count", 0) or 0) != 0
    )
    return "FAIL" if failed else "PASS"


def command_soak(args) -> int:
    if args.duration_seconds <= 0:
        raise SystemExit("--duration-seconds must be > 0")
    container = _container(args.device_id, args.locator)
    started = time.monotonic()
    started_epoch = time.time()
    errors: list[str] = []
    cycles = 0
    xrun_count = 0
    rss_checkpoints: list[dict[str, Any]] = []
    receipts_head: list[dict[str, Any]] = []
    receipts_tail: deque[dict[str, Any]] = deque(maxlen=SOAK_RECEIPTS_SAMPLE_LIMIT // 2)
    receipts_file = (
        Path(args.manifest).parent
        / "receipts"
        / f"soak-receipts-{time.strftime('%Y%m%dT%H%M%S')}.jsonl.gz"
    )
    receipts_file.parent.mkdir(parents=True, exist_ok=True)
    receipts_handle = gzip.open(  # noqa: SIM115 - closed in the command finally
        receipts_file, "wt", encoding="utf-8"
    )
    transition_failures = 0
    previous_identity: dict[str, Any] | None = None
    checkpoints: list[Path] = []
    rss_baseline = _process_rss_kb()
    usb_node = _resolve_usb_sysfs_node(
        args.device_id,
        explicit_path=args.usb_sysfs_path,
    )
    usb_baseline = _read_usb_health_snapshot(usb_node)
    resource_baseline = _runtime_resource_snapshot(container)
    try:
        while time.monotonic() - started < args.duration_seconds:
            media = args.media[cycles % len(args.media)]
            result = _play(container, media, args.mode)
            reasons = result.get("signal_truth_reasons") or []
            if "ST_XRUN" in reasons:
                xrun_count += 1
            receipt = _transition_receipt(result, previous_identity=previous_identity)
            receipts_handle.write(json.dumps(receipt, sort_keys=True) + "\n")
            if len(receipts_head) < SOAK_RECEIPTS_SAMPLE_LIMIT // 2:
                receipts_head.append(receipt)
            receipts_tail.append(receipt)
            if receipt["failed"]:
                transition_failures += 1
            identity = receipt.get("identity")
            previous_identity = identity if isinstance(identity, dict) else None
            if result["error_message"]:
                errors.append(str(result["error_message"]))
            cycles += 1
            _stop(container)
            if cycles % max(1, args.checkpoint_every) == 0:
                resources = _runtime_resource_snapshot(container)
                checkpoint = {
                    "cycle": cycles,
                    "elapsed_seconds": time.monotonic() - started,
                    "rss_kb": _process_rss_kb(),
                    "xrun_count": xrun_count,
                    "runtime_error_count": len(errors),
                    "resources": resources,
                }
                rss_checkpoints.append(checkpoint)
                path = _checkpoint_path(args, cycles)
                _write_json(path, checkpoint)
                checkpoints.append(path)
            if errors and args.fail_fast:
                break
        duration = time.monotonic() - started
        receipts_handle.close()
        receipts_sample: list[dict[str, Any]] = []
        seen_receipts: set[int] = set()
        for receipt in (*receipts_head, *receipts_tail):
            if id(receipt) not in seen_receipts:
                seen_receipts.add(id(receipt))
                receipts_sample.append(receipt)
        receipts_digest = (
            _file_sha256(receipts_file) if receipts_file.exists() else None
        )
        rss_final = _process_rss_kb()
        rss_values = [
            value
            for value in [
                rss_baseline,
                *(item.get("rss_kb") for item in rss_checkpoints),
                rss_final,
            ]
            if isinstance(value, int)
        ]
        growth_kb = (
            rss_final - rss_baseline
            if isinstance(rss_baseline, int) and isinstance(rss_final, int)
            else None
        )
        resource_snapshots = [
            resource_baseline,
            *(item["resources"] for item in rss_checkpoints),
            _runtime_resource_snapshot(container),
        ]
        owned_peak = max(
            (int(item.get("owned_pipelines", 0)) for item in resource_snapshots),
            default=0,
        )
        residual_peak = max(
            (
                int(item.get("residual_bus_watches", 0))
                + int(item.get("residual_timer_sources", 0))
                for item in resource_snapshots
            ),
            default=0,
        )
        usb_final = _read_usb_health_snapshot(usb_node)
        finished_epoch = time.time()
        facts = {
            "duration_seconds": duration,
            "cycles": cycles,
            "xrun_count": xrun_count,
            "runtime_error_count": len(errors),
            "errors": errors[:20],
            "rss_baseline_kb": rss_baseline,
            "rss_peak_kb": max(rss_values) if rss_values else None,
            "rss_final_kb": rss_final,
            "memory_growth_kb": growth_kb,
            "rss_checkpoints": rss_checkpoints,
            "checkpoint_files": [str(path) for path in checkpoints],
            "pump_health": {
                "cycles_completed": cycles,
                "pump_alive": _pump_alive(container),
                "alive_at_every_checkpoint": bool(rss_checkpoints)
                and all(
                    item["resources"].get("pump_alive") is True
                    for item in rss_checkpoints
                ),
            },
            "transition_failures": transition_failures,
            "receipts_total": cycles,
            "receipts_failed": transition_failures,
            "receipts_sample": receipts_sample,
            "receipts_sample_limit": SOAK_RECEIPTS_SAMPLE_LIMIT,
            "receipts_file": str(receipts_file) if receipts_file.exists() else None,
            "receipts_file_sha256": receipts_digest,
            "resource_growth": {
                "observed": bool(resource_snapshots),
                "unbounded": owned_peak > 1 or residual_peak > 0,
                "owned_pipelines_baseline": resource_baseline["owned_pipelines"],
                "owned_pipelines_peak": owned_peak,
                "residual_native_resources_peak": residual_peak,
            },
            "usb_errors_observed": _usb_health_evidence(
                args.device_id,
                usb_node,
                usb_baseline,
                usb_final,
                since_epoch=started_epoch,
                until_epoch=finished_epoch,
            ),
        }
        status = _soak_status(facts)
        _record(
            args.manifest,
            experiment="R32",
            status=status,
            evidence=[f"soak:{duration:.3f}s", *(f"runtime:{m}" for m in args.media)],
            facts=facts,
        )
    finally:
        receipts_handle.close()
        container.shutdown()
    return 0


R35_FIXTURES = R35_REQUIRED_FIXTURES


def _merge_r35_fixture(
    existing_facts: dict[str, Any], fixture: str, entry: dict[str, Any]
) -> dict[str, Any]:
    fixtures = copy.deepcopy(existing_facts.get("fixtures") or {})
    fixtures[fixture] = copy.deepcopy(entry)
    return fixtures


def _r35_status(fixtures: dict[str, Any]) -> str:
    if any(
        isinstance(entry, dict)
        and (
            entry.get("result") == "FAIL"
            or entry.get("falsifier_observed") is True
            or entry.get("playback_error")
        )
        for entry in fixtures.values()
    ):
        return "FAIL"
    if set(fixtures) != set(R35_FIXTURES):
        return "REQUIRES_OPERATOR_CONFIRMATION"
    return (
        "PASS"
        if all(
            isinstance(fixtures[name], dict)
            and fixtures[name].get("result") == "PASS"
            and fixtures[name].get("falsifier_observed") is False
            for name in R35_FIXTURES
        )
        else "REQUIRES_OPERATOR_CONFIRMATION"
    )


def _r35_fixture_entry(
    *,
    media: Path,
    result: str,
    evidence_kind: str,
    evidence_reference: str,
    method: str,
    falsifier_observed: bool,
    playback_error: str | None = None,
    terminal_status: str | None = None,
) -> dict[str, Any]:
    if not media.is_file():
        raise SystemExit(f"media fixture does not exist: {media}")
    entry: dict[str, Any] = {
        "result": result,
        "evidence_kind": evidence_kind,
        "evidence_reference": evidence_reference,
        "method": method,
        "fixture_sha256": _file_sha256(media),
        "falsifier_observed": bool(falsifier_observed),
        "playback_error": playback_error,
        "terminal_status": terminal_status,
    }
    if evidence_kind == "capture":
        artifact = Path(evidence_reference)
        if not artifact.is_file():
            raise SystemExit(f"capture artifact does not exist: {artifact}")
        entry.update(
            {
                "artifact": str(artifact),
                "sha256": _file_sha256(artifact),
            }
        )
    elif not evidence_reference.strip():
        raise SystemExit("operator evidence requires a concrete reference")
    return entry


def _r35_wip_dir(args) -> Path:
    explicit = getattr(args, "wip_dir", None)
    if explicit is not None:
        return Path(explicit)
    run_dir = os.environ.get("M11_4_RUN_DIR")
    if run_dir:
        return Path(run_dir) / "r35"
    evidence = _evidence_module()
    return evidence.STATE_ROOT / "r35-wip" / time.strftime("%Y%m%dT%H%M%S") / "r35"


def _r35_wip_meta(container, args) -> dict[str, Any]:
    qualification = getattr(getattr(container, "_aob", None), "_qualification", None)
    fingerprint = None
    if qualification is not None:
        with contextlib.suppress(Exception):
            fingerprint = qualification.current_environment_fingerprint(args.device_id)
    return {
        "schema_version": 1,
        "experiment": "R35",
        "device_id": args.device_id,
        "locator": args.locator,
        "environment_fingerprint": fingerprint,
        "implementation_head": _git_head(),
        "canonical_fixtures": list(R35_FIXTURES),
        "fixture_inputs": {
            args.fixture: {
                "media": str(args.media),
                "media_sha256": _file_sha256(args.media),
            }
        },
        "created_wallclock_utc": _evidence_module().utc_now_iso(),
    }


def _r35_wip_mismatch(previous: dict[str, Any], current: dict[str, Any]) -> str | None:
    checks = (
        ("device_id", "device identity"),
        ("locator", "ALSA locator"),
        ("environment_fingerprint", "environment fingerprint"),
        ("implementation_head", "implementation HEAD"),
        ("canonical_fixtures", "canonical R35 fixture contract"),
    )
    for key, label in checks:
        if previous.get(key) != current.get(key):
            return f"{label} changed ({key})"
    previous_inputs = previous.get("fixture_inputs") or {}
    current_inputs = current.get("fixture_inputs") or {}
    for name, current_input in current_inputs.items():
        previous_input = previous_inputs.get(name)
        if isinstance(previous_input, dict) and previous_input != current_input:
            return f"fixture input changed for {name} (fixture_inputs)"
    return None


def _r35_sealed_fixtures(wip_dir: Path) -> dict[str, dict[str, Any]]:
    """Sealed fixture entries from durable checkpoints; a crash never erases them."""
    fixtures: dict[str, dict[str, Any]] = {}
    for name in R35_FIXTURES:
        path = wip_dir / f"fixture-{name}.json"
        if not path.is_file():
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        entry = record.get("entry") if isinstance(record, dict) else None
        if isinstance(entry, dict):
            fixtures[name] = entry
    return fixtures


def command_tail(args) -> int:
    if not args.media.is_file():
        raise SystemExit(f"media fixture does not exist: {args.media}")
    evidence = _evidence_module()
    resume = bool(getattr(args, "resume", False))
    wip_dir = _r35_wip_dir(args)
    wip_dir.mkdir(parents=True, exist_ok=True)
    journal = evidence.EventJournal(wip_dir / "journal.jsonl")
    container = _container(args.device_id, args.locator)
    try:
        meta = _r35_wip_meta(container, args)
        meta_path = wip_dir / "wip-meta.json"
        previous_meta = None
        if meta_path.is_file():
            previous_meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if isinstance(previous_meta, dict):
            mismatch = _r35_wip_mismatch(previous_meta, meta)
            if mismatch:
                raise SystemExit(f"STOP_R35_WIP_PROVENANCE_MISMATCH: {mismatch}")
            merged_inputs = dict(previous_meta.get("fixture_inputs") or {})
            merged_inputs.update(meta["fixture_inputs"])
            meta["fixture_inputs"] = merged_inputs
            meta["created_wallclock_utc"] = previous_meta.get(
                "created_wallclock_utc", meta["created_wallclock_utc"]
            )
        evidence.atomic_write_json(meta_path, meta)
        journal.append(
            "R35_FIXTURE_START",
            {
                "fixture": args.fixture,
                "media": str(args.media),
                "resumed": resume,
            },
        )
        _wip_heartbeat(args, "r35-fixture-start", args.fixture, wip_dir=wip_dir)
        fixture_path = wip_dir / f"fixture-{args.fixture}.json"
        if resume and fixture_path.is_file():
            journal.append("R35_FIXTURE_RECOVERED", {"fixture": args.fixture})
        else:
            if fixture_path.is_file():
                previous = json.loads(fixture_path.read_text(encoding="utf-8"))
                previous_entry = (
                    previous.get("entry") if isinstance(previous, dict) else None
                )
                previous_result = (previous_entry or {}).get("result")
                if (
                    previous_result == "PASS"
                    and (previous_entry or {}).get("falsifier_observed") is False
                ):
                    raise SystemExit(
                        f"STOP_R35_FIXTURE_ALREADY_SEALED: {args.fixture} is already "
                        "sealed PASS; physical evidence is append-only"
                    )
                if (
                    previous_result == "FAIL"
                    or (previous_entry or {}).get("falsifier_observed") is True
                ):
                    raise SystemExit(
                        f"STOP_R35_FIXTURE_SEALED_FAIL: {args.fixture} is sealed as "
                        "FAIL; use a fresh WIP directory for an intentional retest"
                    )
                journal.append(
                    "R35_FIXTURE_RETRY",
                    {"fixture": args.fixture, "previous_result": previous_result},
                )
            result = _play(container, args.media, args.mode)
            _pump(
                container,
                args.timeout_seconds,
                settled=lambda: (
                    container._playback.state.status is PlaybackStatus.STOPPED
                ),
            )
            terminal = container._playback.state.status.value
            entry = _r35_fixture_entry(
                media=args.media,
                result=args.tail_result,
                evidence_kind=args.evidence_kind,
                evidence_reference=args.evidence_reference,
                method=args.method,
                falsifier_observed=(
                    args.falsifier_observed or args.tail_result == "FAIL"
                ),
                playback_error=result["error_message"],
                terminal_status=terminal,
            )
            evidence.atomic_write_json(
                fixture_path,
                {
                    "schema_version": 1,
                    "fixture": args.fixture,
                    "entry": entry,
                    "sealed_wallclock_utc": evidence.utc_now_iso(),
                },
            )
            journal.append(
                "R35_FIXTURE_SEALED",
                {
                    "fixture": args.fixture,
                    "result": entry["result"],
                    "falsifier_observed": entry["falsifier_observed"],
                    "fixture_sha256": entry["fixture_sha256"],
                },
            )
        _wip_heartbeat(args, "r35-fixture-sealed", args.fixture, wip_dir=wip_dir)
        existing_facts = _manifest(args.manifest)["experiments"]["R35"].get("facts")
        existing_fixtures = (
            existing_facts.get("fixtures") if isinstance(existing_facts, dict) else None
        )
        fixtures = dict(existing_fixtures or {})
        fixtures.update(_r35_sealed_fixtures(wip_dir))
        facts = {"fixtures": fixtures}
        if existing_facts == facts:
            print("R35: canonical record already matches the sealed fixtures")
            return 0
        evidence_refs = [
            f"{entry['evidence_kind']}:{entry['evidence_reference']}"
            for name in R35_FIXTURES
            if isinstance((entry := fixtures.get(name)), dict)
            and entry.get("evidence_kind")
            and entry.get("evidence_reference")
        ]
        _record(
            args.manifest,
            experiment="R35",
            status=_r35_status(fixtures),
            evidence=evidence_refs,
            facts=facts,
        )
    finally:
        container.shutdown()
    return 0


R36_CASES = ("induced_underrun", "suspend_resume", "device_failure")


def _r36_case_status(case: str, facts: dict[str, Any]) -> str:
    if facts.get("case") != case:
        return "FAIL"
    required_true = (
        "incident_retained",
        "recovered_state_reported",
        "continuity_proof",
        "generation_fresh",
    )
    if any(facts.get(field) is False for field in required_true):
        return "FAIL"
    if any(facts.get(field) is not True for field in required_true):
        return "REQUIRES_OPERATOR_CONFIRMATION"
    if facts.get("false_verified_after_incident") is True:
        return "FAIL"
    loops = facts.get("recovery_loop_count")
    if not isinstance(loops, int):
        return "REQUIRES_OPERATOR_CONFIRMATION"
    if loops != 0:
        return "FAIL"
    if case == "induced_underrun":
        if facts.get("fault_injected") is False or facts.get("xrun_observed") is False:
            return "FAIL"
        if (
            facts.get("fault_injected") is not True
            or facts.get("xrun_observed") is not True
        ):
            return "REQUIRES_OPERATOR_CONFIRMATION"
        return "PASS"
    if facts.get("mechanism_available") is not True:
        return "REQUIRES_OPERATOR_CONFIRMATION"
    if not facts.get("operator_reference") or facts.get("action_completed") is not True:
        return "REQUIRES_OPERATOR_CONFIRMATION"
    if case == "device_failure":
        if facts.get("same_identity_after") is not True:
            return "FAIL"
        if facts.get("physical_reenumeration_observed") is not True:
            return "FAIL"
    if case == "suspend_resume":
        if not isinstance(facts.get("signal_truth_after"), dict):
            return "FAIL"
        before = facts.get("suspend_success_before")
        after = facts.get("suspend_success_after")
        if not isinstance(before, int) or not isinstance(after, int) or after <= before:
            return "FAIL"
    return "PASS"


def _r36_cases_status(cases: dict[str, Any]) -> str:
    statuses = {
        case: _r36_case_status(case, cases[case])
        for case in R36_CASES
        if isinstance(cases.get(case), dict)
    }
    if any(status == "FAIL" for status in statuses.values()):
        return "FAIL"
    if set(statuses) != set(R36_CASES):
        return "REQUIRES_OPERATOR_CONFIRMATION"
    return (
        "PASS"
        if all(status == "PASS" for status in statuses.values())
        else "REQUIRES_OPERATOR_CONFIRMATION"
    )


def _r36_prepare_facts(
    *,
    case: str,
    device_id: str,
    locator: str,
    device_generation: int | None,
    signal_identity: dict[str, Any] | None,
    playback_status: str,
    operator_reference: str,
    usb_instance_before: dict[str, Any] | None = None,
    suspend_success_before: int | None = None,
) -> dict[str, Any]:
    return {
        "case": case,
        "state": "WAITING_OPERATOR_ACTION",
        "device_id": device_id,
        "locator": locator,
        "device_generation_before": device_generation,
        "signal_identity_before": copy.deepcopy(signal_identity),
        "playback_status_before": playback_status,
        "operator_reference": operator_reference,
        "usb_instance_before": copy.deepcopy(usb_instance_before),
        "suspend_success_before": suspend_success_before,
        "prepared_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }


def _r36_complete_facts(
    baseline: dict[str, Any],
    *,
    after_row: dict[str, Any] | None,
    after_result: dict[str, Any],
    after_usb_instance: dict[str, Any] | None = None,
    suspend_success_after: int | None = None,
) -> dict[str, Any]:
    after_row = after_row if isinstance(after_row, dict) else {}
    truth = after_result.get("signal_truth")
    truth = truth if isinstance(truth, dict) else {}
    after_identity = truth.get("identity")
    after_identity = after_identity if isinstance(after_identity, dict) else None
    before_identity = baseline.get("signal_identity_before")
    before_identity = before_identity if isinstance(before_identity, dict) else None
    before_device_generation = baseline.get("device_generation_before")
    after_device_generation = after_row.get("generation")

    def positive_delta(before, after) -> int | None:
        if not isinstance(before, int) or not isinstance(after, int):
            return None
        return after - before

    device_delta = positive_delta(before_device_generation, after_device_generation)
    execution_delta = positive_delta(
        (before_identity or {}).get("execution_generation"),
        (after_identity or {}).get("execution_generation"),
    )
    port_delta = positive_delta(
        (before_identity or {}).get("port_generation"),
        (after_identity or {}).get("port_generation"),
    )
    case = baseline.get("case")
    before_usb = baseline.get("usb_instance_before")
    before_usb = before_usb if isinstance(before_usb, dict) else None
    physical_reenumeration = bool(
        case == "device_failure"
        and before_usb
        and after_usb_instance
        and before_usb.get("busnum") == after_usb_instance.get("busnum")
        and isinstance(before_usb.get("devnum"), int)
        and isinstance(after_usb_instance.get("devnum"), int)
        and before_usb["devnum"] != after_usb_instance["devnum"]
    )
    suspend_before = baseline.get("suspend_success_before")
    suspend_delta = positive_delta(suspend_before, suspend_success_after)
    if case == "device_failure":
        generation_fresh = physical_reenumeration
        observed_deltas = [1] if physical_reenumeration else []
    else:
        generation_fresh = bool(
            isinstance(suspend_delta, int)
            and suspend_delta > 0
            and after_identity is not None
        )
        observed_deltas = [suspend_delta] if isinstance(suspend_delta, int) else []
    recovery_loop_count = max([max(0, value - 1) for value in observed_deltas] or [0])
    same_identity = bool(
        after_row.get("stableDeviceId") == baseline.get("device_id")
        and after_row.get("alsaLocator") == baseline.get("locator")
    )
    state = (truth.get("verdict") or {}).get("state")
    state_reported = isinstance(state, str) and bool(state)
    direct_state = state in {"direct", "direct_container_adapted"}
    action_completed = bool(baseline.get("operator_reference") and generation_fresh)
    continuity = bool(
        same_identity
        and after_row.get("available") is True
        and after_result.get("status") == PlaybackStatus.PLAYING.value
        and not after_result.get("error_message")
        and direct_state
        and generation_fresh
    )
    return {
        "case": case,
        "mechanism_available": True,
        "operator_reference": baseline.get("operator_reference"),
        "action_completed": action_completed,
        "incident_retained": bool(before_identity and baseline.get("prepared_at")),
        "device_id": baseline.get("device_id"),
        "same_identity_after": same_identity,
        "device_generation_before": before_device_generation,
        "device_generation_after": after_device_generation,
        "device_generation_delta": device_delta,
        "signal_identity_before": before_identity,
        "signal_identity_after": after_identity,
        "execution_generation_delta": execution_delta,
        "port_generation_delta": port_delta,
        "usb_instance_before": before_usb,
        "usb_instance_after": copy.deepcopy(after_usb_instance),
        "physical_reenumeration_observed": physical_reenumeration,
        "suspend_success_before": suspend_before,
        "suspend_success_after": suspend_success_after,
        "suspend_success_delta": suspend_delta,
        "generation_fresh": generation_fresh,
        "recovered_state_reported": state_reported,
        "continuity_proof": continuity,
        "false_verified_after_incident": bool(direct_state and not generation_fresh),
        "recovery_loop_count": recovery_loop_count,
        "signal_truth_after": truth,
    }


def _r36_wip_dir(args) -> Path:
    explicit = getattr(args, "wip_dir", None)
    if explicit is not None:
        return Path(explicit)
    run_dir = os.environ.get("M11_4_RUN_DIR")
    if run_dir:
        return Path(run_dir) / "r36"
    evidence = _evidence_module()
    return evidence.STATE_ROOT / "r36-wip" / time.strftime("%Y%m%dT%H%M%S") / "r36"


def _r36_wip_meta(container, args) -> dict[str, Any]:
    qualification = getattr(getattr(container, "_aob", None), "_qualification", None)
    fingerprint = None
    if qualification is not None:
        with contextlib.suppress(Exception):
            fingerprint = qualification.current_environment_fingerprint(args.device_id)
    return {
        "schema_version": 1,
        "experiment": "R36",
        "device_id": args.device_id,
        "locator": args.locator,
        "environment_fingerprint": fingerprint,
        "implementation_head": _git_head(),
        "canonical_cases": list(R36_CASES),
        "case_media": {
            args.case: {
                "media": str(args.media),
                "media_sha256": _file_sha256(args.media),
            }
        },
        "created_wallclock_utc": _evidence_module().utc_now_iso(),
    }


def _r36_wip_mismatch(previous: dict[str, Any], current: dict[str, Any]) -> str | None:
    checks = (
        ("device_id", "device identity"),
        ("locator", "ALSA locator"),
        ("environment_fingerprint", "environment fingerprint"),
        ("implementation_head", "implementation HEAD"),
        ("canonical_cases", "canonical R36 case contract"),
    )
    for key, label in checks:
        if previous.get(key) != current.get(key):
            return f"{label} changed ({key})"
    previous_media = previous.get("case_media") or {}
    current_media = current.get("case_media") or {}
    for name, current_input in current_media.items():
        previous_input = previous_media.get(name)
        if isinstance(previous_input, dict) and previous_input != current_input:
            return f"case media changed for {name} (case_media)"
    return None


def _r36_meta_sync(evidence, wip_dir: Path, meta: dict[str, Any]) -> None:
    meta_path = wip_dir / "wip-meta.json"
    previous = None
    if meta_path.is_file():
        previous = json.loads(meta_path.read_text(encoding="utf-8"))
    if isinstance(previous, dict):
        mismatch = _r36_wip_mismatch(previous, meta)
        if mismatch:
            raise SystemExit(f"STOP_R36_WIP_PROVENANCE_MISMATCH: {mismatch}")
        merged = dict(previous.get("case_media") or {})
        merged.update(meta["case_media"])
        meta["case_media"] = merged
        meta["created_wallclock_utc"] = previous.get(
            "created_wallclock_utc", meta["created_wallclock_utc"]
        )
    evidence.atomic_write_json(meta_path, meta)


def _r36_checkpoint(wip_dir: Path, case: str, phase: str) -> dict[str, Any] | None:
    """Full checkpoint record for one case phase; survive crash and reboot."""
    path = wip_dir / f"case-{case}-{phase}.json"
    if not path.is_file():
        return None
    record = json.loads(path.read_text(encoding="utf-8"))
    return record if isinstance(record, dict) else None


def _r36_payload(record: dict[str, Any] | None) -> dict[str, Any] | None:
    payload = record.get("payload") if isinstance(record, dict) else None
    return payload if isinstance(payload, dict) else None


def _r36_write_checkpoint(
    evidence,
    journal,
    wip_dir: Path,
    *,
    case: str,
    phase: str,
    payload: dict[str, Any],
    event: str,
    result: str | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": 1,
        "case": case,
        "phase": phase,
        "payload": payload,
        "sealed_wallclock_utc": evidence.utc_now_iso(),
    }
    if result is not None:
        record["result"] = result
    evidence.atomic_write_json(wip_dir / f"case-{case}-{phase}.json", record)
    journal.append(event, {"case": case, "phase": phase, "result": result})
    return record


def _r36_wip_cases(wip_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Completed (or deferred) cases and pending prepared baselines."""
    cases: dict[str, Any] = {}
    pending: dict[str, Any] = {}
    for case in R36_CASES:
        complete = _r36_payload(_r36_checkpoint(wip_dir, case, "complete"))
        if complete is not None:
            cases[case] = complete
            continue
        deferred = _r36_payload(_r36_checkpoint(wip_dir, case, "deferred"))
        if deferred is not None:
            cases[case] = deferred
            continue
        prepare = _r36_payload(_r36_checkpoint(wip_dir, case, "prepare"))
        if prepare is not None:
            pending[case] = prepare
    return cases, pending


def _r36_canonical_facts(wip_dir: Path, existing_facts: Any) -> dict[str, Any]:
    existing = existing_facts if isinstance(existing_facts, dict) else {}
    cases = copy.deepcopy(existing.get("cases") or {})
    pending = copy.deepcopy(existing.get("pending_cases") or {})
    wip_cases, wip_pending = _r36_wip_cases(wip_dir)
    cases.update(wip_cases)
    pending.update(wip_pending)
    for case in list(pending):
        if case in cases:
            pending.pop(case, None)
    return {"cases": cases, "pending_cases": pending}


def _r36_import(args, wip_dir: Path) -> None:
    """Import sealed case evidence into the canonical manifest, once."""
    existing_facts = _manifest(args.manifest)["experiments"]["R36"].get("facts")
    facts = _r36_canonical_facts(wip_dir, existing_facts)
    if existing_facts == facts:
        print("R36: canonical record already matches the sealed cases")
        return
    refs: list[str] = []
    for case in R36_CASES:
        entry = facts["cases"].get(case)
        reference = entry.get("operator_reference") if isinstance(entry, dict) else None
        if isinstance(reference, str) and reference.strip():
            refs.append(f"operator:{reference}")
    refs.append(f"runtime:{args.media}")
    _record(
        args.manifest,
        experiment="R36",
        status=_r36_cases_status(facts["cases"]),
        evidence=refs,
        facts=facts,
    )


def command_fault_prepare(args) -> int:
    if args.case not in {"suspend_resume", "device_failure"}:
        raise SystemExit("fault-prepare is only for operator-driven R36 cases")
    if not args.media.is_file():
        raise SystemExit(f"media fixture does not exist: {args.media}")
    evidence = _evidence_module()
    wip_dir = _r36_wip_dir(args)
    wip_dir.mkdir(parents=True, exist_ok=True)
    journal = evidence.EventJournal(wip_dir / "journal.jsonl")
    container = _container(args.device_id, args.locator)
    try:
        _r36_meta_sync(evidence, wip_dir, _r36_wip_meta(container, args))
        if _r36_checkpoint(wip_dir, args.case, "complete") is not None:
            raise SystemExit(
                f"STOP_R36_CASE_ALREADY_COMPLETED: {args.case} already has a complete "
                "checkpoint; use a fresh WIP directory to repeat the case"
            )
        if _r36_checkpoint(wip_dir, args.case, "prepare") is not None:
            journal.append("R36_CASE_REPREPARE", {"case": args.case})
        journal.append("R36_CASE_START", {"case": args.case, "phase": "prepare"})
        _wip_heartbeat(args, "r36-prepare", args.case, wip_dir=wip_dir)
        result = _play(container, args.media, args.mode)
        row = _row(container, args.device_id, args.locator)
        truth = result.get("signal_truth") or {}
        baseline = _r36_prepare_facts(
            case=args.case,
            device_id=args.device_id,
            locator=args.locator,
            device_generation=row.get("generation"),
            signal_identity=truth.get("identity") if isinstance(truth, dict) else None,
            playback_status=result.get("status") or "unknown",
            operator_reference=args.operator_reference,
            usb_instance_before=_usb_instance_witness(args.device_id),
            suspend_success_before=_suspend_success_count(),
        )
        _r36_write_checkpoint(
            evidence,
            journal,
            wip_dir,
            case=args.case,
            phase="prepare",
            payload=baseline,
            event="R36_CASE_PREPARE",
        )
        _wip_heartbeat(args, "r36-prepared", args.case, wip_dir=wip_dir)
        _r36_import(args, wip_dir)
    finally:
        container.shutdown()
    print(
        f"R36 {args.case} baseline saved; perform the operator action, then "
        "run fault-complete with the same device, manifest and media."
    )
    return 0


def command_fault_complete(args) -> int:
    if not args.media.is_file():
        raise SystemExit(f"media fixture does not exist: {args.media}")
    evidence = _evidence_module()
    resume = bool(getattr(args, "resume", False))
    wip_dir = _r36_wip_dir(args)
    wip_dir.mkdir(parents=True, exist_ok=True)
    journal = evidence.EventJournal(wip_dir / "journal.jsonl")
    container = _container(args.device_id, args.locator)
    try:
        _r36_meta_sync(evidence, wip_dir, _r36_wip_meta(container, args))
        journal.append(
            "R36_CASE_START",
            {"case": args.case, "phase": "complete", "resumed": resume},
        )
        _wip_heartbeat(args, "r36-complete", args.case, wip_dir=wip_dir)
        complete_record = _r36_checkpoint(wip_dir, args.case, "complete")
        if resume and complete_record is not None:
            journal.append("R36_CASE_RECOVERED", {"case": args.case})
        else:
            if complete_record is not None:
                previous_result = complete_record.get("result")
                if previous_result == "PASS":
                    raise SystemExit(
                        f"STOP_R36_CASE_ALREADY_SEALED: {args.case} is already sealed "
                        "PASS; physical evidence is append-only"
                    )
                if previous_result == "FAIL":
                    raise SystemExit(
                        f"STOP_R36_CASE_SEALED_FAIL: {args.case} is sealed as FAIL; "
                        "use a fresh WIP directory for an intentional retest"
                    )
                journal.append(
                    "R36_CASE_RETRY",
                    {"case": args.case, "previous_result": previous_result},
                )
            baseline = _r36_payload(_r36_checkpoint(wip_dir, args.case, "prepare"))
            existing_facts = _manifest(args.manifest)["experiments"]["R36"].get("facts")
            existing_facts = existing_facts if isinstance(existing_facts, dict) else {}
            manifest_pending = (existing_facts.get("pending_cases") or {}).get(
                args.case
            )
            if (
                isinstance(baseline, dict)
                and isinstance(manifest_pending, dict)
                and manifest_pending != baseline
            ):
                raise SystemExit(
                    "STOP_R36_WIP_PROVENANCE_MISMATCH: "
                    f"{args.case} baseline differs between WIP and manifest"
                )
            if not isinstance(baseline, dict):
                baseline = manifest_pending
                if isinstance(baseline, dict):
                    journal.append("R36_BASELINE_FROM_MANIFEST", {"case": args.case})
            if not isinstance(baseline, dict) or baseline.get("case") != args.case:
                raise SystemExit(
                    "matching R36 baseline missing; run fault-prepare first"
                )
            result = _play(container, args.media, args.mode)
            row = _row(container, args.device_id, args.locator)
            after_usb = _usb_instance_witness(args.device_id)
            after_suspend = _suspend_success_count()
            _r36_write_checkpoint(
                evidence,
                journal,
                wip_dir,
                case=args.case,
                phase="action",
                payload={
                    "case": args.case,
                    "operator_reference": baseline.get("operator_reference"),
                    "device_generation_after": row.get("generation"),
                    "usb_instance_after": copy.deepcopy(after_usb),
                    "suspend_success_after": after_suspend,
                    "observed_wallclock_utc": evidence.utc_now_iso(),
                },
                event="R36_CASE_ACTION",
            )
            _wip_heartbeat(args, "r36-action", args.case, wip_dir=wip_dir)
            facts = _r36_complete_facts(
                baseline,
                after_row=row,
                after_result=result,
                after_usb_instance=after_usb,
                suspend_success_after=after_suspend,
            )
            _r36_write_checkpoint(
                evidence,
                journal,
                wip_dir,
                case=args.case,
                phase="complete",
                payload=facts,
                event="R36_CASE_COMPLETE",
                result=_r36_case_status(args.case, facts),
            )
        _wip_heartbeat(args, "r36-complete-sealed", args.case, wip_dir=wip_dir)
        _r36_import(args, wip_dir)
    finally:
        container.shutdown()
    return 0


def command_xrun(args) -> int:
    if not args.inject:
        raise SystemExit("R36 is destructive fault injection; pass --inject explicitly")
    if args.case != "induced_underrun":
        # suspend/resume and device-failure recovery need operator-driven
        # mechanisms this lab cannot synthesize: record NOT_RUN honestly.
        previous = _manifest(args.manifest)["experiments"]["R36"].get("facts")
        previous = previous if isinstance(previous, dict) else {}
        cases = copy.deepcopy(previous.get("cases") or {})
        cases[args.case] = {
            "case": args.case,
            "mechanism_available": False,
            "reason": "requires an operator-driven mechanism, not lab-synthesizable",
            "recovered_state_reported": None,
            "continuity_proof": None,
            "generation_fresh": None,
            "recovery_loop_count": None,
        }
        _record(
            args.manifest,
            experiment="R36",
            status=_r36_cases_status(cases),
            evidence=[f"case:{args.case}"],
            facts={
                "cases": cases,
                "pending_cases": copy.deepcopy(previous.get("pending_cases") or {}),
            },
        )
        return 0
    if not args.media.is_file():
        raise SystemExit(f"media fixture does not exist: {args.media}")
    evidence = _evidence_module()
    resume = bool(getattr(args, "resume", False))
    wip_dir = _r36_wip_dir(args)
    wip_dir.mkdir(parents=True, exist_ok=True)
    journal = evidence.EventJournal(wip_dir / "journal.jsonl")
    container = _container(args.device_id, args.locator)
    try:
        _r36_meta_sync(evidence, wip_dir, _r36_wip_meta(container, args))
        journal.append(
            "R36_CASE_START",
            {"case": args.case, "phase": "induced_underrun", "resumed": resume},
        )
        _wip_heartbeat(args, "r36-xrun", args.case, wip_dir=wip_dir)
        complete_record = _r36_checkpoint(wip_dir, args.case, "complete")
        if resume and complete_record is not None:
            journal.append("R36_CASE_RECOVERED", {"case": args.case})
        else:
            if complete_record is not None:
                previous_result = complete_record.get("result")
                if previous_result == "PASS":
                    raise SystemExit(
                        f"STOP_R36_CASE_ALREADY_SEALED: {args.case} is already sealed "
                        "PASS; physical evidence is append-only"
                    )
                if previous_result == "FAIL":
                    raise SystemExit(
                        f"STOP_R36_CASE_SEALED_FAIL: {args.case} is sealed as FAIL; "
                        "use a fresh WIP directory for an intentional retest"
                    )
                journal.append(
                    "R36_CASE_RETRY",
                    {"case": args.case, "previous_result": previous_result},
                )
            if _r36_checkpoint(wip_dir, args.case, "deferred") is not None:
                journal.append(
                    "R36_CASE_RETRY",
                    {"case": args.case, "previous_result": "DEFERRED_ENVIRONMENT"},
                )
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
                # Never fabricate fault_injected=true: keep the case deferred
                # with the environment limitation spelled out.
                _r36_write_checkpoint(
                    evidence,
                    journal,
                    wip_dir,
                    case=args.case,
                    phase="deferred",
                    payload={
                        "case": args.case,
                        "mechanism_available": False,
                        "environment_deferred": True,
                        "reason": (
                            "kernel does not expose xrun_injection for this substream"
                        ),
                        "incident_retained": None,
                        "recovered_state_reported": None,
                        "continuity_proof": None,
                        "generation_fresh": None,
                        "recovery_loop_count": None,
                    },
                    event="R36_CASE_DEFERRED",
                )
            else:
                _r36_write_checkpoint(
                    evidence,
                    journal,
                    wip_dir,
                    case=args.case,
                    phase="prepare",
                    payload={
                        "case": args.case,
                        "signal_identity_before": (
                            truth.get("identity") if isinstance(truth, dict) else None
                        ),
                        "alsa_locator": (
                            (alsa or {}).get("locator")
                            if isinstance(alsa, dict)
                            else None
                        ),
                    },
                    event="R36_CASE_PREPARE",
                )
                before = (
                    status_path.read_text(encoding="utf-8")
                    if status_path.exists()
                    else ""
                )
                xrun_path.write_text("1\n", encoding="utf-8")
                immediate = (
                    status_path.read_text(encoding="utf-8")
                    if status_path.exists()
                    else ""
                )
                _r36_write_checkpoint(
                    evidence,
                    journal,
                    wip_dir,
                    case=args.case,
                    phase="action",
                    payload={
                        "case": args.case,
                        "xrun_path": str(xrun_path),
                        "status_path": str(status_path),
                        "status_before": before,
                        "status_immediate": immediate,
                    },
                    event="R36_CASE_ACTION",
                )
                _pump(container, 2.0)
                after_truth = _truth(container) or {}
                after_reasons = (after_truth.get("verdict") or {}).get(
                    "reason_codes"
                ) or []
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
                before_identity = (
                    truth.get("identity") if isinstance(truth, dict) else None
                )
                after_identity = (
                    after_truth.get("identity")
                    if isinstance(after_truth, dict)
                    else None
                )
                generation_fresh = bool(
                    isinstance(before_identity, dict)
                    and isinstance(after_identity, dict)
                    and (
                        after_identity.get("execution_generation")
                        != before_identity.get("execution_generation")
                        or after_identity.get("port_generation")
                        != before_identity.get("port_generation")
                    )
                )
                resources = _runtime_resource_snapshot(container)
                facts = {
                    "case": args.case,
                    "fault_injected": True,
                    "xrun_observed": observed,
                    "incident_retained": True,
                    "recovered_state_reported": after_state is not None,
                    "continuity_proof": bool(
                        observed
                        and generation_fresh
                        and resources["pump_alive"]
                        and not result["error_message"]
                    ),
                    "false_verified_after_incident": bool(
                        false_verified and not generation_fresh
                    ),
                    "generation_fresh": generation_fresh,
                    "recovery_loop_count": max(
                        0,
                        int(resources.get("port_generation") or 0)
                        - int((before_identity or {}).get("port_generation") or 0)
                        - 1,
                    ),
                    "status_before": before,
                    "status_immediate": immediate,
                    "signal_truth_after": after_truth,
                    "alsa_locator": (
                        (alsa or {}).get("locator") if isinstance(alsa, dict) else None
                    ),
                }
                _r36_write_checkpoint(
                    evidence,
                    journal,
                    wip_dir,
                    case=args.case,
                    phase="complete",
                    payload=facts,
                    event="R36_CASE_COMPLETE",
                    result=_r36_case_status(args.case, facts),
                )
        _wip_heartbeat(args, "r36-xrun-sealed", args.case, wip_dir=wip_dir)
        _r36_import(args, wip_dir)
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
    transition.add_argument("--first-sample-method", required=True)
    transition.add_argument("--first-sample-fixture", type=Path, required=True)
    transition.add_argument("--first-sample-expected-marker", required=True)
    transition.add_argument(
        "--first-sample-observations",
        type=Path,
        required=True,
        help=(
            "JSON object keyed by 0/100/250/500/1000; each value supplies "
            "evidence_reference and observed_result"
        ),
    )
    transition.add_argument(
        "--wip-dir",
        type=Path,
        help=(
            "Durable work-in-progress directory; defaults to "
            "$M11_4_RUN_DIR/r25 or the local state root"
        ),
    )
    transition.add_argument(
        "--resume",
        action="store_true",
        help="Continue missing delays only when WIP provenance still matches",
    )
    transition.set_defaults(func=command_transition)

    soak = common("soak")
    soak.add_argument("--media", type=Path, nargs="+", required=True)
    soak.add_argument("--duration-seconds", type=float, required=True)
    soak.add_argument("--fail-fast", action="store_true")
    soak.add_argument("--checkpoint-every", type=int, default=20)
    soak.add_argument(
        "--usb-sysfs-path",
        type=Path,
        help="Exact sysfs USB node; its VID/PID is verified against --device-id",
    )
    soak.set_defaults(func=command_soak)

    tail = common("tail")
    tail.add_argument("--media", type=Path, required=True)
    tail.add_argument("--fixture", choices=R35_FIXTURES, required=True)
    tail.add_argument(
        "--tail-result", choices=("PASS", "FAIL", "NOT_OBSERVED"), required=True
    )
    tail.add_argument("--evidence-kind", choices=("capture", "operator"), required=True)
    tail.add_argument("--evidence-reference", required=True)
    tail.add_argument("--method", required=True)
    tail.add_argument("--falsifier-observed", action="store_true")
    tail.add_argument("--timeout-seconds", type=float, default=30.0)
    tail.add_argument(
        "--wip-dir",
        type=Path,
        help=(
            "Durable work-in-progress directory; defaults to "
            "$M11_4_RUN_DIR/r35 or the local state root"
        ),
    )
    tail.add_argument(
        "--resume",
        action="store_true",
        help="Recover an already-sealed fixture only when WIP provenance still matches",
    )
    tail.set_defaults(func=command_tail)

    fault_prepare = common("fault-prepare")
    fault_prepare.add_argument("--media", type=Path, required=True)
    fault_prepare.add_argument(
        "--case", choices=("suspend_resume", "device_failure"), required=True
    )
    fault_prepare.add_argument("--operator-reference", required=True)
    fault_prepare.add_argument(
        "--wip-dir",
        type=Path,
        help=(
            "Durable work-in-progress directory; defaults to "
            "$M11_4_RUN_DIR/r36 or the local state root"
        ),
    )
    fault_prepare.set_defaults(func=command_fault_prepare)

    fault_complete = common("fault-complete")
    fault_complete.add_argument("--media", type=Path, required=True)
    fault_complete.add_argument(
        "--case", choices=("suspend_resume", "device_failure"), required=True
    )
    fault_complete.add_argument(
        "--wip-dir",
        type=Path,
        help=(
            "Durable work-in-progress directory; defaults to "
            "$M11_4_RUN_DIR/r36 or the local state root"
        ),
    )
    fault_complete.add_argument(
        "--resume",
        action="store_true",
        help="Recover an already-sealed case only when WIP provenance still matches",
    )
    fault_complete.set_defaults(func=command_fault_complete)

    xrun = common("xrun")
    xrun.add_argument("--media", type=Path, required=True)
    xrun.add_argument("--inject", action="store_true")
    xrun.add_argument("--case", choices=R36_CASES, default="induced_underrun")
    xrun.add_argument(
        "--wip-dir",
        type=Path,
        help=(
            "Durable work-in-progress directory; defaults to "
            "$M11_4_RUN_DIR/r36 or the local state root"
        ),
    )
    xrun.add_argument(
        "--resume",
        action="store_true",
        help="Recover an already-sealed case only when WIP provenance still matches",
    )
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
