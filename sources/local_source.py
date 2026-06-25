"""LocalSource — wraps LibraryDB as a MusicSource, with FTS5 search engine."""
import os
from sources.base_source import MusicSource, TrackRef
from library.library_db import LibraryDB


def _fallback_title(item) -> str:
    t = getattr(item, "title", "") or ""
    if t:
        return t
    fp = getattr(item, "filepath", "")
    if fp:
        return os.path.splitext(os.path.basename(fp))[0]
    return "Sin título"


def _fallback_artist(item) -> str:
    return getattr(item, "artist", "") or "Artista desconocido"


def _fallback_album(item) -> str:
    return getattr(item, "album", "") or "Sin álbum"


def _fallback_genre(item) -> str:
    return getattr(item, "genre", "") or "—"


class LocalSource(MusicSource):
    def __init__(self, db: LibraryDB):
        self._db = db
        self._engine = None  # lazy SearchEngine

    def list_tracks(self) -> list[TrackRef]:
        items = self._db.get_all()
        return self._to_refs(items)

    def search(self, query: str) -> list[TrackRef]:
        engine = self._get_engine()
        if engine:
            results = engine.search(query, limit=200)
            return self._dicts_to_refs(results)
        # Fallback to LIKE-based search when SearchEngine unavailable
        return self._to_refs(self._db.get_all(search=query))

    def _get_engine(self):
        if self._engine is None:
            try:
                from library.search_engine import SearchEngine
                self._engine = SearchEngine(self._db._conn)
            except Exception:
                pass
        return self._engine

    def _to_refs(self, items) -> list[TrackRef]:
        return [TrackRef(
            uri=i.filepath,
            title=_fallback_title(i),
            artist=_fallback_artist(i),
            album=_fallback_album(i),
            duration=getattr(i, "duration", 0.0) or 0.0,
            cover_path="",
            track_number=getattr(i, "track_number", 0) or 0,
            year=getattr(i, "year", 0) or 0,
            genre=_fallback_genre(i),
        ) for i in items]

    def _dicts_to_refs(self, rows: list[dict]) -> list[TrackRef]:
        return [TrackRef(
            uri=row.get("filepath", ""),
            title=row.get("title", "") or os.path.splitext(os.path.basename(row.get("filepath", "")))[0] or "Sin título",
            artist=row.get("artist", "") or "Artista desconocido",
            album=row.get("album", "") or "Sin álbum",
            duration=row.get("duration", 0.0),
            cover_path="",
            track_number=row.get("track_number", 0),
            year=row.get("year", 0),
            genre=row.get("genre", "") or "—",
        ) for row in rows]

    def get_artwork(self, track: TrackRef) -> str | None:
        return track.cover_path or None
