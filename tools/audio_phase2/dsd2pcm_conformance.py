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
import shutil
import struct
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

F32LE = "F32LE"
DSD_BIT_RATE_HZ = 2_822_400
SILENCE_SAMPLE_COUNT = 44_100
CORPUS_SAMPLE_COUNT = 17_640
#: §274.4/§275 corpus: (name, analytic tone, source bytes/channel, stopband).
CORPUS_VECTORS: tuple[tuple[str, int, int, int | None], ...] = (
    ("silence", 0, SILENCE_SAMPLE_COUNT, None),
    # Low frequencies need more than one cycle for a stable projection.
    ("tone_20hz", 20, 70_560, None),
    ("tone_100hz", 100, 35_280, None),
    ("tone_1khz", 1_000, CORPUS_SAMPLE_COUNT, None),
    ("tone_10khz", 10_000, CORPUS_SAMPLE_COUNT, None),
    ("tone_20khz", 20_000, CORPUS_SAMPLE_COUNT, None),
    ("tone_30khz", 30_000, CORPUS_SAMPLE_COUNT, None),
    # 80 kHz folds to 8.2 kHz at 88.2 kHz when the resampler fails to reject
    # it. A longer capture separates the coherent alias from the DSD noise.
    ("stopband_80khz", 80_000, 70_560, 80_000),
)
DSD64_CORPUS: tuple[tuple[str, int], ...] = tuple(
    (name, frequency) for name, frequency, _samples, _stopband in CORPUS_VECTORS
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
        mono = _tone_bits(frequency_hz=frequency_hz, bit_count=sample_count * 8)
    return _dsf_block_payload(mono)


def _dsf_blob(*, sample_count: int, frequency_hz: int) -> bytes:
    """Build a reproducible DSF for one corpus vector.

    The DSF header stores ``sample_count`` in DSD bits per channel. The data
    chunk is padded to whole 4096-byte blocks, and the demuxer uses the
    declared bit count to separate real audio from that padding. Declaring
    bytes (or the padded size) makes the decoder treat padding as audio and
    stop before EOS.
    """
    payload = _tone_payload(sample_count=sample_count, frequency_hz=frequency_hz)
    # DSF stores the sample count in DSD bits per channel; the demuxer divides
    # it by 8 to obtain the real byte count used to separate audio from the
    # block padding. The payload is already padded to whole 4096-byte blocks.
    return build_dsf(sample_count=sample_count * 8, payload=payload)


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
    # The corpus tones are not FFT-bin centred at 88.2 kHz. Reading the peak
    # bin of a Hann-windowed spectrum therefore under-reads their amplitude by
    # the window scalloping loss (up to ~0.8 dB at 20 kHz). Project the
    # captured signal onto the known analytic frequency instead; that estimate
    # is unbiased for any fractional bin offset.
    offsets = np.arange(finite.size)

    def _amplitude(signal: Any) -> float:
        if not expected_hz or signal.size == 0:
            return 0.0
        projection = (
            np.sum(
                signal * window * np.exp(-2j * math.pi * expected_hz * offsets / rate)
            )
            / window.sum()
        )
        return float(2.0 * abs(projection))

    measured_amp = _amplitude(finite)
    channel_amplitudes = [
        _amplitude(
            np.nan_to_num(
                frames[:, channel].astype(np.float64),
                nan=0.0,
                posinf=0.0,
                neginf=0.0,
            )
        )
        for channel in range(channels)
    ]
    mismatch = 0.0
    if (
        len(channel_amplitudes) >= 2
        and min(channel_amplitudes) > 1e-12
        and max(channel_amplitudes) > 0
    ):
        mismatch = 20.0 * math.log10(max(channel_amplitudes) / min(channel_amplitudes))

    def _channel_lag(left_signal, right_signal, max_lag: int = 16) -> int:
        count = min(left_signal.size, right_signal.size)
        if count <= max_lag:
            return 0
        left_signal = left_signal[:count]
        right_signal = right_signal[:count]
        best_lag = 0
        best_score = -1.0
        for lag in range(-max_lag, max_lag + 1):
            if lag >= 0:
                left_part = left_signal[: count - lag]
                right_part = right_signal[lag:]
            else:
                left_part = left_signal[-lag:]
                right_part = right_signal[: count + lag]
            denominator = math.sqrt(
                float(np.dot(left_part, left_part))
                * float(np.dot(right_part, right_part))
            )
            if denominator <= 1e-12:
                continue
            score = abs(float(np.dot(left_part, right_part))) / denominator
            if score > best_score:
                best_score = score
                best_lag = lag
        return best_lag

    latency_samples = (
        _channel_lag(
            np.nan_to_num(
                frames[:, 0].astype(np.float64), nan=0.0, posinf=0.0, neginf=0.0
            ),
            np.nan_to_num(
                frames[:, 1].astype(np.float64), nan=0.0, posinf=0.0, neginf=0.0
            ),
        )
        if channels >= 2
        else 0
    )
    expected_amp = 0.5
    gain_error_db = 20.0 * math.log10(max(measured_amp, 1e-12) / expected_amp)
    exclusion = (freqs >= 20_000.0) & (freqs <= 40_000.0)
    exclusion &= ~((freqs >= expected_hz - 500.0) & (freqs <= expected_hz + 500.0))
    stopband = float(
        math.sqrt(float(np.sum(spectrum[exclusion] ** 2))) / max(measured_amp, 1e-12)
    )
    return {
        "sample_count": int(finite.size),
        "nan_inf": nan_inf,
        "dc_offset": float(np.mean(finite)),
        # A linear residual offset is not a dB gain error. The normative DC
        # gain is NOT_MEASURED by this corpus: a dedicated DC stimulus and a
        # versioned reference are required to claim it.
        "dc_gain_error_db": None,
        "dc_gain_status": "NOT_MEASURED",
        "dc_gain_reason": (
            "no DC stimulus; residual offset is linear, not a gain error"
        ),
        "peak": float(np.max(np.abs(finite))) if finite.size else None,
        "clipping_samples": int(
            np.count_nonzero(
                np.isfinite(frames) & (np.abs(np.nan_to_num(frames)) >= 0.999)
            )
        ),
        "tone_frequency_hz": measured_hz,
        "tone_frequency_error_hz": abs(measured_hz - expected_hz)
        if expected_hz
        else 0.0,
        "tone_amplitude": measured_amp,
        "channel_amplitudes": channel_amplitudes,
        "tone_gain_error_db": gain_error_db,
        "stopband_rejection_db": (
            -20.0 * math.log10(max(stopband, 1e-12)) if expected_hz else None
        ),
        "inter_channel_gain_mismatch_db": abs(mismatch),
        "inter_channel_latency_samples": latency_samples,
        "rate_hz": rate,
        "channels": channels,
    }


def _ffmpeg_version(ffmpeg: str) -> str:
    try:
        completed = subprocess.run(
            [ffmpeg, "-version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return (completed.stdout or "").splitlines()[0] if completed.stdout else ""


def _reference_capture(
    path: Path, *, channels: int, rate: int, expected_hz: int
) -> dict[str, Any]:
    """Decode the same DSF with an independent decoder and measure its tone.

    §274.4 bounds the magnitude error against a versioned reference, not
    against the pre-modulation analytic amplitude: a sigma-delta modulator has
    its own passband droop. FFmpeg is an independent DSF decoder; its capture
    is recorded with a SHA256 so the comparison is traceable.
    """
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return {"status": "NOT_RUN", "reason": "ffmpeg not found"}
    with tempfile.TemporaryDirectory(prefix="michi-dsd2pcm-reference-") as tmp:
        target = Path(tmp) / "reference.f32"
        try:
            completed = subprocess.run(
                [
                    ffmpeg,
                    "-v",
                    "error",
                    "-y",
                    "-i",
                    str(path),
                    "-f",
                    "f32le",
                    "-acodec",
                    "pcm_f32le",
                    "-ar",
                    str(rate),
                    str(target),
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return {"status": "NOT_RUN", "reason": f"ffmpeg failed: {exc}"}
        if completed.returncode != 0 or not target.exists():
            detail = (completed.stderr or "no reference output").strip()
            return {"status": "NOT_RUN", "reason": detail[:500]}
        raw = target.read_bytes()
    metrics = _tone_metrics(raw, channels=channels, rate=rate, expected_hz=expected_hz)
    if not metrics.get("sample_count"):
        return {"status": "NOT_RUN", "reason": "empty reference capture"}
    return {
        "status": "PASS",
        "tool": "ffmpeg",
        "version": _ffmpeg_version(ffmpeg),
        "target_rate_hz": rate,
        "sample_count": metrics["sample_count"],
        "sha256": hashlib.sha256(raw).hexdigest(),
        "amplitude": metrics["tone_amplitude"],
        "gain_db": metrics["tone_gain_error_db"],
    }


def _checks_disposition(checks: dict[str, str]) -> str:
    values = tuple(checks.values())
    if any(value == "FAIL" for value in values):
        return "FAIL"
    if any(value == "NOT_RUN" for value in values):
        return "NOT_RUN"
    return "PASS"


def _vector_status(
    *,
    sample_count: int,
    cleanup_confirmed: bool,
    eos_observed: bool,
    numeric_checks: dict[str, str],
) -> str:
    if sample_count <= 0 or not cleanup_confirmed:
        return "FAIL"
    if not eos_observed:
        return "PARTIAL"
    disposition = _checks_disposition(numeric_checks) if numeric_checks else "PASS"
    if disposition == "FAIL":
        return "FAIL"
    if disposition == "NOT_RUN":
        return "PARTIAL"
    return "PASS"


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
        # fakesink keeps consuming to EOS; appsink (even with drop=true)
        # can stall the streaming thread. Capture comes from the pad probe.
        "sink_factory": "fakesink",
        "capture_max_frames": 1_000_000,
    }
    return DsdPcmHostRuntime(), payload


def run(
    *,
    fixture: Path | None,
    target_rate: int,
    profile: str,
    expected_frequency_hz: int = 0,
    fixture_name: str | None = None,
    stopband_hz: int | None = None,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="michi-dsd2pcm-") as tmp:
        path = fixture
        generated = False
        if path is None:
            path = Path(tmp) / "silence.dsf"
            path.write_bytes(
                _dsf_blob(
                    sample_count=SILENCE_SAMPLE_COUNT,
                    frequency_hz=0,
                )
            )
            generated = True
        source = path.read_bytes()
        runtime, payload = _request(
            path, target_rate=target_rate, profile=profile, execution="exec:conformance"
        )
        identity = runtime.prepare(payload)
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
        stable_since: float | None = None
        while time.monotonic() < deadline:
            if runtime.query_identity().get("eos"):
                eos_observed = True
                break
            length = len(runtime.captured_bytes())
            if length == last_length:
                stable_polls += 1
            else:
                stable_polls = 0
                last_length = length
                stable_since = None
            # Capture can stabilise a few milliseconds before the bus delivers
            # EOS; keep polling briefly instead of declaring a false failure.
            if stable_polls >= 5 and length > 0:
                if stable_since is None:
                    stable_since = time.monotonic()
                elif time.monotonic() - stable_since >= 1.0:
                    break
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
        reference: dict[str, Any] = {}
        magnitude_error_db: float | None = None
        if expected_frequency_hz:
            reference = _reference_capture(
                path,
                channels=2,
                rate=target_rate,
                expected_hz=expected_frequency_hz,
            )
            if reference.get("status") == "PASS":
                magnitude_error_db = 20.0 * math.log10(
                    max(tone["tone_amplitude"], 1e-12)
                    / max(reference["amplitude"], 1e-12)
                )
                tone["magnitude_error_vs_reference_db"] = magnitude_error_db
        numeric_checks = {}
        stopband: dict[str, Any] = {}
        if stopband_hz:
            alias_hz = abs(target_rate - stopband_hz)
            alias = (
                _tone_metrics(
                    raw,
                    channels=2,
                    rate=target_rate,
                    expected_hz=alias_hz,
                )
                if alias_hz < target_rate / 2
                else {}
            )
            reference_stopband = _reference_capture(
                path,
                channels=2,
                rate=max(target_rate * 4, 352_800),
                expected_hz=stopband_hz,
            )
            rejection_db: float | None = None
            if reference_stopband.get("status") == "PASS" and alias.get(
                "tone_amplitude"
            ):
                rejection_db = 20.0 * math.log10(
                    max(reference_stopband["amplitude"], 1e-12)
                    / max(alias["tone_amplitude"], 1e-12)
                )
            stopband = {
                "stimulus_hz": stopband_hz,
                "alias_hz": alias_hz,
                "reference": reference_stopband,
                "alias_amplitude": alias.get("tone_amplitude"),
                "rejection_db": rejection_db,
                "clipping_disposition": (
                    "NOT_APPLICABLE — an out-of-band stimulus may reconstruct "
                    "above full scale; clipping is not a pass/fail criterion here"
                ),
                "status": (
                    "NOT_RUN"
                    if rejection_db is None
                    else "PASS"
                    if rejection_db >= 80.0
                    else "FAIL"
                ),
            }
            numeric_checks = {
                "resampler_stopband_ge_80_db": stopband["status"],
                "nan_inf_zero": "PASS" if metrics.get("nan_inf") == 0 else "FAIL",
                "no_unexpected_clipping": "NOT_APPLICABLE",
                "eos_observed": "PASS" if eos_observed else "FAIL",
            }
        elif expected_frequency_hz:
            magnitude_key = (
                "magnitude_error_le_0_25_db"
                if expected_frequency_hz > 20_000
                else "magnitude_error_le_0_10_db"
            )
            magnitude_limit = 0.25 if expected_frequency_hz > 20_000 else 0.10
            numeric_checks = {
                "nan_inf_zero": "PASS" if tone.get("nan_inf") == 0 else "FAIL",
                "dc_gain_error_le_0_05_db": "NOT_MEASURED",
                magnitude_key: (
                    "NOT_RUN"
                    if magnitude_error_db is None
                    else "PASS"
                    if abs(magnitude_error_db) <= magnitude_limit
                    else "FAIL"
                ),
                "inter_channel_gain_le_0_01_db": (
                    "PASS"
                    if tone.get("inter_channel_gain_mismatch_db", 1.0) <= 0.01
                    else "FAIL"
                ),
                "inter_channel_latency_zero_samples": (
                    "PASS"
                    if tone.get("inter_channel_latency_samples", 1) == 0
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
                "eos_observed": "PASS" if eos_observed else "FAIL",
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
            "reference": reference,
            "stopband": stopband,
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
                    _checks_disposition(numeric_checks) if numeric_checks else "NOT_RUN"
                ),
            },
            "status": _vector_status(
                sample_count=metrics.get("sample_count", 0),
                cleanup_confirmed=bool(release.get("release")),
                eos_observed=eos_observed,
                numeric_checks=numeric_checks,
            ),
            "environment": {"python": "3.11", "sink": "fakesink"},
            "cleanup_confirmed": bool(release.get("release")),
            "eos_observed": eos_observed,
            "release": release.get("release"),
        }


def run_corpus(*, target_rate: int, profile: str) -> dict[str, Any]:
    vectors = []
    with tempfile.TemporaryDirectory(prefix="michi-dsd2pcm-corpus-") as tmp:
        for name, frequency, sample_count, stopband_hz in CORPUS_VECTORS:
            path = Path(tmp) / f"{name}.dsf"
            path.write_bytes(
                _dsf_blob(
                    sample_count=sample_count,
                    frequency_hz=frequency,
                )
            )
            vectors.append(
                run(
                    fixture=path,
                    target_rate=target_rate,
                    profile=profile,
                    expected_frequency_hz=0 if stopband_hz else frequency,
                    fixture_name=name,
                    stopband_hz=stopband_hz,
                )
            )
    for vector in vectors:
        # Generated fixtures live in a temporary directory; the SHA256 and the
        # fixture name are the reproducible identity, not the temp path.
        vector["fixture"]["path"] = None
    rate_rule = _profile_rate_rule(target_rate=target_rate, profile=profile)
    statuses = {vector["status"] for vector in vectors}
    return {
        "schema_version": 1,
        "phase": "AP2-F10",
        "corpus": "dsd64_v2",
        "target_rate_hz": target_rate,
        "profile": profile,
        "profile_rules": rate_rule,
        "vectors": vectors,
        "status": (
            "FAIL"
            if rate_rule["status"] == "FAIL" or "FAIL" in statuses
            else "PASS"
            if statuses == {"PASS"}
            else "PARTIAL"
        ),
        "environment": {"python": "3.11", "sink": "fakesink"},
    }


def _profile_rate_rule(*, target_rate: int, profile: str) -> dict[str, Any]:
    manifest = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "audio"
        / "phase2"
        / "dsd2pcm_profiles_v1.json"
    )
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        ladder = payload["profiles"][profile]["ladder_hz"]
    except (OSError, KeyError, TypeError, ValueError) as exc:
        return {
            "status": "NOT_RUN",
            "reason": f"profile manifest unavailable: {exc}",
        }
    allowed = int(target_rate) in {int(value) for value in ladder}
    return {
        "status": "PASS" if allowed else "FAIL",
        "profile": profile,
        "target_rate_hz": target_rate,
        "ladder_hz": list(ladder),
        "reason": (
            "target rate belongs to the profile ladder"
            if allowed
            else "target rate is outside the profile ladder"
        ),
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
