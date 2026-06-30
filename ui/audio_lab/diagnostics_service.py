"""Diagnostics service — analyse single files or directories using format_probe and quality_classifier.

Reuses existing audio/format_probe.py and audio/quality_classifier.py.
No fake hi-res detection yet (SpectralAuthenticator is separate).
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("michi.diagnostics.service")

AUDIO_EXTS = frozenset({
    ".flac", ".wav", ".mp3", ".ogg", ".opus",
    ".m4a", ".aiff", ".wv", ".ape", ".dsf", ".dff",
})


def analyse_file(filepath: str) -> dict[str, Any]:
    """Analyse a single audio file and return a technical report.

    Returns dict with keys:
      - filepath, filename, exists, error
      - format_info: dict from format_probe
      - quality: dict from quality_classifier
      - size_mb, duration_str
    """
    result: dict[str, Any] = {
        "filepath": filepath,
        "filename": os.path.basename(filepath),
        "exists": os.path.isfile(filepath),
        "error": "",
        "format_info": {},
        "quality": {},
        "size_mb": 0.0,
        "duration_str": "",
    }

    if not result["exists"]:
        result["error"] = "Archivo no encontrado"
        return result

    import contextlib
    with contextlib.suppress(OSError):
        result["size_mb"] = round(os.path.getsize(filepath) / (1024 * 1024), 1)

    # Format probe
    try:
        from audio.format_probe import probe_format
        fmt = probe_format(filepath)
        if fmt:
            result["format_info"] = {
                "container": fmt.container or "",
                "codec": fmt.codec or "",
                "sample_rate": fmt.sample_rate or 0,
                "bit_depth": fmt.bit_depth or 0,
                "channels": fmt.channels or 0,
                "bitrate": fmt.bitrate or 0,
                "duration": fmt.duration or 0.0,
                "is_lossless": fmt.is_lossless if hasattr(fmt, 'is_lossless') else False,
                "is_dsd": fmt.is_dsd if hasattr(fmt, 'is_dsd') else False,
                "warnings": fmt.warnings if hasattr(fmt, 'warnings') else [],
            }
            secs = fmt.duration or 0
            m, s = divmod(int(secs), 60)
            h, m = divmod(m, 60)
            if h:
                result["duration_str"] = f"{h}h {m}m {s}s"
            else:
                result["duration_str"] = f"{m}m {s}s"
    except Exception as e:
        logger.warning("format_probe failed for %s: %s", filepath, e)
        result["format_info"] = {"error": str(e)}

    # Quality classification
    try:
        from audio.quality_classifier import classify_audio_quality
        qc = classify_audio_quality(filepath)
        if isinstance(qc, dict):
            result["quality"] = {
                "category": qc.get("category", "unknown"),
                "label": qc.get("label", ""),
                "tooltip": qc.get("tooltip", ""),
            }
    except Exception as e:
        logger.warning("quality_classifier failed for %s: %s", filepath, e)
        result["quality"] = {"category": "error", "label": "Error", "tooltip": str(e)}

    # If format_probe provided a TrackRef/MediaItem-like object, quality_classifier
    # will work. Otherwise try with a basic dict.
    if not result["quality"].get("category"):
        try:
            from audio.quality_classifier import classify_audio_quality
            ext = os.path.splitext(filepath)[1].lower().lstrip(".")
            qc = classify_audio_quality(type("obj", (), {
                "ext": ext,
                "sample_rate": result["format_info"].get("sample_rate", 0),
                "bit_depth": result["format_info"].get("bit_depth", 0),
                "bitrate": result["format_info"].get("bitrate", 0),
            })())
            if isinstance(qc, dict):
                result["quality"] = qc
        except Exception:
            pass

    return result


def analyse_directory(directory: str) -> list[dict[str, Any]]:
    """Analyse all audio files in a directory recursively.

    Returns list of per-file analysis dicts.
    """
    if not os.path.isdir(directory):
        return []

    results = []
    for root, _dirs, files in os.walk(directory):
        for f in sorted(files):
            ext = os.path.splitext(f)[1].lower()
            if ext in AUDIO_EXTS:
                fp = os.path.join(root, f)
                results.append(analyse_file(fp))
    return results


def generate_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate a summary report from a list of per-file analyses.

    Returns dict with:
      - total_files, total_size_mb, total_duration_str
      - format_counts: {ext: count}
      - quality_counts: {category: count}
      - sample_rates: list of detected rates
      - bit_depths: list of detected depths
      - errors: list of filepaths with errors
      - warnings: list of (filepath, warning) tuples
    """
    total = len(results)
    total_size = 0.0
    total_secs = 0.0
    format_counts: dict[str, int] = {}
    quality_counts: dict[str, int] = {}
    sample_rates: set[int] = set()
    bit_depths: set[int] = set()
    errors: list[str] = []
    warnings: list[tuple[str, str]] = []

    for r in results:
        total_size += r.get("size_mb", 0)
        fi = r.get("format_info", {})
        if fi.get("duration"):
            total_secs += fi["duration"]
        ext = os.path.splitext(r.get("filename", ""))[1].lower().lstrip(".")
        if ext:
            format_counts[ext] = format_counts.get(ext, 0) + 1
        q = r.get("quality", {})
        cat = q.get("category", "unknown")
        quality_counts[cat] = quality_counts.get(cat, 0) + 1
        sr = fi.get("sample_rate", 0)
        if sr:
            sample_rates.add(sr)
        bd = fi.get("bit_depth", 0)
        if bd:
            bit_depths.add(bd)
        if r.get("error"):
            errors.append(r["filepath"])
        for w in fi.get("warnings", []):
            warnings.append((r["filepath"], w))

    m, s = divmod(int(total_secs), 60)
    h, m = divmod(m, 60)
    dur = f"{h}h {m}m {s}s" if h else f"{m}m {s}s"

    return {
        "total_files": total,
        "total_size_mb": round(total_size, 1),
        "total_duration_str": dur,
        "format_counts": dict(sorted(format_counts.items())),
        "quality_counts": dict(sorted(quality_counts.items())),
        "sample_rates": sorted(sample_rates),
        "bit_depths": sorted(bit_depths),
        "errors": errors,
        "warnings": warnings,
    }
