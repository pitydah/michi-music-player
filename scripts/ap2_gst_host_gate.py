#!/usr/bin/env python
"""AP2 GST OUTPUT HOST — real short reproducer / containment gate.

Runs the productive GStreamer lifecycle (load/stop churn) through the REAL
hosted transport: every pipeline lives in the supervised child process. The
parent only owns semantic authority and bounded deadlines.

Acceptable outcomes (BOTH are containment success):
  A) no wedge occurs during the declared envelope;
  B) the host wedges/dies; the parent detects it within its own deadline,
     kills and reaps the child, converges, and can start a fresh host.

Deterministic fault injections (real process, real host):
  --inject-hang-at N   SIGSTOP the host before cycle N (a truly stuck host
                       that never answers; the parent must contain it)
  --inject-kill-at N   SIGKILL the host before cycle N (crash injection)

Run under external supervision:
  python scripts/m11_4_physical_supervisor.py run \
      --campaign-id gst-output-host-gate --experiment host-containment \
      --watchdog-seconds 180 -- \
      python scripts/ap2_gst_host_gate.py --seconds 90 --rate 25 ...

Progress is published to $M11_4_RUN_DIR/progress.json every cycle so the
external watchdog can distinguish a live child from a vanished one.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

from michi.application.ports import (  # noqa: E402
    AudioLoadError,
    AudioTransportCommandError,
)
from michi.infrastructure.audio_engines.gstreamer_host_client import (  # noqa: E402
    SupervisorState,
)

_CORPUS = REPO / "evidence/dac-v35-110/2026-09-25-smsl-152a85dd-operator-run/fixtures"
_R25 = REPO / "evidence/dac-v35-pcm-closure/2026-09-30-smsl-152a85dd/fixtures"
DEFAULT_FIXTURES = (
    _CORPUS / "pcm16_44100.wav",
    _CORPUS / "pcm16_48000.wav",
    _CORPUS / "pcm24_96000.wav",
    _R25 / "r25_marker_44100.wav",
)

STATUS_OK = 0
STATUS_CONTAINMENT_FAILED = 2
STATUS_SETUP_FAILED = 3


class Progress:
    def __init__(self, run_dir: Path | None) -> None:
        self._path = None if run_dir is None else run_dir / "progress.json"
        self._lock = threading.Lock()
        self._payload: dict = {}

    def update(self, **fields) -> None:
        with self._lock:
            self._payload.update(fields)
            self._payload["monotonic_ns"] = time.monotonic_ns()
            if self._path is not None:
                tmp = self._path.with_suffix(".tmp")
                tmp.write_text(
                    json.dumps(self._payload, sort_keys=True), encoding="utf-8"
                )
                tmp.replace(self._path)


class Heartbeat:
    """Parent-thread responsiveness probe (10 ms tick)."""

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._last = time.monotonic()
        self.max_stall_ms = 0.0
        self.ticks = 0

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2.0)

    def _run(self) -> None:
        while not self._stop.is_set():
            now = time.monotonic()
            stall = (now - self._last) * 1000.0
            self.max_stall_ms = max(self.max_stall_ms, stall)
            self.ticks += 1
            self._last = now
            time.sleep(0.01)


def _build_transport(load_deadline_s: float):
    from michi.infrastructure.audio_engines.gstreamer_host_client import (
        GStreamerHostSupervisor,
    )
    from michi.infrastructure.audio_engines.gstreamer_host_port import (
        GStreamerHostedAudioPort,
    )
    from michi.infrastructure.audio_output.direct_output_executor import (
        GStreamerDirectOutputExecutor,
    )

    supervisor = GStreamerHostSupervisor(
        start_timeout_s=45.0,
        command_timeout_s=max(5.0, load_deadline_s),
        terminate_grace_s=4.0,
        term_grace_s=2.0,
        kill_grace_s=3.0,
    )
    executor = GStreamerDirectOutputExecutor()
    port = GStreamerHostedAudioPort(
        supervisor,
        command_deadline_s=max(5.0, load_deadline_s),
        load_deadline_s=max(5.0, load_deadline_s),
        direct_executor=executor,
    )
    executor.bind_port_provider(lambda: port)
    return supervisor, port


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=90.0)
    parser.add_argument("--rate", type=float, default=25.0, help="target cycles/s")
    parser.add_argument("--load-deadline", type=float, default=6.0)
    parser.add_argument("--inject-hang-at", type=int, default=0)
    parser.add_argument("--inject-kill-at", type=int, default=0)
    parser.add_argument("--receipt", type=Path, default=None)
    parser.add_argument("--fixtures", type=Path, nargs="*", default=None)
    args = parser.parse_args(argv)

    run_dir = (
        Path(os.environ["M11_4_RUN_DIR"]) if "M11_4_RUN_DIR" in os.environ else None
    )
    receipt_path = args.receipt or (
        (run_dir / "gst_host_gate_receipt.json")
        if run_dir
        else Path("/tmp/opencode/gst_host_gate_receipt.json")
    )
    progress = Progress(run_dir)
    files = [path for path in (args.fixtures or DEFAULT_FIXTURES) if path.is_file()]
    if not files:
        print("SETUP_FAILED: no fixtures available", file=sys.stderr)
        return STATUS_SETUP_FAILED

    heartbeat = Heartbeat()
    heartbeat.start()
    containments: list[dict] = []
    host_pids: list[int] = []
    media_rejections = 0
    cycles = 0
    started = time.monotonic()
    deadline = started + max(1.0, args.seconds)
    min_period = 1.0 / max(0.1, args.rate)

    supervisor = None
    port = None
    closed_receipts: list[dict] = []
    setup_error = None
    try:
        supervisor, port = _build_transport(args.load_deadline)
        port.activate()
        host_pids.append(supervisor.pid or -1)
        progress.update(
            cycle=0, host_generation=supervisor.host_generation, phase="READY"
        )
        print(
            f"host ready pid={supervisor.pid} generation={supervisor.host_generation}"
        )
    except Exception as exc:  # noqa: BLE001 - setup boundary
        setup_error = f"{type(exc).__name__}: {exc}"
        print(f"SETUP_FAILED: {setup_error}", file=sys.stderr)
        if supervisor is not None:
            supervisor.close()
        heartbeat.stop()
        receipt = {
            "verdict": "SETUP_FAILED",
            "setup_error": setup_error,
        }
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        return STATUS_SETUP_FAILED

    try:
        while time.monotonic() < deadline:
            cycles += 1
            cycle_started = time.monotonic()
            # ── deterministic injections on the REAL host ─────────────
            if args.inject_hang_at and cycles == args.inject_hang_at:
                pid = supervisor.pid
                if pid:
                    os.kill(pid, signal.SIGSTOP)
                    containments.append(
                        {"cycle": cycles, "injection": "SIGSTOP", "pid": pid}
                    )
                    print(f"[{cycles}] injected SIGSTOP to host pid {pid}")
            if args.inject_kill_at and cycles == args.inject_kill_at:
                pid = supervisor.pid
                if pid:
                    os.kill(pid, signal.SIGKILL)
                    containments.append(
                        {"cycle": cycles, "injection": "SIGKILL", "pid": pid}
                    )
                    print(f"[{cycles}] injected SIGKILL to host pid {pid}")

            try:
                port.load(files[cycles % len(files)])
                port.stop()
                port.dispatch_pending()  # consume owner events (no Qt loop here)
                progress.update(
                    cycle=cycles,
                    phase="churn",
                    host_generation=supervisor.host_generation,
                )
            except Exception as exc:  # noqa: BLE001 - containment boundary
                host_healthy = (
                    supervisor is not None
                    and supervisor.pid_alive()
                    and supervisor.state is not SupervisorState.FAILED
                )
                if (
                    isinstance(exc, (AudioLoadError, AudioTransportCommandError))
                    and host_healthy
                ):
                    # Engine-level rejection with a LIVE host is not
                    # containment: it is a media/ARM outcome. Counted, never
                    # restarted blindly.
                    media_rejections += 1
                    if media_rejections <= 5:
                        print(f"[{cycles}] media rejection (host alive): {exc}")
                    continue
                contained_at = time.monotonic()
                kind = type(exc).__name__
                detail = str(exc)[:300]
                print(f"[{cycles}] contained host failure: {kind}: {detail}")
                # Bounded close/reap of the failed incarnation.
                close_kind = None
                try:
                    port.close()
                    close_kind = port.termination_kind
                except Exception as close_exc:  # noqa: BLE001
                    close_kind = f"close_error: {close_exc}"
                reaped = not supervisor.pid_alive()
                containments.append(
                    {
                        "cycle": cycles,
                        "injection": containments[-1]["injection"]
                        if containments and containments[-1].get("cycle") == cycles
                        else None,
                        "error": kind,
                        "detail": detail,
                        "deadline_seconds": args.load_deadline,
                        "contained_in_seconds": round(contained_at - cycle_started, 3),
                        "termination_kind": close_kind,
                        "reaped": reaped,
                    }
                )
                if not reaped:
                    print("FATAL: failed host was not reaped")
                    break
                # Explicit recovery: a fresh supervised host (never autoplay).
                supervisor, port = _build_transport(args.load_deadline)
                port.activate()
                host_pids.append(supervisor.pid or -1)
                containments[-1]["restart_ok"] = True
                containments[-1]["new_generation"] = supervisor.host_generation
                containments[-1]["new_pid"] = supervisor.pid
                print(f"[{cycles}] fresh host pid={supervisor.pid} after containment")
            elapsed = time.monotonic() - cycle_started
            if elapsed < min_period:
                time.sleep(min_period - elapsed)
    finally:
        heartbeat.stop()
        final_kind = None
        if port is not None:
            try:
                port.close()
                final_kind = port.termination_kind
            except Exception as exc:  # noqa: BLE001 - final boundary
                final_kind = f"close_error: {exc}"
        closed_receipts.append({"final_termination_kind": final_kind})
        if supervisor is not None:
            supervisor.close()

    orphans = []
    for pid in host_pids:
        if pid <= 0:
            continue
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            continue
        except PermissionError:
            orphans.append(pid)
            continue
        orphans.append(pid)
    if supervisor is not None and supervisor.pid and supervisor.pid_alive():
        orphans.append(supervisor.pid)

    duration = time.monotonic() - started
    receipt = {
        "schema_version": 1,
        "reproducer": "ap2_gst_host_gate",
        "seconds_requested": args.seconds,
        "seconds_actual": round(duration, 2),
        "target_rate_hz": args.rate,
        "cycles": cycles,
        "cycles_per_second": round(cycles / duration, 2) if duration else None,
        "host_pids": [pid for pid in host_pids if pid > 0],
        "host_incarnations": len(host_pids),
        "containments": containments,
        "containment_count": len(containments),
        "media_rejections": media_rejections,
        "parent_heartbeat": {
            "ticks": heartbeat.ticks,
            "max_stall_ms": round(heartbeat.max_stall_ms, 2),
            "responsive": heartbeat.max_stall_ms < 2000.0,
        },
        "orphans": orphans,
        "final": closed_receipts,
        "verdict": None,
    }
    ok = (
        receipt["parent_heartbeat"]["responsive"]
        and not orphans
        and all(item.get("reaped", True) for item in containments if "error" in item)
    )
    receipt["verdict"] = "PASS_CONTAINED" if ok else "FAIL_CONTAINMENT"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return STATUS_OK if ok else STATUS_CONTAINMENT_FAILED


if __name__ == "__main__":
    sys.exit(main())
