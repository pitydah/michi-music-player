"""AudioQualityAdapter — async quality probe for audio files.

Created by BridgeFactory, injected into NowPlayingBridge.
Uses WorkerManager for async probe when available.
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject

logger = logging.getLogger("michi.qml.quality")


class AudioQualityAdapter(QObject):
    """Probes audio files for quality metadata. Thread-safe via WorkerManager."""

    def __init__(self, worker_manager=None, parent=None):
        super().__init__(parent)
        self._wm = worker_manager
        self._cache: dict[str, dict] = {}
        self._max_cache = 200

    def _make_key(self, filepath: str) -> str:
        p = Path(filepath)
        try:
            if not p.exists():
                return filepath
            stat = p.stat()
            return f"{hashlib.md5(filepath.encode()).hexdigest()[:16]}_{stat.st_mtime}_{stat.st_size}"
        except Exception:
            return hashlib.md5(filepath.encode()).hexdigest()[:16]

    def _probe_sync(self, filepath: str) -> dict:
        """Synchronous probe — runs in current thread or worker."""
        p = Path(filepath)
        if not p.is_file():
            return {"ok": False, "error": "FILE_NOT_FOUND", "source_type": "unknown"}

        suffix = p.suffix.lower()
        result = {
            "ok": True,
            "format_label": suffix.lstrip(".").upper(),
            "sample_rate": 0,
            "bit_depth": 0,
            "channels": 0,
            "bitrate": 0,
            "quality_label": "",
            "quality_category": "unknown",
            "quality_tooltip": "",
            "source_type": "local_file",
        }

        try:
            from mutagen import File as MFile
            audio = MFile(str(p))
            if audio and hasattr(audio, 'info'):
                info = audio.info
                if hasattr(info, 'sample_rate') and info.sample_rate:
                    result["sample_rate"] = int(info.sample_rate)
                if hasattr(info, 'bitrate') and info.bitrate:
                    result["bitrate"] = int(info.bitrate)
                if hasattr(info, 'channels') and info.channels:
                    result["channels"] = int(info.channels)
                if hasattr(info, 'bits_per_sample') and info.bits_per_sample:
                    result["bit_depth"] = int(info.bits_per_sample)
                try:
                    from audio.quality_classifier import classify_audio_quality
                    q = classify_audio_quality(audio)
                    if q:
                        result["quality_label"] = q.get("label", q.get("quality", ""))
                        result["quality_category"] = q.get("category", "unknown")
                        result["quality_tooltip"] = q.get("tooltip", "")
                except Exception:
                    pass
        except Exception:
            logger.debug("Quality probe failed for %s", filepath, exc_info=True)

        if result["sample_rate"]:
            result["sample_rate_label"] = f"{result['sample_rate']} Hz"
        if result["bit_depth"]:
            result["bit_depth_label"] = f"{result['bit_depth']} bit"
        if result["channels"]:
            result["channels_label"] = f"{result['channels']}ch"
        if result["bitrate"]:
            result["bitrate_label"] = f"{result['bitrate'] // 1000} kbps"

        return result

    def probe(self, filepath: str, request_id: int = 0, callback: Callable | None = None) -> dict | int:
        """Probe a file. Returns result dict if sync, or job_id if async.

        If WorkerManager is available and callback is provided, runs async.
        Otherwise runs synchronously.
        """
        if not filepath:
            return {"ok": False, "error": "EMPTY_FILEPATH", "source_type": "unknown"}

        key = self._make_key(filepath)
        if key in self._cache:
            cached = dict(self._cache[key])
            if callback:
                callback(cached)
            return cached

        if self._wm and callback and hasattr(self._wm, 'run'):
            job_id = id({})

            def _job():
                return self._probe_sync(filepath)

            def _done(result):
                if result and result.get("ok"):
                    self._cache_result(key, result)
                callback(result)

            self._wm.run(_job, callback=_done)
            return job_id

        result = self._probe_sync(filepath)
        if result.get("ok"):
            self._cache_result(key, result)
        return result

    def _cache_result(self, key: str, result: dict):
        if len(self._cache) >= self._max_cache:
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        self._cache[key] = dict(result)

    def clear_cache(self):
        self._cache.clear()

    def invalidate(self, filepath: str):
        key = self._make_key(filepath)
        self._cache.pop(key, None)
