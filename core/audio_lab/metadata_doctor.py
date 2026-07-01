"""Metadata Doctor — analiza metadatos de la biblioteca sin modificarlos.

Sugiere normalizaciones. No aplica cambios.
"""

from __future__ import annotations

import os
import re
from typing import Any


def suggest_normalizations(conn) -> list[dict[str, Any]]:
    """Analiza la biblioteca y sugiere normalizaciones de metadatos.

    Returns list of dicts con:
        type: tipo de sugerencia
        filepath: ruta del archivo
        field: campo afectado
        current: valor actual
        suggested: valor sugerido
        reason: explicación
    """
    suggestions: list[dict[str, Any]] = []

    if conn is None:
        return suggestions

    try:
        rows = conn.execute(
            "SELECT filepath, title, artist, album, genre, year, track_number "
            "FROM media_items WHERE deleted_at IS NULL"
        ).fetchall()
    except Exception:
        return suggestions

    for row in rows:
        fp, title, artist, album, genre, year, track = row

        if not title:
            suggestions.append(_sug(fp, "title", "", os.path.splitext(os.path.basename(fp or ""))[0],
                                     "Título vacío — usar nombre de archivo"))

        if artist and _has_extra_spaces(artist):
            suggestions.append(_sug(fp, "artist", artist, _clean_spaces(artist),
                                     "Espacios dobles"))

        if album and _has_extra_spaces(album):
            suggestions.append(_sug(fp, "album", album, _clean_spaces(album),
                                     "Espacios dobles"))

        if year and (not str(year).isdigit() or int(year) < 1900 or int(year) > 2030):
            suggestions.append(_sug(fp, "year", str(year), "",
                                     f"Año inválido: {year}"))

        if not genre:
            suggestions.append(_sug(fp, "genre", "", "Desconocido",
                                     "Género vacío"))

    return suggestions


def _sug(fp, field, current, suggested, reason) -> dict:
    return {
        "filepath": fp,
        "field": field,
        "current": current,
        "suggested": suggested,
        "reason": reason,
    }


def _has_extra_spaces(text: str) -> bool:
    return "  " in text or text.startswith(" ") or text.endswith(" ")


def _clean_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
