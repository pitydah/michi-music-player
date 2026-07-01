"""Library Health — resumen ligero de estado de la biblioteca usando cache existente.

No analiza archivos. Solo consulta DB y cache de diagnóstico.
"""

from __future__ import annotations

from typing import Any


def compute_health(conn, cache=None) -> dict[str, Any]:
    """Compute library health summary from DB and diagnostics cache.

    Args:
        conn: SQLite connection to library DB (or object with .execute).
        cache: Optional DiagnosticsCache instance. If None, skips cache metrics.

    Returns dict with keys:
        total_tracks, analysed_tracks, pending_analysis, error_analysis,
        hires_count, lossless_count, lossy_count, dsd_count,
        spectral_warnings, missing_metadata, missing_covers, missing_lyrics,
        total_size_mb, total_duration_str
    """
    result: dict[str, Any] = {
        "total_tracks": 0,
        "analysed_tracks": 0,
        "pending_analysis": 0,
        "error_analysis": 0,
        "hires_count": 0,
        "lossless_count": 0,
        "lossy_count": 0,
        "dsd_count": 0,
        "spectral_warnings": 0,
        "missing_metadata": 0,
        "missing_covers": 0,
        "missing_lyrics": 0,
        "total_size_mb": 0.0,
        "total_duration_str": "",
    }

    if conn is None:
        return result


    try:
        # Total tracks
        row = conn.execute(
            "SELECT COUNT(*) FROM media_items WHERE deleted_at IS NULL"
        ).fetchone()
        result["total_tracks"] = row[0] if row else 0

        # Analysis status counts
        rows = conn.execute(
            "SELECT analysis_status, COUNT(*) as cnt FROM media_items "
            "WHERE deleted_at IS NULL GROUP BY analysis_status"
        ).fetchall()
        for status, cnt in rows:
            if status == "done":
                result["analysed_tracks"] = cnt
            elif status == "pending":
                result["pending_analysis"] = cnt
            elif status == "error":
                result["error_analysis"] = cnt

        # Quality counts
        qrows = conn.execute(
            "SELECT quality, COUNT(*) as cnt FROM media_items "
            "WHERE deleted_at IS NULL AND quality != '' GROUP BY quality"
        ).fetchall()
        for q, cnt in qrows:
            if q == "hires":
                result["hires_count"] = cnt
            elif q == "lossless":
                result["lossless_count"] = cnt
            elif q == "lossy":
                result["lossy_count"] = cnt
            elif q == "dsd":
                result["dsd_count"] = cnt

        # Spectral warnings
        spec_row = conn.execute(
            "SELECT COUNT(*) FROM media_items WHERE deleted_at IS NULL "
            "AND spectral_verdict IN ('SUSPICIOUS_UPSAMPLING', 'POSSIBLE_LOSSY_SOURCE')"
        ).fetchone()
        result["spectral_warnings"] = spec_row[0] if spec_row else 0

        # Missing metadata
        meta_row = conn.execute(
            "SELECT COUNT(*) FROM media_items WHERE deleted_at IS NULL "
            "AND (title IS NULL OR title = '' OR artist IS NULL OR artist = '')"
        ).fetchone()
        result["missing_metadata"] = meta_row[0] if meta_row else 0

        # Total size
        size_row = conn.execute(
            "SELECT COALESCE(SUM(size), 0) FROM media_items WHERE deleted_at IS NULL"
        ).fetchone()
        total_bytes = size_row[0] if size_row else 0
        result["total_size_mb"] = round(total_bytes / (1024 * 1024), 1)

        # Duration
        dur_row = conn.execute(
            "SELECT COALESCE(SUM(duration), 0) FROM media_items WHERE deleted_at IS NULL"
        ).fetchone()
        total_secs = dur_row[0] if dur_row else 0
        m, s = divmod(int(total_secs), 60)
        h, m = divmod(m, 60)
        result["total_duration_str"] = f"{h}h {m}m {s}s" if h else f"{m}m {s}s"

    except Exception:
        import logging
        logging.getLogger("michi.health").warning("Library health query failed", exc_info=True)

    return result
