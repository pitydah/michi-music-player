"""Tests for ReplayGain advanced module."""
import pytest
from audio.replaygain import (
    parse_gain_db, db_to_linear, linear_to_db, select_gain,
    compute_safe_gain, apply_full, ReplayGainConfig,
)


class TestReplayGain:
    def test_parse_gain_db_simple(self):
        assert parse_gain_db("-5.2 dB") == -5.2
        assert parse_gain_db("-5.2dB") == -5.2
        assert parse_gain_db(" 3.1 ") == 3.1

    def test_parse_gain_db_empty(self):
        assert parse_gain_db("") is None
        assert parse_gain_db(None) is None

    def test_db_to_linear(self):
        assert db_to_linear(0.0) == 1.0
        assert db_to_linear(-6.0) == pytest.approx(0.501, abs=0.01)
        assert db_to_linear(6.0) == pytest.approx(1.995, abs=0.01)

    def test_linear_to_db(self):
        assert linear_to_db(1.0) == 0.0
        assert linear_to_db(0.5) == pytest.approx(-6.02, abs=0.1)

    def test_select_gain_track(self):
        assert select_gain("track", -5.0, -3.0) == -5.0
        # Fallback: when track_gain is None, falls through to album_gain
        assert select_gain("track", None, -3.0) == -3.0

    def test_select_gain_album(self):
        assert select_gain("album", -5.0, -3.0) == -3.0
        # Fallback: when album_gain is None, falls through to track_gain
        assert select_gain("album", -5.0, None) == -5.0

    def test_select_gain_auto(self):
        assert select_gain("auto", -5.0, -3.0) == -3.0  # prefers album
        assert select_gain("auto", -5.0, None) == -5.0  # falls back to track

    def test_select_gain_off(self):
        assert select_gain("off", -5.0, -3.0) is None

    def test_compute_safe_gain_basic(self):
        gain = compute_safe_gain(-6.0, 2.0)
        assert gain == pytest.approx(db_to_linear(-8.0), abs=0.01)

    def test_compute_safe_gain_anticlip(self):
        # peak 0.5, gain would be 2.0 → clipped to 2.0
        gain = compute_safe_gain(6.0, 0.0, track_peak=0.5, anti_clip=True)
        assert gain == pytest.approx(2.0, abs=0.01)

    def test_compute_safe_gain_no_anticlip(self):
        gain = compute_safe_gain(6.0, 0.0, track_peak=0.5, anti_clip=False)
        assert gain == pytest.approx(db_to_linear(6.0), abs=0.01)

    def test_apply_full_off(self):
        config = ReplayGainConfig(mode="off")
        gain, label = apply_full(config, -5.0, -3.0)
        assert gain == 1.0
        assert "off" in label

    def test_apply_full_track(self):
        config = ReplayGainConfig(mode="track", preamp_db=2.0, headroom_db=1.0,
                                  anti_clip=False)
        gain, label = apply_full(config, -5.0, -3.0)
        expected_db = -5.0 + 2.0 - 1.0  # track_gain + preamp - headroom
        assert gain == pytest.approx(db_to_linear(expected_db), abs=0.01)
        assert "Track" in label

    def test_replaygain_config_defaults(self):
        config = ReplayGainConfig()
        assert config.mode == "track"
        assert config.preamp_db == 0.0
        assert config.headroom_db == 0.0
        assert config.anti_clip is True
        assert config.is_active is True
        assert config.peak_limit == 1.0

    def test_replaygain_config_off_inactive(self):
        config = ReplayGainConfig(mode="off")
        assert config.is_active is False
