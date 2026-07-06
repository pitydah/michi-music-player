"""LibraryRefreshCoordinator — central point for refreshing all library models."""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject

logger = logging.getLogger("michi.refresh_coordinator")


class LibraryRefreshCoordinator(QObject):
    """Coordinates refresh of all paged library models."""

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
        if self._track and hasattr(self._track, 'refresh'):
            self._track.refresh(
                search=self._get_search(),
                artist=self._get_artist(),
                album=self._get_album(),
                fmt=self._get_format(),
                sort=self._get_sort(),
                asc=self._get_asc(),
            )

    def refresh_albums(self):
        if self._album and hasattr(self._album, 'refresh'):
            self._album.refresh(search=self._get_search())

    def refresh_artists(self):
        if self._artist and hasattr(self._artist, 'refresh'):
            self._artist.refresh(search=self._get_search())

    def refresh_folders(self):
        if self._folder and hasattr(self._folder, 'refresh'):
            self._folder.refresh()

    def refresh_after_metadata(self, track_id: int):
        self.refresh_tracks()
        self.refresh_albums()

    def refresh_after_artwork(self, album_key: str):
        self.refresh_albums()

    def refresh_after_scan(self, summary: dict | None = None):
        self.refresh_all()

    def refresh_after_playlist_change(self):
        pass

    def _get_search(self):
        return getattr(self._lib, '_search_query', '')

    def _get_artist(self):
        return getattr(self._lib, '_filter_artist', '')

    def _get_album(self):
        return getattr(self._lib, '_filter_album', '')

    def _get_format(self):
        return getattr(self._lib, '_filter_format', '')

    def _get_sort(self):
        return getattr(self._lib, '_sort_key', 'title')

    def _get_asc(self):
        return getattr(self._lib, '_sort_asc', True)
