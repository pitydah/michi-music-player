"""AP2-F10 C7 — reproducible DSD64 conformance corpus generation."""

from __future__ import annotations

import hashlib
import math

import pytest

pytest.importorskip("numpy")

from tools.audio_phase2.dsd2pcm_conformance import (  # noqa: E402
    CORPUS_SAMPLE_COUNT,
    DSD64_CORPUS,
    _tone_bits,
    _tone_payload,
)


@pytest.mark.parametrize(("name", "frequency"), DSD64_CORPUS)
def test_corpus_vector_is_deterministic_and_block_interleaved(
    name: str, frequency: int
) -> None:
    first = _tone_payload(sample_count=CORPUS_SAMPLE_COUNT, frequency_hz=frequency)
    second = _tone_payload(sample_count=CORPUS_SAMPLE_COUNT, frequency_hz=frequency)
    assert first == second
    assert len(first) % 8192 == 0
    assert hashlib.sha256(first).hexdigest() == hashlib.sha256(second).hexdigest()


def test_corpus_vectors_are_distinct() -> None:
    hashes = {
        hashlib.sha256(
            _tone_payload(sample_count=CORPUS_SAMPLE_COUNT, frequency_hz=frequency)
        ).hexdigest()
        for _name, frequency in DSD64_CORPUS
    }
    assert len(hashes) == len(DSD64_CORPUS)


@pytest.mark.parametrize(
    ("name", "frequency"),
    [(name, frequency) for name, frequency in DSD64_CORPUS[1:] if frequency <= 20_000],
)
def test_modulator_produces_the_requested_analytic_tone(
    name: str, frequency: int
) -> None:
    """Independent oracle: decimate the 1-bit stream and find the tone."""
    import numpy as np

    bit_count = 282_240
    raw = _tone_bits(frequency_hz=frequency, bit_count=bit_count)
    bits = np.unpackbits(np.frombuffer(raw, dtype=np.uint8), bitorder="little").astype(
        np.float64
    )
    samples = bits * 2.0 - 1.0
    decimated = samples[: (samples.size // 64) * 64].reshape(-1, 64).mean(axis=1)
    window = np.hanning(decimated.size)
    spectrum = np.abs(np.fft.rfft(decimated * window)) / (window.sum() / 2.0)
    freqs = np.fft.rfftfreq(decimated.size, 1.0 / 44_100.0)
    peak = float(freqs[int(np.argmax(spectrum[1:]) + 1)])
    amplitude = float(np.max(spectrum[1:]))
    # The boxcar decimator has a known sinc droop; compensate analytically.
    ratio = math.pi * frequency / 44_100.0
    decimator_gain = abs(math.sin(ratio) / ratio)
    expected = 0.5 * decimator_gain
    assert abs(peak - frequency) <= 20.0
    assert abs(20.0 * math.log10(amplitude / expected)) <= 0.10


@pytest.mark.parametrize(
    ("_name", "frequency"),
    [(name, frequency) for name, frequency in DSD64_CORPUS if frequency > 20_000],
)
def test_high_frequency_vectors_are_well_formed(_name: str, frequency: int) -> None:
    """The naive 44.1 kHz decimator aliases above 22.05 kHz; the production
    harness measures those vectors against the ffmpeg reference instead."""
    raw = _tone_payload(sample_count=CORPUS_SAMPLE_COUNT, frequency_hz=frequency)
    assert len(raw) % 8192 == 0
    assert len(raw) >= CORPUS_SAMPLE_COUNT * 2
    assert raw != bytes(len(raw))
