"""Canonical presentation facts for local audio container/codec formats."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class TrackFormatFacts:
    key: str
    label: str
    dsd_rate: str = ""


_LABELS = {
    "mp3": "MP3",
    "flac": "FLAC",
    "wav": "WAV",
    "aiff": "AIFF",
    "aif": "AIF",
    "alac": "ALAC",
    "aac": "AAC",
    "m4a": "M4A",
    "ogg": "OGG",
    "opus": "OPUS",
    "wma": "WMA",
    "ape": "APE",
    "wavpack": "WV",
    "dsf": "DSF",
    "dff": "DFF",
    "unknown": "UNKNOWN",
}


def _token(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def _codec_key(codec: str) -> str:
    token = _token(codec)
    if "flac" in token:
        return "flac"
    if token in {"mp3", "mpeglayer3", "mpegaudiolayer3"} or "layeriii" in token:
        return "mp3"
    if "alac" in token or "applelossless" in token:
        return "alac"
    if token.startswith("aac") or "advancedaudiocoding" in token:
        return "aac"
    if "vorbis" in token:
        return "ogg"
    if "opus" in token:
        return "opus"
    if "wavpack" in token:
        return "wavpack"
    if "monkeysaudio" in token or token == "ape":
        return "ape"
    if token.startswith("wma") or "windowsmediaaudio" in token:
        return "wma"
    if token.startswith("dsd") or "directstreamdigital" in token:
        return "dsd"
    return ""


def _container_key(container: str) -> str:
    token = _token(container)
    aliases = {
        "wave": "wav",
        "wav": "wav",
        "aiff": "aiff",
        "aif": "aif",
        "flac": "flac",
        "mp3": "mp3",
        "m4a": "m4a",
        "mp4": "m4a",
        "mpeg4": "m4a",
        "ogg": "ogg",
        "opus": "opus",
        "asf": "wma",
        "wma": "wma",
        "ape": "ape",
        "wavpack": "wavpack",
        "wv": "wavpack",
        "dsf": "dsf",
        "dff": "dff",
        "dsdiff": "dff",
    }
    return aliases.get(token, "")


def _suffix_key(file_path: Path) -> str:
    suffix = file_path.suffix.casefold().lstrip(".")
    aliases = {"wv": "wavpack"}
    key = aliases.get(suffix, suffix)
    return key if key in _LABELS else ""


def _dsd_rate(sample_rate_hz: int) -> str:
    if sample_rate_hz <= 0:
        return ""
    # DSD64 is 2.8224 MHz. Metadata readers may round by a few Hz, so choose
    # the nearest canonical power-of-two multiple within a 1% tolerance.
    base = 2_822_400
    for multiplier in (1, 2, 4, 8, 16):
        expected = base * multiplier
        if abs(sample_rate_hz - expected) <= expected * 0.01:
            return f"DSD{64 * multiplier}"
    return ""


def normalize_track_format(
    codec: str,
    container: str,
    file_path: Path,
    sample_rate_hz: int = 0,
) -> TrackFormatFacts:
    """Normalize truthful codec/container facts with suffix as final fallback.

    Codec disambiguates shared containers (notably AAC vs ALAC in M4A). The
    file extension is never the sole authority when richer metadata exists.
    """
    codec_key = _codec_key(codec)
    container_key = _container_key(container)
    suffix_key = _suffix_key(file_path)

    if codec_key == "dsd":
        key = container_key if container_key in {"dsf", "dff"} else suffix_key
        if key not in {"dsf", "dff"}:
            key = "unknown"
        return TrackFormatFacts(key, _LABELS[key], _dsd_rate(sample_rate_hz))

    key = codec_key or container_key or suffix_key or "unknown"
    return TrackFormatFacts(key, _LABELS.get(key, "UNKNOWN"))
