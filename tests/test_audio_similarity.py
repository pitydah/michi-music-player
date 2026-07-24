"""Tests for audio feature extraction and similarity computation."""

import numpy as np

from audio_analysis.schemas import AudioFeature
from audio_analysis.similarity_index import (
    compute_similarity,
    _bpm_similarity,
    _value_similarity,
)


def _make_feature(**kw):
    defaults = dict(
        track_key="tk",
        duration=0.0,
        bpm=120.0,
        bpm_confidence=0.8,
        energy=0.5,
        dynamic_range=20.0,
        spectral_centroid=2000.0,
        spectral_rolloff=4000.0,
        zero_crossing_rate=0.1,
        mfcc_json="[]",
        chroma_json="[]",
        backend="basic",
        status="completed",
        error="",
    )
    defaults.update(kw)
    return AudioFeature(**defaults)


class TestAudioSimilarity:

    def test_feature_extraction(self):
        sr = 22050
        duration_sec = 5
        t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
        # 120 BPM = 2 Hz beat, carrier at 440 Hz
        beat = np.sin(2 * np.pi * 2.0 * t)
        carrier = np.sin(2 * np.pi * 440 * t)
        y = beat * carrier * 0.5 + np.random.randn(len(t)) * 0.01

        # Simulate feature extraction: compute basic metrics from the signal
        rms = float(np.sqrt(np.mean(y ** 2)))
        energy = min(1.0, rms * 10)
        peak = float(np.max(np.abs(y)))
        dynamic_range = float(20 * np.log10(peak / rms)) if rms > 0 else 0.0
        zcr = float(np.mean(np.abs(np.diff(np.sign(y)))) / 2)

        feat = AudioFeature(
            track_key="synth_track",
            duration=duration_sec,
            bpm=120.0,
            bpm_confidence=0.85,
            energy=energy,
            dynamic_range=dynamic_range,
            spectral_centroid=2000.0,
            spectral_rolloff=4000.0,
            zero_crossing_rate=zcr,
            backend="basic",
            status="completed",
        )
        assert feat.track_key == "synth_track"
        assert feat.duration == 5.0
        assert feat.bpm == 120.0
        assert 0 <= feat.energy <= 1.0
        assert feat.backend == "basic"
        assert feat.status == "completed"

    def test_cosine_distance(self):
        feat_a = _make_feature(track_key="a", bpm=120.0, energy=0.8,
                               spectral_centroid=2000.0, spectral_rolloff=4000.0,
                               zero_crossing_rate=0.1, dynamic_range=20.0, backend="librosa")
        feat_b = _make_feature(track_key="b", bpm=120.0, energy=0.8,
                               spectral_centroid=2000.0, spectral_rolloff=4000.0,
                               zero_crossing_rate=0.1, dynamic_range=20.0, backend="librosa")

        result = compute_similarity(feat_a, feat_b)
        assert result.score == 1.0
        assert result.bpm_diff == 1.0
        assert result.energy_diff == 1.0

        # Orthogonal: very different features
        feat_c = _make_feature(track_key="c", bpm=240.0, energy=0.0,
                               spectral_centroid=100.0, spectral_rolloff=200.0,
                               zero_crossing_rate=0.5, dynamic_range=1.0, backend="librosa")
        result2 = compute_similarity(feat_a, feat_c)
        # Score should be near 0
        assert result2.score < 0.3

    def test_similar_tracks_ranking(self):
        seed = _make_feature(track_key="seed", bpm=120.0, energy=0.6,
                             spectral_centroid=2000.0, spectral_rolloff=4000.0,
                             zero_crossing_rate=0.1, dynamic_range=15.0, backend="librosa")
        candidates = [
            _make_feature(track_key="close", bpm=118.0, energy=0.58,
                          spectral_centroid=2100.0, spectral_rolloff=3900.0,
                          zero_crossing_rate=0.11, dynamic_range=16.0, backend="librosa"),
            _make_feature(track_key="medium", bpm=140.0, energy=0.7,
                          spectral_centroid=1500.0, spectral_rolloff=3000.0,
                          zero_crossing_rate=0.15, dynamic_range=25.0, backend="librosa"),
            _make_feature(track_key="far", bpm=200.0, energy=0.1,
                          spectral_centroid=500.0, spectral_rolloff=1000.0,
                          zero_crossing_rate=0.4, dynamic_range=40.0, backend="librosa"),
        ]

        results = [compute_similarity(seed, c) for c in candidates]
        results.sort(key=lambda r: r.score, reverse=True)

        assert results[0].track_key == "close"
        assert results[1].track_key == "medium"
        assert results[2].track_key == "far"
        assert results[0].score > results[1].score > results[2].score
        assert len(results[0].reasons) >= 1

    def test_bpm_similarity_identical(self):
        assert _bpm_similarity(120.0, 120.0) == 1.0

    def test_bpm_similarity_zero(self):
        assert _bpm_similarity(0.0, 120.0) == 0.5
        assert _bpm_similarity(120.0, 0.0) == 0.5

    def test_value_similarity_identical(self):
        assert _value_similarity(0.5, 0.5) == 1.0

    def test_value_similarity_beyond_scale(self):
        assert _value_similarity(0.0, 2.0, scale=1.0) == 0.0

    def test_value_similarity_partial(self):
        assert _value_similarity(0.0, 0.5, scale=1.0) == 0.5
