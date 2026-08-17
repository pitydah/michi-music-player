"""Technical-quality label projection (LOCAL-META-02.2d).

Facts only — never marketing labels ("Hi-Res"/"Lossless"). The label is a
centralized projection so QML delegates never compose it themselves."""


def make_audio_quality_label(meta) -> str:
    """Render an honest technical-quality label from TrackMetadata.

    - Lossless (bit_depth > 0 and sample_rate_hz > 0):
      "FLAC · 24-bit · 96 kHz" (kHz with up to 1 decimal).
    - Lossy (bit_depth == 0 and bitrate_bps > 0): "MP3 · 320 kbps".
    - Bare codec when only the codec is known.
    - "" when nothing technical is known.
    """
    codec = meta.codec
    if meta.bit_depth > 0 and meta.sample_rate_hz > 0:
        khz = meta.sample_rate_hz / 1000
        khz_text = f"{khz:g} kHz"
        return f"{codec} · {meta.bit_depth}-bit · {khz_text}"
    if meta.bit_depth == 0 and meta.bitrate_bps > 0:
        return f"{codec} · {meta.bitrate_bps // 1000} kbps"
    if codec:
        return codec
    return ""
