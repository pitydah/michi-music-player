"""AudioProbeService — technical probe of audio files.

Extracts format, codec, container, duration, file size, bitrate,
sample rate, bit depth, channels, channel layout, encoder, tags,
artwork presence, ReplayGain tags, peak, loudness.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject

logger = logging.getLogger("michi.audio_lab.probe")

@dataclass
class AudioProbeResult:
    filepath: str = ""
    format: str = "UNSUPPORTED"
    codec: str = ""
    container: str = ""
    duration: float = 0.0
    file_size: int = 0
    bitrate: int = 0
    sample_rate: int = 0
    bit_depth: int = 0
    channels: int = 0
    channel_layout: str = ""
    encoder: str = ""
    has_tags: bool = False
    has_artwork: bool = False
    replaygain_track_gain: float | None = None
    replaygain_album_gain: float | None = None
    replaygain_track_peak: float | None = None
    replaygain_album_peak: float | None = None
    loudness: float | None = None
    peak: float | None = None
    checksum: str = ""
    decode_status: str = "unchecked"
    corruption: bool = False
    inconsistencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "filepath": self.filepath,
            "format": self.format,
            "codec": self.codec,
            "container": self.container,
            "duration": self.duration,
            "file_size": self.file_size,
            "bitrate": self.bitrate,
            "sample_rate": self.sample_rate,
            "bit_depth": self.bit_depth,
            "channels": self.channels,
            "channel_layout": self.channel_layout,
            "encoder": self.encoder,
            "has_tags": self.has_tags,
            "has_artwork": self.has_artwork,
            "replaygain_track_gain": self.replaygain_track_gain,
            "replaygain_album_gain": self.replaygain_album_gain,
            "replaygain_track_peak": self.replaygain_track_peak,
            "replaygain_album_peak": self.replaygain_album_peak,
            "loudness": self.loudness,
            "peak": self.peak,
            "checksum": self.checksum,
            "decode_status": self.decode_status,
            "corruption": self.corruption,
            "inconsistencies": self.inconsistencies,
        }


class AudioProbeService(QObject):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db

    def probe(self, filepath: str) -> AudioProbeResult:
        result = AudioProbeResult(filepath=filepath)
        if not filepath or not os.path.isfile(filepath):
            result.decode_status = "not_found"
            result.inconsistencies.append("FILE_NOT_FOUND")
            return result

        try:
            result.file_size = os.path.getsize(filepath)
            ext = Path(filepath).suffix.lower()
            result.format = self._detect_format(ext)
            result.container = ext.lstrip(".")

            codec_info = self._probe_codec(filepath, result.format)
            result.codec = codec_info.get("codec", "")
            result.sample_rate = codec_info.get("sample_rate", 0)
            result.bit_depth = codec_info.get("bit_depth", 0)
            result.channels = codec_info.get("channels", 0)
            result.channel_layout = self._layout_name(result.channels)
            result.bitrate = codec_info.get("bitrate", 0)
            result.duration = codec_info.get("duration", 0.0)
            result.encoder = codec_info.get("encoder", "")

            if result.format == "UNSUPPORTED":
                result.decode_status = "unsupported"
                result.inconsistencies.append("UNSUPPORTED_FORMAT")
            else:
                result.decode_status = "ok"

            tag_info = self._probe_tags(filepath)
            result.has_tags = tag_info.get("has_tags", False)
            result.has_artwork = tag_info.get("has_artwork", False)
            result.replaygain_track_gain = tag_info.get("track_gain")
            result.replaygain_album_gain = tag_info.get("album_gain")
            result.replaygain_track_peak = tag_info.get("track_peak")
            result.replaygain_album_peak = tag_info.get("album_peak")
            result.loudness = tag_info.get("loudness")
            result.peak = tag_info.get("peak")

            if result.decode_status == "ok" and result.file_size > 0 and result.duration <= 0:
                result.inconsistencies.append("ZERO_DURATION")

        except Exception:
            logger.exception("Probe failed for %s", filepath)
            result.decode_status = "error"
            result.inconsistencies.append("PROBE_ERROR")

        return result

    def _detect_format(self, ext: str) -> str:
        mapping = {
            ".flac": "FLAC",
            ".wav": "WAV",
            ".aiff": "AIFF", ".aif": "AIFF",
            ".mp3": "MP3",
            ".m4a": "AAC", ".mp4": "AAC",
            ".opus": "Opus",
            ".ogg": "Vorbis",
            ".mka": "ALAC",
            ".wma": "WMA",
            ".dsf": "DSD",
            ".dff": "DSD",
        }
        fmt = mapping.get(ext, "UNSUPPORTED")
        if fmt != "UNSUPPORTED":
            return fmt
        if ext in (".ape", ".tak", ".tta", ".wv"):
            return "UNSUPPORTED"
        return fmt

    def _probe_codec(self, filepath: str, fmt: str) -> dict[str, Any]:
        info: dict[str, Any] = {}
        try:
            import mutagen
            af = mutagen.File(filepath)
            if af is None:
                return info
            info["codec"] = af.__class__.__name__
            if hasattr(af.info, "sample_rate"):
                info["sample_rate"] = af.info.sample_rate
            if hasattr(af.info, "bitrate"):
                info["bitrate"] = af.info.bitrate
            if hasattr(af.info, "channels"):
                info["channels"] = af.info.channels
            if hasattr(af.info, "bits_per_sample"):
                info["bit_depth"] = af.info.bits_per_sample
            if hasattr(af.info, "length"):
                info["duration"] = af.info.length
            if fmt in ("FLAC", "Vorbis", "Opus") and hasattr(af, "tags") and af.tags:
                enc = af.tags.get("ENCODER")
                if enc:
                    info["encoder"] = str(enc)
            if fmt == "MP3" and hasattr(af.info, "encoder_info"):
                info["encoder"] = af.info.encoder_info
            if fmt == "AAC" and hasattr(af.info, "codec"):
                info["codec"] = af.info.codec
                if hasattr(af.info, "bitrate") and af.info.bitrate:
                    info["bitrate"] = af.info.bitrate
        except Exception:
            logger.debug("mutagen probe failed for %s", filepath)
        return info

    def _probe_tags(self, filepath: str) -> dict[str, Any]:
        info: dict[str, Any] = {"has_tags": False, "has_artwork": False}
        try:
            import mutagen
            af = mutagen.File(filepath)
            if af is None or not hasattr(af, "tags") or af.tags is None:
                return info
            info["has_tags"] = True

            if hasattr(af.tags, "pictures") and af.tags.pictures:
                info["has_artwork"] = True
            elif hasattr(af, "get"):
                for key in ("APIC:", "covr", "metadata_block_picture"):
                    if af.get(key):
                        info["has_artwork"] = True
                        break

            import contextlib
            for tg, rg_key in (
                ("TXXX:REPLAYGAIN_TRACK_GAIN", "track_gain"),
                ("TXXX:REPLAYGAIN_ALBUM_GAIN", "album_gain"),
                ("TXXX:REPLAYGAIN_TRACK_PEAK", "track_peak"),
                ("TXXX:REPLAYGAIN_ALBUM_PEAK", "album_peak"),
            ):
                val = af.get(tg) or af.tags.get(tg)
                if val:
                    with contextlib.suppress(ValueError):
                        info[rg_key] = float(str(val).replace(" dB", ""))

            for rg_key, vg_name in (
                ("track_gain", "REPLAYGAIN_TRACK_GAIN"),
                ("album_gain", "REPLAYGAIN_ALBUM_GAIN"),
                ("track_peak", "REPLAYGAIN_TRACK_PEAK"),
                ("album_peak", "REPLAYGAIN_ALBUM_PEAK"),
            ):
                val = af.tags.get(vg_name)
                if val:
                    with contextlib.suppress(ValueError, IndexError):
                        info[rg_key] = float(str(val[0]).replace(" dB", ""))

        except Exception:
            logger.debug("Tag probe failed for %s", filepath)

        return info

    def _layout_name(self, channels: int) -> str:
        return {1: "mono", 2: "stereo", 3: "2.1", 4: "quad", 5: "5.0", 6: "5.1", 7: "6.1", 8: "7.1"}.get(channels, f"{channels}ch")
