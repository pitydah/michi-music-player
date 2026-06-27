"""FolderSource — wraps folder_index as a MusicSource, enriched with DB metadata."""

import os

from sources.base_source import MusicSource, TrackRef
from library.folder_index import list_audio_files, list_subfolders
from library.metadata_normalizer import infer_metadata_from_filename


AUDIO_EXTS = {".mp3", ".flac", ".ogg", ".wav", ".m4a", ".aac", ".opus",
              ".dsf", ".dff", ".aiff", ".ape", ".wv", ".wma", ".spx"}


class FolderSource(MusicSource):
    def __init__(self, root: str, db=None):
        self.root = root
        self._db = db

    def list_tracks(self) -> list[TrackRef]:
        if self._db:
            items = self._db.get_all_by_directory(self.root, exact=True)
            if items:
                return self._items_to_refs(items)
        return self._files_to_refs(list_audio_files(self.root))

    def search(self, query: str) -> list[TrackRef]:
        q = query.lower()
        return [t for t in self.list_tracks()
                if q in t.title.lower() or q in t.artist.lower()
                or q in t.album.lower() or q in os.path.dirname(t.uri).lower()]

    def _files_to_refs(self, paths: list[str]) -> list[TrackRef]:
        refs = []
        for p in paths:
            fname = os.path.splitext(os.path.basename(p))[0]
            inferred = infer_metadata_from_filename(p)
            refs.append(TrackRef(
                uri=p,
                title=inferred.get("title", "") or fname,
                artist=str(inferred.get("artist", "") or ""),
                album=str(inferred.get("album", "") or ""),
                duration=0.0,
            ))
        return refs

    def _items_to_refs(self, items) -> list[TrackRef]:
        refs = []
        for item in items:
            title = item.title or ""
            artist = item.artist or ""
            if not title and item.filepath:
                inferred = infer_metadata_from_filename(item.filepath)
                title = inferred.get("title", "") or os.path.splitext(
                    os.path.basename(item.filepath))[0]
                artist = artist or str(inferred.get("artist", "") or "")
            refs.append(TrackRef(
                uri=item.filepath,
                title=title or os.path.splitext(os.path.basename(item.filepath))[0],
                artist=artist or "Artista desconocido",
                album=item.album or "Sin álbum",
                duration=item.duration or 0.0,
                track_number=item.track_number or 0,
                year=item.year or 0,
                genre=item.genre or "—",
            ))
        return refs

    def list_folders(self, path: str | None = None) -> list[str]:
        return list_subfolders(path or self.root)

    def list_folder_tracks(self, path: str) -> list[TrackRef]:
        if self._db:
            items = self._db.get_all_by_directory(path, exact=True)
            if items:
                return self._items_to_refs(items)
        return self._files_to_refs(list_audio_files(path))

    def get_folder_stats(self, path: str) -> dict:
        """Return aggregated stats for a directory."""
        files = list_audio_files(path)
        folders = list_subfolders(path)
        total_duration = 0.0
        if self._db:
            row = self._db._conn.execute(
                "SELECT COALESCE(SUM(duration), 0) FROM media_items "
                "WHERE directory = ? AND deleted_at IS NULL",
                (path,)).fetchone()
            if row:
                total_duration = row[0] or 0.0
        return {
            "file_count": len(files),
            "folder_count": len(folders),
            "total_duration": total_duration,
        }

    def set_db(self, db):
        self._db = db
