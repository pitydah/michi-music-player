"""Technical-quality label projections (LOCAL-META-02.2d).

Facts only — never marketing labels ("Hi-Res"/"Lossless"). The label is a
centralized projection so QML delegates never compose it themselves. The
pure render lives in the domain; this module adapts it for TrackMetadata
and the canonical TrackRef.
"""

from michi.domain.library import render_technical_label


def make_audio_quality_label(meta) -> str:
    """Render an honest technical-quality label from TrackMetadata."""
    return render_technical_label(
        meta.codec, meta.bit_depth, meta.sample_rate_hz, meta.bitrate_bps
    )


def make_track_quality_label(track) -> str:
    """Render an honest technical-quality label from a canonical TrackRef
    (M6-PRODUCTION-INTEGRATION: TrackRef retains the technical carrier)."""
    return render_technical_label(
        track.codec, track.bit_depth, track.sample_rate_hz, track.bitrate_bps
    )
