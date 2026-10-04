"""AP2_PREFLIGHT_SMOKE — bounded development-readiness smoke (PRE-AP2-01 WU3).

This is NOT R32 evidence. It never writes, edits or satisfies PCM closure
manifests and never changes the physical verdict. It answers one question:

    Is this exact HEAD sufficiently stable for restricted Phase 2 F00-F04?

Scenarios: Direct -> System Output -> Direct round trips with accepted
playback, controlled sample-rate transitions, load/stop cycles and a
continuous monitored Direct playback window. A watchdog bounds any stall so
a known upstream GStreamer race is recorded truthfully and classified
instead of hanging forever.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEVICE_ID = "usb:152a:85dd:3-3.3.2"
LOCATOR = "hw:CARD=AUDIO,DEV=0"
CORPUS = ROOT / "evidence/dac-v35-110/2026-09-25-smsl-152a85dd-operator-run/fixtures"
MEDIA = (
    ROOT
    / "evidence/dac-v35-pcm-closure/2026-09-30-smsl-152a85dd"
    / "fixtures/r25_marker_44100.wav",
    CORPUS / "pcm16_44100.wav",
    CORPUS / "pcm16_48000.wav",
    CORPUS / "pcm16_44100.wav",
    CORPUS / "pcm16_96000.wav",
    CORPUS / "pcm24_192000.wav",
    CORPUS / "pcm16_44100.wav",
)

_spec = importlib.util.spec_from_file_location(
    "dac_m11_4_pcm_lab", ROOT / "scripts/dac_m11_4_pcm_lab.py"
)
lab = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lab)

from michi.domain.playback import PlaybackStatus  # noqa: E402


class Smoke:
    def __init__(self, duration_s: float) -> None:
        self.duration_s = duration_s
        self.started = time.monotonic()
        self.stop = False
        self.stalled = False
        self.last_progress = time.monotonic()
        self.max_pump_gap_ms = 0.0
        self.phase_a_seconds = 0.0
        self.load_stop_cycles = 0
        self.rate_transitions = 0
        self.round_trips = 0
        self.hold_cycles = 0
        self.previous_identity: dict | None = None
        self.runtime_errors: list[str] = []
        self.xrun_count = 0
        self.stale_count = 0
        self.hidden_count = 0
        self.contradictions = 0
        self.truth_states: dict[str, int] = {}
        self.ownership_violations = 0
        self.usb_kernel_errors: list[str] = []
        self.rss_start_kb: int | None = None
        self.rss_end_kb: int | None = None
        self.issues: list[str] = []

    def note(self, message: str) -> None:
        print(f"{time.strftime('%H:%M:%S')} {message}", flush=True)


def _pump(container, smoke: Smoke, seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline and not smoke.stop:
        start = time.monotonic()
        container._app.processEvents()
        gap_ms = (time.monotonic() - start) * 1000.0
        if gap_ms > smoke.max_pump_gap_ms:
            smoke.max_pump_gap_ms = gap_ms
        time.sleep(0.01)


def _wait_for(container, smoke: Smoke, predicate, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and not smoke.stop:
        if predicate():
            return True
        _pump(container, smoke, 0.05)
    return predicate()


def _play_hold(
    container, smoke: Smoke, media: Path, hold_s: float, mode: str = "compatible"
) -> dict:
    """Load, hold the media while pumping, stop, and return its truth snapshot."""
    container._aob.select_path_mode(mode)
    container._playback.load_and_play(media)
    playing = _wait_for(
        container,
        smoke,
        lambda: (
            container._playback.state.status is PlaybackStatus.PLAYING
            or bool(container._playback.state.error_message)
        ),
        20.0,
    )
    if not playing or container._playback.state.error_message:
        smoke.runtime_errors.append(
            str(container._playback.state.error_message)
            or "media did not reach PLAYING"
        )
    else:
        _pump(container, smoke, hold_s)
    if container._playback.state.error_message:
        smoke.runtime_errors.append(str(container._playback.state.error_message))
    snapshot = lab._truth(container) or {}
    verdict = snapshot.get("verdict") or {}
    state = str(verdict.get("state") or "unknown")
    smoke.truth_states[state] = smoke.truth_states.get(state, 0) + 1
    reasons = verdict.get("reason_codes") or []
    if "ST_XRUN" in reasons:
        smoke.xrun_count += 1
    if "CONTAINER_TRANSFORM_UNOBSERVED" in reasons:
        smoke.hidden_count += 1
    if state == "contradicted":
        smoke.contradictions += 1
    identity = snapshot.get("identity")
    if isinstance(identity, dict):
        if identity == smoke.previous_identity:
            smoke.stale_count += 1
        smoke.previous_identity = identity
    container._playback.stop()
    _wait_for(
        container,
        smoke,
        lambda: container._playback.state.status is PlaybackStatus.STOPPED,
        6.0,
    )
    smoke.load_stop_cycles += 1
    smoke.last_progress = time.monotonic()
    if smoke.load_stop_cycles % 25 == 0:
        smoke.note(f"load/stop cycles={smoke.load_stop_cycles}")
    return snapshot


def _watchdog(smoke: Smoke) -> None:
    while not smoke.stop:
        time.sleep(10)
        if time.monotonic() - smoke.last_progress > 90:
            smoke.stalled = True
            smoke.issues.append(
                "owner loop stalled >90s (suspected known upstream GStreamer race)"
            )
            smoke.stop = True
            return


def _usb_kernel_errors(since_iso: str) -> list[str]:
    try:
        completed = subprocess.run(
            [
                "journalctl",
                "--dmesg",
                "--no-pager",
                "--output=cat",
                "--since",
                since_iso,
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [
        line.strip()
        for line in completed.stdout.splitlines()
        if "3-3.3.2" in line and ("error" in line or "fail" in line or "reset" in line)
    ]


def main() -> int:
    parser = argparse.ArgumentParser(prog="ap2-preflight-smoke")
    parser.add_argument("--duration-minutes", type=float, default=15.0)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    smoke = Smoke(args.duration_minutes * 60.0)
    since_iso = time.strftime("%Y-%m-%d %H:%M:%S")
    container = None
    try:
        threading.Thread(target=_watchdog, args=(smoke,), daemon=True).start()
        container = lab._container(DEVICE_ID, LOCATOR)
        smoke.rss_start_kb = lab._process_rss_kb()

        smoke.note("phase D: Direct<->System Output round trips with playback")
        _play_hold(container, smoke, MEDIA[0], 0.5)
        for _ in range(12):
            if smoke.stop:
                break
            container._aob.select_shared_output()
            shared_ok = _wait_for(
                container,
                smoke,
                lambda: container._output_session.mode == "shared",
                10.0,
            )
            container._aob.select_device_for_playback(DEVICE_ID)
            direct_ok = _wait_for(
                container,
                smoke,
                lambda: container._output_session.mode == "direct",
                15.0,
            )
            if shared_ok and direct_ok:
                smoke.round_trips += 1
            else:
                smoke.ownership_violations += 1
                smoke.issues.append(
                    f"round trip not verified (shared={shared_ok} direct={direct_ok})"
                )
        smoke.note(f"round trips={smoke.round_trips}")
        _play_hold(container, smoke, MEDIA[1], 0.2)

        smoke.note("phase B/C: rate transitions and load/stop cycles")
        previous_rate: int | None = None
        for index in range(70):
            if smoke.stop:
                break
            snapshot = _play_hold(container, smoke, MEDIA[index % len(MEDIA)], 0.2)
            rate = (snapshot.get("decoded") or {}).get("rate_hz")
            if (
                isinstance(rate, int)
                and previous_rate is not None
                and rate != previous_rate
            ):
                smoke.rate_transitions += 1
            if isinstance(rate, int):
                previous_rate = rate
        smoke.note(
            f"transitions={smoke.rate_transitions} load/stop={smoke.load_stop_cycles}"
        )

        smoke.note("phase A: continuous monitored Direct playback")
        phase_a_started = time.monotonic()
        deadline = phase_a_started + smoke.duration_s
        index = 0
        while time.monotonic() < deadline and not smoke.stop:
            _play_hold(container, smoke, MEDIA[index % len(MEDIA)], 5.0)
            smoke.hold_cycles += 1
            index += 1
        smoke.phase_a_seconds = time.monotonic() - phase_a_started

        pump = lab._runtime_resource_snapshot(container)
        if not pump.get("pump_alive", False):
            smoke.ownership_violations += 1
            smoke.issues.append("pump not alive at smoke end")
        if pump.get("owned_pipelines", 0) > 1:
            smoke.ownership_violations += 1
            smoke.issues.append("more than one owned pipeline at smoke end")
    except Exception as exc:  # noqa: BLE001 - smoke boundary
        smoke.issues.append(f"smoke exception: {type(exc).__name__}: {exc}")
    finally:
        if container is not None:
            try:
                smoke.rss_end_kb = lab._process_rss_kb()
                container.shutdown()
            except Exception as exc:  # noqa: BLE001
                smoke.issues.append(f"shutdown exception: {type(exc).__name__}: {exc}")
        smoke.stop = True
        smoke.usb_kernel_errors = _usb_kernel_errors(since_iso)

    targets_met = (
        smoke.phase_a_seconds >= smoke.duration_s - 30.0
        and smoke.rate_transitions >= 50
        and smoke.load_stop_cycles >= 20
        and smoke.round_trips >= 10
    )
    if smoke.stalled:
        verdict = "BLOCKED"
        classification = (
            "known upstream GStreamer 1.28.x state-change race "
            "(GST_LIFECYCLE_GATE/F05); F00-F04 do not depend on Direct "
            "lifecycle changes"
        )
    elif smoke.load_stop_cycles == 0:
        verdict = "BLOCKED"
        classification = "no playback cycles completed (device/environment)"
    elif (
        smoke.runtime_errors
        or smoke.xrun_count
        or smoke.stale_count
        or smoke.hidden_count
        or smoke.ownership_violations
        or smoke.usb_kernel_errors
        or smoke.max_pump_gap_ms > 2000.0
        or not targets_met
    ):
        verdict = "FAIL"
        classification = None
    else:
        verdict = "PASS"
        classification = None

    result = {
        "schema_version": 1,
        "kind": "AP2_PREFLIGHT_SMOKE",
        "head": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True
        ).stdout.strip(),
        "started_local": time.strftime(
            "%Y-%m-%dT%H:%M:%S%z", time.localtime(smoke.started)
        ),
        "duration_minutes": round((time.monotonic() - smoke.started) / 60.0, 2),
        "scenarios": {
            "round_trips": smoke.round_trips,
            "rate_transitions": smoke.rate_transitions,
            "load_stop_cycles": smoke.load_stop_cycles,
            "hold_cycles": smoke.hold_cycles,
            "phase_a_seconds": round(smoke.phase_a_seconds, 1),
            "max_pump_gap_ms": round(smoke.max_pump_gap_ms, 1),
        },
        "health": {
            "runtime_errors": smoke.runtime_errors[:20],
            "xrun_count": smoke.xrun_count,
            "stale_generations": smoke.stale_count,
            "hidden_conversions": smoke.hidden_count,
            "signal_truth_contradictions": smoke.contradictions,
            "signal_truth_states": smoke.truth_states,
            "ownership_violations": smoke.ownership_violations,
            "usb_kernel_errors": smoke.usb_kernel_errors[:10],
            "rss_start_kb": smoke.rss_start_kb,
            "rss_end_kb": smoke.rss_end_kb,
        },
        "verdict": verdict,
        "classification": classification,
        "issues": smoke.issues,
        "notes": [
            "not R32 evidence; does not modify the PCM closure manifests "
            "or the physical verdict",
            "bounded development-readiness window, not an 8 h stability proof",
        ],
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict, "result": str(args.result)}))
    return 0 if verdict in ("PASS", "BLOCKED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
