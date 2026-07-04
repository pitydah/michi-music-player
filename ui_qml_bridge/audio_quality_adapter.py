"""AudioQualityAdapter — probes file quality stats using existing services."""
from __future__ import annotations

from pathlib import Path
import hashlib
import logging

logger = logging.getLogger("michi.qml.quality")

_CACHE: dict[str, dict] = {}
_MAX_CACHE = 200


def _make_key(filepath: str) -> str:
    return hashlib.md5(Path(filepath).as_posix().encode()).hexdigest()[:16]


def probe(filepath: str) -> dict:
    """Probe a file for quality metadata. Returns dict with ok/error."""
    if not filepath:
        return {"ok": False, "error": "EMPTY_FILEPATH"}
    p = Path(filepath)
    if not p.is_file():
        return {"ok": False, "error": "FILE_NOT_FOUND"}

    key = _make_key(filepath)
    if key in _CACHE:
        return dict(_CACHE[key])

    result = {
        "ok": True,
        "format_label": p.suffix.lower().lstrip(".").upper() if p.suffix else "",
        "sample_rate": "",
        "bit_depth": "",
        "channels": "",
        "bitrate": "",
        "quality_label": "",
        "source_type": "local_file",
    }

    try:
        from mutagen import File as MFile
        audio = MFile(str(p), easy=True)
        if audio and hasattr(audio, 'info'):
            info = audio.info
            if hasattr(info, 'sample_rate') and info.sample_rate:
                result["sample_rate"] = f"{info.sample_rate} Hz"
            if hasattr(info, 'bitrate') and info.bitrate:
                result["bitrate"] = f"{info.bitrate // 1000} kbps"
            if hasattr(info, 'channels') and info.channels:
                result["channels"] = f"{info.channels}ch"
            if hasattr(info, 'bits_per_sample') and info.bits_per_sample:
                result["bit_depth"] = f"{info.bits_per_sample} bit"
            try:
                from audio.quality_classifier import classify
                q = classify(audio)
                if q:
                    result["quality_label"] = str(q.get("label", q.get("quality", "")))
            except Exception:
                pass
    except Exception:
        logger.debug("Quality probe failed for %s", filepath, exc_info=True)

    if len(_CACHE) >= _MAX_CACHE:
        oldest = next(iter(_CACHE))
        del _CACHE[oldest]
    _CACHE[key] = dict(result)
    return result


def clear_cache():
    _CACHE.clear()
