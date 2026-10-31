#!/usr/bin/env python3
"""AP2-F10 physical DoP <-> Native DSD handover evidence.

Plays a DSD64 fixture as DoP on DAC A, hands the accepted media over to Native
DSD on DAC B, then returns to DoP on DAC A through the real production
container. Records the observed family, plan identity, host release receipt and
Signal Truth. Audibility is never inferred: the report is explicitly marked
REQUIRES_OPERATOR_CONFIRMATION.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests" / "audio_phase2"))

from audio_phase2.dsd2pcm_conformance import _dsf_block_payload  # noqa: E402
from test_dsd_source_truth import build_dsf  # noqa: E402

from michi.bootstrap import ApplicationContainer  # noqa: E402
from michi.domain.audio_engine import AudioEngineId  # noqa: E402
from michi.domain.playback import PlaybackStatus  # noqa: E402

DEFAULT_A = "usb:152a:85dd:3-3.3.2"
DEFAULT_B = "usb:2fc6:f882:HA01"
DEFAULT_PREFIX = ROOT / "build/lib.linux-x86_64-cpython-311/michi/native/gstreamer-1.0"
AUDIBILITY = "REQUIRES_OPERATOR_CONFIRMATION"


def _pump(container: ApplicationContainer, seconds: float, until=None) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        container._app.processEvents()
        if until is not None and until():
            return True
        time.sleep(0.02)
    return bool(until is not None and until())


def _fixture(path: Path, *, seconds: int) -> dict:
    rate = 2_822_400
    mono = bytes([0x69]) * (rate // 8 * seconds)
    payload = _dsf_block_payload(mono)
    blob = build_dsf(
        rate=rate, channels=2, bits=8, sample_count=len(mono) * 8, payload=payload
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(blob)
    return {
        "path": str(path),
        "bytes": len(blob),
        "sha256": hashlib.sha256(blob).hexdigest(),
        "rate_hz": rate,
        "seconds": seconds,
        "pattern": "0x69",
    }


def _snapshot(container: ApplicationContainer, tag: str) -> dict:
    session = container._output_session
    state = container._playback.state
    snapshot = session.transition_snapshot()
    family = snapshot.get("family")
    if hasattr(family, "value"):
        snapshot["family"] = family.value
    return {
        "tag": tag,
        "status": state.status.name.lower(),
        "error": state.error_message,
        "mode": session.mode,
        "dop_active": session.dop_active,
        "native_dsd_active": session.native_dsd_active,
        "dsd_pcm_active": session.dsd_pcm_active,
        "selected_device_id": container._aob.selectedDeviceId,
        "path_mode": container._aob.selectedPathMode,
        "generation": session.generation,
        "handover_state": (
            str(session.handover_state) if session.handover_state else None
        ),
        "handover_target": session.handover_target_family,
        "release": session.last_handover_release_evidence,
        "snapshot": snapshot,
        "output_truth": getattr(state, "output_truth", None),
        "output_truth_label": getattr(state, "output_truth_label", None),
    }


def _playing(container: ApplicationContainer, device: str, family: str) -> bool:
    session = container._output_session
    return (
        container._playback.state.status is PlaybackStatus.PLAYING
        and container._aob.selectedDeviceId == device
        and getattr(session, f"{family}_active", False)
    )


def _release_matches(release, *, execution_id: str, device: str) -> bool:
    return (
        isinstance(release, dict)
        and release.get("confirmed") is True
        and release.get("terminal_state") == "RELEASED"
        and release.get("provenance") == "SUPERVISED_HOST"
        and release.get("execution_id") == execution_id
        and release.get("device") == device
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device-a", default=DEFAULT_A)
    parser.add_argument("--device-b", default=DEFAULT_B)
    parser.add_argument("--locator-a", default="hw:CARD=AUDIO,DEV=0")
    parser.add_argument("--locator-b", default="hw:CARD=HA01,DEV=0")
    parser.add_argument("--plugin-prefix", type=Path, default=DEFAULT_PREFIX)
    parser.add_argument("--fixture-dir", type=Path, default=Path("/tmp/opencode"))
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    os.environ.pop("MICHI_GST_LAB_SINK", None)
    os.environ["MICHI_DOP_PLUGIN_PREFIX"] = str(args.plugin_prefix)
    fixture = _fixture(
        args.fixture_dir / "f10_physical_family_handover.dsf", seconds=args.seconds
    )

    container = ApplicationContainer()
    phases: list[dict] = []
    checks: dict[str, bool] = {}
    failure = ""
    try:
        container.initialize()
        _pump(
            container,
            15.0,
            lambda: container._playback.engine_switch_readiness().allowed,
        )
        container._engine_selection_coordinator.switch_to(AudioEngineId.GSTREAMER)
        _pump(
            container,
            20.0,
            lambda: (
                container._audio_engine_service.state.active_engine_id
                is AudioEngineId.GSTREAMER
            ),
        )
        os.environ["MICHI_DOP_EXPLICIT"] = "1"
        container._aob.select_device(args.device_a)
        container._aob.select_path_mode("compatible")
        container._playback.load_and_play(Path(fixture["path"]))
        a_ok = _pump(
            container,
            args.timeout,
            lambda: _playing(container, args.device_a, "dop"),
        )
        phase_a = _snapshot(container, "dop_on_device_a")
        phases.append(phase_a)
        checks["dop_on_a"] = a_ok and phase_a["error"] is None
        if not checks["dop_on_a"]:
            failure = "DoP did not reach PLAYING on device A"
            raise RuntimeError(failure)

        dop_execution = phase_a["snapshot"]["execution_id"]
        os.environ["MICHI_DOP_EXPLICIT"] = "0"
        container._aob.select_device_for_playback(args.device_b)
        b_ok = _pump(
            container,
            args.timeout,
            lambda: _playing(container, args.device_b, "native_dsd"),
        )
        phase_b = _snapshot(container, "native_dsd_on_device_b")
        phases.append(phase_b)
        checks["dop_to_native"] = (
            b_ok
            and phase_b["error"] is None
            and phase_b["handover_state"] == "ready"
            and phase_b["handover_target"] == "native_dsd"
            and _release_matches(
                phase_b["release"],
                execution_id=dop_execution,
                device=args.locator_a,
            )
        )
        if not checks["dop_to_native"]:
            failure = "DoP -> Native DSD handover was not confirmed"
            raise RuntimeError(failure)

        native_execution = phase_b["snapshot"]["execution_id"]
        os.environ["MICHI_DOP_EXPLICIT"] = "1"
        container._aob.select_device_for_playback(args.device_a)
        c_ok = _pump(
            container,
            args.timeout,
            lambda: _playing(container, args.device_a, "dop"),
        )
        phase_c = _snapshot(container, "dop_on_device_a_again")
        phases.append(phase_c)
        checks["native_to_dop"] = (
            c_ok
            and phase_c["error"] is None
            and phase_c["handover_state"] == "ready"
            and phase_c["handover_target"] == "dop"
            and _release_matches(
                phase_c["release"],
                execution_id=native_execution,
                device=args.locator_b,
            )
        )
        if not checks["native_to_dop"]:
            failure = "Native DSD -> DoP handover was not confirmed"
            raise RuntimeError(failure)
    except Exception as exc:  # noqa: BLE001 - evidence must record the failure
        failure = failure or str(exc)
    finally:
        with contextlib.suppress(Exception):
            container._playback.stop()
            _pump(
                container,
                3.0,
                lambda: container._playback.state.status is PlaybackStatus.STOPPED,
            )
        with contextlib.suppress(Exception):
            container.shutdown()

    result = "PASS" if all(checks.values()) and not failure else "FAIL"
    payload = {
        "schema": "michi.f10.physical_family_handover.v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "physical_dac": True,
        "devices": {
            "a": {"stable_device_id": args.device_a, "locator": args.locator_a},
            "b": {"stable_device_id": args.device_b, "locator": args.locator_b},
        },
        "fixture": fixture,
        "result": result,
        "checks": checks,
        "failure": failure,
        "phases": phases,
        "audibility": AUDIBILITY,
        "certification_claim": "NONE",
    }
    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    out = args.evidence_dir / "family_handover.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"result": result, "checks": checks, "evidence": str(out)}))
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
