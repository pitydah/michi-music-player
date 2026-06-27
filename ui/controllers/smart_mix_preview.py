"""SmartMixPreview — lightweight preview/count layer for smart mixes.

Returns counts and descriptions WITHOUT mutating the UI (no model populate,
no fade_content, no playback). Used by MixHubPage for its dynamic cards.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from library.library_db import LibraryDB
from library.smart_mixes import (
    get_daily_mix, get_unplayed, get_popular,
)

logger = logging.getLogger("michi.smart_preview")


@dataclass
class MixPreview:
    key: str
    label: str
    description: str
    count: int
    empty_reason: str
    files: list[str]


class SmartMixPreview:
    """Provides counts and file lists for smart mixes without touching window state."""

    _MIXES = {
        "mix_daily": {
            "label": "Mix diario",
            "description": "Lo que más escuchaste esta semana, combinado en una lista nueva.",
            "fn": lambda: get_daily_mix(limit=30),
            "empty_reason": (
                "Aún no hay historial de reproducción. "
                "Escuchá música para generar tu mix diario."
            ),
        },
        "mix_unplayed": {
            "label": "No escuchadas",
            "description": "Canciones de tu biblioteca que aún no reprodujiste.",
            "fn": lambda: get_unplayed(limit=30),
            "empty_reason": "¡Escuchaste todo! No hay canciones pendientes en tu biblioteca.",
        },
        "mix_popular": {
            "label": "Más escuchadas",
            "description": "Las canciones con mayor número de reproducciones.",
            "fn": lambda: get_popular(limit=30),
            "empty_reason": (
                "Todavía no hay canciones con reproducciones. "
                "Empezá a escuchar música para generar este mix."
            ),
        },
        "favs": {
            "label": "Favoritos",
            "description": "Canciones que marcaste como favoritas.",
            "fn": lambda: _get_fav_filepaths(),
            "empty_reason": (
                "No tenés favoritos todavía. "
                "Marcá canciones como favoritas para verlas aquí."
            ),
        },
        "recent": {
            "label": "Recientes",
            "description": "Las canciones que reproduciste más recientemente.",
            "fn": lambda: _get_recent_filepaths(),
            "empty_reason": "Aún no hay canciones reproducidas recientemente.",
        },
    }

    def __init__(self, db: LibraryDB):
        self._db = db

    def get_preview(self, key: str) -> MixPreview:
        """Return a MixPreview for the given key. Never raises — returns empty on error."""
        mix = self._MIXES.get(key)
        if not mix:
            return MixPreview(
                key=key, label=key, description="", count=0,
                empty_reason="Mix no disponible.", files=[],
            )
        try:
            files = mix["fn"]()
        except Exception:
            logger.exception("SmartMixPreview failed for key=%s", key)
            files = []

        valid = [f for f in files if isinstance(f, str) and (
            f.startswith("http") or os.path.isfile(f))]
        count = len(valid)
        empty_reason = "" if count > 0 else mix["empty_reason"]

        return MixPreview(
            key=key,
            label=mix["label"],
            description=mix["description"],
            count=count,
            empty_reason=empty_reason,
            files=valid,
        )

    def get_all_previews(self) -> list[MixPreview]:
        return [self.get_preview(k) for k in self._MIXES]


def _get_fav_filepaths() -> list[str]:
    """Get favorite filepaths from LibraryDB."""
    import sqlite3
    from library.library_db import DB_PATH
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT f.track_id, m.filepath FROM favorites f "
            "LEFT JOIN media_items m ON f.track_id = m.filepath OR f.track_id = CAST(m.id AS TEXT) "
            "WHERE m.deleted_at IS NULL AND m.filepath IS NOT NULL "
            "ORDER BY f.added_at DESC LIMIT 30"
        ).fetchall()
        conn.close()
        return [r["filepath"] for r in rows]
    except Exception:
        logger.exception("_get_fav_filepaths failed")
        return []


def _get_recent_filepaths() -> list[str]:
    """Get recent filepaths from play_history."""
    import sqlite3
    from library.library_db import DB_PATH
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT h.track_id, m.filepath FROM play_history h "
            "LEFT JOIN media_items m ON h.track_id = m.filepath OR h.track_id = CAST(m.id AS TEXT) "
            "WHERE m.deleted_at IS NULL AND m.filepath IS NOT NULL "
            "ORDER BY h.played_at DESC LIMIT 30"
        ).fetchall()
        conn.close()
        return [r["filepath"] for r in rows]
    except Exception:
        logger.exception("_get_recent_filepaths failed")
        return []
