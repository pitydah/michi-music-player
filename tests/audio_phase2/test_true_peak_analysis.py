"""AP2-F06 — corrected true-peak estimator + multichannel capture analysis.

Pure numerical tests (no Gst): the estimator has NO heuristic pruning, and the
capture analysis is per channel. A high-resolution reference (32x/32-tap) is
implemented independently here for offline comparison only.
"""

from __future__ import annotations

import array
import math

import pytest

from michi.infrastructure.audio_engines.gstreamer import GStreamerAudioPort

RATE = 44100


def _samples(values):
    return [float(value) for value in values]


def _tone(freq, amplitude=0.9, phase=0.0, count=64, rate=RATE):
    return [
        amplitude * math.sin(2 * math.pi * freq * index / rate + phase)
        for index in range(count)
    ]


def _old_pruned_estimate(samples, factor=4, half_taps=8):
    """Simulation of the REMOVED heuristic (pruning by neighbor*1.25)."""
    best = max(abs(value) for value in samples)
    count = len(samples)
    for index in range(count - 1):
        neighbor = max(abs(samples[index]), abs(samples[index + 1]))
        if neighbor * 1.25 <= best:
            continue
        for step in range(1, factor):
            fraction = step / factor
            total = 0.0
            for tap in range(-half_taps + 1, half_taps + 1):
                position = index + tap
                if 0 <= position < count:
                    x = fraction - tap
                    weight = (
                        1.0
                        if abs(x) < 1e-9
                        else (math.sin(math.pi * x) / (math.pi * x))
                        * (0.5 + 0.5 * math.cos(math.pi * x / half_taps))
                    )
                    total += samples[position] * weight
            best = max(best, abs(total))
    return best


def _reference_estimate(samples, factor=32, half_taps=32):
    """Independent higher-resolution reference (test-only)."""
    best = max(abs(value) for value in samples)
    count = len(samples)
    for index in range(count - 1):
        for step in range(1, factor):
            fraction = step / factor
            total = 0.0
            for tap in range(-half_taps + 1, half_taps + 1):
                position = index + tap
                if 0 <= position < count:
                    x = fraction - tap
                    weight = (
                        1.0 if abs(x) < 1e-9 else math.sin(math.pi * x) / (math.pi * x)
                    )
                    total += samples[position] * weight
            best = max(best, abs(total))
    return best


def test_fs4_phase_separates_sample_peak_from_true_peak() -> None:
    samples = _tone(RATE / 4.0, amplitude=0.9, phase=math.pi / 4.0)
    result = GStreamerAudioPort._true_peak_metrics(samples)
    sample_peak = max(abs(value) for value in samples)
    assert sample_peak == pytest.approx(0.636, abs=0.02)
    assert result["estimated_true_peak"] == pytest.approx(0.9, abs=0.06)
    assert result["estimated_true_peak"] > sample_peak + 0.2
    assert result["true_peak_method"] == "windowed_sinc_4x"
    assert result["oversampling_factor"] == 4
    assert result["analysis_window"] == len(samples)
    assert result["measurement_scope"] == "bounded_window_estimate"
    assert result["intersample_over_full_scale"] is False


def test_pruning_heuristic_is_gone_and_no_longer_hides_a_peak() -> None:
    """Deterministic counterexample found against the old pruning.

    Components normalized to 0.9 sample peak: the old estimator reported
    ~0.9568 while the unpruned 4x estimator finds ~1.0466 (an intersample
    peak above 0 dBFS).
    """
    components = (
        (19910.386036729422, 2.4807491916553555, 0.06931456945072495),
        (17264.632702618343, 0.5914364964796116, 0.2831152023613421),
        (19112.814919690838, 1.3489884553048155, 0.08437889347566868),
        (8839.797963648873, 1.5121302263798826, 0.2704189015165543),
    )
    count = 48
    raw = [
        sum(
            amplitude * math.sin(2 * math.pi * freq * index / RATE + phase)
            for freq, phase, amplitude in components
        )
        for index in range(count)
    ]
    peak = max(abs(value) for value in raw)
    samples = [value / peak * 0.9 for value in raw]

    old = _old_pruned_estimate(samples)
    new = GStreamerAudioPort._true_peak_metrics(samples)["estimated_true_peak"]
    reference = _reference_estimate(samples)

    assert new == pytest.approx(1.0466, abs=0.01), (new, old, reference)
    assert new > old + 0.05, (new, old)
    assert new <= reference + 0.05, (new, reference)
    result = GStreamerAudioPort._true_peak_metrics(samples)
    assert result["intersample_over_full_scale"] is True


@pytest.mark.parametrize(
    "signal",
    [
        _tone(1000.0, amplitude=0.5),
        _tone(18000.0, amplitude=0.5, phase=0.7),
        [value * -1.0 for value in _tone(1000.0, amplitude=0.5)],
        [
            _tone(1000.0, amplitude=0.3)[index]
            + _tone(15000.0, amplitude=0.3, phase=0.9)[index]
            for index in range(64)
        ],
    ],
)
def test_estimate_is_never_below_sample_peak_and_matches_reference_scale(
    signal,
) -> None:
    result = GStreamerAudioPort._true_peak_metrics(signal)
    reference = _reference_estimate(signal)
    sample_peak = max(abs(value) for value in signal)
    assert result["estimated_true_peak"] >= sample_peak - 1e-12
    assert result["estimated_true_peak"] <= reference + 0.06
    assert result["estimated_true_peak"] >= reference - 0.12


def test_silence_and_degenerate_windows_are_honest() -> None:
    silence = GStreamerAudioPort._true_peak_metrics([0.0] * 32)
    assert silence["estimated_true_peak"] == 0.0
    assert silence["true_peak_db"] is None
    assert silence["intersample_over_full_scale"] is False

    for bad in ([], [0.5], [math.nan, 0.1] * 8, [math.inf, 0.1] * 8):
        result = GStreamerAudioPort._true_peak_metrics(bad)
        assert result["estimated_true_peak"] is None
        assert result["intersample_over_full_scale"] is None


def _chunk(typecode, divisor, channels, values) -> tuple:
    data = array.array(typecode, values).tobytes()
    return (typecode, float(divisor), channels, data)


def test_multichannel_analysis_identifies_the_worst_channel() -> None:
    # Right channel is louder: the aggregate must be driven by channel 1.
    frames = [(int(round(0.5 * 32767)), int(round(0.9 * 32767))) for _ in range(64)]
    values = [value for frame in frames for value in frame]
    analysis = GStreamerAudioPort._analyze_capture([_chunk("h", 32768.0, 2, values)])
    channels = analysis["channels_metrics"]
    assert len(channels) == 2
    assert channels[0]["sample_peak"] == pytest.approx(0.5, abs=0.01)
    assert channels[1]["sample_peak"] == pytest.approx(0.9, abs=0.01)
    assert analysis["worst_channel"] == 1
    assert analysis["sample_peak"] == pytest.approx(0.9, abs=0.01)
    assert analysis["rms"] == pytest.approx(
        math.sqrt((0.5**2 + 0.9**2) / 2.0), abs=0.01
    )
    assert analysis["samples_analyzed"] == 128


def test_right_channel_only_over_full_scale_is_detected() -> None:
    values = []
    for _ in range(32):
        values.extend((0.5, 1.2))
    analysis = GStreamerAudioPort._analyze_capture([_chunk("f", 1.0, 2, values)])
    left, right = analysis["channels_metrics"]
    assert left["samples_over_full_scale"] == 0
    assert right["samples_over_full_scale"] == 32
    assert analysis["exceeds_full_scale"] is True
    assert analysis["worst_channel"] == 1


def test_four_channel_analysis_is_per_channel() -> None:
    amplitudes = (0.1, 0.4, 0.8, 0.6)
    values = []
    for _ in range(16):
        values.extend(amplitudes)
    analysis = GStreamerAudioPort._analyze_capture([_chunk("f", 1.0, 4, values)])
    assert analysis["channels_analyzed"] == 4
    peaks = [entry["sample_peak"] for entry in analysis["channels_metrics"]]
    assert peaks == pytest.approx(list(amplitudes), abs=1e-6)
    assert analysis["worst_channel"] == 2
    assert analysis["sample_peak"] == pytest.approx(0.8, abs=1e-6)


def test_partial_frame_bytes_are_ignored_and_counted() -> None:
    values = array.array("h", [1000, -1000, 2000, -2000, 3000]).tobytes()
    analysis = GStreamerAudioPort._analyze_capture([("h", 32768.0, 2, values)])
    assert analysis["frames_analyzed"] == 2
    assert analysis["samples_analyzed"] == 4
    assert analysis["partial_bytes_ignored"] == 2


def test_mid_capture_layout_change_is_not_mixed() -> None:
    stereo = []
    for _ in range(8):
        stereo.extend((0.2, 0.2))
    mono = [0.9] * 8
    analysis = GStreamerAudioPort._analyze_capture(
        [
            _chunk("f", 1.0, 2, stereo),
            _chunk("f", 1.0, 1, mono),
        ]
    )
    assert analysis["channels_analyzed"] == 2
    assert analysis["frames_analyzed"] == 8
    assert analysis["channels_metrics"][0]["sample_peak"] == pytest.approx(0.2)
    assert analysis["worst_channel"] == 0


def test_non_finite_and_silence_are_counted_not_averaged() -> None:
    values = [0.5, 0.5, math.nan, 0.5, 0.5, math.inf, 0.5, 0.5]
    analysis = GStreamerAudioPort._analyze_capture([_chunk("f", 1.0, 2, values)])
    assert analysis["non_finite_samples"] == 2
    assert analysis["channels_metrics"][0]["samples_analyzed"] == 3
    assert analysis["channels_metrics"][1]["samples_analyzed"] == 3
    assert analysis["rms"] == pytest.approx(0.5)

    silence = GStreamerAudioPort._analyze_capture([_chunk("f", 1.0, 2, [0.0] * 16)])
    assert silence["sample_peak"] == 0.0
    assert silence["headroom_db"] is None
    assert silence["estimated_true_peak"] == 0.0


def test_float64_chunks_and_per_channel_true_peak() -> None:
    quarter = _tone(RATE / 4.0, amplitude=0.9, phase=math.pi / 4.0, count=64)
    values = []
    for value in quarter:
        values.extend((value, value))
    analysis = GStreamerAudioPort._analyze_capture([_chunk("d", 1.0, 2, values)])
    channels = analysis["channels_metrics"]
    for channel in channels:
        assert channel["sample_peak"] == pytest.approx(0.636, abs=0.02)
        assert channel["estimated_true_peak"] == pytest.approx(0.9, abs=0.06)
        assert channel["intersample_over_full_scale"] is False
    assert analysis["estimated_true_peak"] == pytest.approx(0.9, abs=0.06)


def _finalize(
    chunks,
    *,
    frames=None,
    dropped=0,
    mismatch=0,
    unsupported=0,
    rate_changes=0,
    format_changes=0,
):
    analysis = GStreamerAudioPort._analyze_capture(chunks)
    captured = {
        "frames": analysis["frames_analyzed"] if frames is None else frames,
        "dropped": dropped,
        "channel_mismatch": mismatch,
        "channel_count": analysis["channels_analyzed"],
        "buffers_observed": 1,
        "buffers_accepted": 0 if unsupported else 1,
        "buffers_unsupported": unsupported,
        "rate_changes": rate_changes,
        "format_changes": format_changes,
    }
    return GStreamerAudioPort._finalize_capture(
        GStreamerAudioPort._analyze_capture, chunks, captured
    )


def _counterexample_signal(sample_peak: float, count: int = 48):
    components = (
        (19910.386036729422, 2.4807491916553555, 0.06931456945072495),
        (17264.632702618343, 0.5914364964796116, 0.2831152023613421),
        (19112.814919690838, 1.3489884553048155, 0.08437889347566868),
        (8839.797963648873, 1.5121302263798826, 0.2704189015165543),
    )
    raw = [
        sum(
            amplitude * math.sin(2 * math.pi * freq * index / RATE + phase)
            for freq, phase, amplitude in components
        )
        for index in range(count)
    ]
    peak = max(abs(value) for value in raw)
    return [value / peak * sample_peak for value in raw]


def test_worst_sample_peak_and_true_peak_channels_are_distinct() -> None:
    # L: highest SAMPLE peak (0.9, fs/4 at 0 deg -> true peak also 0.9).
    left = _tone(RATE / 4.0, amplitude=0.9, phase=0.0, count=48)
    # R: lower sample peak (0.85) but a higher TRUE peak (~0.99).
    right = _counterexample_signal(0.85)
    assert max(abs(value) for value in right) < 0.9
    values = []
    for l_value, r_value in zip(left, right, strict=True):
        values.extend((l_value, r_value))
    analysis = _finalize([_chunk("d", 1.0, 2, values)])
    assert analysis["worst_sample_peak_channel"] == 0
    assert analysis["worst_true_peak_channel"] == 1
    assert analysis["channels_with_valid_true_peak"] == 2
    right_true_peak = analysis["channels_metrics"][1]["estimated_true_peak"]
    assert right_true_peak > analysis["channels_metrics"][0]["estimated_true_peak"]
    assert analysis["estimated_true_peak"] == pytest.approx(right_true_peak)
    assert analysis["true_peak_db"] == pytest.approx(
        round(20.0 * math.log10(right_true_peak), 3), abs=1e-9
    )
    assert analysis["capture_completeness"] == "complete"
    assert analysis["clipping_assessment"] == "no_clipping_observed"


def test_invalid_true_peak_channel_keeps_unknown_and_partial_completeness() -> None:
    left = _tone(1000.0, amplitude=0.5, count=32)
    values = []
    for value in left:
        values.extend((value, math.nan))
    analysis = _finalize([_chunk("d", 1.0, 2, values)])
    assert analysis["channels_with_valid_true_peak"] == 1
    assert analysis["channels_metrics"][1]["estimated_true_peak"] is None
    assert analysis["estimated_true_peak"] is not None
    assert analysis["capture_completeness"] == "partial"
    assert analysis["clipping_assessment"] == "unknown"


def test_truncated_capture_never_claims_absence_of_clipping() -> None:
    values = [0.2, 0.2] * 32
    analysis = _finalize([_chunk("f", 1.0, 2, values)], frames=100, dropped=36)
    assert analysis["capture_completeness"] == "partial"
    assert analysis["clipping_assessment"] == "unknown"


def test_over_full_scale_is_reported_as_detected_clipping() -> None:
    values = [0.5, 1.2] * 16
    analysis = _finalize([_chunk("f", 1.0, 2, values)])
    assert analysis["clipping_assessment"] == "clipping_detected"
    assert analysis["channels_metrics"][1]["samples_over_full_scale"] == 16
    assert analysis["capture_completeness"] == "complete"


def test_no_samples_yields_unavailable_not_zero_claim() -> None:
    analysis = _finalize([])
    assert analysis["capture_completeness"] == "unavailable"
    assert analysis["clipping_assessment"] == "unknown"
    assert analysis["estimated_true_peak"] is None


def test_rejected_buffers_always_remove_complete_coverage() -> None:
    values = [0.2, 0.2] * 16
    for kwargs in (
        {"unsupported": 1},
        {"rate_changes": 1},
        {"format_changes": 1},
        {"dropped": 16},
        {"mismatch": 1},
    ):
        analysis = _finalize([_chunk("f", 1.0, 2, values)], **kwargs)
        assert analysis["capture_completeness"] == "partial", kwargs
        assert analysis["clipping_assessment"] == "unknown", kwargs
    clean = _finalize([_chunk("f", 1.0, 2, values)])
    assert clean["capture_completeness"] == "complete"
    assert clean["buffers_observed"] == 1
    assert clean["buffers_unsupported"] == 0


def test_s24_packed_samples_are_decoded_per_channel() -> None:
    def s24(value: float) -> bytes:
        raw = int(round(value * (1 << 23)))
        return (raw & 0xFFFFFF).to_bytes(3, "little")

    data = bytearray()
    for _ in range(8):
        data += s24(0.5) + s24(-0.25)
    analysis = GStreamerAudioPort._analyze_capture(
        [("S24", float(1 << 23), 2, bytes(data))]
    )
    channels = analysis["channels_metrics"]
    assert channels[0]["sample_peak"] == pytest.approx(0.5, abs=1e-6)
    assert channels[1]["sample_peak"] == pytest.approx(0.25, abs=1e-6)
    assert analysis["worst_sample_peak_channel"] == 0
    assert analysis["samples_analyzed"] == 16
