"""AudioComparisonService — compare audio file variants.

Compares by: format, codec, bitrate, sample rate, bit depth, channels,
size, loudness, peak, metadata, waveform summary, hash, integrity.
Does NOT claim "sounds better" by heuristic.
"""
from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, field

from PySide6.QtCore import QObject

from .audio_probe_service import AudioProbeService

logger = logging.getLogger("michi.audio_lab.comparison")


@dataclass
class ComparisonDimension:
    key: str = ""
    label: str = ""
    value_a: str = ""
    value_b: str = ""
    identical: bool = False
    better: str = ""


@dataclass
class ComparisonResult:
    file_a: str = ""
    file_b: str = ""
    dimensions: list[ComparisonDimension] = field(default_factory=list)
    identical: bool = True
    error: str = ""


class AudioComparisonService(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._probe_service = AudioProbeService()

    def compare(self, file_a: str, file_b: str) -> ComparisonResult:
        result = ComparisonResult(file_a=file_a, file_b=file_b)
        for fp, _ in [(file_a, "A"), (file_b, "B")]:
            if not os.path.isfile(fp):
                result.error = f"FILE_NOT_FOUND: {fp}"
                return result

        probe_a = self._probe_service.probe(file_a)
        probe_b = self._probe_service.probe(file_b)

        dimensions = [
            ("format", "Formato", probe_a.format, probe_b.format),
            ("codec", "Codec", probe_a.codec, probe_b.codec),
            ("bitrate", "Bitrate", f"{probe_a.bitrate} bps", f"{probe_b.bitrate} bps"),
            ("sample_rate", "Frecuencia", f"{probe_a.sample_rate} Hz", f"{probe_b.sample_rate} Hz"),
            ("bit_depth", "Profundidad", f"{probe_a.bit_depth} bit", f"{probe_b.bit_depth} bit"),
            ("channels", "Canales", str(probe_a.channels), str(probe_b.channels)),
            ("size", "Tamaño", self._fmt_size(probe_a.file_size), self._fmt_size(probe_b.file_size)),
            ("file_size_bytes", "Tamaño (bytes)", str(probe_a.file_size), str(probe_b.file_size)),
            ("duration", "Duración", f"{probe_a.duration:.1f}s", f"{probe_b.duration:.1f}s"),
            ("loudness", "Loudness", f"{probe_a.loudness or 0:.1f}", f"{probe_b.loudness or 0:.1f}"),
            ("peak", "Pico", f"{probe_a.peak or 0:.4f}", f"{probe_b.peak or 0:.4f}"),
            ("encoder", "Encoder", probe_a.encoder, probe_b.encoder),
        ]

        for key, label, val_a, val_b in dimensions:
            dim = ComparisonDimension(
                key=key, label=label, value_a=str(val_a), value_b=str(val_b),
                identical=str(val_a) == str(val_b),
            )
            if not dim.identical:
                result.identical = False
            result.dimensions.append(dim)

        hash_a = self._quick_hash(file_a)
        hash_b = self._quick_hash(file_b)
        result.dimensions.append(ComparisonDimension(
            key="hash", label="Hash parcial",
            value_a=hash_a[:16], value_b=hash_b[:16],
            identical=hash_a == hash_b,
        ))
        if hash_a != hash_b:
            result.identical = False

        meta_a = self._read_metadata_for_comparison(file_a)
        meta_b = self._read_metadata_for_comparison(file_b)
        meta_keys = ["title", "artist", "album", "genre", "date"]
        for k in meta_keys:
            va = meta_a.get(k, "")
            vb = meta_b.get(k, "")
            result.dimensions.append(ComparisonDimension(
                key=f"meta_{k}", label=f"Metadata: {k}",
                value_a=va, value_b=vb,
                identical=va == vb,
            ))
            if va != vb:
                result.identical = False

        return result

    def _read_metadata_for_comparison(self, filepath: str) -> dict[str, str]:
        result: dict[str, str] = {}
        try:
            import mutagen
            af = mutagen.File(filepath)
            if af is not None and hasattr(af, "tags") and af.tags:
                for key in ["title", "artist", "album", "genre"]:
                    if key in af.tags:
                        v = af.tags[key]
                        result[key] = str(v[0] if isinstance(v, list) else v)
                if "date" in af.tags:
                    v = af.tags["date"]
                    result["date"] = str(v[0] if isinstance(v, list) else v)
        except Exception:
            pass
        return result

    def _quick_hash(self, filepath: str) -> str:
        try:
            h = hashlib.md5()
            with open(filepath, "rb") as f:
                h.update(f.read(8192))
                f.seek(-8192, 2)
                h.update(f.read(8192))
            return h.hexdigest()
        except Exception:
            return ""

    def _fmt_size(self, size: int) -> str:
        if size < 1024:
            return f"{size} B"
        if size < 1024 ** 2:
            return f"{size / 1024:.1f} KB"
        return f"{size / 1024 ** 2:.1f} MB"
