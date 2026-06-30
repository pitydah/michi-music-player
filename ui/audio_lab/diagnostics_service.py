"""Diagnostics service — analyse single files or directories using format_probe and quality_classifier.

Reuses existing audio/format_probe.py and audio/quality_classifier.py.
No fake hi-res detection yet (SpectralAuthenticator is separate).
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import sqlite3

logger = logging.getLogger("michi.diagnostics.service")

AUDIO_EXTS = frozenset({
    ".flac", ".wav", ".mp3", ".ogg", ".opus",
    ".m4a", ".aiff", ".wv", ".ape", ".dsf", ".dff",
})

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS audio_lab_quality_cache (
    path TEXT PRIMARY KEY,
    mtime REAL NOT NULL DEFAULT 0,
    size INTEGER NOT NULL DEFAULT 0,
    container TEXT DEFAULT '',
    codec TEXT DEFAULT '',
    sample_rate INTEGER DEFAULT 0,
    bit_depth INTEGER DEFAULT 0,
    channels INTEGER DEFAULT 0,
    duration REAL DEFAULT 0.0,
    bitrate INTEGER DEFAULT 0,
    quality_category TEXT DEFAULT '',
    quality_label TEXT DEFAULT '',
    warnings_json TEXT DEFAULT '[]',
    error TEXT DEFAULT '',
    analyzed_at TEXT DEFAULT ''
);
"""


class DiagnosticsCache:
    """SQLite cache for diagnostic results.

    Avoids re-analysing files whose mtime and size haven't changed.
    Thread-safe via single connection with WAL mode.
    """

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            from core.paths import app_data_dir
            db_path = os.path.join(app_data_dir(), "diagnostics_cache.db")
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA_SQL)
        self._conn.commit()

    def get(self, filepath: str) -> dict[str, Any] | None:
        """Return cached result if file hasn't changed, else None."""
        try:
            stat = os.stat(filepath)
            mtime = stat.st_mtime
            size = stat.st_size
        except OSError:
            return None

        row = self._conn.execute(
            "SELECT * FROM audio_lab_quality_cache WHERE path=?",
            (filepath,),
        ).fetchone()
        if not row:
            return None

        if row["mtime"] != mtime or row["size"] != size:
            return None

        return {
            "filepath": row["path"],
            "exists": True,
            "error": row["error"] or "",
            "size_mb": round(row["size"] / (1024 * 1024), 1) if row["size"] else 0.0,
            "from_cache": True,
            "format_info": {
                "container": row["container"] or "",
                "codec": row["codec"] or "",
                "sample_rate": row["sample_rate"] or 0,
                "bit_depth": row["bit_depth"] or 0,
                "channels": row["channels"] or 0,
                "duration": row["duration"] or 0.0,
                "bitrate": row["bitrate"] or 0,
                "warnings": json.loads(row["warnings_json"] or "[]"),
            },
            "quality": {
                "category": row["quality_category"] or "",
                "label": row["quality_label"] or "",
            },
        }

    def put(self, filepath: str, result: dict[str, Any]):
        try:
            stat = os.stat(filepath)
            mtime = stat.st_mtime
            size = stat.st_size
        except OSError:
            mtime = 0.0
            size = 0

        fi = result.get("format_info", {})
        q = result.get("quality", {})
        self._conn.execute(
            """INSERT OR REPLACE INTO audio_lab_quality_cache
            (path, mtime, size, container, codec, sample_rate, bit_depth,
             channels, duration, bitrate, quality_category, quality_label,
             warnings_json, error, analyzed_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                filepath, mtime, size,
                fi.get("container", ""), fi.get("codec", ""),
                fi.get("sample_rate", 0), fi.get("bit_depth", 0),
                fi.get("channels", 0), fi.get("duration", 0.0),
                fi.get("bitrate", 0),
                q.get("category", ""), q.get("label", ""),
                json.dumps(fi.get("warnings", [])),
                result.get("error", ""),
                time.strftime("%Y-%m-%dT%H:%M:%S"),
            ),
        )
        self._conn.commit()

    def invalidate(self, filepath: str):
        self._conn.execute(
            "DELETE FROM audio_lab_quality_cache WHERE path=?", (filepath,)
        )
        self._conn.commit()

    def clear(self):
        self._conn.execute("DELETE FROM audio_lab_quality_cache")
        self._conn.commit()

    def stats(self) -> dict[str, Any]:
        row = self._conn.execute(
            "SELECT COUNT(*) as total, "
            "SUM(size) as total_bytes FROM audio_lab_quality_cache"
        ).fetchone()
        total = row["total"] if row else 0
        total_bytes = row["total_bytes"] or 0 if row else 0
        return {"cached_files": total, "total_bytes": total_bytes}

    def close(self):
        self._conn.close()


_GLOBAL_CACHE: DiagnosticsCache | None = None


def _get_cache() -> DiagnosticsCache:
    global _GLOBAL_CACHE
    if _GLOBAL_CACHE is None:
        try:
            _GLOBAL_CACHE = DiagnosticsCache()
        except Exception as e:
            logger.warning("DiagnosticsCache init failed: %s", e)
            _GLOBAL_CACHE = None  # type: ignore
    return _GLOBAL_CACHE  # type: ignore


def analyse_file(filepath: str, use_cache: bool = True) -> dict[str, Any]:
    """Analyse a single audio file and return a technical report.

    Args:
        filepath: Path to audio file.
        use_cache: If True, check cache before analysing.

    Returns dict with keys:
      - filepath, filename, exists, error
      - format_info: dict from format_probe
      - quality: dict from quality_classifier
      - size_mb, duration_str, from_cache (bool)
    """
    if use_cache:
        cache = _get_cache()
        if cache:
            cached = cache.get(filepath)
            if cached:
                return cached

    result: dict[str, Any] = {
        "filepath": filepath,
        "filename": os.path.basename(filepath),
        "exists": os.path.isfile(filepath),
        "error": "",
        "format_info": {},
        "quality": {},
        "size_mb": 0.0,
        "duration_str": "",
        "from_cache": False,
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

    # Cache result
    if use_cache and result["exists"] and not result.get("from_cache"):
        cache = _get_cache()
        if cache:
            import contextlib
            with contextlib.suppress(Exception):
                cache.put(filepath, result)

    return result


def analyse_directory(directory: str,
                      include_spectral: bool = False) -> list[dict[str, Any]]:
    """Analyse all audio files in a directory recursively.

    Args:
        directory: Path to directory.
        include_spectral: If True, also run spectral analysis on WAV files.

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
                result = analyse_file(fp)
                if include_spectral and ext == ".wav":
                    try:
                        sr = result.get("format_info", {}).get("sample_rate", 0)
                        bd = result.get("format_info", {}).get("bit_depth", 0)
                        if sr > 0 and bd > 0:
                            from core.audio_analysis.spectral_authenticator import (
                                analyse_spectral as _analyse_spec,
                                can_analyse,
                            )
                            if can_analyse(fp):
                                spec = _analyse_spec(fp, sr, bd)
                                result["spectral"] = spec
                    except Exception:
                        pass
                results.append(result)
    return results


def _read_wav_metadata(filepath: str) -> dict[str, Any]:
    """Read real sample rate and bit depth from a WAV file."""
    import wave
    meta: dict[str, Any] = {"sample_rate": 0, "bit_depth": 16, "channels": 0, "duration": 0.0}
    try:
        with wave.open(filepath, "rb") as wf:
            meta["sample_rate"] = wf.getframerate()
            meta["channels"] = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            meta["bit_depth"] = sampwidth * 8
            n_frames = wf.getnframes()
            if meta["sample_rate"] > 0:
                meta["duration"] = n_frames / meta["sample_rate"]
    except Exception:
        pass
    return meta


def analyse_spectral(filepath: str) -> dict[str, Any]:
    """Run spectral authenticity analysis on a WAV file.

    Delegates to core/audio_analysis/spectral_authenticator.analyse_spectral.
    Only supports WAV files. Returns verdict or error.

    Before calling the core analyser, obtains real sample rate and bit depth
    from the file header so 96 kHz / 24-bit files are handled correctly.
    """
    if not os.path.isfile(filepath):
        return {"verdict": "ANALYSIS_ERROR", "label": "Error",
                "explanation": "Archivo no encontrado", "error": "Archivo no encontrado"}

    try:
        from core.audio_analysis.spectral_authenticator import (
            analyse_spectral as _analyse,
            can_analyse,
        )

        if not can_analyse(filepath):
            return {"verdict": "ANALYSIS_ERROR", "label": "No soportado",
                    "explanation": "El análisis espectral requiere un archivo WAV PCM.",
                    "error": "Formato no soportado"}

        # Obtain real metadata before analysis
        meta = _read_wav_metadata(filepath)
        real_sr = meta["sample_rate"]
        real_bd = meta["bit_depth"]
        if real_sr <= 0:
            return {"verdict": "ANALYSIS_ERROR", "label": "Error",
                    "explanation": "No se pudo leer la frecuencia de muestreo del archivo.",
                    "error": "sample_rate=0"}

        result = _analyse(
            filepath,
            declared_sample_rate=real_sr,
            declared_bit_depth=real_bd,
        )
        # Inject real metadata into result
        if "metrics" not in result:
            result["metrics"] = {}
        result["metrics"]["declared_sample_rate"] = real_sr
        result["metrics"]["declared_bit_depth"] = real_bd
        return result

    except ImportError as e:
        return {"verdict": "ANALYSIS_ERROR", "label": "Dependencia faltante",
                "explanation": f"numpy no disponible: {e}",
                "error": str(e)}
    except Exception as e:
        logger.exception("Spectral analysis failed")
        return {"verdict": "ANALYSIS_ERROR", "label": "Error",
                "explanation": str(e), "error": str(e)}


def get_badge_for_file(filepath: str) -> dict[str, str]:
    """Return a badge dict for a file based on cached diagnostic data.

    Returns dict with:
      - label: short human-readable string (e.g. "FLAC 24/96")
      - kind: "hires" | "lossless" | "lossy" | "dsd" | "unknown" | "warning"
      - tooltip: longer explanation

    Uses the diagnostics cache if available. If no cache, returns a basic
    badge derived from the file extension.
    """
    cache = _get_cache()
    if cache:
        cached = cache.get(filepath)
        if cached:
            fi = cached.get("format_info", {})
            q = cached.get("quality", {})
            cont = fi.get("container", "").upper()
            sr = fi.get("sample_rate", 0)
            bd = fi.get("bit_depth", 0)
            label = cont if cont else os.path.splitext(filepath)[1].upper().lstrip(".")
            if sr and bd:
                label += f" {bd}/{sr // 1000}"
            elif sr:
                label += f" {sr // 1000} kHz"
            kind = q.get("category", "unknown")
            if kind == "hires":
                tooltip = "Respuesta espectral coherente con resolución Hi-Res"
            elif kind == "lossless":
                tooltip = "Archivo lossless analizado por Audio Lab"
            elif kind == "lossy":
                tooltip = "Archivo con pérdida"
            elif kind == "dsd":
                tooltip = "DSD"
            else:
                tooltip = "Archivo analizado por Audio Lab"
            return {"label": label, "kind": kind, "tooltip": tooltip}

    # Fallback: basic badge from extension
    ext = os.path.splitext(filepath)[1].lower().lstrip(".")
    label = ext.upper() if ext else "?"
    kind = "unknown"
    if ext in ("flac", "wav", "aiff", "alac"):
        kind = "lossless"
    elif ext in ("mp3", "aac", "ogg", "opus"):
        kind = "lossy"
    elif ext in ("dsf", "dff"):
        kind = "dsd"
    return {"label": label, "kind": kind, "tooltip": ""}


def get_spectral_badge(result: dict[str, Any]) -> dict[str, str]:
    """Return a badge dict for a spectral analysis result.

    Returns dict with:
      - label: short label (e.g. "Upsampling sospechoso")
      - kind: "warning" | "info" | "success"
      - tooltip: explanation
    """
    verdict = result.get("verdict", "ANALYSIS_ERROR")
    label = result.get("label", "Error")
    explanation = result.get("explanation", "")

    if verdict in ("HI_RES_COHERENT", "LOSSLESS_COHERENT"):
        kind = "success"
    elif verdict in ("SUSPICIOUS_UPSAMPLING", "POSSIBLE_LOSSY_SOURCE"):
        kind = "warning"
    else:
        kind = "info"

    conf = result.get("confidence", 0)
    if conf:
        explanation += f" (confianza: {conf:.0%})"

    return {"label": label, "kind": kind, "tooltip": explanation}


def generate_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate a comprehensive summary report from a list of per-file analyses.

    Returns dict with:
      - total_files, total_size_mb, total_duration_str
      - format_counts: {ext: count}
      - quality_counts: {category: count}
      - lossless_count, lossy_count, hires_count, dsd_count
      - sample_rates: list of detected rates
      - bit_depths: list of detected depths
      - channels_set: list of detected channel counts
      - missing_bit_depth: list of filepaths without bit_depth
      - missing_duration: list of filepaths without duration
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
    channels_set: set[int] = set()
    errors: list[str] = []
    warnings: list[tuple[str, str]] = []
    missing_bit_depth: list[str] = []
    missing_duration: list[str] = []
    lossless_count = 0
    lossy_count = 0
    hires_count = 0
    dsd_count = 0

    for r in results:
        total_size += r.get("size_mb", 0)
        fi = r.get("format_info", {})
        if fi.get("duration"):
            total_secs += fi["duration"]
        else:
            missing_duration.append(r["filepath"])
        ext = os.path.splitext(r.get("filename", ""))[1].lower().lstrip(".")
        if ext:
            format_counts[ext] = format_counts.get(ext, 0) + 1
        chan = fi.get("channels", 0)
        if chan:
            channels_set.add(chan)
        sr = fi.get("sample_rate", 0)
        if sr:
            sample_rates.add(sr)
        bd = fi.get("bit_depth", 0)
        if bd:
            bit_depths.add(bd)
        else:
            missing_bit_depth.append(r["filepath"])
        if fi.get("is_dsd"):
            dsd_count += 1
        if fi.get("is_lossless"):
            lossless_count += 1
        q = r.get("quality", {})
        cat = q.get("category", "unknown")
        quality_counts[cat] = quality_counts.get(cat, 0) + 1
        if cat == "hires":
            hires_count += 1
        elif cat in ("lossy",):
            lossy_count += 1
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
        "lossless_count": lossless_count,
        "lossy_count": lossy_count,
        "hires_count": hires_count,
        "dsd_count": dsd_count,
        "sample_rates": sorted(sample_rates),
        "bit_depths": sorted(bit_depths),
        "channels": sorted(channels_set),
        "missing_bit_depth": missing_bit_depth,
        "missing_duration": missing_duration,
        "errors": errors,
        "warnings": warnings,
    }
