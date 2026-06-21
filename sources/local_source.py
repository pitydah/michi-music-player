"""LocalSource — wraps LibraryDB as a MusicSource, with FTS5 search engine."""
from sources.base_source import MusicSource, TrackRef
from library.library_db import LibraryDB


class LocalSource(MusicSource):
    def __init__(self, db: LibraryDB):
        self._db = db
        self._engine = None  # lazy SearchEngine

    def list_tracks(self) -> list[TrackRef]:
        items = self._db.get_all()
        return self._to_refs(items)

    def search(self, query: str) -> list[TrackRef]:
        # Use SearchEngine 2.0 for FTS5 + field-filtered queries
        engine = self._get_engine()
        if engine and self._has_field_syntax(query):
            results = engine.search(query, limit=200)
            return self._dicts_to_refs(results)
        # Fallback to LIKE-based search
        return self._to_refs(self._db.get_all(search=query))

    def _get_engine(self):
        if self._engine is None:
            try:
                from library.search_engine import SearchEngine
                self._engine = SearchEngine(self._db._conn)
            except Exception:
                pass
        return self._engine

    @staticmethod
    def _has_field_syntax(query: str) -> bool:
        """Detect if query contains field:value syntax."""
        return ":" in query and any(
            q.split(":")[0].strip().lower() in (
                "artist", "album", "genre", "format", "year",
                "bitrate", "rating", "play_count", "path", "source",
                "bpm", "sample_rate", "channels", "bit_depth",
            ) for q in query.split() if ":" in q)

    def _to_refs(self, items) -> list[TrackRef]:
        return [TrackRef(
            uri=i.filepath,
            title=i.title,
            artist=i.artist,
            album=i.album,
            duration=i.duration,
            cover_path="",
            track_number=i.track_number,
            year=i.year,
            genre=i.genre,
        ) for i in items]

    def _dicts_to_refs(self, rows: list[dict]) -> list[TrackRef]:
        return [TrackRef(
            uri=row.get("filepath", ""),
            title=row.get("title", ""),
            artist=row.get("artist", ""),
            album=row.get("album", ""),
            duration=row.get("duration", 0.0),
            cover_path="",
            track_number=row.get("track_number", 0),
            year=row.get("year", 0),
            genre=row.get("genre", ""),
        ) for row in rows]

    def get_artwork(self, track: TrackRef) -> str | None:
        return track.cover_path or None
