#!/usr/bin/env python3
"""AP2-F10 numeric DSD→PCM conformance harness.

The harness executes the SAME supervised child runtime used by playback, but
in-process for measurement. It captures the actual F32LE buffers arriving at
the sink and emits only measured facts; it never certifies a profile without a
traceable oracle.

§274.4/§275 numeric contract:

* the DC criterion is measured with an explicit non-zero DC stimulus and a
  versioned FFmpeg reference. The linear residual offset is reported in linear
  units and is never converted into a dB gain;
* the resampler stopband criterion is measured on an ISOLATED audioresample
  pipeline configured exactly like production. An end-to-end DSD alias
  comparison is kept as INFORMATIONAL evidence only: it is bounded by the
  modulator noise floor and therefore cannot certify the resampler;
* every criterion carries one of PASS / FAIL / NOT_RUN / NOT_MEASURED /
  NOT_APPLICABLE / INFORMATIONAL and the corpus exposes an explicit
  ``certification`` flag. ``corpus.status`` is never PASS while a mandatory
  criterion is not PASS.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import shutil
import struct
import subprocess
import tempfile
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

F32LE = "F32LE"
DSD_BIT_RATE_HZ = 2_822_400
DSD_NATIVE_RATE_HZ = DSD_BIT_RATE_HZ // 8
SILENCE_SAMPLE_COUNT = 44_100
CORPUS_SAMPLE_COUNT = 17_640
#: One processing block at the target rate (GStreamer default buffer size).
PROCESSING_BLOCK_FRAMES = 1024

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_NOT_RUN = "NOT_RUN"
STATUS_NOT_MEASURED = "NOT_MEASURED"
STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"
STATUS_INFORMATIONAL = "INFORMATIONAL"
CRITERION_STATUSES: tuple[str, ...] = (
    STATUS_PASS,
    STATUS_FAIL,
    STATUS_NOT_RUN,
    STATUS_NOT_MEASURED,
    STATUS_NOT_APPLICABLE,
    STATUS_INFORMATIONAL,
)

#: §274.4 thresholds. They are Michi acceptance criteria, not upstream claims.
DC_GAIN_ERROR_LIMIT_DB = 0.05
PASSBAND_LIMIT_DB_20K = 0.10
PASSBAND_LIMIT_DB_40K = 0.25
STOPBAND_MIN_REJECTION_DB = 80.0
INTER_CHANNEL_GAIN_LIMIT_DB = 0.01
#: A dB gain ratio is only defined on a reference far enough from zero.
DC_REFERENCE_MIN_ABS = 0.05

#: Non-zero DC stimuli: the exact mean of each 1-bit stream equals the level.
DC_STIMULUS_LEVELS: tuple[float, ...] = (0.25, -0.25)
DC_STIMULUS_BITS = 176_400

#: Isolated resampler stopband sweep. 40 kHz is the in-band control.
STOPBAND_SWEEP_HZ: tuple[int, ...] = (
    40_000,
    60_000,
    80_000,
    100_000,
    120_000,
    160_000,
)
STOPBAND_CONTROL_HZ = 40_000
SWEEP_INPUT_SECONDS = 0.5
RESAMPLER_POLICY: tuple[tuple[str, Any], ...] = (
    ("quality", 10),
    ("resample-method", "kaiser"),
    ("sinc-filter-mode", "full"),
    ("sinc-filter-interpolation", "none"),
)

#: §274.1 profile ladders are read from dsd2pcm_profiles_v1.json. The corpus
#: only ever certifies the profile/rate it actually executed.
PROFILE_NAMES: tuple[str, ...] = ("FAST", "BALANCED", "HIGH", "REFERENCE")
PROFILE_MANIFEST = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "audio"
    / "phase2"
    / "dsd2pcm_profiles_v1.json"
)
PROCEDURE_VERSION = "ap2-f10-s14-cut5-v1"
PROCEDURE_DESCRIPTION = (
    "DC: second-order sigma-delta constant-level stimulus; linear DC offset "
    "reported separately; DC gain error = 20*log10(measured_dc/reference_dc) "
    "against the versioned FFmpeg F32LE capture at the same target rate, only "
    "when |reference_dc| >= 0.05. Stopband: isolated filesrc(F32LE at 352800) "
    "-> audioresample(quality=10,kaiser,full,none) -> F32LE at the target rate; "
    "input amplitude and folded-alias output amplitude measured by complex "
    "projection with a Hann window. Passband: production capture versus the "
    "versioned FFmpeg capture at the same target rate. Latency: step midpoint "
    "crossing on the decoder-only and full paths plus the isolated resampler."
)


@dataclass(frozen=True, slots=True)
class _VectorSpec:
    """One reproducible corpus vector."""

    name: str
    kind: str
    frequency_hz: int = 0
    sample_count: int = CORPUS_SAMPLE_COUNT
    stopband_hz: int | None = None
    expected_dc: float | None = None
    expect_inverted: bool = False


#: §275.3 corpus. Tones ascend so a band failure is localised.
CORPUS_SPECS: tuple[_VectorSpec, ...] = (
    _VectorSpec("silence", "silence", sample_count=SILENCE_SAMPLE_COUNT),
    # Low frequencies need several cycles at the decoder native rate for a
    # stable projection; the resampler magnifies the capture length.
    _VectorSpec("tone_20hz", "tone", 20, 564_480),
    _VectorSpec("tone_100hz", "tone", 100, 112_896),
    _VectorSpec("tone_1khz", "tone", 1_000),
    _VectorSpec("tone_5khz", "tone", 5_000),
    _VectorSpec("tone_10khz", "tone", 10_000),
    _VectorSpec("tone_15khz", "tone", 15_000),
    _VectorSpec("tone_20khz", "tone", 20_000),
    _VectorSpec("tone_25khz", "tone", 25_000),
    _VectorSpec("tone_30khz", "tone", 30_000),
    _VectorSpec("tone_35khz", "tone", 35_000),
    _VectorSpec("tone_40khz", "tone", 40_000),
    _VectorSpec("dc_plus_0p25", "dc", sample_count=DC_STIMULUS_BITS, expected_dc=0.25),
    _VectorSpec(
        "dc_minus_0p25", "dc", sample_count=DC_STIMULUS_BITS, expected_dc=-0.25
    ),
    _VectorSpec(
        "phase_inverted_1khz",
        "tone",
        1_000,
        expect_inverted=True,
    ),
    # 80 kHz folds to 8.2 kHz at 88.2 kHz when the resampler fails to reject
    # it. Kept as end-to-end evidence, never as the resampler criterion.
    _VectorSpec("stopband_80khz", "stopband", 80_000, 70_560, stopband_hz=80_000),
)
#: Legacy tuple of (name, analytic frequency) for tone/silence fixtures.
DSD64_CORPUS: tuple[tuple[str, int], ...] = tuple(
    (spec.name, spec.frequency_hz)
    for spec in CORPUS_SPECS
    if spec.kind in {"silence", "tone", "stopband"} and not spec.expect_inverted
)


def _modulate(levels: Iterable[float]) -> bytes:
    """Second-order sigma-delta modulation of an arbitrary level sequence.

    At DC the loop forces ``mean(feedback) == mean(level)``, so the exact mean
    of the resulting 1-bit stream is the requested level. That makes the DC
    stimulus analytically known instead of decoder-defined.
    """
    first = 0.0
    second = 0.0
    feedback = 0.0
    out = bytearray()
    byte = 0
    index = -1
    for index, level in enumerate(levels):
        first += level - feedback
        second += first - feedback
        bit = 1 if second >= 0.0 else 0
        feedback = 1.0 if bit else -1.0
        # DSF stores DSD bytes least-significant-bit first.
        byte |= bit << (index % 8)
        if index % 8 == 7:
            out.append(byte)
            byte = 0
    if index >= 0 and index % 8 != 7:
        out.append(byte)
    return bytes(out)


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
        + struct.pack("<I", DSD_BIT_RATE_HZ)
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


def _tone_bits(
    *,
    frequency_hz: int,
    bit_count: int,
    amplitude: float = 0.5,
    polarity: float = 1.0,
) -> bytes:
    """Second-order sigma-delta 1-bit stream for one analytic sine.

    The corpus is intentionally analytic: the independent reference is the
    requested sine amplitude, not a capture produced by the decoder itself.
    """
    return _modulate(
        polarity
        * amplitude
        * math.sin(2.0 * math.pi * frequency_hz * index / DSD_BIT_RATE_HZ)
        for index in range(bit_count)
    )


def _dc_bits(*, level: float, bit_count: int) -> bytes:
    """Constant-level stream whose exact 1-bit mean is ``level``."""
    if not -1.0 < level < 1.0:
        raise ValueError("DC level must be strictly inside (-1, 1)")
    return _modulate(itertools.repeat(level, bit_count))


def _step_bits(
    *,
    level_before: float,
    level_after: float,
    bit_count: int,
    transition_bit: int,
) -> bytes:
    """DC step whose transition index is known to the bit."""
    transition = max(0, min(int(bit_count), int(transition_bit)))
    return _modulate(
        level_before if index < transition else level_after
        for index in range(bit_count)
    )


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


def _dsf_stereo_payload(left: bytes, right: bytes, *, block_size: int = 4096) -> bytes:
    """DSF stereo payload with independent per-channel blocks."""
    left = left + b"\x00" * ((-len(left)) % block_size)
    right = right + b"\x00" * ((-len(right)) % block_size)
    if len(left) != len(right):
        raise ValueError("stereo channels must be block aligned to equal size")
    payload = bytearray()
    for offset in range(0, len(left), block_size):
        payload.extend(left[offset : offset + block_size])
        payload.extend(right[offset : offset + block_size])
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


def _dsf_dc_blob(*, sample_count: int, level: float) -> bytes:
    payload = _dsf_block_payload(_dc_bits(level=level, bit_count=sample_count * 8))
    return build_dsf(sample_count=sample_count * 8, payload=payload)


def _dsf_stereo_tone_blob(
    *,
    sample_count: int,
    left_frequency_hz: int,
    right_frequency_hz: int,
    right_polarity: float = 1.0,
) -> bytes:
    bit_count = sample_count * 8
    left = (
        _tone_bits(frequency_hz=left_frequency_hz, bit_count=bit_count)
        if left_frequency_hz
        else _silence_mono(bit_count // 8)
    )
    right = (
        _tone_bits(
            frequency_hz=right_frequency_hz,
            bit_count=bit_count,
            polarity=right_polarity,
        )
        if right_frequency_hz
        else _silence_mono(bit_count // 8)
    )
    return build_dsf(
        sample_count=bit_count,
        payload=_dsf_stereo_payload(left, right),
    )


def _project_amplitude(
    raw: bytes,
    *,
    channels: int,
    rate: int,
    frequency_hz: int,
    start_fraction: float = 0.0,
    end_fraction: float = 1.0,
) -> float:
    """Unbiased amplitude at a known frequency (complex Hann projection)."""
    import numpy as np

    usable = len(raw) - (len(raw) % (4 * channels))
    if usable <= 0 or frequency_hz <= 0:
        return 0.0
    frames = np.frombuffer(raw[:usable], dtype="<f4").reshape(-1, channels)
    signal = np.nan_to_num(
        frames[:, 0].astype(np.float64), nan=0.0, posinf=0.0, neginf=0.0
    )
    first = int(signal.size * start_fraction)
    last = int(signal.size * end_fraction)
    signal = signal[first:last]
    if signal.size < 8:
        return 0.0
    window = np.hanning(signal.size)
    offsets = np.arange(signal.size, dtype=np.float64) + first
    projection = (
        np.sum(signal * window * np.exp(-2j * math.pi * frequency_hz * offsets / rate))
        / window.sum()
    )
    return float(2.0 * abs(projection))


def _fold_frequency(frequency_hz: float, rate: int) -> float:
    """Fold a stimulus into [0, rate/2] for alias measurement."""
    remainder = frequency_hz % rate
    return min(remainder, rate - remainder)


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
    channel_signals = [
        np.nan_to_num(
            frames[:, channel].astype(np.float64),
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )
        for channel in range(channels)
    ]
    channel_amplitudes = [_amplitude(signal) for signal in channel_signals]
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

    correlation: float | None = None
    channel_polarity = STATUS_NOT_APPLICABLE
    if channels >= 2 and channel_signals[0].size and channel_signals[1].size:
        left_signal = channel_signals[0]
        right_signal = channel_signals[1]
        denominator = math.sqrt(
            float(np.dot(left_signal, left_signal))
            * float(np.dot(right_signal, right_signal))
        )
        if denominator > 1e-12:
            correlation = float(np.dot(left_signal, right_signal)) / denominator
            if correlation >= 0.5:
                channel_polarity = "IN_PHASE"
            elif correlation <= -0.5:
                channel_polarity = "INVERTED"
            else:
                channel_polarity = "UNCORRELATED"
    latency_samples = (
        _channel_lag(channel_signals[0], channel_signals[1]) if channels >= 2 else 0
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
        # A linear residual offset is not a dB gain error. §274.4 DC gain is
        # measured by the dedicated DC vectors against a versioned reference.
        "dc_gain_error_db": None,
        "dc_gain_status": STATUS_NOT_MEASURED,
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
        "inter_channel_correlation": correlation,
        "channel_polarity": channel_polarity,
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
        return {"status": STATUS_NOT_RUN, "reason": "ffmpeg not found"}
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
                timeout=120,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return {"status": STATUS_NOT_RUN, "reason": f"ffmpeg failed: {exc}"}
        if completed.returncode != 0 or not target.exists():
            detail = (completed.stderr or "no reference output").strip()
            return {"status": STATUS_NOT_RUN, "reason": detail[:500]}
        raw = target.read_bytes()
    metrics = _tone_metrics(raw, channels=channels, rate=rate, expected_hz=expected_hz)
    if not metrics.get("sample_count"):
        return {"status": STATUS_NOT_RUN, "reason": "empty reference capture"}
    return {
        "status": STATUS_PASS,
        "tool": "ffmpeg",
        "version": _ffmpeg_version(ffmpeg),
        "reference_role": (
            "decoder_native_reference"
            if rate == DSD_NATIVE_RATE_HZ
            else "target_rate_reference"
        ),
        "target_rate_hz": rate,
        "sample_count": metrics["sample_count"],
        "sha256": hashlib.sha256(raw).hexdigest(),
        "amplitude": metrics["tone_amplitude"] if expected_hz else None,
        "gain_db": metrics["tone_gain_error_db"] if expected_hz else None,
        "dc_offset": metrics["dc_offset"],
    }


def _dc_measurement(
    *,
    measured: float | None,
    reference: dict[str, Any],
    expected_level: float | None,
) -> dict[str, Any]:
    """§274.4 DC gain in dB, or an explicit NOT_MEASURED reason.

    The linear offset stays a linear quantity. The dB figure is a ratio of two
    non-zero DC levels; a near-zero reference cannot produce a valid dB gain.
    """
    reference_dc = reference.get("dc_offset")
    result: dict[str, Any] = {
        "expected_level": expected_level,
        "measured_dc_offset": measured,
        "reference_dc_offset": reference_dc,
        "reference_sha256": reference.get("sha256"),
        "reference_version": reference.get("version"),
        "dc_gain_error_db": None,
        "dc_gain_error_vs_stimulus_db": None,
        "units": "dB = 20*log10(measured_dc / reference_dc)",
        "status": STATUS_NOT_MEASURED,
        "reason": "",
    }
    if reference.get("status") != STATUS_PASS:
        result["reason"] = (
            "versioned reference capture unavailable: "
            f"{reference.get('reason') or reference.get('status')}"
        )
        return result
    if measured is None or not math.isfinite(measured):
        result["reason"] = "measured DC offset is not finite"
        return result
    if reference_dc is None or not math.isfinite(reference_dc):
        result["reason"] = "reference DC offset is not finite"
        return result
    if abs(reference_dc) < DC_REFERENCE_MIN_ABS:
        result["reason"] = (
            f"reference DC magnitude {abs(reference_dc):.6g} is below the "
            f"{DC_REFERENCE_MIN_ABS} floor; a near-zero reference cannot "
            "establish a relative dB gain"
        )
        return result
    if measured == 0.0 or (measured < 0.0) != (reference_dc < 0.0):
        result["reason"] = "measured and reference DC have inconsistent sign"
        return result
    error_db = 20.0 * math.log10(abs(measured / reference_dc))
    result["dc_gain_error_db"] = error_db
    if expected_level not in (None, 0.0) and (expected_level < 0.0) == (measured < 0.0):
        result["dc_gain_error_vs_stimulus_db"] = 20.0 * math.log10(
            abs(measured / expected_level)
        )
    if abs(error_db) <= DC_GAIN_ERROR_LIMIT_DB:
        result["status"] = STATUS_PASS
        result["reason"] = (
            f"DC gain error {error_db:.6f} dB is within "
            f"{DC_GAIN_ERROR_LIMIT_DB} dB of the versioned reference"
        )
    else:
        result["status"] = STATUS_FAIL
        result["reason"] = (
            f"DC gain error {error_db:.6f} dB exceeds {DC_GAIN_ERROR_LIMIT_DB} dB"
        )
    return result


def _checks_disposition(checks: dict[str, str]) -> str:
    values = tuple(checks.values())
    if not values:
        return STATUS_PASS
    if STATUS_FAIL in values:
        return STATUS_FAIL
    if STATUS_NOT_MEASURED in values:
        return STATUS_NOT_MEASURED
    if STATUS_NOT_RUN in values:
        return STATUS_NOT_RUN
    return STATUS_PASS


def _aggregate_status(values: Iterable[str]) -> str:
    """Aggregate criterion dispositions; any unmeasured value blocks PASS."""
    collected = list(values)
    if not collected:
        return STATUS_NOT_RUN
    for status in (STATUS_FAIL, STATUS_NOT_MEASURED, STATUS_NOT_RUN):
        if status in collected:
            return status
    if STATUS_PASS in collected:
        return STATUS_PASS
    if all(value == STATUS_NOT_APPLICABLE for value in collected):
        return STATUS_NOT_APPLICABLE
    return STATUS_NOT_RUN


def _vector_status(
    *,
    sample_count: int,
    cleanup_confirmed: bool,
    eos_observed: bool,
    numeric_checks: dict[str, str],
) -> str:
    if sample_count <= 0 or not cleanup_confirmed:
        return STATUS_FAIL
    if not eos_observed:
        return "PARTIAL"
    disposition = _checks_disposition(numeric_checks)
    if disposition == STATUS_FAIL:
        return STATUS_FAIL
    if disposition in (STATUS_NOT_RUN, STATUS_NOT_MEASURED):
        return "PARTIAL"
    return STATUS_PASS


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
        "source_rate_hz": DSD_BIT_RATE_HZ,
        "source_bits": DSD_BIT_RATE_HZ,
        "bit_order": "LSBF",
        "channels": 2,
        "decoder_factory": "avdec_dsd_lsbf",
        "target_rate_hz": target_rate,
        "output_format": F32LE,
        "quality_profile": profile,
        "resampler_policy": (
            []
            if target_rate == DSD_NATIVE_RATE_HZ
            else [[name, value] for name, value in RESAMPLER_POLICY]
        ),
        # fakesink keeps consuming to EOS; appsink (even with drop=true)
        # can stall the streaming thread. Capture comes from the pad probe.
        "sink_factory": "fakesink",
        "capture_max_frames": 4_000_000,
    }
    return DsdPcmHostRuntime(), payload


def _capture_fixture(path: Path, *, target_rate: int, profile: str) -> dict[str, Any]:
    """Run one fixture through the production host runtime and capture F32LE."""
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
    deadline = time.monotonic() + 20.0
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
    return {
        "raw": raw,
        "observed": observed,
        "release": release,
        "eos_observed": eos_observed,
    }


def run(
    *,
    fixture: Path | None,
    target_rate: int,
    profile: str,
    expected_frequency_hz: int = 0,
    fixture_name: str | None = None,
    stopband_hz: int | None = None,
    expected_dc: float | None = None,
    expect_inverted: bool = False,
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
        capture = _capture_fixture(path, target_rate=target_rate, profile=profile)
        raw = capture["raw"]
        observed = capture["observed"]
        release = capture["release"]
        eos_observed = capture["eos_observed"]
        metrics = _metrics(raw, 2, target_rate)
        tone: dict[str, Any] = {}
        reference: dict[str, Any] = {}
        dc_measurement: dict[str, Any] = {}
        numeric_checks: dict[str, str] = {}
        informational: dict[str, Any] = {
            "disposition": (
                "INFORMATIONAL — not the §274.4 isolated resampler criterion"
            ),
            "stopband_rejection_db": None,
        }
        stopband: dict[str, Any] = {}
        if expected_dc is not None:
            tone = _tone_metrics(raw, channels=2, rate=target_rate, expected_hz=0)
            reference = _reference_capture(
                path, channels=2, rate=target_rate, expected_hz=0
            )
            dc_measurement = _dc_measurement(
                measured=metrics.get("dc"),
                reference=reference,
                expected_level=expected_dc,
            )
            numeric_checks = {
                "dc_gain_error_le_0_05_db": dc_measurement["status"],
                "nan_inf_zero": (
                    STATUS_PASS if metrics.get("nan_inf") == 0 else STATUS_FAIL
                ),
                "no_unexpected_clipping": (
                    STATUS_PASS if tone.get("clipping_samples") == 0 else STATUS_FAIL
                ),
                "eos_observed": (STATUS_PASS if eos_observed else STATUS_FAIL),
            }
        elif stopband_hz:
            alias_hz = int(_fold_frequency(stopband_hz, target_rate))
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
                rate=max(target_rate * 4, DSD_NATIVE_RATE_HZ),
                expected_hz=stopband_hz,
            )
            rejection_db: float | None = None
            if reference_stopband.get("status") == STATUS_PASS and alias.get(
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
                "disposition": (
                    "INFORMATIONAL — end-to-end alias rejection is bounded by "
                    "the modulator noise floor; §274.4 is certified only by the "
                    "isolated pre/post resampler sweep"
                ),
            }
            informational["stopband_rejection_db"] = rejection_db
            numeric_checks = {
                "nan_inf_zero": (
                    STATUS_PASS if metrics.get("nan_inf") == 0 else STATUS_FAIL
                ),
                "no_unexpected_clipping": STATUS_NOT_APPLICABLE,
                "eos_observed": (STATUS_PASS if eos_observed else STATUS_FAIL),
            }
        elif expected_frequency_hz:
            tone = _tone_metrics(
                raw,
                channels=2,
                rate=target_rate,
                expected_hz=expected_frequency_hz,
            )
            # §274.4 magnitude is measured against the independent decoder at
            # its native rate. FFmpeg's own -ar resampler droops near Nyquist
            # (1.29 dB at 40 kHz), so a target-rate reference would report the
            # reference's roll-off as a product failure. The native-rate capture
            # isolates the production resampler's passband response.
            reference = _reference_capture(
                path,
                channels=2,
                rate=DSD_NATIVE_RATE_HZ,
                expected_hz=expected_frequency_hz,
            )
            magnitude_error_db: float | None = None
            if reference.get("status") == STATUS_PASS:
                magnitude_error_db = 20.0 * math.log10(
                    max(tone["tone_amplitude"], 1e-12)
                    / max(reference["amplitude"], 1e-12)
                )
                tone["magnitude_error_vs_reference_db"] = magnitude_error_db
            nyquist_hz = target_rate / 2
            if expected_frequency_hz >= nyquist_hz:
                magnitude_key = "magnitude_error_le_0_25_db"
                magnitude_limit = PASSBAND_LIMIT_DB_40K
                magnitude_status = STATUS_NOT_APPLICABLE
                band = "above_target_nyquist"
            elif expected_frequency_hz > 20_000:
                magnitude_key = "magnitude_error_le_0_25_db"
                magnitude_limit = PASSBAND_LIMIT_DB_40K
                magnitude_status = (
                    STATUS_NOT_RUN
                    if magnitude_error_db is None
                    else STATUS_PASS
                    if abs(magnitude_error_db) <= magnitude_limit
                    else STATUS_FAIL
                )
                band = "20kHz-40kHz"
            else:
                magnitude_key = "magnitude_error_le_0_10_db"
                magnitude_limit = PASSBAND_LIMIT_DB_20K
                magnitude_status = (
                    STATUS_NOT_RUN
                    if magnitude_error_db is None
                    else STATUS_PASS
                    if abs(magnitude_error_db) <= magnitude_limit
                    else STATUS_FAIL
                )
                band = "20Hz-20kHz"
            tone["magnitude_band"] = band
            expected_polarity = "INVERTED" if expect_inverted else "IN_PHASE"
            polarity_status = (
                STATUS_PASS
                if tone.get("channel_polarity") == expected_polarity
                else STATUS_FAIL
            )
            numeric_checks = {
                "nan_inf_zero": (
                    STATUS_PASS if tone.get("nan_inf") == 0 else STATUS_FAIL
                ),
                magnitude_key: magnitude_status,
                "inter_channel_gain_le_0_01_db": (
                    STATUS_PASS
                    if tone.get("inter_channel_gain_mismatch_db", 1.0)
                    <= INTER_CHANNEL_GAIN_LIMIT_DB
                    else STATUS_FAIL
                ),
                "inter_channel_latency_zero_samples": (
                    STATUS_PASS
                    if tone.get("inter_channel_latency_samples", 1) == 0
                    else STATUS_FAIL
                ),
                "no_unexpected_clipping": (
                    STATUS_PASS if tone.get("clipping_samples") == 0 else STATUS_FAIL
                ),
                # 6615-frame captures at 88.2 kHz have ~13.3 Hz FFT bins.
                "frequency_error_le_20_hz": (
                    STATUS_PASS
                    if tone.get("tone_frequency_error_hz", 999.0) <= 20.0
                    else STATUS_FAIL
                ),
                "eos_observed": (STATUS_PASS if eos_observed else STATUS_FAIL),
            }
            if expect_inverted:
                numeric_checks["channel_polarity_inversion_detected"] = polarity_status
            else:
                numeric_checks["channel_polarity_in_phase"] = polarity_status
        return {
            "schema_version": 2,
            "fixture": {
                "path": str(path),
                "name": fixture_name,
                "sha256": hashlib.sha256(source).hexdigest(),
                "generated": generated,
                "bit_order": "LSBF",
                "analytic_frequency_hz": expected_frequency_hz,
                "analytic_dc_level": expected_dc,
                "oracle": (
                    "analytic_dc_level"
                    if expected_dc is not None
                    else "analytic_sine_amplitude_0.5"
                ),
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
            "dc": dc_measurement,
            "stopband": stopband,
            "numeric_checks": numeric_checks,
            "informational_metrics": informational,
            "metric_dispositions": {
                "signal_present": (
                    STATUS_PASS if metrics.get("sample_count", 0) > 0 else STATUS_FAIL
                ),
                "numeric_finiteness": (
                    STATUS_PASS if metrics.get("nan_inf") == 0 else STATUS_FAIL
                ),
                "eos": STATUS_PASS if eos_observed else STATUS_FAIL,
                "oracle": (
                    _checks_disposition(numeric_checks)
                    if numeric_checks
                    else STATUS_NOT_RUN
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


def _load_resampler_policy(resampler: Any) -> dict[str, Any]:
    readback: dict[str, Any] = {}
    contract_ok = True
    for name, value in RESAMPLER_POLICY:
        try:
            resampler.set_property(name, value)
            actual = resampler.get_property(name)
        except Exception as exc:  # noqa: BLE001 - contract unavailable
            readback[name] = {
                "expected": value,
                "actual": None,
                "error": str(exc),
            }
            contract_ok = False
            continue
        actual_value = getattr(actual, "value_nick", actual)
        readback[name] = {
            "expected": value,
            "actual": actual_value,
            "exact": str(actual_value) == str(value),
        }
        if str(actual_value) != str(value):
            contract_ok = False
    return {"ok": contract_ok, "properties": readback}


def _resampler_capture(
    raw: bytes, *, input_rate: int, output_rate: int
) -> dict[str, Any]:
    """Run one F32LE buffer through audioresample configured like production."""
    try:
        import gi

        gi.require_version("Gst", "1.0")
        from gi.repository import Gst
    except Exception as exc:  # noqa: BLE001 - unmeasured is not a failure
        return {
            "status": STATUS_NOT_RUN,
            "reason": f"GStreamer bindings unavailable: {exc}",
        }
    Gst.init(None)
    with tempfile.TemporaryDirectory(prefix="michi-resampler-isolation-") as tmp:
        source = Path(tmp) / "input.f32"
        source.write_bytes(raw)
        pipeline = Gst.Pipeline.new("michi-resampler-isolation")
        filesrc = Gst.ElementFactory.make("filesrc", "src")
        incaps = Gst.ElementFactory.make("capsfilter", "incaps")
        resampler = Gst.ElementFactory.make("audioresample", "resampler")
        outcaps = Gst.ElementFactory.make("capsfilter", "outcaps")
        sink = Gst.ElementFactory.make("fakesink", "sink")
        missing = [
            name
            for name, element in (
                ("filesrc", filesrc),
                ("capsfilter", incaps),
                ("audioresample", resampler),
                ("capsfilter", outcaps),
                ("fakesink", sink),
            )
            if element is None
        ]
        if missing:
            return {
                "status": STATUS_NOT_RUN,
                "reason": f"missing GStreamer factories: {missing}",
            }
        filesrc.set_property("location", str(source))
        incaps.set_property(
            "caps",
            Gst.Caps.from_string(
                "audio/x-raw,format=F32LE,layout=interleaved,"
                f"rate={input_rate},channels=2"
            ),
        )
        policy = _load_resampler_policy(resampler)
        outcaps.set_property(
            "caps",
            Gst.Caps.from_string(
                "audio/x-raw,format=F32LE,layout=interleaved,"
                f"rate={output_rate},channels=2"
            ),
        )
        sink.set_property("sync", False)
        for element in (filesrc, incaps, resampler, outcaps, sink):
            pipeline.add(element)
        for upper, lower in (
            (filesrc, incaps),
            (incaps, resampler),
            (resampler, outcaps),
            (outcaps, sink),
        ):
            if not upper.link(lower):
                return {
                    "status": STATUS_NOT_RUN,
                    "reason": f"cannot link {upper.get_name()} -> {lower.get_name()}",
                    "policy": policy,
                }
        captured = bytearray()

        def _probe(_pad, info):
            buffer = info.get_buffer()
            if buffer is None:
                return Gst.PadProbeReturn.OK
            success, map_info = buffer.map(Gst.MapFlags.READ)
            if success:
                captured.extend(bytes(map_info.data))
                buffer.unmap(map_info)
            return Gst.PadProbeReturn.OK

        pad = sink.get_static_pad("sink")
        if pad is None:
            return {
                "status": STATUS_NOT_RUN,
                "reason": "fakesink has no sink pad",
                "policy": policy,
            }
        pad.add_probe(Gst.PadProbeType.BUFFER, _probe)
        bus = pipeline.get_bus()
        pipeline.set_state(Gst.State.PLAYING)
        eos = False
        error: str | None = None
        deadline = time.monotonic() + 30.0
        while time.monotonic() < deadline:
            message = bus.timed_pop_filtered(
                50 * Gst.MSECOND,
                Gst.MessageType.EOS | Gst.MessageType.ERROR,
            )
            if message is None:
                continue
            if message.type == Gst.MessageType.EOS:
                eos = True
            else:
                err, debug = message.parse_error()
                error = f"{err}: {debug}"
            break
        pipeline.set_state(Gst.State.NULL)
        if not eos:
            return {
                "status": STATUS_NOT_RUN,
                "reason": error or "isolated resampler pipeline did not reach EOS",
                "policy": policy,
            }
        output = bytes(captured)
        return {
            "status": STATUS_PASS,
            "raw": output,
            "sha256": hashlib.sha256(output).hexdigest(),
            "frames": len(output) // 8,
            "eos": True,
            "policy": policy,
            "input_sha256": hashlib.sha256(raw).hexdigest(),
        }


def _sweep_point(
    *,
    stimulus_hz: int,
    target_rate: int,
    input_rate: int,
) -> dict[str, Any]:
    import numpy as np

    frames = int(input_rate * SWEEP_INPUT_SECONDS)
    offsets = np.arange(frames)
    tone = 0.5 * np.sin(2.0 * math.pi * stimulus_hz * offsets / input_rate)
    raw_input = np.stack([tone, tone], axis=1).astype("<f4").tobytes()
    capture = _resampler_capture(
        raw_input, input_rate=input_rate, output_rate=target_rate
    )
    alias_hz = _fold_frequency(stimulus_hz, target_rate)
    role = "control" if stimulus_hz == STOPBAND_CONTROL_HZ else "stopband"
    point: dict[str, Any] = {
        "stimulus_hz": stimulus_hz,
        "alias_hz": alias_hz,
        "role": role,
        "counts_toward_verdict": role == "stopband",
        "input_amplitude": _project_amplitude(
            raw_input, channels=2, rate=input_rate, frequency_hz=stimulus_hz
        ),
        "alias_amplitude": None,
        "rejection_db": None,
        "pass_at_80_db": None,
        "control_transfer_db": None,
        "control_pass": None,
        "measurement_uncertainty_db": None,
        "status": STATUS_NOT_RUN,
    }
    if capture.get("status") != STATUS_PASS:
        point["reason"] = capture.get("reason") or capture.get("status")
        return point
    output = capture["raw"]
    input_rate_amp = point["input_amplitude"]
    alias_amp = _project_amplitude(
        output,
        channels=2,
        rate=target_rate,
        frequency_hz=alias_hz,
    )
    point["alias_amplitude"] = alias_amp
    first_half = _project_amplitude(
        output,
        channels=2,
        rate=target_rate,
        frequency_hz=alias_hz,
        end_fraction=0.8,
    )
    second_half = _project_amplitude(
        output,
        channels=2,
        rate=target_rate,
        frequency_hz=alias_hz,
        start_fraction=0.2,
    )
    if first_half > 0.0 and second_half > 0.0:
        point["measurement_uncertainty_db"] = abs(
            20.0 * math.log10(first_half / second_half)
        )
    point["input_sha256"] = capture.get("input_sha256")
    point["output_sha256"] = capture.get("sha256")
    point["output_frames"] = capture.get("frames")
    point["resampler_policy"] = capture.get("policy")
    if role == "control":
        transfer_db = 20.0 * math.log10(
            max(alias_amp, 1e-30) / max(input_rate_amp, 1e-30)
        )
        point["control_transfer_db"] = transfer_db
        point["control_pass"] = abs(transfer_db) <= PASSBAND_LIMIT_DB_20K
        point["status"] = STATUS_PASS if point["control_pass"] else STATUS_FAIL
        point["reason"] = (
            "in-band control: the resampler must preserve a 40 kHz tone "
            f"within {PASSBAND_LIMIT_DB_20K} dB"
        )
        return point
    rejection_db = 20.0 * math.log10(max(input_rate_amp, 1e-30) / max(alias_amp, 1e-30))
    point["rejection_db"] = rejection_db
    point["pass_at_80_db"] = rejection_db >= STOPBAND_MIN_REJECTION_DB
    point["status"] = STATUS_PASS if point["pass_at_80_db"] else STATUS_FAIL
    point["reason"] = (
        f"isolated resampler rejection {rejection_db:.3f} dB "
        f"{'>=' if point['pass_at_80_db'] else '<'} "
        f"{STOPBAND_MIN_REJECTION_DB} dB"
    )
    return point


def run_stopband_sweep(*, target_rate: int, profile: str) -> dict[str, Any]:
    """§274.4 isolated resampler stopband sweep (pre/post of the same node)."""
    points = [
        _sweep_point(
            stimulus_hz=frequency,
            target_rate=target_rate,
            input_rate=DSD_NATIVE_RATE_HZ,
        )
        for frequency in STOPBAND_SWEEP_HZ
    ]
    judged = [point for point in points if point["counts_toward_verdict"]]
    control = next((point for point in points if point["role"] == "control"), None)
    statuses = [point["status"] for point in judged]
    control_ok = bool(control and control["status"] == STATUS_PASS)
    overall = _aggregate_status(statuses)
    if overall == STATUS_PASS and not control_ok:
        overall = STATUS_FAIL
    policy = next(
        (
            point.get("resampler_policy")
            for point in points
            if point.get("resampler_policy")
        ),
        None,
    )
    contract_ok = bool(
        isinstance(policy, dict) and isinstance(policy.get("ok"), bool) and policy["ok"]
    )
    return {
        "schema_version": 1,
        "criterion": "resampler_stopband_ge_80_db",
        "section": "§274.4",
        "target_rate_hz": target_rate,
        "profile": profile,
        "procedure_version": PROCEDURE_VERSION,
        "procedure_sha256": hashlib.sha256(
            PROCEDURE_DESCRIPTION.encode("utf-8")
        ).hexdigest(),
        "measurement": (
            "isolated filesrc F32LE at the decoder native rate -> audioresample "
            "with the exact §274.3 policy -> F32LE at the target rate; complex "
            "projection of the input tone and of the folded alias"
        ),
        "threshold_db": STOPBAND_MIN_REJECTION_DB,
        "points": points,
        "control_pass": control_ok,
        "resampler_contract": policy,
        "resampler_contract_ok": contract_ok,
        "status": overall,
        "reason": (
            "every isolated stopband point meets the threshold"
            if overall == STATUS_PASS
            else "at least one isolated stopband point is below the threshold"
            if overall == STATUS_FAIL
            else "the isolated sweep could not be measured"
        ),
    }


def _crossing_index(
    raw: bytes, *, channels: int, search_start: int, search_end: int
) -> float | None:
    """Interpolated first non-negative crossing inside a search window."""
    import numpy as np

    usable = len(raw) - (len(raw) % (4 * channels))
    if usable <= 0:
        return None
    signal = np.frombuffer(raw[:usable], dtype="<f4").reshape(-1, channels)[:, 0]
    signal = np.nan_to_num(signal.astype(np.float64), nan=0.0, posinf=0.0, neginf=0.0)
    first = max(1, int(search_start))
    last = min(signal.size, int(search_end))
    for index in range(first, last):
        if signal[index - 1] < 0.0 <= signal[index]:
            delta = signal[index] - signal[index - 1]
            if delta == 0.0:
                return float(index)
            return index - 1 + (-signal[index - 1]) / delta
    return None


def measure_latency(*, target_rate: int, profile: str) -> dict[str, Any]:
    """§274.5 effective decoder/resampler latency from measured step crossings.

    No documentation constant is used as runtime truth: the decoder delay, the
    isolated resampler delay and the end-to-end delay are each measured, and
    the summed projection is compared with the end-to-end measurement.
    """
    import numpy as np

    bit_count = 176_400
    transition_bit = bit_count // 2
    step_blob = _step_bits(
        level_before=-0.25,
        level_after=0.25,
        bit_count=bit_count,
        transition_bit=transition_bit,
    )
    with tempfile.TemporaryDirectory(prefix="michi-latency-") as tmp:
        path = Path(tmp) / "step.dsf"
        path.write_bytes(
            build_dsf(
                sample_count=bit_count,
                payload=_dsf_block_payload(step_blob),
            )
        )
        native = _capture_fixture(path, target_rate=DSD_NATIVE_RATE_HZ, profile=profile)
        full = _capture_fixture(path, target_rate=target_rate, profile=profile)
    native_expected = transition_bit / 8
    target_expected = transition_bit * target_rate / DSD_BIT_RATE_HZ
    native_crossing = _crossing_index(
        native["raw"],
        channels=2,
        search_start=native_expected * 0.85,
        search_end=native_expected * 1.35 + 100,
    )
    full_crossing = _crossing_index(
        full["raw"],
        channels=2,
        search_start=max(1, target_expected * 0.8),
        search_end=target_expected * 1.5 + 100,
    )

    step_frames = int(DSD_NATIVE_RATE_HZ * 0.0625)
    offsets = np.arange(step_frames)
    step_input = np.where(offsets < transition_bit / 8, -0.25, 0.25)
    step_raw = np.stack([step_input, step_input], axis=1).astype("<f4").tobytes()
    isolated = _resampler_capture(
        step_raw,
        input_rate=DSD_NATIVE_RATE_HZ,
        output_rate=target_rate,
    )
    isolated_crossing = None
    if isolated.get("status") == STATUS_PASS:
        isolated_crossing = _crossing_index(
            isolated["raw"],
            channels=2,
            search_start=max(1, target_expected * 0.8),
            search_end=target_expected * 1.5 + 100,
        )

    result: dict[str, Any] = {
        "schema_version": 1,
        "criterion": "latency_projection_error_le_1_block",
        "section": "§274.5",
        "target_rate_hz": target_rate,
        "profile": profile,
        "processing_block_frames": PROCESSING_BLOCK_FRAMES,
        "stimulus": {
            "type": "dc_step",
            "transition_bit": transition_bit,
            "level_before": -0.25,
            "level_after": 0.25,
        },
        "decoder_filter_delay_frames": None,
        "decoder_filter_delay_us": None,
        "resampler_latency_frames": None,
        "processing_latency_frames": 0,
        "dsp_nodes": [],
        "projected_total_latency_frames": None,
        "measured_total_latency_frames": None,
        "difference_frames": None,
        "status": STATUS_NOT_MEASURED,
        "reason": "",
    }
    if native_crossing is None or full_crossing is None:
        result["reason"] = "step midpoint crossing could not be located"
        return result
    if isolated_crossing is None:
        result["reason"] = (
            "isolated resampler step latency could not be measured: "
            f"{isolated.get('reason') or isolated.get('status')}"
        )
        return result
    decoder_frames = native_crossing - native_expected
    decoder_in_target = decoder_frames * target_rate / DSD_NATIVE_RATE_HZ
    resampler_frames = isolated_crossing - target_expected
    measured_total = full_crossing - target_expected
    projected_total = decoder_in_target + resampler_frames
    difference = abs(measured_total - projected_total)
    result.update(
        {
            "decoder_filter_delay_frames": decoder_frames,
            "decoder_filter_delay_us": decoder_frames / DSD_NATIVE_RATE_HZ * 1e6,
            "resampler_latency_frames": resampler_frames,
            "processing_latency_frames": 0,
            "projected_total_latency_frames": projected_total,
            "measured_total_latency_frames": measured_total,
            "difference_frames": difference,
            "isolated_resampler_eos": isolated.get("eos"),
            "isolated_resampler_sha256": isolated.get("sha256"),
        }
    )
    if difference <= PROCESSING_BLOCK_FRAMES:
        result["status"] = STATUS_PASS
        result["reason"] = (
            f"measured {measured_total:.3f} frames vs projected "
            f"{projected_total:.3f} frames; difference {difference:.3f} "
            f"<= {PROCESSING_BLOCK_FRAMES} frames"
        )
    else:
        result["status"] = STATUS_FAIL
        result["reason"] = (
            f"measured {measured_total:.3f} frames vs projected "
            f"{projected_total:.3f} frames; difference {difference:.3f} "
            f"> {PROCESSING_BLOCK_FRAMES} frames"
        )
    return result


def _profile_rate_rule(*, target_rate: int, profile: str) -> dict[str, Any]:
    try:
        payload = json.loads(PROFILE_MANIFEST.read_text(encoding="utf-8"))
        ladder = payload["profiles"][profile]["ladder_hz"]
    except (OSError, KeyError, TypeError, ValueError) as exc:
        return {
            "status": STATUS_NOT_RUN,
            "reason": f"profile manifest unavailable: {exc}",
        }
    allowed = int(target_rate) in {int(value) for value in ladder}
    return {
        "status": STATUS_PASS if allowed else STATUS_FAIL,
        "profile": profile,
        "target_rate_hz": target_rate,
        "ladder_hz": list(ladder),
        "reason": (
            "target rate belongs to the profile ladder"
            if allowed
            else "target rate is outside the profile ladder"
        ),
    }


def _profile_matrix(
    *, executed_profile: str, target_rate: int, certified: bool, worst: str
) -> dict[str, Any]:
    try:
        payload = json.loads(PROFILE_MANIFEST.read_text(encoding="utf-8"))
        profiles = payload["profiles"]
    except (OSError, KeyError, TypeError, ValueError) as exc:
        return {
            "status": STATUS_NOT_RUN,
            "reason": f"profile manifest unavailable: {exc}",
        }
    matrix: dict[str, Any] = {}
    for name in PROFILE_NAMES:
        profile_payload = profiles.get(name) or {}
        rates: dict[str, Any] = {}
        for rate in profile_payload.get("ladder_hz", []):
            rate = int(rate)
            if name == executed_profile and rate == target_rate:
                status = STATUS_PASS if certified else worst
                reason = "measured by this corpus run"
            elif rate > DSD_NATIVE_RATE_HZ:
                status = "UNAVAILABLE"
                reason = (
                    f"rate {rate} exceeds the DSD64 decoder native rate "
                    f"{DSD_NATIVE_RATE_HZ}"
                )
            else:
                status = "CONDITIONAL"
                reason = "not executed by this corpus run; no inferred qualification"
            rates[str(rate)] = {"status": status, "reason": reason}
        matrix[name] = {
            "purpose": profile_payload.get("purpose"),
            "rates": rates,
            "qualified": name == executed_profile and certified,
        }
    return matrix


def _requirement(
    *,
    requirement_id: str,
    section: str,
    threshold: str,
    status: str,
    measured: Any,
    evidence: list[str],
    reason: str,
    mandatory: bool = True,
) -> dict[str, Any]:
    if status not in CRITERION_STATUSES:
        raise ValueError(f"unknown criterion status {status!r}")
    return {
        "id": requirement_id,
        "section": section,
        "threshold": threshold,
        "status": status,
        "measured": measured,
        "evidence": evidence,
        "reason": reason,
        "mandatory": mandatory,
    }


def _collect(vectors: list[dict[str, Any]], key: str) -> list[str]:
    return [
        vector["numeric_checks"][key]
        for vector in vectors
        if key in vector["numeric_checks"]
    ]


def _evidence_names(vectors: list[dict[str, Any]], key: str) -> list[str]:
    return [
        str(vector.get("fixture", {}).get("name"))
        for vector in vectors
        if key in vector["numeric_checks"]
    ]


def _build_requirements(
    *,
    vectors: list[dict[str, Any]],
    sweep: dict[str, Any],
    latency: dict[str, Any],
    target_rate: int,
) -> list[dict[str, Any]]:
    mandatory: list[dict[str, Any]] = []
    f32le_ok = all(
        vector.get("backend", {}).get("output_format") == F32LE
        and F32LE in (vector.get("caps_negotiated") or "")
        for vector in vectors
    )
    mandatory.append(
        _requirement(
            requirement_id="numeric_type_f32le",
            section="§274.4",
            threshold="PCM numeric type after decoder = F32LE",
            status=STATUS_PASS if f32le_ok else STATUS_FAIL,
            measured=f32le_ok,
            evidence=[str(vector.get("fixture", {}).get("name")) for vector in vectors],
            reason=(
                "every capture negotiated F32LE"
                if f32le_ok
                else "at least one capture did not negotiate F32LE"
            ),
        )
    )
    for key, section, threshold in (
        ("nan_inf_zero", "§274.4", "NaN/Inf = 0"),
        ("no_unexpected_clipping", "§274.4", "unexpected clipping = 0 samples"),
        ("eos_observed", "§275.4", "capture reaches EOS"),
        (
            "inter_channel_gain_le_0_01_db",
            "§274.4",
            "inter-channel gain mismatch <= 0.01 dB",
        ),
        (
            "inter_channel_latency_zero_samples",
            "§274.4",
            "inter-channel latency mismatch = 0 samples",
        ),
    ):
        values = _collect(vectors, key)
        mandatory.append(
            _requirement(
                requirement_id=key,
                section=section,
                threshold=threshold,
                status=_aggregate_status(values),
                measured=sorted(set(values)),
                evidence=_evidence_names(vectors, key),
                reason=(
                    "all measured vectors pass"
                    if _aggregate_status(values) == STATUS_PASS
                    else "criterion not demonstrated on every applicable vector"
                ),
            )
        )

    dc_vectors = [
        vector
        for vector in vectors
        if "dc_gain_error_le_0_05_db" in vector["numeric_checks"]
    ]
    dc_values = _collect(dc_vectors, "dc_gain_error_le_0_05_db")
    mandatory.append(
        _requirement(
            requirement_id="dc_gain_error_le_0_05_db",
            section="§274.4",
            threshold="DC gain error <= 0.05 dB vs versioned reference",
            status=_aggregate_status(dc_values),
            measured=[
                {
                    "stimulus": vector["fixture"].get("analytic_dc_level"),
                    "measured_dc_offset": vector.get("dc", {}).get(
                        "measured_dc_offset"
                    ),
                    "reference_dc_offset": vector.get("dc", {}).get(
                        "reference_dc_offset"
                    ),
                    "dc_gain_error_db": vector.get("dc", {}).get("dc_gain_error_db"),
                }
                for vector in dc_vectors
            ]
            or None,
            evidence=[str(vector["fixture"].get("name")) for vector in dc_vectors],
            reason=(
                dc_vectors[0].get("dc", {}).get("reason", "no DC stimulus")
                if dc_vectors
                else "no DC stimulus vector was executed"
            ),
        )
    )

    passband_values = []
    passband_evidence = []
    high_band_values = []
    high_band_evidence = []
    for vector in vectors:
        name = str(vector.get("fixture", {}).get("name"))
        checks = vector["numeric_checks"]
        if "magnitude_error_le_0_10_db" in checks:
            passband_values.append(checks["magnitude_error_le_0_10_db"])
            passband_evidence.append(name)
        if "magnitude_error_le_0_25_db" in checks:
            high_band_values.append(checks["magnitude_error_le_0_25_db"])
            high_band_evidence.append(name)
    mandatory.append(
        _requirement(
            requirement_id="magnitude_error_le_0_10_db",
            section="§274.4",
            threshold="20 Hz..20 kHz magnitude error <= 0.10 dB vs reference",
            status=_aggregate_status(passband_values),
            measured={
                str(vector["fixture"].get("name")): vector["tone_metrics"].get(
                    "magnitude_error_vs_reference_db"
                )
                for vector in vectors
                if "magnitude_error_le_0_10_db" in vector["numeric_checks"]
            },
            evidence=passband_evidence,
            reason=(
                "every 20 Hz..20 kHz point is within 0.10 dB of the reference"
                if _aggregate_status(passband_values) == STATUS_PASS
                else "at least one 20 Hz..20 kHz point is unmeasured or out of bound"
            ),
        )
    )
    nyquist_hz = target_rate / 2
    if nyquist_hz <= 20_000:
        high_band_status = STATUS_NOT_APPLICABLE
        high_band_reason = (
            f"target Nyquist {nyquist_hz:.0f} Hz does not permit 20-40 kHz"
        )
    else:
        high_band_status = _aggregate_status(high_band_values)
        high_band_reason = (
            "every 20-40 kHz point is within 0.25 dB of the reference"
            if high_band_status == STATUS_PASS
            else "at least one 20-40 kHz point is unmeasured or out of bound"
        )
    mandatory.append(
        _requirement(
            requirement_id="magnitude_error_le_0_25_db",
            section="§274.4",
            threshold=(
                "20 kHz..40 kHz magnitude error <= 0.25 dB when Nyquist permits"
            ),
            status=high_band_status,
            measured={
                str(vector["fixture"].get("name")): vector["tone_metrics"].get(
                    "magnitude_error_vs_reference_db"
                )
                for vector in vectors
                if "magnitude_error_le_0_25_db" in vector["numeric_checks"]
            },
            evidence=high_band_evidence,
            reason=high_band_reason,
        )
    )
    mandatory.append(
        _requirement(
            requirement_id="resampler_stopband_ge_80_db",
            section="§274.4",
            threshold="added resampler stopband rejection >= 80 dB (isolated)",
            status=sweep.get("status", STATUS_NOT_RUN),
            measured={
                str(point["stimulus_hz"]): point.get("rejection_db")
                for point in sweep.get("points", [])
            },
            evidence=[
                f"isolated_resampler:{point['stimulus_hz']}Hz"
                for point in sweep.get("points", [])
                if point.get("counts_toward_verdict")
            ],
            reason=sweep.get("reason", "isolated sweep not executed"),
        )
    )
    mandatory.append(
        _requirement(
            requirement_id="resampler_contract_exact",
            section="§274.3",
            threshold="quality=10, kaiser, full, none with exact readback",
            status=(
                STATUS_PASS
                if sweep.get("resampler_contract_ok")
                else STATUS_NOT_MEASURED
                if sweep.get("status") == STATUS_NOT_RUN
                else STATUS_FAIL
            ),
            measured=sweep.get("resampler_contract"),
            evidence=["isolated_resampler_contract"],
            reason=(
                "the exact §274.3 resampler policy was read back"
                if sweep.get("resampler_contract_ok")
                else "the exact §274.3 resampler policy could not be confirmed"
            ),
        )
    )
    mandatory.append(
        _requirement(
            requirement_id="latency_projection_error_le_1_block",
            section="§274.5",
            threshold="measured vs projected total latency <= 1 processing block",
            status=latency.get("status", STATUS_NOT_RUN),
            measured={
                "decoder_filter_delay_us": latency.get("decoder_filter_delay_us"),
                "resampler_latency_frames": latency.get("resampler_latency_frames"),
                "measured_total_latency_frames": latency.get(
                    "measured_total_latency_frames"
                ),
                "projected_total_latency_frames": latency.get(
                    "projected_total_latency_frames"
                ),
                "difference_frames": latency.get("difference_frames"),
            },
            evidence=["dc_step_latency"],
            reason=latency.get("reason", "latency not measured"),
        )
    )
    return mandatory


def run_corpus(*, target_rate: int, profile: str) -> dict[str, Any]:
    vectors = []
    with tempfile.TemporaryDirectory(prefix="michi-dsd2pcm-corpus-") as tmp:
        for spec in CORPUS_SPECS:
            path = Path(tmp) / f"{spec.name}.dsf"
            if spec.kind == "dc":
                path.write_bytes(
                    _dsf_dc_blob(
                        sample_count=spec.sample_count,
                        level=float(spec.expected_dc),
                    )
                )
            elif spec.expect_inverted:
                path.write_bytes(
                    _dsf_stereo_tone_blob(
                        sample_count=spec.sample_count,
                        left_frequency_hz=spec.frequency_hz,
                        right_frequency_hz=spec.frequency_hz,
                        right_polarity=-1.0,
                    )
                )
            else:
                path.write_bytes(
                    _dsf_blob(
                        sample_count=spec.sample_count,
                        frequency_hz=spec.frequency_hz,
                    )
                )
            vectors.append(
                run(
                    fixture=path,
                    target_rate=target_rate,
                    profile=profile,
                    expected_frequency_hz=(
                        0
                        if spec.stopband_hz or spec.kind in {"silence", "dc"}
                        else spec.frequency_hz
                    ),
                    fixture_name=spec.name,
                    stopband_hz=spec.stopband_hz,
                    expected_dc=spec.expected_dc,
                    expect_inverted=spec.expect_inverted,
                )
            )
    for vector in vectors:
        # Generated fixtures live in a temporary directory; the SHA256 and the
        # fixture name are the reproducible identity, not the temp path.
        vector["fixture"]["path"] = None
    sweep = run_stopband_sweep(target_rate=target_rate, profile=profile)
    latency = measure_latency(target_rate=target_rate, profile=profile)
    requirements = _build_requirements(
        vectors=vectors,
        sweep=sweep,
        latency=latency,
        target_rate=target_rate,
    )
    mandatory = [item for item in requirements if item["mandatory"]]
    blocked = [item["id"] for item in mandatory if item["status"] != STATUS_PASS]
    certified = not blocked
    if any(item["status"] == STATUS_FAIL for item in mandatory):
        status = STATUS_FAIL
    elif certified:
        status = STATUS_PASS
    else:
        status = "PARTIAL"
    rate_rule = _profile_rate_rule(target_rate=target_rate, profile=profile)
    if rate_rule["status"] != STATUS_PASS and certified:
        certified = False
        blocked = [*blocked, "profile_rate_ladder"]
        status = STATUS_FAIL if rate_rule["status"] == STATUS_FAIL else "PARTIAL"
    worst = (
        STATUS_FAIL
        if STATUS_FAIL in {item["status"] for item in mandatory}
        else "PARTIAL"
    )
    return {
        "schema_version": 2,
        "phase": "AP2-F10",
        "corpus": "dsd64_v3",
        "target_rate_hz": target_rate,
        "profile": profile,
        "profile_rules": rate_rule,
        "procedure": {
            "version": PROCEDURE_VERSION,
            "sha256": hashlib.sha256(PROCEDURE_DESCRIPTION.encode("utf-8")).hexdigest(),
            "description": PROCEDURE_DESCRIPTION,
            "ffmpeg": _ffmpeg_version(shutil.which("ffmpeg") or "ffmpeg"),
        },
        "vectors": vectors,
        "stopband_sweep": sweep,
        "latency": latency,
        "requirements": requirements,
        "certification": {
            "flag": "CERTIFIED" if certified else "NOT_CERTIFIED",
            "certified": certified,
            "blocked_by": blocked,
            "scope": {
                "corpus": "dsd64_v3",
                "profile": profile,
                "target_rate_hz": target_rate,
                "decoder": "avdec_dsd_lsbf",
                "output_format": F32LE,
                "sink": "fakesink",
                "bit_order": "LSBF",
                "channels": 2,
                "physical_device": None,
                "note": ("lab supervised host path only; no physical DAC claim"),
            },
            "profiles": _profile_matrix(
                executed_profile=profile,
                target_rate=target_rate,
                certified=certified,
                worst=worst,
            ),
        },
        "status": status,
        "environment": {"python": "3.11", "sink": "fakesink"},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--target-rate", type=int, default=88_200)
    parser.add_argument("--profile", default="FAST")
    parser.add_argument("--json", type=Path)
    parser.add_argument("--corpus", action="store_true")
    parser.add_argument("--stopband-sweep", action="store_true")
    parser.add_argument("--latency", action="store_true")
    args = parser.parse_args()
    if args.stopband_sweep:
        result = run_stopband_sweep(target_rate=args.target_rate, profile=args.profile)
    elif args.latency:
        result = measure_latency(target_rate=args.target_rate, profile=args.profile)
    elif args.corpus:
        result = run_corpus(target_rate=args.target_rate, profile=args.profile)
    else:
        result = run(
            fixture=args.fixture,
            target_rate=args.target_rate,
            profile=args.profile,
        )
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.json is not None:
        args.json.write_text(text + "\n", encoding="utf-8")
    print(text)
    if args.corpus:
        return 0 if result["certification"]["certified"] else 1
    if args.stopband_sweep or args.latency:
        return 0 if result["status"] == STATUS_PASS else 1
    complete = (
        result["sample_count"] > 0
        and result["cleanup_confirmed"]
        and result["eos_observed"]
    )
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
