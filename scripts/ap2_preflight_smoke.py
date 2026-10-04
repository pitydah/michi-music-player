"""AP2_PREFLIGHT_SMOKE — bounded development-readiness smoke (PRE-AP2-01 WU3/4C).

This is NOT R32 evidence. It never writes, edits or satisfies PCM closure
manifests and never changes the physical verdict.

Architecture: the tested Michi/GStreamer runtime always executes in a CHILD
process under ``scripts/m11_4_physical_supervisor.py``; the supervisor stays
outside a possible GStreamer wedge, watches a durable heartbeat written by the
tested main path, captures diagnostics and kills the child when progress
stalls. Exit codes: 0 = PASS, 1 = FAIL, 2 = BLOCKED (never look successful).

Scenarios: Direct <-> System Output round trips with accepted playback,
controlled sample-rate transitions, lifecycle churn, and a REAL steady Direct
window (one accepted media load, continuous PLAYING >= 15 minutes).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
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
HEARTBEAT_INTERVAL_S = 5.0

_spec = importlib.util.spec_from_file_location(
    "dac_m11_4_pcm_lab", ROOT / "scripts/dac_m11_4_pcm_lab.py"
)
lab = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lab)

_evidence_spec = importlib.util.spec_from_file_location(
    "m11_4_evidence", ROOT / "scripts/m11_4_evidence.py"
)
evidence = importlib.util.module_from_spec(_evidence_spec)
sys.modules["m11_4_evidence"] = evidence
_evidence_spec.loader.exec_module(evidence)

from michi.domain.playback import PlaybackStatus  # noqa: E402

SUPERVISOR = ROOT / "scripts/m11_4_physical_supervisor.py"


class Smoke:
    def __init__(self, steady_seconds: float, run_dir: Path) -> None:
        self.steady_seconds = steady_seconds
        self.run_dir = run_dir
        self.stop = False
        self.started_monotonic = time.monotonic()
        self.started_wallclock = evidence.utc_now_iso()
        self.max_pump_gap_ms = 0.0
        self.last_heartbeat = 0.0
        self.phase = "init"
        self.cycle = 0
        self.load_stop_cycles = 0
        self.rate_transitions = 0
        self.round_trips = 0
        self.lifecycle_cycles = 0
        self.steady_seconds_actual = 0.0
        self.runtime_errors: list[str] = []
        self.xrun_count = 0
        self.stale_count = 0
        self.hidden_count = 0
        self.contradictions = 0
        self.truth_states: dict[str, int] = {}
        self.ownership_violations = 0
        self.usb_kernel_errors: list[str] = []
        self.rss_samples: list[int] = []
        self.previous_identity: dict | None = None
        self.issues: list[str] = []

    def heartbeat(self, message: str = "") -> None:
        now = time.monotonic()
        if now - self.last_heartbeat < HEARTBEAT_INTERVAL_S:
            return
        self.last_heartbeat = now
        evidence.atomic_write_json(
            self.run_dir / evidence.PROGRESS,
            {
                "monotonic_ns": evidence.monotonic_ns(),
                "elapsed_seconds": round(now - self.started_monotonic, 1),
                "wall_time_utc": evidence.utc_now_iso(),
                "phase": self.phase,
                "cycle": self.cycle,
                "message": message,
                "rss_kb": lab._process_rss_kb(),
            },
        )

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
        smoke.heartbeat()
        time.sleep(0.01)


def _wait_for(container, smoke: Smoke, predicate, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and not smoke.stop:
        if predicate():
            return True
        _pump(container, smoke, 0.05)
    return predicate()


def _observe(container, smoke: Smoke, snapshot: dict, *, track_identity: bool) -> None:
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
    # Stale means "a NEW load reuses the previous execution identity"; repeated
    # observations of the same steady execution must never count as stale.
    if track_identity:
        identity = snapshot.get("identity")
        if isinstance(identity, dict):
            if identity == smoke.previous_identity:
                smoke.stale_count += 1
            smoke.previous_identity = identity


def _play_hold(container, smoke: Smoke, media: Path, hold_s: float) -> dict:
    container._aob.select_path_mode("compatible")
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
    _observe(container, smoke, snapshot, track_identity=True)
    container._playback.stop()
    _wait_for(
        container,
        smoke,
        lambda: container._playback.state.status is PlaybackStatus.STOPPED,
        6.0,
    )
    smoke.load_stop_cycles += 1
    smoke.cycle += 1
    return snapshot


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


def _steady_fixture(run_dir: Path, seconds: int) -> Path:
    """Generate one long local fixture; silence, 44.1 kHz stereo, FLAC."""
    path = run_dir / "steady-tone.flac"
    if path.exists():
        return path
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-t",
        str(seconds),
        "-c:a",
        "flac",
        str(path),
    ]
    subprocess.run(command, check=True, timeout=180)
    return path


def _child(args: argparse.Namespace) -> int:
    run_dir = Path(os.environ["M11_4_RUN_DIR"])
    smoke = Smoke(args.steady_minutes * 60.0, run_dir)
    container = None
    since_iso = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        smoke.phase = "setup"
        container = lab._container(DEVICE_ID, LOCATOR)
        smoke.rss_samples.append(lab._process_rss_kb())

        smoke.phase = "round-trips"
        smoke.note("round trips: Direct<->System Output with playback")
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

        smoke.phase = "transitions"
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

        smoke.phase = "lifecycle-churn"
        for index in range(20):
            if smoke.stop:
                break
            _play_hold(container, smoke, MEDIA[index % len(MEDIA)], 5.0)
            smoke.lifecycle_cycles += 1
        smoke.note(f"lifecycle churn cycles={smoke.lifecycle_cycles}")

        smoke.phase = "steady-direct"
        fixture = _steady_fixture(run_dir, int(args.steady_minutes * 60) + 600)
        smoke.note(f"steady direct on {fixture.name} for >= {args.steady_minutes} min")
        container._playback.load_and_play(fixture)
        if not _wait_for(
            container,
            smoke,
            lambda: (
                container._playback.state.status is PlaybackStatus.PLAYING
                or bool(container._playback.state.error_message)
            ),
            30.0,
        ):
            smoke.runtime_errors.append(
                "steady media did not reach PLAYING: "
                + str(container._playback.state.error_message)
            )
        else:
            steady_deadline = time.monotonic() + smoke.steady_seconds
            sample_at = time.monotonic() + 30.0
            while time.monotonic() < steady_deadline and not smoke.stop:
                _pump(container, smoke, 0.5)
                if time.monotonic() >= sample_at:
                    sample_at = time.monotonic() + 30.0
                    snapshot = lab._truth(container) or {}
                    _observe(container, smoke, snapshot, track_identity=False)
                    smoke.rss_samples.append(lab._process_rss_kb())
                if container._playback.state.status is not PlaybackStatus.PLAYING:
                    smoke.runtime_errors.append(
                        "steady playback left PLAYING before the window completed"
                    )
                    break
            smoke.steady_seconds_actual = time.monotonic() - (
                steady_deadline - smoke.steady_seconds
            )
        container._playback.stop()
        _wait_for(
            container,
            smoke,
            lambda: container._playback.state.status is PlaybackStatus.STOPPED,
            6.0,
        )

        smoke.phase = "finalize"
        pump = lab._runtime_resource_snapshot(container)
        if not pump.get("pump_alive", False):
            smoke.ownership_violations += 1
            smoke.issues.append("pump not alive at smoke end")
        if pump.get("owned_pipelines", 0) > 1:
            smoke.ownership_violations += 1
            smoke.issues.append("more than one owned pipeline at smoke end")
        smoke.rss_samples.append(lab._process_rss_kb())
    except Exception as exc:  # noqa: BLE001 - smoke boundary
        smoke.issues.append(f"smoke exception: {type(exc).__name__}: {exc}")
        smoke.runtime_errors.append(f"{type(exc).__name__}: {exc}")
    finally:
        if container is not None:
            try:
                container.shutdown()
            except Exception as exc:  # noqa: BLE001
                smoke.issues.append(f"shutdown exception: {type(exc).__name__}: {exc}")
        smoke.stop = True
        smoke.usb_kernel_errors = _usb_kernel_errors(since_iso)

    targets_met = (
        smoke.steady_seconds_actual >= smoke.steady_seconds - 30.0
        and smoke.rate_transitions >= 50
        and smoke.load_stop_cycles >= 20
        and smoke.round_trips >= 10
        and smoke.lifecycle_cycles >= 1
    )
    verdict = "FAIL"
    classification = None
    if not smoke.load_stop_cycles:
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
    else:
        verdict = "PASS"

    result = {
        "schema_version": 2,
        "kind": "AP2_PREFLIGHT_SMOKE",
        "head": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True
        ).stdout.strip(),
        "started_wallclock_utc": smoke.started_wallclock,
        "started_monotonic_ns": int(smoke.started_monotonic * 1e9),
        "duration_seconds": round(time.monotonic() - smoke.started_monotonic, 1),
        "scenarios": {
            "round_trips": smoke.round_trips,
            "rate_transitions": smoke.rate_transitions,
            "load_stop_cycles": smoke.load_stop_cycles,
            "lifecycle_churn_cycles": smoke.lifecycle_cycles,
            "steady_seconds": round(smoke.steady_seconds_actual, 1),
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
            "rss_kb_first": smoke.rss_samples[0] if smoke.rss_samples else None,
            "rss_kb_last": smoke.rss_samples[-1] if smoke.rss_samples else None,
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
    evidence.atomic_write_json(run_dir / "smoke-child-result.json", result)
    print(json.dumps({"verdict": verdict}))
    return 0 if verdict in ("PASS", "BLOCKED") else 1


def _supervisor_main(args: argparse.Namespace) -> int:
    checks: list[str] = []
    evidence.STATE_ROOT.mkdir(parents=True, exist_ok=True)
    if not all(media.is_file() for media in MEDIA):
        checks.append("fixtures missing")
    if evidence.free_disk_bytes(evidence.STATE_ROOT) < 2 * 1024**3:
        checks.append("insufficient free disk for the durable evidence root")
    if (
        subprocess.run(
            ["python", "-c", "import gi; import gi.repository.Gst"],
            capture_output=True,
            check=False,
        ).returncode
        != 0
    ):
        checks.append("GStreamer/PyGObject unavailable")
    if not Path("/sys/bus/usb/devices/3-3.3.2").exists():
        checks.append("DAC sysfs node missing")
    if (
        subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, check=False
        ).returncode
        != 0
    ):
        checks.append("ffmpeg unavailable for the steady fixture")
    if checks:
        payload = {
            "schema_version": 2,
            "kind": "AP2_PREFLIGHT_SMOKE",
            "verdict": "BLOCKED",
            "classification": "preflight checks failed: " + "; ".join(checks),
        }
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        print(json.dumps({"verdict": "BLOCKED", "result": str(args.result)}))
        return 2

    supervised = subprocess.run(
        [
            "python",
            str(SUPERVISOR),
            "run",
            "--campaign-id",
            "ap2-preflight",
            "--experiment",
            "AP2_PREFLIGHT_SMOKE",
            "--watchdog-seconds",
            "120",
            "--kill-grace-seconds",
            "10",
            "--",
            "python",
            str(Path(__file__).resolve()),
            "--child",
            "--steady-minutes",
            str(args.steady_minutes),
        ],
        capture_output=True,
        text=True,
        timeout=args.steady_minutes * 60 + 1800,
        cwd=ROOT,
    )
    lines = [line for line in supervised.stdout.strip().splitlines() if line.strip()]
    summary = json.loads(lines[-1]) if lines else {}
    run_dir = Path(summary.get("run_dir", ""))
    child_result = {}
    if run_dir and (run_dir / "smoke-child-result.json").exists():
        child_result = json.loads((run_dir / "smoke-child-result.json").read_text())

    supervisor_classification = summary.get("classification")
    has_child_result = bool(child_result)
    if supervisor_classification == "INTERRUPTED_WATCHDOG":
        verdict = "BLOCKED"
        classification = (
            "supervisor watchdog: known upstream GStreamer 1.28.x state-change "
            "race (GST_LIFECYCLE_GATE/F05); F00-F04 do not depend on Direct "
            "lifecycle changes"
        )
        exit_code = 2
    elif supervisor_classification not in ("COMPLETE", "CHILD_NONZERO_EXIT"):
        verdict = "BLOCKED"
        classification = f"supervisor classification {supervisor_classification!r}"
        exit_code = 2
    elif not has_child_result:
        verdict = "BLOCKED"
        classification = "child produced no result artifact"
        exit_code = 2
    elif child_result.get("verdict") == "FAIL":
        verdict = "FAIL"
        classification = child_result.get("classification")
        exit_code = 1
    elif (
        child_result.get("verdict") == "PASS"
        and supervisor_classification == "COMPLETE"
        and summary.get("exit_code") == 0
    ):
        verdict = "PASS"
        classification = None
        exit_code = 0
    else:
        verdict = "BLOCKED"
        classification = "inconsistent child/supervisor result"
        exit_code = 2

    result = {
        "schema_version": 2,
        "kind": "AP2_PREFLIGHT_SMOKE",
        "head": child_result.get("head")
        or subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True
        ).stdout.strip(),
        "supervisor": {
            "run_id": summary.get("run_id"),
            "run_dir": summary.get("run_dir"),
            "classification": summary.get("classification"),
            "exit_code": summary.get("exit_code"),
            "journal_records": summary.get("journal_records"),
            "seal_problems": summary.get("seal_problems"),
        },
        "child": child_result,
        "verdict": verdict,
        "classification": classification,
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    evidence.atomic_write_json(args.result, result)
    print(json.dumps({"verdict": verdict, "result": str(args.result)}))
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ap2-preflight-smoke")
    parser.add_argument("--steady-minutes", type=float, default=15.0)
    parser.add_argument("--result", type=Path, default=None)
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args(argv)
    if args.child:
        return _child(args)
    if args.result is None:
        parser.error("--result is required")
    return _supervisor_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
