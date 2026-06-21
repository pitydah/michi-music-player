"""LocalSource — wraps LibraryDB as a MusicSource."""

from sources.base_source import MusicSource, TrackRef
from library.library_db import LibraryDB


class LocalSource(MusicSource):
    def __init__(self, db: LibraryDB):
        self._db = db

    def list_tracks(self) -> list[TrackRef]:
        return self._to_refs(self._db.get_all())

    def search(self, query: str) -> list[TrackRef]:
        return self._to_refs(self._db.get_all(search=query))

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

    def get_artwork(self, track: TrackRef) -> str | None:
        return track.cover_path or None
