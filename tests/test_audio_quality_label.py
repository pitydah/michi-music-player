"""LOCAL-META-02.2d technical-quality label — Phase-1 RED tests.

The target contract (mega-WP §14, DoD 52) is NOT implemented on the current
baseline: ``make_audio_quality_label`` does not exist yet. It will live in a
small reusable application module (``michi/application/audio_quality.py``) so
it is importable from the bridge and unit-testable; importing it now raises
``ModuleNotFoundError`` (or ``ImportError``) — that IS the expected Phase-1 red
evidence. These tests encode the target contract and must pass once the
production module lands.

Contract being encoded — facts only, NEVER marketing labels ("Hi-Res"/
"Lossless"):
- Lossless (bit_depth > 0 and sample_rate_hz > 0):
  "{codec} · {bit_depth}-bit · {sample_rate/1000} kHz" — kHz with up to 1
  decimal: 44100 -> "44.1 kHz", 96000 -> "96 kHz".
- Lossy (bit_depth == 0 and bitrate_bps > 0):
  "{codec} · {bitrate_bps//1000} kbps".
- Codec fallback (codec known, nothing else): the bare codec, e.g. "FLAC".
- Unknown (no codec/technical data): "" (empty string — the UI shows nothing).
- The codec is used as extracted ("FLAC"/"MP3"); never fabricated.
- The lossless branch requires BOTH bit_depth and sample_rate_hz; partial
  technical data falls back gracefully (e.g. depth without rate -> bare codec).
"""

from michi.application.audio_quality import make_audio_quality_label
from michi.domain.library import TrackMetadata


def test_lossless_flac_label():
    meta = TrackMetadata(codec="FLAC", bit_depth=24, sample_rate_hz=96000)
    assert make_audio_quality_label(meta) == "FLAC · 24-bit · 96 kHz"


def test_lossless_44k1_khz_decimal():
    meta = TrackMetadata(codec="FLAC", bit_depth=16, sample_rate_hz=44100)
    assert make_audio_quality_label(meta) == "FLAC · 16-bit · 44.1 kHz"


def test_lossy_mp3_label():
    meta = TrackMetadata(codec="MP3", bit_depth=0, bitrate_bps=320000)
    assert make_audio_quality_label(meta) == "MP3 · 320 kbps"


def test_lossy_bitrate_rounded_down():
    meta = TrackMetadata(codec="MP3", bit_depth=0, bitrate_bps=256000)
    assert make_audio_quality_label(meta) == "MP3 · 256 kbps"


def test_codec_only_fallback():
    meta = TrackMetadata(codec="FLAC", bit_depth=0, sample_rate_hz=0, bitrate_bps=0)
    assert make_audio_quality_label(meta) == "FLAC"


def test_unknown_returns_empty():
    assert make_audio_quality_label(TrackMetadata()) == ""


def test_never_fabricates_hi_res():
    samples = [
        TrackMetadata(codec="FLAC", bit_depth=24, sample_rate_hz=96000),
        TrackMetadata(codec="FLAC", bit_depth=24, sample_rate_hz=192000),
        TrackMetadata(codec="FLAC", bit_depth=16, sample_rate_hz=44100),
        TrackMetadata(codec="FLAC", bit_depth=24, sample_rate_hz=0),
        TrackMetadata(
            codec="FLAC", bit_depth=24, sample_rate_hz=96000, bitrate_bps=1411000
        ),
        TrackMetadata(codec="MP3", bit_depth=0, bitrate_bps=320000),
        TrackMetadata(
            codec="MP3", bit_depth=0, sample_rate_hz=44100, bitrate_bps=192000
        ),
        TrackMetadata(),
    ]
    for meta in samples:
        label = make_audio_quality_label(meta)
        assert "Hi-Res" not in label
        assert "Lossless" not in label


def test_partial_technical_fields_graceful():
    meta = TrackMetadata(codec="FLAC", bit_depth=24, sample_rate_hz=0)
    assert make_audio_quality_label(meta) == "FLAC"
