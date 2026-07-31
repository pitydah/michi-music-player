"""LibraryBridge — connects QML Library page to QueryService with pagination, filters, sort."""
from __future__ import annotations

import contextlib
import json
import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal, Property, Slot, QUrl
from PySide6.QtGui import QDesktopServices

logger = logging.getLogger("michi.library_bridge")


class LibraryState(Enum):
    INITIALIZING = "INITIALIZING"
    NO_SOURCES = "NO_SOURCES"
    SOURCE_EMPTY = "SOURCE_EMPTY"
    SOURCE_OFFLINE = "SOURCE_OFFLINE"
    SOURCE_PERMISSION_ERROR = "SOURCE_PERMISSION_ERROR"
    SCANNING = "SCANNING"
    INDEXING = "INDEXING"
    LOADING = "LOADING"
    READY = "READY"
    FILTERED_EMPTY = "FILTERED_EMPTY"
    DATABASE_ERROR = "DATABASE_ERROR"
    QUERY_ERROR = "QUERY_ERROR"
    PARTIAL_RESULTS = "PARTIAL_RESULTS"
    CANCELLED = "CANCELLED"
    MISSING_CONTENT = "MISSING_CONTENT"


class LibraryBridge(QObject):
    """Adapt library queries and canonical track actions for QML."""

    dataChanged = Signal()
    stateChanged = Signal()
    formatsChanged = Signal()

    def __init__(self, db: Any | None = None, search_engine: Any | None = None,
                 player_service: Any | None = None, query_service: Any | None = None,
                 query_executor: Any | None = None, worker_manager: Any | None = None,
                 job_bridge: Any | None = None, track_action_service: Any | None = None,
                 library_sources_service: Any | None = None,
                 library_service: Any | None = None, songs_service: Any | None = None,
                 track_service: Any | None = None, genres_service: Any | None = None,
                 collection_service: Any | None = None,
                 folder_tree_model: Any | None = None,
                 playlists_bridge: Any | None = None, container: Any | None = None,
                 queue_service: Any | None = None,
                 artwork_svc: Any | None = None, cover_provider: Any | None = None,
                 parent: QObject | None = None) -> None:
        assert query_service is not None, "LibraryBridge: query_service is REQUIRED"
        super().__init__(parent)
        self._db = db
        self._search_engine = search_engine
        self._playback_ctrl = player_service
        self._query_svc = query_service
        self._qe = query_executor
        self._job_bridge = job_bridge
        self._tas = track_action_service
        self._queue_service = queue_service
        self._sources_svc = library_sources_service
        self._playlists_bridge = playlists_bridge
        self._container = container
        self._library_svc = library_service
        self._songs_svc = songs_service
        self._track_svc = track_service
        self._genres_svc = genres_service
        self._collection_svc = collection_service
        self._folder_tree_model = folder_tree_model
        self._artwork_svc = artwork_svc
        self._cover_provider = cover_provider
        self._search_query = ""
        self._sort_key = "title"
        self._sort_asc = True
        self._filter_artist = ""
        self._filter_album = ""
        self._filter_format = ""
        self._filter_folder = ""
        self._filter_genre = ""
        self._filter_composer = ""
        self._filter_year = ""
        self._filter_favorites = False
        self._filter_unplayed = False
        self._filter_missing = False
        self._filter_missing_artist = False
        self._filter_missing_album = False
        self._page_size = 100
        self._loaded_count = 0
        self._error_message = ""
        self._last_operation = ""
        self._last_op_ok = False
        self._state = LibraryState.INITIALIZING
        self._formats: list[str] | None = None
        from ui_qml.models.TrackListModel import TrackListModel
        from ui_qml.models.AlbumListModel import AlbumListModel
        from ui_qml.models.ArtistListModel import ArtistListModel
        from ui_qml.models.FolderTreeModel import FolderTreeModel
        self._track_model = TrackListModel(query_service=self._query_svc, query_executor=self._qe, parent=self)
        self._album_model = AlbumListModel(query_service=self._query_svc, query_executor=self._qe, parent=self)
        self._artist_model = ArtistListModel(query_service=self._query_svc, query_executor=self._qe, parent=self)
        self._folder_model = FolderTreeModel(query_service=self._query_svc, query_executor=self._qe, parent=self)
        from ui_qml_bridge.library_refresh_coordinator import LibraryRefreshCoordinator
        self._refresh_coordinator = LibraryRefreshCoordinator(
            track_model=self._track_model, album_model=self._album_model,
            artist_model=self._artist_model, folder_model=self._folder_model,
            library_bridge=self, parent=self,
        )
        for model in (self._track_model, self._album_model, self._artist_model):
            model.loadingChanged.connect(self._sync_state)
            model.initializedChanged.connect(self._sync_state)
            model.errorChanged.connect(self._sync_state)
            model.cancelledChanged.connect(self._sync_state)
            model.countChanged.connect(self._on_model_data_changed)
            model.totalCountChanged.connect(self._on_model_data_changed)

    def set_cover_provider(self, provider) -> None:
        """Second-phase wiring for the CoverProvider (Corrección 3).

        ``cover_provider`` is created after this bridge in BridgeFactory, so
        the constructor may receive ``None``. The two-phase ``_wire_bridges``
        pass injects the real provider here.
        """
        self._cover_provider = provider

    def _set_state(self, state: LibraryState) -> None:
        if state == self._state:
            return
        self._state = state
        self.stateChanged.emit()

    def _has_active_filters(self) -> bool:
        return bool(
            self._search_query or self._filter_artist or self._filter_album
            or self._filter_format or self._filter_folder or self._filter_genre
            or self._filter_composer or self._filter_year
            or self._filter_favorites or self._filter_unplayed or self._filter_missing
        )

    def _source_state(self) -> LibraryState | None:
        if not self._sources_svc or not hasattr(self._sources_svc, "list"):
            return None
        sources = self._sources_svc.list()
        if not sources:
            return LibraryState.NO_SOURCES
        enabled = [source for source in sources if source.get("enabled", True)]
        if enabled and not any(source.get("available", True) for source in enabled):
            return LibraryState.SOURCE_OFFLINE
        if any(source.get("error_code") == "PERMISSION_DENIED" for source in enabled):
            return LibraryState.SOURCE_PERMISSION_ERROR
        return None

    def _sync_state(self) -> None:
        models = (self._track_model, self._album_model, self._artist_model)
        if any(model.errorCode for model in models):
            failed = next(model for model in models if model.errorCode)
            self._error_message = failed.errorMessage
            self._set_state(LibraryState.QUERY_ERROR)
            return
        if any(model.cancelled for model in models):
            self._set_state(LibraryState.CANCELLED)
            return
        if any(model.loading for model in models):
            self._set_state(LibraryState.LOADING)
            return
        if not all(model.initialized for model in models):
            self._set_state(LibraryState.INITIALIZING)
            return
        if self._track_model.totalCount == 0:
            if self._has_active_filters():
                self._set_state(LibraryState.FILTERED_EMPTY)
                return
            source_state = self._source_state()
            self._set_state(source_state or LibraryState.SOURCE_EMPTY)
            return
        self._set_state(LibraryState.READY)

    def _on_model_data_changed(self) -> None:
        self._loaded_count = min(self._page_size, self.visibleCount)
        self._sync_state()
        self.dataChanged.emit()

    @Property(str, notify=stateChanged)
    def state(self):
        return self._state.value

    @Property(int, notify=dataChanged)
    def songCount(self):
        return self._track_model.totalCount if self._track_model else 0

    @Property(int, notify=dataChanged)
    def albumCount(self):
        return self._album_model.totalCount if self._album_model else 0

    @Property(int, notify=dataChanged)
    def artistCount(self):
        return self._artist_model.count if self._artist_model else 0

    @Property(int, notify=dataChanged)
    def totalSongs(self):
        return self.songCount

    @Property(int, notify=dataChanged)
    def visibleCount(self):
        return self._track_model.totalCount if self._track_model else 0

    @Property(int, notify=dataChanged)
    def loadedCount(self):
        return self._loaded_count

    @Property(bool, notify=dataChanged)
    def hasMoreSongs(self):
        return self._track_model.hasMore if self._track_model else False

    @Property("QVariantList", notify=dataChanged)
    def songs(self):
        model = self._track_model
        if model is None:
            return []
        try:
            return [model.get(i) for i in range(min(model.count, 100))]
        except Exception:
            return []

    @Property("QVariantList", notify=dataChanged)
    def albums(self):
        return []

    @Property("QVariantList", notify=dataChanged)
    def artists(self):
        return []

    @Property("QVariantList", notify=dataChanged)
    def folders(self):
        return []

    @Property("QVariant", notify=dataChanged)
    def trackModel(self):
        return self._track_model

    @Property("QVariant", notify=dataChanged)
    def albumModel(self):
        return self._album_model

    @Property("QVariant", notify=dataChanged)
    def artistModel(self):
        return self._artist_model

    @Property("QVariant", notify=dataChanged)
    def folderModel(self):
        return self._folder_model

    @Property("QVariant", constant=True)
    def folderTreeModel(self):
        """Return the hierarchical filesystem model for QML TreeView."""
        return self._folder_tree_model

    @Property(int, notify=dataChanged)
    def pageSize(self):
        return self._page_size

    @Property(str, notify=dataChanged)
    def errorMessage(self):
        return self._error_message

    @Property(str, notify=dataChanged)
    def activeSortKey(self):
        return self._sort_key

    @Property(bool, notify=dataChanged)
    def activeSortAscending(self):
        return self._sort_asc

    @Property(str, notify=dataChanged)
    def activeFormatFilter(self):
        return self._filter_format

    @Property("QVariantList", notify=formatsChanged)
    def availableFormats(self):
        """Reactive, cached list of distinct audio formats in the library."""
        if self._formats is None:
            self._refresh_formats()
        return self._formats or []

    def _refresh_formats(self) -> None:
        """Recompute the cached format list and notify QML consumers."""
        previous = self._formats
        try:
            if self._query_svc and hasattr(self._query_svc, "get_formats"):
                self._formats = list(self._query_svc.get_formats())
            else:
                self._formats = []
        except Exception as error:
            logger.debug("availableFormats refresh failed: %s", error)
            self._formats = []
        if previous != self._formats:
            self.formatsChanged.emit()

    @Property(str, notify=dataChanged)
    def activeGenreFilter(self):
        return self._filter_genre

    @Property(str, notify=dataChanged)
    def searchQuery(self):
        return self._search_query

    @Slot(int, int, result="QVariantList")
    def getSongsPage(self, page: int, pageSize: int):
        if not self._query_svc:
            return []
        try:
            offset = page * pageSize
            items = self._query_svc.fetch_tracks(
                offset=offset, limit=pageSize,
                search=self._search_query, artist=self._filter_artist,
                album=self._filter_album, fmt=self._filter_format,
                folder=self._filter_folder, genre=self._filter_genre,
                composer=self._filter_composer, year=self._filter_year,
                favorites=self._filter_favorites, unplayed=self._filter_unplayed,
                missing=self._filter_missing,
                sort=self._sort_key, asc=self._sort_asc,
            )
            return [self._dict_to_qml(t) for t in items]
        except Exception as e:
            logger.debug("getSongsPage failed: %s", e)
            return []

    @Slot(result=dict)
    def loadNextPage(self):
        self._loaded_count = min(self._loaded_count + self._page_size, self.visibleCount)
        self.dataChanged.emit()
        return {"ok": True, "loaded": self._loaded_count, "visible": self.visibleCount, "has_more": self.hasMoreSongs}

    @Slot(int, result=dict)
    def setPageSize(self, size: int):
        self._page_size = max(20, min(500, int(size)))
        self._loaded_count = min(self._loaded_count, self.visibleCount)
        self.dataChanged.emit()
        return {"ok": True, "page_size": self._page_size}

    @Slot(result=dict)
    def resetPaging(self):
        self._loaded_count = min(self._page_size, self.visibleCount)
        self.dataChanged.emit()
        return {"ok": True, "loaded": self._loaded_count}

    def _refresh_track_query(self):
        if self._refresh_coordinator:
            self._refresh_coordinator.refresh_tracks()
            self._refresh_coordinator.refresh_albums()
            self._refresh_coordinator.refresh_artists()

    @Slot(str, result=dict)
    def setSearchQuery(self, query: str):
        self._search_query = query
        self._refresh_track_query()
        self._loaded_count = min(self._page_size, self.visibleCount)
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def clearSearch(self):
        self._search_query = ""
        self._refresh_track_query()
        self._loaded_count = min(self._page_size, self.visibleCount)
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(str, result=dict)
    def search(self, query: str):
        return self.setSearchQuery(query)

    @Slot(str, result=dict)
    def setFormatFilter(self, fmt: str):
        self._filter_format = fmt
        self._filter_favorites = False
        self._filter_unplayed = False
        self._filter_missing = False
        self._refresh_track_query()
        self._loaded_count = min(self._page_size, self.visibleCount)
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(str, result=dict)
    def setGenreFilter(self, genre: str):
        self._filter_genre = genre
        self._refresh_track_query()
        self._loaded_count = min(self._page_size, self.visibleCount)
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(str, result=dict)
    def setComposerFilter(self, composer: str):
        self._filter_composer = composer
        self._refresh_track_query()
        self._loaded_count = min(self._page_size, self.visibleCount)
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(str, result=dict)
    def setYearFilter(self, year: str):
        self._filter_year = year
        self._refresh_track_query()
        self._loaded_count = min(self._page_size, self.visibleCount)
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(str, result=dict)
    def filterByArtist(self, artist: str):
        self._filter_artist = artist
        self._filter_album = ""
        self._refresh_track_query()
        self._loaded_count = min(self._page_size, self.visibleCount)
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(str, result=dict)
    def setArtistFilter(self, artist: str):
        return self.filterByArtist(artist)

    @Slot(str, result=dict)
    def filterByAlbum(self, album_key: str):
        self._filter_album = album_key
        self._refresh_track_query()
        self._loaded_count = min(self._page_size, self.visibleCount)
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(str, result=dict)
    def setAlbumFilter(self, album_key: str):
        return self.filterByAlbum(album_key)

    @Slot(str, result=dict)
    def setFolderFilter(self, folder_path: str):
        self._filter_folder = folder_path
        self._refresh_track_query()
        self._loaded_count = min(self._page_size, self.visibleCount)
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def setFavoritesFilter(self):
        self._filter_favorites = True
        self._filter_unplayed = False
        self._filter_missing = False
        self._refresh_track_query()
        self._loaded_count = min(self._page_size, self.visibleCount)
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def setUnplayedFilter(self):
        self._filter_favorites = False
        self._filter_unplayed = True
        self._filter_missing = False
        self._refresh_track_query()
        self._loaded_count = min(self._page_size, self.visibleCount)
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def setMissingFilter(self):
        self._filter_favorites = False
        self._filter_unplayed = False
        self._filter_missing = True
        self._refresh_track_query()
        self._loaded_count = min(self._page_size, self.visibleCount)
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def clearSpecialFilters(self):
        self._filter_favorites = False
        self._filter_unplayed = False
        self._filter_missing = False
        self._refresh_track_query()
        self._loaded_count = min(self._page_size, self.visibleCount)
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def clearFilters(self):
        self._search_query = ""
        self._filter_artist = ""
        self._filter_album = ""
        self._filter_format = ""
        self._filter_folder = ""
        self._filter_genre = ""
        self._filter_composer = ""
        self._filter_year = ""
        self._filter_favorites = False
        self._filter_unplayed = False
        self._filter_missing = False
        self._filter_missing_artist = False
        self._filter_missing_album = False
        self._refresh_track_query()
        self._loaded_count = min(self._page_size, self.visibleCount)
        self._error_message = ""
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(str, result=dict)
    def sortBy(self, key: str):
        if key == self._sort_key:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_key = key
            self._sort_asc = True
        self._refresh_track_query()
        self._loaded_count = min(self._page_size, self.visibleCount)
        self.dataChanged.emit()
        return {"ok": True, "key": key, "asc": self._sort_asc}

    @Slot(result=dict)
    def refresh(self, limit: int = 0):
        del limit
        self._error_message = ""
        self._set_state(LibraryState.LOADING)
        if self._refresh_coordinator:
            self._refresh_coordinator.refresh_all()
        self._loaded_count = min(self._page_size, self.visibleCount)
        self._refresh_formats()
        self._sync_state()
        self.dataChanged.emit()
        return {"ok": True, "count": self.visibleCount}

    @Slot(result=dict)
    def ensureLoaded(self):
        models = (self._track_model, self._album_model, self._artist_model)
        if any(model.loading for model in models) or all(model.initialized for model in models):
            self._sync_state()
            return {"ok": True, "refreshed": False, "count": self.visibleCount}
        result = self.refresh()
        return {**result, "refreshed": True}

    @Slot(int, result=dict)
    def playTrackById(self, track_id: int):
        if not self._tas:
            return {"ok": False, "error": "NO_TRACK_ACTION_SERVICE"}
        return self._tas.play_track(track_id)

    @Slot(str, result=dict)
    def play_song(self, filepath: str):
        if not filepath:
            return {"ok": False, "error": "EMPTY_FILEPATH"}
        if not self._queue_service:
            return {"ok": False, "error": "NO_QUEUE_SERVICE"}
        if not filepath.startswith(("http://", "https://", "radio://", "stream://")) and not Path(filepath).is_file():
            return {"ok": False, "error": "FILE_NOT_FOUND"}
        track = {"filepath": filepath}
        if self._query_svc:
            with contextlib.suppress(Exception):
                track = self._query_svc.fetch_track_by_filepath(filepath) or track
        try:
            return self._queue_service.replace_and_play([track])
        except Exception as e:
            return {"ok": False, "error": f"PLAYBACK_ERROR: {e}"}

    @Slot(int, result=dict)
    def enqueueTrackById(self, track_id: int):
        if not self._tas:
            return {"ok": False, "error": "NO_TRACK_ACTION_SERVICE"}
        return self._tas.enqueue_track(track_id)

    @Slot(int, result=dict)
    def playNextTrackById(self, track_id: int):
        if not self._tas:
            return {"ok": False, "error": "NO_TRACK_ACTION_SERVICE"}
        return self._tas.play_next(track_id)

    @Slot(int, int, result=dict)
    def addTrackToPlaylistById(self, track_id: int, playlist_id: int):
        if not self._query_svc:
            return {"ok": False, "error": "NO_QUERY_SERVICE"}
        try:
            track = self._query_svc.fetch_track_internal(track_id)
            if not track or not track.get("filepath"):
                return {"ok": False, "error": "NOT_FOUND"}
            pb = getattr(self, '_playlists_bridge', None)
            if pb:
                return pb.addTrackToPlaylist(playlist_id, filepath=track["filepath"])
            return {"ok": False, "error": "NO_PLAYLISTS_BRIDGE"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(int, result=dict)
    def revealTrackById(self, track_id: int):
        if not self._query_svc:
            return {"ok": False, "error": "NO_QUERY_SERVICE"}
        try:
            track = self._query_svc.fetch_track_internal(track_id)
            if not track or not track.get("filepath"):
                return {"ok": False, "error": "NOT_FOUND"}
            parent = str(Path(track["filepath"]).parent)
            QDesktopServices.openUrl(QUrl.fromLocalFile(parent))
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(int, result=dict)
    def toggleFavoriteById(self, track_id: int):
        if not self._tas:
            return {"ok": False, "error": "NO_TRACK_ACTION_SERVICE"}
        try:
            result = self._tas.toggle_favorite(track_id)
            if result.get("ok"):
                self._refresh_coordinator.refresh_tracks()
                self._sync_state()
                self.dataChanged.emit()
            return result
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, bool, result=dict)
    def setFavoriteBulk(self, track_ids_json: str, favorite: bool):
        """Set favorite status on multiple tracks in one SQL operation."""
        if not self._db or not hasattr(self._db, "conn"):
            return {"ok": False, "error": "NO_DB"}
        try:
            track_ids = json.loads(track_ids_json)
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"INVALID_JSON: {e}"}
        if (
            not isinstance(track_ids, list)
            or not track_ids
            or any(not isinstance(track_id, int) or isinstance(track_id, bool)
                   for track_id in track_ids)
        ):
            return {"ok": False, "error": "INVALID_TRACK_IDS"}

        unique_ids = list(dict.fromkeys(track_ids))
        placeholders = ", ".join("?" for _ in unique_ids)
        try:
            if favorite:
                sql = (
                    "INSERT OR IGNORE INTO favorites (track_id) "
                    "SELECT filepath FROM media_items "
                    f"WHERE deleted_at IS NULL AND id IN ({placeholders})"
                )
            else:
                sql = (
                    "DELETE FROM favorites WHERE track_id IN ("
                    "SELECT filepath FROM media_items "
                    f"WHERE id IN ({placeholders}))"
                )
            with self._db.conn:
                cursor = self._db.conn.execute(sql, unique_ids)
            self._refresh_coordinator.refresh_tracks()
            self._sync_state()
            self.dataChanged.emit()
            return {"ok": True, "favorite": favorite, "count": cursor.rowcount}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _tracks_for_bulk(self, track_ids_json: str) -> tuple[list[dict[str, Any]], str | None]:
        """Fetch canonical queue payloads for track IDs with one SQL query."""
        if not self._db or not hasattr(self._db, "conn"):
            return [], "NO_DB"
        try:
            track_ids = json.loads(track_ids_json)
        except json.JSONDecodeError as error:
            return [], f"INVALID_JSON: {error}"
        if (
            not isinstance(track_ids, list)
            or not track_ids
            or any(not isinstance(track_id, int) or isinstance(track_id, bool)
                   for track_id in track_ids)
        ):
            return [], "INVALID_TRACK_IDS"
        unique_ids = list(dict.fromkeys(track_ids))
        placeholders = ", ".join("?" for _ in unique_ids)
        rows = self._db.conn.execute(
            "SELECT id, filepath, title, artist, album, album_key, track_uid, duration "
            f"FROM media_items WHERE deleted_at IS NULL AND id IN ({placeholders})",
            unique_ids,
        ).fetchall()
        by_id = {
            int(row[0]): {
                "track_id": int(row[0]),
                "filepath": row[1] or "",
                "title": row[2] or "",
                "artist": row[3] or "",
                "album": row[4] or "",
                "album_key": row[5] or "",
                "track_uid": row[6] or "",
                "duration": float(row[7] or 0),
                "cover_key": f"album:{row[5]}" if row[5] else f"file:{row[1]}",
            }
            for row in rows
            if row[1]
        }
        tracks = [by_id[track_id] for track_id in unique_ids if track_id in by_id]
        return tracks, None if tracks else "NO_TRACKS"

    @Slot(str, result=dict)
    def enqueueBulk(self, track_ids_json: str):
        """Append multiple tracks with one SQL read and one queue mutation."""
        if not self._queue_service:
            return {"ok": False, "error": "NO_QUEUE_SERVICE"}
        try:
            tracks, error = self._tracks_for_bulk(track_ids_json)
            if error:
                return {"ok": False, "error": error}
            return self._queue_service.enqueue(tracks, play_now=False)
        except Exception as error:
            return {"ok": False, "error": str(error)}

    @Slot(str, result=dict)
    def playBulk(self, track_ids_json: str):
        """Replace playback with multiple tracks using one queue mutation."""
        if not self._queue_service:
            return {"ok": False, "error": "NO_QUEUE_SERVICE"}
        try:
            tracks, error = self._tracks_for_bulk(track_ids_json)
            if error:
                return {"ok": False, "error": error}
            return self._queue_service.replace_and_play(tracks, 0)
        except Exception as error:
            return {"ok": False, "error": str(error)}

    def _set_group_favorite(
        self,
        where_clause: str,
        params: tuple[Any, ...],
        favorite: bool,
    ) -> dict:
        """Set favorite state for every track matching a trusted SQL predicate."""
        if not self._db or not hasattr(self._db, "conn"):
            return {"ok": False, "error": "NO_DB"}
        try:
            count_row = self._db.conn.execute(
                f"SELECT COUNT(*) FROM media_items WHERE deleted_at IS NULL AND {where_clause}",
                params,
            ).fetchone()
            matched = int(count_row[0]) if count_row else 0
            if favorite:
                sql = (
                    "INSERT OR IGNORE INTO favorites (track_id) "
                    "SELECT filepath FROM media_items "
                    f"WHERE deleted_at IS NULL AND {where_clause}"
                )
            else:
                sql = (
                    "DELETE FROM favorites WHERE track_id IN ("
                    "SELECT filepath FROM media_items WHERE deleted_at IS NULL AND "
                    f"{where_clause} UNION SELECT CAST(id AS TEXT) FROM media_items "
                    f"WHERE deleted_at IS NULL AND {where_clause} UNION SELECT track_uid "
                    f"FROM media_items WHERE deleted_at IS NULL AND {where_clause})"
                )
                params = params * 3
            with self._db.conn:
                self._db.conn.execute(sql, params)
            self._refresh_coordinator.refresh_all()
            self._sync_state()
            self.dataChanged.emit()
            return {"ok": True, "favorite": favorite, "count": matched}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, bool, result=dict)
    def setAlbumFavorite(self, album_key: str, favorite: bool):
        """Set favorite state for every track belonging to an album."""
        key = str(album_key or "").strip()
        if not key:
            return {"ok": False, "error": "EMPTY_ALBUM_KEY"}
        return self._set_group_favorite(
            "COALESCE(NULLIF(album_key, ''), album, '') = ? COLLATE NOCASE",
            (key,),
            favorite,
        )

    @Slot(str, bool, result=dict)
    def setArtistFavorite(self, artist_name: str, favorite: bool):
        """Set favorite state for every track belonging to an artist."""
        artist = str(artist_name or "").strip()
        if not artist:
            return {"ok": False, "error": "EMPTY_ARTIST_NAME"}
        return self._set_group_favorite(
            "(artist = ? COLLATE NOCASE OR albumartist = ? COLLATE NOCASE)",
            (artist, artist),
            favorite,
        )

    @Slot(str, result=dict)
    def enqueueSong(self, filepath: str):
        if not filepath:
            return {"ok": False, "error": "EMPTY_FILEPATH"}
        if not self._queue_service:
            return {"ok": False, "error": "NO_QUEUE_SERVICE"}
        return self._queue_service.enqueue({"filepath": filepath}, play_now=False)

    @Slot(str, result=dict)
    def revealInFileManager(self, filepath: str):
        if not filepath or not Path(filepath).exists():
            return {"ok": False, "error": "FILE_NOT_FOUND"}
        parent = str(Path(filepath).parent)
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(parent))
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def getAlbumDetail(self, album_key: str):
        if not self._query_svc:
            return {"ok": False, "error": "NO_QUERY_SERVICE"}
        try:
            detail = self._query_svc.fetch_album_detail(album_key)
            if not detail:
                return {"ok": False, "error": "NOT_FOUND"}
            return {"ok": True, **detail}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result="QVariantList")
    def getAlbumTracks(self, album_key: str):
        if not self._query_svc:
            return []
        try:
            tracks = self._query_svc.fetch_album_tracks_internal(album_key)
            return [self._dict_to_qml(t) for t in tracks]
        except Exception:
            return []

    @Slot(str, result=dict)
    def playAlbum(self, album_key: str):
        if not self._query_svc:
            return {"ok": False, "error": "NO_QUERY_SERVICE"}
        if not self._queue_service:
            return {"ok": False, "error": "NO_QUEUE_SERVICE"}
        try:
            internal = self._query_svc.fetch_album_tracks_internal(album_key)
            if not internal:
                return {"ok": False, "error": "NO_TRACKS"}
            tracks = [t for t in internal if t.get("filepath")]
            if not tracks:
                return {"ok": False, "error": "NO_VALID_TRACKS"}
            return self._queue_service.replace_and_play(tracks, 0)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def enqueueAlbum(self, album_key: str):
        if not self._query_svc:
            return {"ok": False, "error": "NO_QUERY_SERVICE"}
        if not self._queue_service:
            return {"ok": False, "error": "NO_QUEUE_SERVICE"}
        try:
            internal = self._query_svc.fetch_album_tracks_internal(album_key)
            if not internal:
                return {"ok": False, "error": "NO_TRACKS"}
            tracks = [t for t in internal if t.get("filepath")]
            if not tracks:
                return {"ok": False, "error": "NO_VALID_TRACKS"}
            return self._queue_service.enqueue(tracks, play_now=False)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def playAlbumNext(self, album_key: str):
        """Insert album tracks right after the current track in the queue."""
        if not self._query_svc:
            return {"ok": False, "error": "NO_QUERY_SERVICE"}
        if not self._queue_service:
            return {"ok": False, "error": "NO_QUEUE_SERVICE"}
        try:
            internal = self._query_svc.fetch_album_tracks_internal(album_key)
            if not internal:
                return {"ok": False, "error": "NO_TRACKS"}
            tracks = [t for t in internal if t.get("filepath")]
            if not tracks:
                return {"ok": False, "error": "NO_VALID_TRACKS"}
            idx = self._queue_service.current_index + 1
            return self._queue_service.insert(idx, tracks)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def getArtistDetail(self, artist_name: str):
        if not self._query_svc:
            return {"ok": False, "error": "NO_QUERY_SERVICE"}
        try:
            detail = self._query_svc.fetch_artist_detail(artist_name)
            if not detail:
                return {"ok": False, "error": "NOT_FOUND"}
            return {"ok": True, **detail}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result="QVariantList")
    def getArtistTracks(self, artist_name: str):
        if not self._query_svc:
            return []
        try:
            tracks = self._query_svc.fetch_artist_tracks_internal(artist_name)
            return [self._dict_to_qml(t) for t in tracks]
        except Exception:
            return []

    @Slot(str, result="QVariantList")
    def getArtistAlbums(self, artist_name: str):
        if not self._query_svc:
            return []
        try:
            tracks = self._query_svc.fetch_artist_tracks_internal(artist_name)
            seen = {}
            for t in tracks:
                key = t.get("album_key", "")
                if key and key not in seen:
                    seen[key] = True
            return [{"album_key": k, "title": k} for k in seen]
        except Exception:
            return []

    @Slot(str, result="QVariantList")
    def getRelatedArtists(self, artist_name: str):
        if not self._query_svc:
            return []
        try:
            detail = self._query_svc.fetch_artist_detail(artist_name)
            if not detail:
                return []
            return detail.get("related_artists", [])
        except Exception:
            return []

    @Slot(str, result=dict)
    def playArtist(self, artist_name: str):
        if not self._query_svc:
            return {"ok": False, "error": "NO_QUERY_SERVICE"}
        if not self._queue_service:
            return {"ok": False, "error": "NO_QUEUE_SERVICE"}
        try:
            internal = self._query_svc.fetch_artist_tracks_internal(artist_name)
            if not internal:
                return {"ok": False, "error": "NO_TRACKS"}
            tracks = [t for t in internal if t.get("filepath")]
            if not tracks:
                return {"ok": False, "error": "NO_VALID_TRACKS"}
            return self._queue_service.replace_and_play(tracks, 0)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result="QVariantList")
    def getFolderTracks(self, folder_path: str):
        if not self._query_svc:
            return []
        try:
            tracks = self._query_svc.fetch_folder_tracks_internal(folder_path)
            return [self._dict_to_qml(t) for t in tracks]
        except Exception:
            return []

    @Slot(str, result=dict)
    def filterByFolder(self, folder_path: str):
        return self.setFolderFilter(folder_path)

    @Slot(str, result=dict)
    def playFolder(self, folder_path: str):
        if not self._query_svc:
            return {"ok": False, "error": "NO_QUERY_SERVICE"}
        if not self._queue_service:
            return {"ok": False, "error": "NO_QUEUE_SERVICE"}
        try:
            internal = self._query_svc.fetch_folder_tracks_internal(folder_path)
            if not internal:
                return {"ok": False, "error": "NO_TRACKS"}
            tracks = [t for t in internal if t.get("filepath")]
            if not tracks:
                return {"ok": False, "error": "NO_VALID_TRACKS"}
            return self._queue_service.replace_and_play(tracks, 0)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def openFolder(self, folder_path: str):
        if not folder_path or not Path(folder_path).is_dir():
            return {"ok": False, "error": "DIR_NOT_FOUND"}
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result="QVariantList")
    def splitPath(self, path: str):
        if not path:
            return []
        return [p for p in path.split("/") if p]

    @Slot(str, result=dict)
    def addFolder(self, folder_path: str):
        if not folder_path:
            return {"ok": False, "error": "EMPTY_PATH"}
        if not Path(folder_path).is_dir():
            return {"ok": False, "error": "DIR_NOT_FOUND"}
        jb = self._job_bridge
        if not jb:
            return {"ok": False, "error": "NO_JOB_SERVICE"}
        result = jb.runJob("library_scan", folder_path)
        if result.get("ok") and self._db:
            ssvc = getattr(self, '_sources_svc', None)
            if ssvc:
                ssvc.add(folder_path)
        return {"ok": True, "path": folder_path, "job": True}

    @Slot(result=str)
    def getMusicFolder(self):
        try:
            from core.settings_manager import get as sg
            return sg("general/music_folder") or os.path.expanduser("~/Música")
        except Exception:
            return os.path.expanduser("~/Música")

    @Slot(str, result=dict)
    def setMusicFolder(self, folder_path: str):
        if not folder_path or not Path(folder_path).is_dir():
            return {"ok": False, "error": "DIR_NOT_FOUND"}
        try:
            from core.settings_manager import set_ as ss
            ss("general/music_folder", folder_path)
            return {"ok": True, "path": folder_path}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def scanMusicFolder(self):
        folder = self.getMusicFolder()
        if folder and Path(folder).is_dir():
            return self.addFolder(folder)
        return {"ok": False, "error": "MUSIC_FOLDER_NOT_FOUND"}

    @Slot(str, result=dict)
    def addMedia(self, path: str):
        if not path:
            return {"ok": False, "error": "EMPTY_PATH"}
        p = Path(path)
        if not p.exists():
            return {"ok": False, "error": "FILE_NOT_FOUND"}
        try:
            if not self._job_bridge:
                return {"ok": False, "error": "NO_JOB_SERVICE"}
            scan_path = path if p.is_dir() else str(p.parent)
            self._job_bridge.runJob("library_scan", scan_path)
            return {"ok": True, "type": "folder" if p.is_dir() else "file", "path": path, "job": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _dict_to_qml(self, item: dict) -> dict:
        result = dict(item)
        track_id = result.get("track_id")
        if track_id is not None:
            result.setdefault("public_ref", f"track_{track_id}")
        result.setdefault("album_artist", result.get("albumartist", ""))
        result.setdefault("cover_key", result.get("album_key", ""))
        if "filepath" in result:
            result["path"] = result["filepath"]
        return result

    # ── LibraryService bridge ──

    @Slot(result=dict)
    def loadLibrary(self):
        svc = getattr(self, '_library_svc', None)
        if svc and hasattr(svc, 'load'):
            return svc.load()
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    @Slot(str, result=dict)
    def refreshTab(self, tab: str = ""):
        svc = getattr(self, '_library_svc', None)
        if svc and hasattr(svc, 'refresh_tab'):
            return svc.refresh_tab(tab)
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    # ── SongsService bridge ──

    @Slot(str, result=dict)
    def loadSongs(self, filter_json: str = ""):
        svc = getattr(self, '_songs_svc', None)
        if svc and hasattr(svc, 'load'):
            try:
                filters = json.loads(filter_json) if filter_json else {}
                if not isinstance(filters, dict):
                    return {"ok": False, "error": "INVALID_FILTERS"}
                return svc.load(filters)
            except json.JSONDecodeError as e:
                return {"ok": False, "error": f"INVALID_JSON: {e}"}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    @Slot(str, result=dict)
    def playSongs(self, items_json: str = ""):
        if not self._queue_service:
            return {"ok": False, "error": "NO_QUEUE_SERVICE"}
        try:
            items = json.loads(items_json) if items_json else []
            if not isinstance(items, list) or not items:
                return {"ok": False, "error": "NO_ITEMS"}
            if not all(isinstance(item, dict) for item in items):
                return {"ok": False, "error": "INVALID_ITEMS"}
            return self._queue_service.replace_and_play(items, 0)
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"INVALID_JSON: {e}"}

    @Slot(str, result=dict)
    def toggleFavorite(self, filepath: str):
        svc = getattr(self, '_songs_svc', None)
        if svc and hasattr(svc, 'toggle_favorite'):
            return svc.toggle_favorite(filepath)
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    # ── TrackService bridge ──

    @Slot(str, result=dict)
    def editTrackMetadata(self, filepath: str):
        svc = getattr(self, '_track_svc', None)
        if svc and hasattr(svc, 'edit_metadata'):
            return {"ok": False, "error": "METADATA_REQUIRED", "path": filepath}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    @Slot(str, str, result=dict)
    def saveTrackMetadata(self, filepath: str, metadata_json: str):
        svc = getattr(self, '_track_svc', None)
        if svc and hasattr(svc, 'edit_metadata'):
            try:
                metadata = json.loads(metadata_json)
                return svc.edit_metadata(filepath, metadata)
            except json.JSONDecodeError as e:
                return {"ok": False, "error": f"INVALID_JSON: {e}"}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    @Slot(str, result=dict)
    def locateTrackFile(self, filepath: str):
        svc = getattr(self, '_track_svc', None)
        if svc and hasattr(svc, 'locate_file'):
            return svc.locate_file(filepath)
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    # ── GenresService bridge ──

    @Slot(result="QVariantList")
    def listGenres(self):
        svc = getattr(self, '_genres_svc', None)
        if svc and hasattr(svc, 'list_genres'):
            return svc.list_genres()
        return []

    @Slot(str, result=dict)
    def playGenre(self, genre: str):
        svc = getattr(self, '_genres_svc', None)
        if svc and hasattr(svc, 'play_genre'):
            return svc.play_genre(genre)
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    @Slot(str, result=dict)
    def enqueueGenre(self, genre: str):
        """Append every track of a genre to the queue without starting playback."""
        if not genre:
            return {"ok": False, "error": "EMPTY_GENRE"}
        svc = getattr(self, '_genres_svc', None)
        if not svc or not hasattr(svc, 'get_genre_tracks'):
            return {"ok": False, "error": "SERVICE_UNAVAILABLE"}
        if not self._queue_service:
            return {"ok": False, "error": "NO_QUEUE_SERVICE"}
        try:
            tracks = svc.get_genre_tracks(genre)
            if not tracks:
                return {"ok": False, "error": "NO_TRACKS"}
            return self._queue_service.enqueue(tracks, play_now=False)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, str, result=dict)
    def normalizeGenre(self, old_name: str, new_name: str):
        svc = getattr(self, '_genres_svc', None)
        if svc and hasattr(svc, 'normalize_genre'):
            return svc.normalize_genre(old_name, new_name)
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    # ── Slots called from sub-pages (discovery) ──

    @Slot(int, int, result=dict)
    def getGenres(self, offset: int = 0, limit: int = 100):
        svc = getattr(self, '_query_svc', None)
        if svc is None or not hasattr(svc, "fetch_genres"):
            entries = self.listGenres()
            page = entries[max(0, offset):max(0, offset) + max(1, limit)]
            return {"items": page, "total": len(entries), "has_more": offset + len(page) < len(entries)}
        try:
            items = svc.fetch_genres(offset=offset, limit=limit)
            total = svc.count_genres()
            return {"items": items, "total": total, "has_more": offset + len(items) < total}
        except Exception as e:
            return {"items": [], "total": 0, "has_more": False, "error": str(e)}

    @Slot(int, int, result=dict)
    def getComposers(self, offset: int = 0, limit: int = 100):
        svc = getattr(self, '_query_svc', None)
        if svc is None:
            return {"items": [], "total": 0, "has_more": False}
        try:
            if hasattr(svc, "fetch_composers"):
                items = svc.fetch_composers(offset=offset, limit=limit)
                total = svc.count_composers()
            else:
                entries = svc.list_composers()
                items = entries[max(0, offset):max(0, offset) + max(1, limit)]
                total = len(entries)
            return {"items": items, "total": total, "has_more": offset + len(items) < total}
        except Exception as e:
            return {"items": [], "total": 0, "has_more": False, "error": str(e)}

    @Slot(result="QVariantList")
    def getCollections(self):
        """Return persisted user-defined smart collections."""
        service = self._collection_svc
        return service.list() if service is not None else []

    @Slot(str, str, str, result=dict)
    def createCollection(self, name: str, rules_json: str, logic: str):
        """Create a validated smart collection through CollectionService."""
        if self._collection_svc is None:
            return {"ok": False, "error": "SERVICE_UNAVAILABLE"}
        try:
            rules = json.loads(rules_json)
        except json.JSONDecodeError as error:
            return {"ok": False, "error": f"INVALID_JSON: {error}"}
        if not isinstance(rules, list):
            return {"ok": False, "error": "INVALID_RULES"}
        return self._collection_svc.create(name, rules, logic)

    @Slot(str, result=dict)
    def deleteCollection(self, collection_id: str):
        """Delete one smart collection."""
        if self._collection_svc is None:
            return {"ok": False, "error": "SERVICE_UNAVAILABLE"}
        return self._collection_svc.delete(collection_id)

    @Slot(str, int, int, result=dict)
    def queryCollection(self, collection_id: str, limit: int, offset: int):
        """Return one page of tracks matching a smart collection."""
        if self._collection_svc is None:
            return {"ok": False, "error": "SERVICE_UNAVAILABLE", "items": [], "total": 0}
        return self._collection_svc.query(collection_id, limit, offset)

    @Slot(str, result=dict)
    def saveCollection(self, collection_json: str):
        """Compatibility adapter for the previous collection editor contract."""
        if self._collection_svc is None:
            return {"ok": False, "error": "SERVICE_UNAVAILABLE"}
        try:
            collection = json.loads(collection_json)
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"INVALID_JSON: {e}"}
        if not isinstance(collection, dict):
            return {"ok": False, "error": "INVALID_COLLECTION"}
        operator_aliases = {
            "equals": "eq",
            "not_equals": "neq",
            "greater_than": "gt",
            "less_than": "lt",
        }
        rules = collection.get("rules", [])
        if isinstance(rules, list):
            rules = [
                {**rule, "operator": operator_aliases.get(rule.get("operator"), rule.get("operator"))}
                for rule in rules
                if isinstance(rule, dict)
            ]
        collection_id = str(collection.get("id") or "").strip()
        values = {
            "name": collection.get("name"),
            "rules": rules,
            "logic": collection.get("logic", collection.get("matchMode", "AND")),
        }
        if collection_id:
            return self._collection_svc.update(collection_id, **values)
        return self._collection_svc.create(values["name"], values["rules"], values["logic"])

    @Slot(result="QVariantList")
    def getYears(self):
        svc = getattr(self, '_query_svc', None)
        if svc is None:
            return []
        try:
            return svc.list_years()
        except Exception:
            return []

    @Slot(result=dict)
    def getSourcesList(self):
        ssvc = getattr(self, '_sources_svc', None)
        if ssvc and hasattr(ssvc, 'get_sources'):
            try:
                sources = ssvc.get_sources()
                return {"ok": True, "sources": sources} if isinstance(sources, list) else {"ok": True, "sources": []}
            except Exception as e:
                return {"ok": False, "error": str(e), "sources": []}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE", "sources": []}

    @Slot(int, result=dict)
    def disableSource(self, source_id: int):
        ssvc = getattr(self, '_sources_svc', None)
        if ssvc and hasattr(ssvc, 'disable_source'):
            try:
                return ssvc.disable_source(source_id)
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    @Slot(int, result=dict)
    def enableSource(self, source_id: int):
        ssvc = getattr(self, '_sources_svc', None)
        if ssvc and hasattr(ssvc, 'enable_source'):
            try:
                return ssvc.enable_source(source_id)
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    @Slot(int, result=dict)
    def scanSource(self, source_id: int):
        ssvc = getattr(self, '_sources_svc', None)
        if ssvc and hasattr(ssvc, 'scan_source'):
            try:
                return ssvc.scan_source(source_id)
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    @Slot(int, result=dict)
    def removeSource(self, source_id: int):
        ssvc = getattr(self, '_sources_svc', None)
        if ssvc and hasattr(ssvc, 'remove_source'):
            try:
                return ssvc.remove_source(source_id)
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    @Slot(int, result=dict)
    def getSourceDetail(self, source_id: int):
        ssvc = getattr(self, '_sources_svc', None)
        if ssvc and hasattr(ssvc, 'get_source_detail'):
            try:
                return ssvc.get_source_detail(source_id)
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    @Slot(result=dict)
    def playAllFiltered(self):
        if self._queue_service:
            try:
                tracks = self._query_svc.fetch_filtered_tracks_internal({
                    "artist": self._filter_artist,
                    "album": self._filter_album,
                    "genre": self._filter_genre,
                    "composer": self._filter_composer,
                    "format": self._filter_format,
                    "folder": self._filter_folder,
                    "year": self._filter_year,
                    "favorites": self._filter_favorites,
                    "unplayed": self._filter_unplayed,
                }, 500)
                if tracks:
                    return self._queue_service.replace_and_play(tracks, 0)
                return {"ok": False, "error": "NO_TRACKS"}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "NO_QUEUE_SERVICE"}

    def _current_query_filters(self) -> dict[str, Any]:
        """Snapshot of the active QML filter contract for query_service calls."""
        return {
            "search": self._search_query,
            "artist": self._filter_artist,
            "album": self._filter_album,
            "fmt": self._filter_format,
            "folder": self._filter_folder,
            "genre": self._filter_genre,
            "composer": self._filter_composer,
            "year": self._filter_year,
            "favorites": self._filter_favorites,
            "unplayed": self._filter_unplayed,
            "missing": self._filter_missing,
            "sort": self._sort_key,
            "asc": self._sort_asc,
        }

    def _collect_filtered_ids(self) -> list[int]:
        """Page through the query service to collect every matching track id."""
        if not self._query_svc:
            return []
        filters = self._current_query_filters()
        page_size = 500
        offset = 0
        ids: list[int] = []
        try:
            total: int | None = None
            if hasattr(self._query_svc, "count_tracks"):
                with contextlib.suppress(Exception):
                    total = int(self._query_svc.count_tracks(**filters))
            while True:
                page = self._query_svc.fetch_tracks(offset=offset, limit=page_size, **filters)
                if not page:
                    break
                for track in page:
                    track_id = track.get("track_id") or track.get("id")
                    if track_id and track_id not in ids:
                        ids.append(int(track_id))
                offset += page_size
                if len(page) < page_size:
                    break
                if total is not None and offset >= total:
                    break
            return ids
        except Exception as error:
            logger.debug("selectAllFiltered collect failed: %s", error)
            return ids

    @Slot(result=dict)
    def selectAllFiltered(self):
        """Return a SelectionDescriptor covering every track matching the filters.

        The descriptor carries ``mode="all_filtered"`` plus the active filters so
        QML can select across all pages without loading every row into the model.
        """
        ids = self._collect_filtered_ids()
        return {
            "ok": True,
            "mode": "all_filtered",
            "ids": ids,
            "count": len(ids),
            "filters": {
                "search": self._search_query,
                "artist": self._filter_artist,
                "album": self._filter_album,
                "format": self._filter_format,
                "folder": self._filter_folder,
                "genre": self._filter_genre,
                "composer": self._filter_composer,
                "year": self._filter_year,
                "favorites": self._filter_favorites,
                "unplayed": self._filter_unplayed,
                "missing": self._filter_missing,
                "sort": self._sort_key,
                "asc": self._sort_asc,
            },
        }

    @Slot(int, result=dict)
    def rescanSource(self, source_id: int = 0):
        if source_id > 0:
            ssvc = getattr(self, '_sources_svc', None)
            if ssvc and hasattr(ssvc, 'scan_source'):
                return ssvc.scan_source(source_id)
        return self.scanMusicFolder()

    @Slot(int, result=dict)
    def cancelScan(self, source_id: int = 0):
        ssvc = getattr(self, '_sources_svc', None)
        if ssvc and hasattr(ssvc, 'cancel_scan'):
            try:
                return ssvc.cancel_scan()
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    @Slot(result=dict)
    def getMetadataCompleteness(self):
        if not self._query_svc or not hasattr(self._query_svc, 'get_metadata_completeness'):
            return {"ok": False, "error": "SERVICE_UNAVAILABLE"}
        try:
            result = self._query_svc.get_metadata_completeness()
            return {"ok": True, **result}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(result="QVariantList")
    def getFormats(self):
        """Return distinct audio formats present in the library."""
        if self._query_svc and hasattr(self._query_svc, "get_formats"):
            return self._query_svc.get_formats()
        return []

    @Slot(result=dict)
    def runArtworkBackfill(self):
        """Run backfill for missing album artwork and invalidate recovered covers."""
        if not self._artwork_svc or not hasattr(self._artwork_svc, "backfill_missing_album_art"):
            return {"ok": False, "error": "BACKFILL_UNAVAILABLE"}
        try:
            result = self._artwork_svc.backfill_missing_album_art()
        except Exception as e:
            return {"ok": False, "error": str(e)}
        if not isinstance(result, dict):
            return {"ok": False, "error": "BACKFILL_INVALID_RESULT"}
        keys = [f"album:{k}" for k in result.get("recovered_keys", [])]
        if keys and self._cover_provider and hasattr(self._cover_provider, "invalidateMany"):
            self._cover_provider.invalidateMany(json.dumps(keys))
        return {"ok": True, **result}
