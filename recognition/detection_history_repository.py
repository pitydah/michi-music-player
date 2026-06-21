"""Detection history repository — CRUD for detected_tracks table."""
import logging
from typing import Optional

from PySide6.QtCore import QObject, Signal

from recognition.models import DetectedTrack

logger = logging.getLogger("astra.recognition.history")


class DetectionHistoryRepository(QObject):
    """Repository for detection history — wraps LibraryDB detected_tracks CRUD."""

    history_changed = Signal()               # Emitted after any mutation
    history_cleared = Signal()

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self._db = db

    def get_all(self, limit: int = 200,
                source_type: str = "") -> list[dict]:
        """Get detection history, optionally filtered by source_type.

        If source_type is empty, returns all; otherwise filters by source column.
        """
        try:
            if source_type:
                rows = self._db._conn.execute(
                    "SELECT * FROM detected_tracks WHERE source = ? "
                    "ORDER BY detected_at DESC LIMIT ?",
                    (source_type, limit)).fetchall()
            else:
                rows = self._db._conn.execute(
                    "SELECT * FROM detected_tracks "
                    "ORDER BY detected_at DESC LIMIT ?",
                    (limit,)).fetchall()
            cols = [desc[0] for desc in
                    self._db._conn.execute("PRAGMA table_info(detected_tracks)").fetchall()]
            return [dict(zip(cols, r, strict=False)) for r in rows]
        except Exception as e:
            logger.warning(f"Failed to get detection history: {e}")
            return []

    def get_recent(self, title: str, artist: str,
                   max_age_hours: int = 24) -> Optional[dict]:
        """Find a recent detection matching title + artist."""
        return self._db.find_detected_track_recent(title, artist, max_age_hours)

    def add(self, track: DetectedTrack):
        """Save a DetectedTrack to the database."""
        try:
            self._db.add_detected_track(
                title=track.title,
                artist=track.artist,
                album=track.album or "",
                year=getattr(track, 'year', 0) or 0,
                genre=getattr(track, 'genre', "") or "",
                duration=getattr(track, 'duration', 0.0) or 0.0,
                source=track.source or "",
                provider=track.provider or "",
                confidence=track.confidence or 0.0,
                isrc=getattr(track, 'isrc', "") or "",
                artwork_url=getattr(track, 'artwork_url', "") or "",
                external_url=getattr(track, 'external_url', "") or "",
                filepath=track.filepath or "",
                matched_library_id=track.matched_library_id or 0,
                raw_json=getattr(track, 'raw_json', "") or "",
            )
            self.history_changed.emit()
        except Exception as e:
            logger.warning(f"Failed to save detection: {e}")

    def delete(self, track_id: int):
        """Delete a specific detection by ID."""
        try:
            self._db.delete_detected_track(track_id)
            self.history_changed.emit()
        except Exception as e:
            logger.warning(f"Failed to delete detection #{track_id}: {e}")

    def clear(self):
        """Clear all detection history."""
        try:
            self._db.clear_detected_tracks()
            self.history_cleared.emit()
            self.history_changed.emit()
        except Exception as e:
            logger.warning(f"Failed to clear history: {e}")

    def count(self, source_type: str = "") -> int:
        """Count detections, optionally by source type."""
        try:
            if source_type:
                row = self._db._conn.execute(
                    "SELECT COUNT(*) FROM detected_tracks WHERE source = ?",
                    (source_type,)).fetchone()
            else:
                row = self._db._conn.execute(
                    "SELECT COUNT(*) FROM detected_tracks").fetchone()
            return row[0] if row else 0
        except Exception:
            return 0

    def get_sources(self) -> list[str]:
        """Get distinct source types from detection history."""
        try:
            rows = self._db._conn.execute(
                "SELECT DISTINCT source FROM detected_tracks ORDER BY source"
            ).fetchall()
            return [r[0] for r in rows]
        except Exception:
            return []
