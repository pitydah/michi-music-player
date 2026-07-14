"""AudioLabProfileService — conversion profiles for Audio Lab.

Profiles: Portable MP3, Portable AAC, Efficient Opus, Lossless FLAC,
Archival FLAC, PCM WAV, Hi-Res Preserve, Device Compatible, Custom.
"""
from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QObject

from .audio_conversion_service import ConversionProfile

logger = logging.getLogger("michi.audio_lab.profiles")


BUILTIN_PROFILES: list[ConversionProfile] = [
    ConversionProfile(name="Portable MP3", format="MP3", codec="libmp3lame",
                      bitrate=320, sample_rate=44100, bit_depth=16, channels=2,
                      copy_metadata=True, copy_artwork=True,
                      filename_template="{artist} - {album} - {track:02d} - {title}"),
    ConversionProfile(name="Portable AAC", format="AAC", codec="aac",
                      bitrate=256, sample_rate=44100, bit_depth=16, channels=2,
                      copy_metadata=True, copy_artwork=True,
                      filename_template="{artist} - {album} - {track:02d} - {title}"),
    ConversionProfile(name="Efficient Opus", format="Opus", codec="libopus",
                      bitrate=128, sample_rate=48000, bit_depth=16, channels=2,
                      copy_metadata=True, copy_artwork=False,
                      filename_template="{artist} - {title}"),
    ConversionProfile(name="Lossless FLAC", format="FLAC", codec="flac",
                      bitrate=0, sample_rate=44100, bit_depth=16, channels=2,
                      copy_metadata=True, copy_artwork=True,
                      filename_template="{artist} - {album} - {track:02d} - {title}"),
    ConversionProfile(name="Archival FLAC", format="FLAC", codec="flac",
                      bitrate=0, sample_rate=192000, bit_depth=24, channels=2,
                      copy_metadata=True, copy_artwork=True,
                      filename_template="{artist} - {album} - {track:02d} - {title}"),
    ConversionProfile(name="PCM WAV", format="WAV", codec="pcm_s16le",
                      bitrate=0, sample_rate=44100, bit_depth=16, channels=2,
                      copy_metadata=True, copy_artwork=False,
                      filename_template="{artist} - {title}"),
    ConversionProfile(name="Hi-Res Preserve", format="FLAC", codec="flac",
                      bitrate=0, sample_rate=0, bit_depth=0, channels=0,
                      copy_metadata=True, copy_artwork=True,
                      filename_template="{artist} - {album} - {track:02d} - {title}"),
    ConversionProfile(name="Device Compatible", format="MP3", codec="libmp3lame",
                      bitrate=192, sample_rate=44100, bit_depth=16, channels=2,
                      copy_metadata=True, copy_artwork=True,
                      filename_template="{artist} - {title}"),
    ConversionProfile(name="Custom", format="FLAC", codec="flac",
                      bitrate=0, sample_rate=0, bit_depth=0, channels=0,
                      copy_metadata=True, copy_artwork=True,
                      filename_template="{artist} - {title}"),
]


class AudioLabProfileService(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._profiles: dict[str, ConversionProfile] = {}
        self._custom_profiles: dict[str, ConversionProfile] = {}
        self._init_builtins()

    def _init_builtins(self):
        for p in BUILTIN_PROFILES:
            self._profiles[p.name.lower().replace(" ", "_")] = p

    def list_profiles(self) -> list[dict[str, Any]]:
        result = []
        for key, p in {**self._profiles, **self._custom_profiles}.items():
            result.append({
                "key": key,
                "name": p.name,
                "format": p.format,
                "codec": p.codec,
                "bitrate": p.bitrate,
                "sample_rate": p.sample_rate,
                "bit_depth": p.bit_depth,
                "channels": p.channels,
                "copy_metadata": p.copy_metadata,
                "copy_artwork": p.copy_artwork,
                "custom": key in self._custom_profiles,
            })
        return result

    def get_profile(self, key: str) -> ConversionProfile | None:
        return self._profiles.get(key) or self._custom_profiles.get(key)

    def save_custom(self, profile: ConversionProfile) -> str:
        key = profile.name.lower().replace(" ", "_")
        self._custom_profiles[key] = profile
        return key

    def delete_custom(self, key: str) -> bool:
        if key in self._custom_profiles:
            del self._custom_profiles[key]
            return True
        return False
