#!/usr/bin/env python3
"""A49 read-only Michi process sampler; never enters DSP/audio callbacks.

This measures OS process CPU/RSS only. A complete audio/UI certification also
requires authentic XRUN receipts, Qt frame traces, audio pipeline and DAC gates.
No baseline threshold is fabricated and no missing dimension becomes zero.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from pathlib import Path

SCENARIOS = (
    "pcm_direct",
    "managed_dsp",
    "managed_dsp_ai",
    "dsd_to_pcm",
    "native_dsd",
    "dop",
    "transition",
)


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, min(len(ordered) - 1, math.ceil(len(ordered) * q) - 1))]


def read_process(pid: int) -> tuple[int, int]:
    """Linux process CPU ticks and VmRSS KiB; guarded against comm spaces."""
    if type(pid) is not int or pid < 1:
        raise ValueError("positive process id required")
    stat = (Path("/proc") / str(pid) / "stat").read_text()
    after = stat.rfind(")")
    if after < 0:
        raise ValueError("malformed process stat")
    tail = stat[after + 2 :].split()
    ticks = int(tail[11]) + int(tail[12])  # utime + stime
    status = (Path("/proc") / str(pid) / "status").read_text()
    rss = next(
        (
            int(line.split()[1])
            for line in status.splitlines()
            if line.startswith("VmRSS:")
        ),
        None,
    )
    if rss is None:
        raise ValueError("VmRSS unavailable")
    return ticks, rss


def sample(pid: int, *, duration_s: float, interval_s: float) -> dict[str, object]:
    if not 0.05 <= interval_s <= 2 or not 0.1 <= duration_s <= 3600:
        raise ValueError("bounded sample interval and duration required")
    hz = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
    previous_t = time.perf_counter()
    previous_ticks, _ = read_process(pid)
    cpu, rss = [], []
    deadline = previous_t + duration_s
    while time.perf_counter() < deadline:
        time.sleep(interval_s)
        now = time.perf_counter()
        ticks, mem = read_process(pid)
        dt = now - previous_t
        if dt > 0:
            cpu.append(100 * (ticks - previous_ticks) / hz / dt)
            rss.append(mem / 1024.0)
        previous_t, previous_ticks = now, ticks
    return {
        "process_cpu_pct": {
            "state": "MEASURED_PROCESS_ONLY",
            "count": len(cpu),
            "p50": percentile(cpu, 0.50),
            "p95": percentile(cpu, 0.95),
            "p99": percentile(cpu, 0.99),
        },
        "process_rss_mib": {
            "state": "MEASURED_PROCESS_ONLY",
            "count": len(rss),
            "p50": percentile(rss, 0.50),
            "p95": percentile(rss, 0.95),
            "p99": percentile(rss, 0.99),
        },
    }


def run(argv: list[str] | None = None) -> dict[str, object]:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pid", type=int)
    ap.add_argument("--scenario", choices=SCENARIOS, required=True)
    ap.add_argument("--duration", type=float, default=30)
    ap.add_argument("--interval", type=float, default=0.1)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    result: dict[str, object] = {
        "schema": "michi.f11.a49.process_benchmark.v1",
        "scenario": args.scenario,
        "scope": "EXTERNAL_PROCESS_ONLY_NOT_AUDIO_RT",
        "pid": args.pid,
        "scenario_attestation": "USER_SELECTED_LABEL_NOT_BACKEND_READBACK",
        "qt_frame_p99_ms": {
            "state": "NOT_RUN",
            "reason": "requires real Qt frame trace",
        },
        "audio_callback_p99_ms": {
            "state": "NOT_RUN",
            "reason": "requires RT owner instrumentation outside this sampler",
        },
        "xrun_count": {
            "state": "NOT_RUN",
            "reason": "requires bound ALSA or backend XRUN receipt",
        },
        "dsp_readback": {"state": "NOT_RUN", "reason": "requires F05 owner receipt"},
        "ai_load_readback": {
            "state": "NOT_RUN",
            "reason": "requires Michi AI owner receipt",
        },
        "dac_boundary": {
            "state": "NOT_RUN",
            "reason": "requires qualified physical receipt",
        },
    }
    try:
        if args.pid is None:
            raise ValueError("no Michi Music Player process PID supplied")
        result.update(
            sample(args.pid, duration_s=args.duration, interval_s=args.interval)
        )
        result["overall"] = "PARTIAL_PROCESS_ONLY"
    except (OSError, ValueError) as e:
        result["overall"] = "NOT_RUN"
        result["blocker"] = str(e).split(":")[0][:120]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


if __name__ == "__main__":
    r = run()
    print(json.dumps({"overall": r["overall"], "scope": r["scope"]}))
    raise SystemExit(0 if r["overall"] == "PARTIAL_PROCESS_ONLY" else 2)
