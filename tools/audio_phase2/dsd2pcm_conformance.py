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
DSD_BIT_RATE_HZ = 2_822_400
SILENCE_SAMPLE_COUNT = 44_100
CORPUS_SAMPLE_COUNT = 17_640
#: DSD64 conformance corpus (§274.4/§275): (name, analytic tone frequency).
DSD64_CORPUS: tuple[tuple[str, int], ...] = (
    ("silence", 0),
    ("tone_1khz", 1_000),
    ("tone_10khz", 10_000),
    ("tone_20khz", 20_000),
)


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


def _tone_bits(*, frequency_hz: int, bit_count: int, amplitude: float = 0.5) -> bytes:
    """Second-order sigma-delta 1-bit stream for one analytic sine.

    The corpus is intentionally analytic: the independent reference is the
    requested sine amplitude, not a capture produced by the decoder itself.
    """
    first = 0.0
    second = 0.0
    feedback = 0.0
    out = bytearray()
    byte = 0
    for index in range(bit_count):
        sample = amplitude * math.sin(
            2.0 * math.pi * frequency_hz * index / DSD_BIT_RATE_HZ
        )
        first += sample - feedback
        second += first - feedback
        bit = 1 if second >= 0.0 else 0
        feedback = 1.0 if bit else -1.0
        # DSF stores DSD bytes least-significant-bit first.
        byte |= bit << (index % 8)
        if index % 8 == 7:
            out.append(byte)
            byte = 0
    if bit_count % 8:
        out.append(byte)
    return bytes(out)


def _dsf_block_payload(mono: bytes, *, block_size: int = 4096) -> bytes:
    """DSF stores channel data as fixed 4096-byte blocks (ch0, ch1, ...)."""
    pad = (-len(mono)) % block_size
    mono = mono + b"\x00" * pad
    payload = bytearray()
    for offset in range(0, len(mono), block_size):
        block = mono[offset : offset + block_size]
        payload.extend(block)
        payload.extend(block)
    return bytes(payload)


def _silence_mono(byte_count: int) -> bytes:
    return bytes(0x69 if index % 2 == 0 else 0x96 for index in range(byte_count))


def _tone_payload(*, sample_count: int, frequency_hz: int) -> bytes:
    """One DSF64 payload with a reproducibly analytic mono stream."""
    if frequency_hz == 0:
        mono = _silence_mono(sample_count)
    else:
        mono = _tone_bits(
            frequency_hz=frequency_hz, bit_count=sample_count * 8
        )
    return _dsf_block_payload(mono)


def _tone_metrics(
    raw: bytes, *, channels: int, rate: int, expected_hz: int
) -> dict[str, Any]:
    import numpy as np

    usable = len(raw) - (len(raw) % (4 * channels))
    frames = np.frombuffer(raw[:usable], dtype="<f4").reshape(-1, channels)
    left = frames[:, 0].astype(np.float64)
    if left.size == 0:
        return {"sample_count": 0}
    nan_inf = int(np.count_nonzero(~np.isfinite(frames)))
    finite = np.nan_to_num(left, nan=0.0, posinf=0.0, neginf=0.0)
    window = np.hanning(finite.size)
    coherent = window.sum() / 2.0
    spectrum = np.abs(np.fft.rfft(finite * window)) / coherent
    freqs = np.fft.rfftfreq(finite.size, 1.0 / rate)
    if expected_hz:
        near = (freqs >= expected_hz - 200.0) & (freqs <= expected_hz + 200.0)
        index = int(np.argmax(np.where(near, spectrum, -1.0)))
    else:
        index = int(np.argmax(spectrum[1:]) + 1)
    measured_hz = float(freqs[index])
    measured_amp = float(spectrum[index])
    expected_amp = 0.5
    gain_error_db = 20.0 * math.log10(max(measured_amp, 1e-12) / expected_amp)
    exclusion = (freqs >= 20_000.0) & (freqs <= 40_000.0)
    exclusion &= ~((freqs >= expected_hz - 500.0) & (freqs <= expected_hz + 500.0))
    stopband = float(
        math.sqrt(float(np.sum(spectrum[exclusion] ** 2))) / max(measured_amp, 1e-12)
    )
    channel_rms = [
        float(np.sqrt(np.mean(frames[:, channel].astype(np.float64) ** 2)))
        for channel in range(channels)
    ]
    mismatch = 0.0
    if len(channel_rms) >= 2 and min(channel_rms) > 0:
        mismatch = 20.0 * math.log10(max(channel_rms) / min(channel_rms))
    return {
        "sample_count": int(finite.size),
        "nan_inf": nan_inf,
        "dc": float(np.mean(finite)),
        "dc_gain_error_db": abs(float(np.mean(finite))),
        "peak": float(np.max(np.abs(finite))) if finite.size else None,
        "clipping_samples": int(np.count_nonzero(np.abs(finite) >= 0.999)),
        "tone_frequency_hz": measured_hz,
        "tone_frequency_error_hz": abs(measured_hz - expected_hz)
        if expected_hz
        else 0.0,
        "tone_gain_error_db": gain_error_db,
        "stopband_rejection_db": (
            -20.0 * math.log10(max(stopband, 1e-12)) if expected_hz else None
        ),
        "inter_channel_gain_mismatch_db": abs(mismatch),
        "rate_hz": rate,
        "channels": channels,
    }


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


def run(
    *,
    fixture: Path | None,
    target_rate: int,
    profile: str,
    expected_frequency_hz: int = 0,
    fixture_name: str | None = None,
) -> dict[str, Any]:
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
        deadline = time.monotonic() + 8.0
        eos_observed = False
        last_length = -1
        stable_polls = 0
        while time.monotonic() < deadline:
            if runtime.query_identity().get("eos"):
                eos_observed = True
                break
            length = len(runtime.captured_bytes())
            if length == last_length:
                stable_polls += 1
                if stable_polls >= 5 and length > 0:
                    break
            else:
                stable_polls = 0
                last_length = length
            time.sleep(0.02)
        raw = runtime.captured_bytes()
        observed = runtime.query_identity()
        release = runtime.stop(expected)
        runtime.close()
        metrics = _metrics(raw, 2, target_rate)
        tone = (
            _tone_metrics(
                raw,
                channels=2,
                rate=target_rate,
                expected_hz=expected_frequency_hz,
            )
            if expected_frequency_hz
            else {}
        )
        numeric_checks = {}
        if expected_frequency_hz:
            numeric_checks = {
                "nan_inf_zero": "PASS" if tone.get("nan_inf") == 0 else "FAIL",
                "dc_gain_error_le_0_05_db": (
                    "PASS"
                    if tone.get("dc_gain_error_db", 1.0) <= 0.05
                    else "FAIL"
                ),
                "magnitude_error_le_0_10_db": (
                    "PASS"
                    if abs(tone.get("tone_gain_error_db", 99.0)) <= 0.10
                    else "FAIL"
                ),
                "inter_channel_gain_le_0_01_db": (
                    "PASS"
                    if tone.get("inter_channel_gain_mismatch_db", 1.0) <= 0.01
                    else "FAIL"
                ),
                "no_unexpected_clipping": (
                    "PASS" if tone.get("clipping_samples") == 0 else "FAIL"
                ),
                # 6615-frame captures at 88.2 kHz have ~13.3 Hz FFT bins.
                "frequency_error_le_20_hz": (
                    "PASS"
                    if tone.get("tone_frequency_error_hz", 999.0) <= 20.0
                    else "FAIL"
                ),
            }
        return {
            "schema_version": 1,
            "fixture": {
                "path": str(path),
                "name": fixture_name,
                "sha256": hashlib.sha256(source).hexdigest(),
                "generated": generated,
                "bit_order": "LSBF",
                "analytic_frequency_hz": expected_frequency_hz,
                "oracle": "analytic_sine_amplitude_0.5",
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
            "tone_metrics": tone,
            "numeric_checks": numeric_checks,
            "informational_metrics": {
                "stopband_rejection_db": tone.get("stopband_rejection_db"),
                "disposition": (
                    "INFORMATIONAL — not the §274.4 resampler stopband criterion"
                ),
            },
            "metric_dispositions": {
                "signal_present": (
                    "PASS" if metrics.get("sample_count", 0) > 0 else "FAIL"
                ),
                "numeric_finiteness": (
                    "PASS" if metrics.get("nan_inf") == 0 else "FAIL"
                ),
                "eos": "PASS" if eos_observed else "FAIL",
                "oracle": (
                    "PASS"
                    if numeric_checks
                    and all(value == "PASS" for value in numeric_checks.values())
                    else ("NOT_RUN" if not numeric_checks else "FAIL")
                ),
            },
            "status": "PARTIAL",
            "environment": {"python": "3.11", "sink": "appsink"},
            "cleanup_confirmed": bool(release.get("release")),
            "eos_observed": eos_observed,
            "release": release.get("release"),
        }


def run_corpus(*, target_rate: int, profile: str) -> dict[str, Any]:
    vectors = []
    with tempfile.TemporaryDirectory(prefix="michi-dsd2pcm-corpus-") as tmp:
        for name, frequency in DSD64_CORPUS:
            path = Path(tmp) / f"{name}.dsf"
            path.write_bytes(
                build_dsf(
                    sample_count=CORPUS_SAMPLE_COUNT,
                    payload=_tone_payload(
                        sample_count=CORPUS_SAMPLE_COUNT,
                        frequency_hz=frequency,
                    ),
                )
            )
            vectors.append(
                run(
                    fixture=path,
                    target_rate=target_rate,
                    profile=profile,
                    expected_frequency_hz=frequency,
                    fixture_name=name,
                )
            )
    return {
        "schema_version": 1,
        "phase": "AP2-F10",
        "corpus": "dsd64_v1",
        "target_rate_hz": target_rate,
        "profile": profile,
        "vectors": vectors,
        "status": (
            "PASS"
            if all(
                vector["sample_count"] > 0
                and vector["cleanup_confirmed"]
                and vector["eos_observed"]
                and (
                    vector["metric_dispositions"]["oracle"] == "PASS"
                    if vector["fixture"]["analytic_frequency_hz"]
                    else True
                )
                for vector in vectors
            )
            else "FAIL"
        ),
        "environment": {"python": "3.11", "sink": "appsink"},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--target-rate", type=int, default=88_200)
    parser.add_argument("--profile", default="FAST")
    parser.add_argument("--json", type=Path)
    parser.add_argument("--corpus", action="store_true")
    args = parser.parse_args()
    result = (
        run_corpus(target_rate=args.target_rate, profile=args.profile)
        if args.corpus
        else run(
            fixture=args.fixture,
            target_rate=args.target_rate,
            profile=args.profile,
        )
    )
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.json is not None:
        args.json.write_text(text + "\n", encoding="utf-8")
    print(text)
    if args.corpus:
        return 0 if result["status"] == "PASS" else 1
    complete = (
        result["sample_count"] > 0
        and result["cleanup_confirmed"]
        and result["eos_observed"]
    )
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
