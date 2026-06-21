"""Tests for audio quality classifier."""
from unittest.mock import MagicMock
from audio.quality_classifier import classify_audio_quality


def _item(ext="", sample_rate=0, bit_depth=0, bitrate=0, codec=""):
    i = MagicMock()
    i.ext = ext
    i.sample_rate = sample_rate
    i.bit_depth = bit_depth
    i.bitrate = bitrate
    i.codec = codec
    i.kind = ""
    return i


class TestQualityClassifier:
    def test_mp3_lossy(self):
        r = classify_audio_quality(_item("mp3", 44100, 0, 320000))
        assert r["category"] == "lossy"
        assert "MP3" in r["label"]

    def test_aac_lossy(self):
        r = classify_audio_quality(_item("aac", 44100, 0, 256000))
        assert r["category"] == "lossy"

    def test_flac_cd_lossless(self):
        r = classify_audio_quality(_item("flac", 44100, 16))
        assert r["category"] == "lossless"

    def test_flac_hires(self):
        r = classify_audio_quality(_item("flac", 96000, 24))
        assert r["category"] == "hires"
        assert "24/96" in r["label"]

    def test_flac_192_hires(self):
        r = classify_audio_quality(_item("flac", 192000, 24))
        assert r["category"] == "hires"

    def test_wav_hires(self):
        r = classify_audio_quality(_item("wav", 96000, 24))
        assert r["category"] == "hires"

    def test_wav_32bit_hires(self):
        r = classify_audio_quality(_item("wav", 48000, 32))
        assert r["category"] == "hires"

    def test_dsd64(self):
        r = classify_audio_quality(_item("dsf", 2822400))
        assert r["category"] == "dsd"

    def test_dsd_no_sample_rate(self):
        r = classify_audio_quality(_item("dsf", 0))
        assert r["category"] == "dsd"
        assert r["label"] == "DSD"

    def test_unknown_no_ext(self):
        r = classify_audio_quality(_item(""))
        assert r["category"] == "unknown"

    def test_mp3_no_bitrate(self):
        r = classify_audio_quality(_item("mp3", 44100))
        assert r["category"] == "lossy"

    def test_opus_no_bitrate(self):
        r = classify_audio_quality(_item("opus", 48000))
        assert r["category"] == "lossy"
        assert "VBR" in r["label"]

    def test_m4a_aac(self):
        r = classify_audio_quality(_item("m4a", 44100, 0, 256000))
        assert r["category"] == "lossy"
        assert "AAC" in r["label"]

    def test_m4a_alac(self):
        r = classify_audio_quality(_item("m4a", 44100, 16, 0, "alac"))
        assert r["category"] == "lossless"
        assert "ALAC" in r["label"]

    def test_flac_no_sample_rate(self):
        r = classify_audio_quality(_item("flac", 0, 16))
        assert r["category"] == "lossless"
        assert "0" not in r["label"]  # no "0/16"
