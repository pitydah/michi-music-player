"""LibraryRefreshCoordinator — central point for refreshing all library models."""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject

logger = logging.getLogger("michi.refresh_coordinator")


class LibraryRefreshCoordinator(QObject):
    """Coordinates refreshes while preserving the complete library query state."""

    def __init__(self, track_model=None, album_model=None, artist_model=None,
                 folder_model=None, library_bridge=None, parent=None):
        super().__init__(parent)
        self._track = track_model
        self._album = album_model
        self._artist = artist_model
        self._folder = folder_model
        self._lib = library_bridge

    def refresh_all(self):
        self.refresh_tracks()
        self.refresh_albums()
        self.refresh_artists()
        self.refresh_folders()

    def refresh_tracks(self):
        if self._track and hasattr(self._track, "refresh"):
            self._track.refresh(
                search=self._get("_search_query", ""),
                artist=self._get("_filter_artist", ""),
                album=self._get("_filter_album", ""),
                fmt=self._get("_filter_format", ""),
                genre=self._get("_filter_genre", ""),
                composer=self._get("_filter_composer", ""),
                year=self._get("_filter_year", ""),
                folder=self._get("_filter_folder", ""),
                favorites=bool(self._get("_filter_favorites", False)),
                unplayed=bool(self._get("_filter_unplayed", False)),
                missing=bool(self._get("_filter_missing", False)),
                sort=self._get("_sort_key", "title"),
                asc=bool(self._get("_sort_asc", True)),
            )

    def refresh_albums(self):
        if self._album and hasattr(self._album, "refresh"):
            self._album.refresh(
                **self._catalog_filters(), sort="year", asc=False,
            )

    def refresh_artists(self):
        if self._artist and hasattr(self._artist, "refresh"):
            self._artist.refresh(**self._catalog_filters(), sort="name", asc=True)

    def refresh_folders(self):
        if self._folder and hasattr(self._folder, "refresh"):
            self._folder.refresh()

    def refresh_after_metadata(self, track_id: int):
        self.refresh_tracks()
        self.refresh_albums()

    def refresh_after_artwork(self, album_key: str):
        self.refresh_albums()

    def refresh_after_scan(self, summary: dict | None = None):
        self.refresh_all()

    def refresh_after_playlist_change(self):
        self.refresh_tracks()

    def refresh_after_relink(self):
        self.refresh_tracks()
        self.refresh_albums()

    def refresh_after_file_delete(self):
        self.refresh_all()

    def refresh_after_import(self, summary: dict | None = None):
        self.refresh_all()

    def activate_songs(self):
        if self._track and self._track.count == 0 and not self._track.loading:
            self.refresh_tracks()

    def activate_albums(self):
        if self._album and self._album.count == 0 and not self._album.loading:
            self.refresh_albums()

    def activate_artists(self):
        if self._artist and self._artist.count == 0 and not self._artist.loading:
            self.refresh_artists()

    def activate_folders(self):
        if self._folder and self._folder.count == 0 and not self._folder.loading:
            self.refresh_folders()

    def _get(self, name: str, default):
        return getattr(self._lib, name, default) if self._lib is not None else default

    def _catalog_filters(self) -> dict:
        return {
            "search": self._get("_search_query", ""),
            "artist": self._get("_filter_artist", ""),
            "album": self._get("_filter_album", ""),
            "fmt": self._get("_filter_format", ""),
            "genre": self._get("_filter_genre", ""),
            "composer": self._get("_filter_composer", ""),
            "year": self._get("_filter_year", ""),
            "folder": self._get("_filter_folder", ""),
            "favorites": bool(self._get("_filter_favorites", False)),
            "unplayed": bool(self._get("_filter_unplayed", False)),
            "missing": bool(self._get("_filter_missing", False)),
        }
