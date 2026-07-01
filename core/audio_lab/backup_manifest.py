"""Backup Manifest — genera manifiesto de preservación de la biblioteca.

No copia archivos. Genera JSON/CSV con metadatos de cada archivo.
"""

from __future__ import annotations

import csv
import io
import json
import os
from typing import Any


def generate_manifest(conn, include_hash: bool = False) -> list[dict[str, Any]]:
    """Generate a preservation manifest for all tracks in the library.

    Args:
        conn: SQLite connection (or object with .execute).
        include_hash: If True, compute SHA256 for each file (SLOW).

    Returns list of dicts per track.
    """
    manifest: list[dict[str, Any]] = []

    if conn is None:
        return manifest

    try:
        rows = conn.execute(
            "SELECT filepath, size, sample_rate, bit_depth, duration, "
            "title, artist, album, genre, year, ext, bitrate "
            "FROM media_items WHERE deleted_at IS NULL"
        ).fetchall()
    except Exception:
        return manifest

    for row in rows:
        fp = row[0]
        entry = {
            "filepath": fp,
            "filename": os.path.basename(fp) if fp else "",
            "size": row[1] or 0,
            "size_mb": round((row[1] or 0) / (1024 * 1024), 1),
            "format": (row[10] or "").lstrip(".").upper(),
            "sample_rate": row[2] or 0,
            "bit_depth": row[3] or 0,
            "duration_sec": row[4] or 0.0,
            "bitrate": row[11] or 0,
            "title": row[5] or "",
            "artist": row[6] or "",
            "album": row[7] or "",
            "genre": row[8] or "",
            "year": row[9] or 0,
        }

        if include_hash and fp and os.path.isfile(fp):
            entry["sha256"] = _compute_hash(fp)
        else:
            entry["sha256"] = ""

        manifest.append(entry)

    return manifest


def manifest_to_json(manifest: list[dict]) -> str:
    return json.dumps(manifest, indent=2, ensure_ascii=False)


def manifest_to_csv(manifest: list[dict]) -> str:
    if not manifest:
        return ""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(manifest[0].keys()))
    w.writeheader()
    w.writerows(manifest)
    return buf.getvalue()


def _compute_hash(filepath: str) -> str:
    import hashlib
    try:
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""
