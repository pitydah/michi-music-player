#!/usr/bin/env python3
"""AP2-F10 numeric DSD→PCM conformance harness.

The harness executes the SAME supervised child runtime used by playback, but
in-process for measurement. It captures the actual F32LE buffers arriving at
the sink and emits only measured facts; it never certifies a profile without a
traceable oracle.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import tempfile
import time
from pathlib import Path
from typing import Any

F32LE = "F32LE"
SILENCE_SAMPLE_COUNT = 44_100


def build_dsf(*, sample_count: int, payload: bytes) -> bytes:
    """Minimal valid DSF container matching the F07 fixture contract."""
    block_size = 4096
    data_chunk_size = 12 + len(payload)
    file_size = 28 + 52 + data_chunk_size
    header = b"DSD " + struct.pack("<QQQ", 28, file_size, 0)
    fmt = (
        b"fmt "
        + struct.pack("<Q", 52)
        + struct.pack("<II", 1, 0)
        + struct.pack("<I", 2)
        + struct.pack("<I", 2)
        + struct.pack("<I", 2_822_400)
        + struct.pack("<I", 8)
        + struct.pack("<Q", sample_count)
        + struct.pack("<I", block_size)
        + b"\x00" * 4
    )
    data = b"data" + struct.pack("<Q", data_chunk_size) + payload
    return header + fmt + data


def _silence_payload(sample_count: int) -> bytes:
    # DSD64: native bytes per channel = sample_count * 2. A 0x69/0x96
    # alternating stream is the conventional low-noise idle pattern.
    frames = sample_count * 2
    return bytes(0x69 if index % 2 == 0 else 0x96 for index in range(frames * 2))


def _metrics(raw: bytes, channels: int, rate: int) -> dict[str, Any]:
    if not raw:
        return {
            "sample_count": 0,
            "nan_inf": 0,
            "peak": None,
            "rms": None,
            "dc": None,
            "channel_balance_db": None,
            "max_step": None,
        }
    usable = len(raw) - (len(raw) % (4 * channels))
    count = usable // 4
    samples = struct.unpack(f"<{count}f", raw[:usable])
    if count == 0 or channels <= 0:
        return {"sample_count": 0}
    frame_count = count // channels
    finite = [value for value in samples if math.isfinite(value)]
    nan_inf = len(samples) - len(finite)
    peak = max((abs(value) for value in finite), default=None)
    rms = (
        math.sqrt(sum(value * value for value in finite) / len(finite))
        if finite
        else None
    )
    dc = sum(finite) / len(finite) if finite else None
    channel_rms = []
    for channel in range(channels):
        values = [value for value in samples[channel::channels] if math.isfinite(value)]
        channel_rms.append(
            math.sqrt(sum(value * value for value in values) / len(values))
            if values
            else None
        )
    balance = None
    if (
        len(channel_rms) >= 2
        and channel_rms[0] is not None
        and channel_rms[1] is not None
        and max(channel_rms[0], channel_rms[1]) > 0
    ):
        balance = 20 * math.log10(
            max(channel_rms[0], 1e-12) / max(channel_rms[1], 1e-12)
        )
    max_step = 0.0
    for channel in range(channels):
        previous = None
        for value in samples[channel::channels]:
            if not math.isfinite(value):
                previous = None
                continue
            if previous is not None:
                max_step = max(max_step, abs(value - previous))
            previous = value
    return {
        "sample_count": frame_count,
        "nan_inf": nan_inf,
        "peak": peak,
        "rms": rms,
        "dc": dc,
        "channel_balance_db": balance,
        "max_step": max_step,
        "rate_hz": rate,
        "channels": channels,
    }


def _request(path: Path, *, target_rate: int, profile: str, execution: str):
    from michi.infrastructure.audio_engines.gstreamer_host_dsd_pcm import (
        DsdPcmHostRuntime,
    )

    payload = {
        "path": str(path),
        "plan_id": f"conformance:{profile}:{target_rate}",
        "execution_id": execution,
        "host_generation": 1,
        "binding_generation": 1,
        "stable_device_id": "lab:fakesink",
        "locator": "lab",
        "source_family": "dsf",
        "source_rate_hz": 2_822_400,
        "source_bits": 2_822_400,
        "bit_order": "LSBF",
        "channels": 2,
        "decoder_factory": "avdec_dsd_lsbf",
        "target_rate_hz": target_rate,
        "output_format": F32LE,
        "quality_profile": profile,
        "resampler_policy": [
            ["quality", 10],
            ["resample-method", "kaiser"],
            ["sinc-filter-mode", "full"],
            ["sinc-filter-interpolation", "none"],
        ]
        if target_rate != 352_800
        else [],
        "sink_factory": "appsink",
    }
    return DsdPcmHostRuntime(), payload


def run(*, fixture: Path | None, target_rate: int, profile: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="michi-dsd2pcm-") as tmp:
        path = fixture
        generated = False
        if path is None:
            path = Path(tmp) / "silence.dsf"
            path.write_bytes(
                build_dsf(
                    sample_count=SILENCE_SAMPLE_COUNT,
                    payload=_silence_payload(SILENCE_SAMPLE_COUNT),
                )
            )
            generated = True
        source = path.read_bytes()
        runtime, payload = _request(
            path, target_rate=target_rate, profile=profile, execution="exec:conformance"
        )
        identity = runtime.prepare(payload)
        runtime.enable_capture(1_000_000)
        expected = {
            "plan_id": identity["plan_id"],
            "execution_id": identity["execution_id"],
            "stable_device_id": identity["stable_device_id"],
            "device": identity["device"],
            "binding_generation": identity["binding_generation"],
            "host_generation": identity["host_generation"],
        }
        runtime.commit(expected)
        runtime.start(expected)
        deadline = time.monotonic() + 15.0
        while time.monotonic() < deadline:
            runtime.query_identity()
            if runtime.query_identity().get("eos"):
                break
            time.sleep(0.02)
        raw = runtime.captured_bytes()
        observed = runtime.query_identity()
        release = runtime.stop(expected)
        runtime.close()
        metrics = _metrics(raw, 2, target_rate)
        return {
            "schema_version": 1,
            "fixture": {
                "path": str(path),
                "sha256": hashlib.sha256(source).hexdigest(),
                "generated": generated,
                "bit_order": "LSBF",
            },
            "backend": {"decoder": "avdec_dsd_lsbf", "output_format": F32LE},
            "profile": profile,
            "target_rate_hz": target_rate,
            "caps_negotiated": observed.get("output_caps") or "",
            "decoder_caps": observed.get("decoder_caps") or "",
            "processing_graph_revision": None,
            "sample_count": metrics.get("sample_count", 0),
            "output_sha256": hashlib.sha256(raw).hexdigest(),
            "metrics": metrics,
            "metric_dispositions": {
                "signal_present": (
                    "PASS" if metrics.get("sample_count", 0) > 0 else "FAIL"
                ),
                "numeric_finiteness": (
                    "PASS" if metrics.get("nan_inf") == 0 else "FAIL"
                ),
                "oracle": "NOT_RUN",
            },
            "status": "PARTIAL",
            "environment": {"python": "3.11", "sink": "appsink"},
            "cleanup_confirmed": bool(release.get("release")),
            "release": release.get("release"),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--target-rate", type=int, default=88_200)
    parser.add_argument("--profile", default="FAST")
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    result = run(
        fixture=args.fixture, target_rate=args.target_rate, profile=args.profile
    )
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.json is not None:
        args.json.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result["sample_count"] > 0 and result["cleanup_confirmed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
