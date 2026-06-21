"""Audio quality classification — lossy/lossless/hires/dsd/unknown."""
from typing import Any


LOSSLESS_EXTS = frozenset({"flac", "alac", "wav", "aiff", "aif", "wv", "ape", "tta", "shn"})
LOSSY_EXTS = frozenset({"mp3", "aac", "ogg", "opus", "wma", "ac3"})
DSD_EXTS = frozenset({"dsf", "dff"})
HIRES_SR_THRESHOLD = 96000   # 96 kHz
HIRES_BIT_THRESHOLD = 24      # 24-bit


def classify_audio_quality(item_or_track: Any) -> dict:
    """Classify audio quality from a MediaItem or TrackRef-like object.

    Returns dict with keys: category, label, tooltip.
    Categories: unknown, lossy, lossless, hires, dsd, error.
    """
    ext = _get_attr(item_or_track, "ext", "").lower().lstrip(".")
    sample_rate = _get_int(item_or_track, "sample_rate")
    bit_depth = _get_int(item_or_track, "bit_depth")
    bitrate = _get_int(item_or_track, "bitrate")
    codec = _get_attr(item_or_track, "codec", "").lower().strip()

    if not ext:
        return _result("unknown", "", "Sin informacion tecnica")

    # M4A can be lossy (AAC) or lossless (ALAC)
    if ext == "m4a":
        if codec and "alac" in codec:
            return _lossless_result("ALAC", sample_rate, bit_depth, bitrate)
        if _detect_alac(item_or_track):
            return _lossless_result("ALAC", sample_rate, bit_depth, bitrate)
        return _lossy_result("AAC", bitrate)

    # DSD
    if ext in DSD_EXTS:
        return _dsd_result(sample_rate)

    # Lossless
    if ext in LOSSLESS_EXTS:
        return _lossless_result(ext.upper(), sample_rate, bit_depth, bitrate)

    # Lossy
    if ext in LOSSY_EXTS:
        return _lossy_result(ext.upper(), bitrate)

    return _result("unknown", ext.upper() if ext else "", "")


# ── Result builders ──

def _lossless_result(codec: str, sample_rate: int, bit_depth: int,
                     bitrate: int) -> dict:
    """Build result for lossless/hires."""
    # Infer bit_depth from sample_rate if missing
    if bit_depth <= 0:
        bit_depth = 24 if sample_rate >= HIRES_SR_THRESHOLD else 16
    # Infer sample_rate from bitrate if missing
    if sample_rate <= 0 and bitrate > 0:
        sample_rate = _infer_sr_from_bitrate(bitrate, bit_depth)

    # Hi-Res: 24-bit+ and 96kHz+
    if bit_depth >= HIRES_BIT_THRESHOLD and sample_rate >= HIRES_SR_THRESHOLD:
        label = f"HI-RES {bit_depth}/{int(sample_rate / 1000)}"
        tooltip = f"{codec} \u00b7 {bit_depth}-bit \u00b7 {sample_rate / 1000:.0f} kHz"
        return _result("hires", label, tooltip)

    # Hi-Res via bit depth alone (32-bit at any rate)
    if bit_depth >= 32 and sample_rate > 0:
        label = f"HI-RES {bit_depth}/{int(sample_rate / 1000)}"
        tooltip = f"{codec} \u00b7 {bit_depth}-bit \u00b7 {sample_rate / 1000:.0f} kHz"
        return _result("hires", label, tooltip)

    # Standard lossless with sample_rate
    if sample_rate > 0:
        bd = bit_depth if bit_depth > 0 else 16
        label = f"{codec} {bd}/{int(sample_rate / 1000)}"
        tooltip = f"{codec} \u00b7 {bd}-bit \u00b7 {sample_rate / 1000:.0f} kHz"
        return _result("lossless", label, tooltip)

    return _result("lossless", codec, f"{codec}")


def _lossy_result(codec: str, bitrate: int) -> dict:
    """Build result for lossy formats."""
    if codec.upper() == "OPUS" and bitrate <= 0:
        return _result("lossy", "OPUS VBR", "OPUS \u00b7 Variable Bitrate")
    if bitrate >= 1000:
        label = f"{codec.upper()} {bitrate // 1000}kbps"
        tooltip = f"{codec.upper()} \u00b7 {bitrate // 1000} kbps"
        return _result("lossy", label, tooltip)
    if bitrate > 0:
        label = f"{codec.upper()} {bitrate}kbps"
        tooltip = f"{codec.upper()} \u00b7 {bitrate} kbps"
        return _result("lossy", label, tooltip)
    return _result("lossy", codec.upper(), f"{codec.upper()}")


def _dsd_result(sample_rate: int) -> dict:
    """Build result for DSD."""
    if sample_rate <= 0:
        return _result("dsd", "DSD", "DSD \u00b7 1-bit")
    label = _dsd_label(sample_rate)
    return _result("dsd", label,
                   f"DSD \u00b7 1-bit \u00b7 {sample_rate / 1e6:.1f} MHz")


# ── Helpers ──

def _detect_alac(item) -> bool:
    """Try to detect if an M4A file contains ALAC (Apple Lossless)."""
    # Check codec attribute from GStreamer discoverer
    codec_attr = _get_attr(item, "codec", "").lower().strip()
    if "alac" in codec_attr or "lossless" in codec_attr:
        return True
    return _get_attr(item, "kind", "") == "alac"


def _infer_sr_from_bitrate(bitrate: int, bit_depth: int) -> int:
    """Infer sample rate from FLAC bitrate (rough heuristic)."""
    if bitrate > 4000:
        return 192000
    if bitrate > 2500:
        return 96000  # 24/96 FLAC
    if bitrate > 1200:
        return 48000
    return 44100  # CD


def _result(category: str, label: str, tooltip: str) -> dict:
    return {"category": category, "label": label, "tooltip": tooltip}


def _get_attr(obj, name: str, default=""):
    val = getattr(obj, name, default)
    return val if val is not None else default


def _get_int(obj, name: str) -> int:
    val = getattr(obj, name, 0)
    try:
        return int(val) if val else 0
    except (ValueError, TypeError):
        return 0


def _dsd_label(sample_rate: int) -> str:
    if sample_rate >= 11289600:
        return "DSD256"
    if sample_rate >= 5644800:
        return "DSD128"
    return "DSD64"
