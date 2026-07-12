"""LibraryBridge — connects QML Library page to QueryService with pagination, filters, sort."""
from __future__ import annotations

import subprocess
import os
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Property, Slot


class LibraryBridge(QObject):
    dataChanged = Signal()

    def __init__(self, db=None, search_engine=None, playback_ctrl=None,
                 query_service=None, query_executor=None, worker_manager=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._search_engine = search_engine
        self._playback_ctrl = playback_ctrl
        self._query_svc = query_service
        self._qe = query_executor
        self._search_query = ""
        self._sort_key = "title"
        self._sort_asc = True
        self._filter_artist = ""
        self._filter_album = ""
        self._filter_format = ""
        self._filter_folder = ""
        self._filter_missing_artist = False
        self._filter_missing_album = False
        self._page_size = 100
        self._loaded_count = 0
        self._error_message = ""
        self._last_operation = ""
        self._last_op_ok = False
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

    # ── Properties ──

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
        """DEPRECATED: QML should use trackModel directly."""
        return []

    @Property("QVariantList", notify=dataChanged)
    def albums(self):
        """DEPRECATED: QML should use albumModel directly."""
        return []

    @Property("QVariantList", notify=dataChanged)
    def artists(self):
        """DEPRECATED: QML should use artistModel directly."""
        return []

    @Property("QVariantList", notify=dataChanged)
    def folders(self):
        """DEPRECATED: QML should use folderModel directly."""
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

    @Property(str, notify=dataChanged)
    def searchQuery(self):
        return self._search_query

    # ── Pagination ──

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
                folder=self._filter_folder,
                sort=self._sort_key, asc=self._sort_asc,
            )
            return [self._dict_to_qml(t) for t in items]
        except Exception:
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
        return {"ok": True}

    @Slot(result=dict)
    def resetPaging(self):
        self._loaded_count = min(self._page_size, self.visibleCount)
        self.dataChanged.emit()
        return {"ok": True}

    def _refresh_track_query(self):
        if self._refresh_coordinator:
            self._refresh_coordinator.refresh_tracks()
            self._refresh_coordinator.refresh_albums()
            self._refresh_coordinator.refresh_artists()

    # ── Search ──

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

    @Slot(str)
    def search(self, query: str):
        self.setSearchQuery(query)

    # ── Filters ──

    @Slot(str, result=dict)
    def setFormatFilter(self, fmt: str):
        self._filter_format = fmt
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
    def setGenreFilter(self, genre: str):
        return {"ok": False, "error": "UNSUPPORTED"}

    @Slot(str, result=dict)
    def setFolderFilter(self, folder_path: str):
        self._filter_folder = folder_path
        self._refresh_track_query()
        self._loaded_count = min(self._page_size, self.visibleCount)
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def clearFilters(self):
        self._filter_artist = ""
        self._filter_album = ""
        self._filter_format = ""
        self._filter_folder = ""
        self._filter_missing_artist = False
        self._filter_missing_album = False
        self._refresh_track_query()
        self._loaded_count = min(self._page_size, self.visibleCount)
        self._error_message = ""
        self.dataChanged.emit()
        return {"ok": True}

    # ── Sort ──

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

    # ── Data loading ──

    @Slot(result=dict)
    def refresh(self, limit: int = 0):
        if self._refresh_coordinator:
            self._refresh_coordinator.refresh_all()
        self._loaded_count = min(self._page_size, self.visibleCount)
        self.dataChanged.emit()
        return {"ok": True, "count": self.visibleCount}

    # ── Playback actions (single) ──

    @Slot(int, result=dict)
    def playTrackById(self, track_id: int):
        if not track_id or not self._query_svc:
            return {"ok": False, "error": "NOT_FOUND"}
        try:
            track = self._query_svc.fetch_track_internal(track_id)
            if track and track.get("filepath"):
                return self.play_song(track["filepath"])
            return {"ok": False, "error": "NOT_FOUND"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def play_song(self, filepath: str):
        if not filepath:
            return {"ok": False, "error": "EMPTY_FILEPATH"}
        if not self._playback_ctrl:
            return {"ok": False, "error": "NO_PLAYER_SERVICE"}
        if not filepath.startswith(("http://", "https://", "radio://", "stream://")) and not Path(filepath).is_file():
            return {"ok": False, "error": "FILE_NOT_FOUND"}
        title = ""
        artist = ""
        album = ""
        if self._query_svc:
            try:
                conn = self._query_svc._get_conn()
                row = conn.execute(
                    "SELECT title, artist, album FROM media_items WHERE filepath=? AND deleted_at IS NULL",
                    (filepath,)
                ).fetchone()
                if row:
                    title = row[0] or ""
                    artist = row[1] or ""
                    album = row[2] or ""
            except Exception:
                pass
        try:
            if hasattr(self._playback_ctrl, 'play_file'):
                self._playback_ctrl.play_file(filepath)
            elif hasattr(self._playback_ctrl, 'play'):
                self._playback_ctrl.play(filepath, title, artist, album)
            elif hasattr(self._playback_ctrl, 'enqueue'):
                self._playback_ctrl.enqueue([filepath], play_now=True)
            else:
                return {"ok": False, "error": "NO_PLAY_METHOD"}
            return {"ok": True, "title": title, "artist": artist, "album": album}
        except Exception as e:
            return {"ok": False, "error": f"PLAYBACK_ERROR: {e}"}

    @Slot(int, result=dict)
    def enqueueTrackById(self, track_id: int):
        if not self._query_svc:
            return {"ok": False, "error": "NO_QUERY_SERVICE"}
        try:
            track = self._query_svc.fetch_track_internal(track_id)
            if not track or not track.get("filepath"):
                return {"ok": False, "error": "NOT_FOUND"}
            return self.enqueueSong(track["filepath"])
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(int, result=dict)
    def playNextTrackById(self, track_id: int):
        if not self._query_svc:
            return {"ok": False, "error": "NO_QUERY_SERVICE"}
        try:
            track = self._query_svc.fetch_track_internal(track_id)
            if not track or not track.get("filepath"):
                return {"ok": False, "error": "NOT_FOUND"}
            if not self._playback_ctrl or not hasattr(self._playback_ctrl, 'enqueue_next'):
                return {"ok": False, "error": "UNSUPPORTED"}
            self._playback_ctrl.enqueue_next(track["filepath"])
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(int, int, result=dict)
    def addTrackToPlaylistById(self, track_id: int, playlist_id: int):
        if not self._query_svc:
            return {"ok": False, "error": "NO_QUERY_SERVICE"}
        try:
            track = self._query_svc.fetch_track_internal(track_id)
            if not track or not track.get("filepath"):
                return {"ok": False, "error": "NOT_FOUND"}
            from ui_qml_bridge.playlists_bridge import PlaylistsBridge
            pb = PlaylistsBridge(db=self._db)
            return pb.addTrackToPlaylist(playlist_id, filepath=track["filepath"])
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
            import subprocess
            import os
            if os.name == "nt":
                subprocess.Popen(["explorer", parent])
            else:
                subprocess.Popen(["xdg-open", parent])
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(int, result=dict)
    def toggleFavoriteById(self, track_id: int):
        if not self._query_svc or not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            track = self._query_svc.fetch_track_internal(track_id)
            if not track or not track.get("filepath"):
                return {"ok": False, "error": "NOT_FOUND"}
            fp = track["filepath"]
            row = self._db.conn.execute(
                "SELECT 1 FROM favorites WHERE track_id=?", (fp,)
            ).fetchone()
            if row:
                self._db.conn.execute("DELETE FROM favorites WHERE track_id=?", (fp,))
                fav = False
            else:
                self._db.conn.execute(
                    "INSERT OR IGNORE INTO favorites (track_id) VALUES (?)", (fp,))
                fav = True
            self._db.conn.commit()
            return {"ok": True, "favorite": fav}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def enqueueSong(self, filepath: str):
        if not filepath:
            return {"ok": False, "error": "EMPTY_FILEPATH"}
        if not self._playback_ctrl:
            return {"ok": False, "error": "NO_PLAYER_SERVICE"}
        if hasattr(self._playback_ctrl, 'enqueue'):
            try:
                self._playback_ctrl.enqueue([filepath], play_now=False)
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "UNSUPPORTED"}

    @Slot(str, result=dict)
    def revealInFileManager(self, filepath: str):
        if not filepath or not Path(filepath).exists():
            return {"ok": False, "error": "FILE_NOT_FOUND"}
        parent = str(Path(filepath).parent)
        try:
            if os.name == "nt":
                subprocess.Popen(["explorer", parent])
            else:
                subprocess.Popen(["xdg-open", parent])
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Album actions ──

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
        if not self._playback_ctrl:
            return {"ok": False, "error": "NO_PLAYER_SERVICE"}
        try:
            internal = self._query_svc.fetch_album_tracks_internal(album_key)
            if not internal:
                return {"ok": False, "error": "NO_TRACKS"}
            fps = [t["filepath"] for t in internal if t.get("filepath")]
            if not fps:
                return {"ok": False, "error": "NO_VALID_TRACKS"}
            if hasattr(self._playback_ctrl, 'enqueue'):
                self._playback_ctrl.enqueue(fps, play_now=True)
                return {"ok": True, "count": len(fps)}
            return self.play_song(fps[0])
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def enqueueAlbum(self, album_key: str):
        if not self._query_svc:
            return {"ok": False, "error": "NO_QUERY_SERVICE"}
        if not self._playback_ctrl:
            return {"ok": False, "error": "NO_PLAYER_SERVICE"}
        try:
            internal = self._query_svc.fetch_album_tracks_internal(album_key)
            if not internal:
                return {"ok": False, "error": "NO_TRACKS"}
            if hasattr(self._playback_ctrl, 'enqueue'):
                fps = [t["filepath"] for t in internal if t.get("filepath")]
                self._playback_ctrl.enqueue(fps, play_now=False)
                return {"ok": True, "count": len(fps)}
            return {"ok": False, "error": "UNSUPPORTED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Artist actions ──

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

    @Slot(str, result=dict)
    def playArtist(self, artist_name: str):
        if not self._query_svc:
            return {"ok": False, "error": "NO_QUERY_SERVICE"}
        if not self._playback_ctrl:
            return {"ok": False, "error": "NO_PLAYER_SERVICE"}
        try:
            internal = self._query_svc.fetch_artist_tracks_internal(artist_name)
            if not internal:
                return {"ok": False, "error": "NO_TRACKS"}
            fps = [t["filepath"] for t in internal if t.get("filepath")]
            if not fps:
                return {"ok": False, "error": "NO_VALID_TRACKS"}
            if hasattr(self._playback_ctrl, 'enqueue'):
                self._playback_ctrl.enqueue(fps, play_now=True)
                return {"ok": True, "count": len(fps)}
            return self.play_song(fps[0])
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Folder actions ──

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
        if not self._playback_ctrl:
            return {"ok": False, "error": "NO_PLAYER_SERVICE"}
        try:
            internal = self._query_svc.fetch_folder_tracks_internal(folder_path)
            if not internal:
                return {"ok": False, "error": "NO_TRACKS"}
            fps = [t["filepath"] for t in internal if t.get("filepath")]
            if not fps:
                return {"ok": False, "error": "NO_VALID_TRACKS"}
            if hasattr(self._playback_ctrl, 'enqueue'):
                self._playback_ctrl.enqueue(fps, play_now=True)
                return {"ok": True, "count": len(fps)}
            return self.play_song(fps[0])
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def openFolder(self, folder_path: str):
        if not folder_path or not Path(folder_path).is_dir():
            return {"ok": False, "error": "DIR_NOT_FOUND"}
        try:
            if os.name == "nt":
                subprocess.Popen(["explorer", folder_path])
            else:
                subprocess.Popen(["xdg-open", folder_path])
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def addFolder(self, folder_path: str):
        if not folder_path:
            return {"ok": False, "error": "EMPTY_PATH"}
        if not Path(folder_path).is_dir():
            return {"ok": False, "error": "DIR_NOT_FOUND"}
        try:
            from library.indexer import Indexer
            if not self._db:
                return {"ok": False, "error": "NO_DATABASE"}
            import logging as _lg
            _log = _lg.getLogger("michi.qml.addfolder")
            _log.info("Indexing: %s", folder_path)
            worker = Indexer(self._db, folder_path)
            worker.run()
            if hasattr(self._db, 'conn') and self._db.conn:
                self._db.conn.commit()
            self.refresh()
            return {"ok": True, "path": folder_path}
        except Exception as e:
            import logging as _lg
            _lg.getLogger("michi.qml.addfolder").error("addFolder failed: %s", e, exc_info=True)
            return {"ok": False, "error": str(e)}

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
            from core.file_actions import FileActions
            from core.paths import database_path
            db_path = database_path()
            actions = FileActions(db_path=db_path)
            if p.is_dir():
                actions.scan_path(path)
                self.refresh()
                return {"ok": True, "type": "folder", "path": path}
            parent = str(p.parent)
            actions.scan_path(parent)
            self.refresh()
            return {"ok": True, "type": "file", "path": path, "parent": parent}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Internal ──

    def _dict_to_qml(self, item: dict) -> dict:
        return {
            "track_id": item.get("track_id", 0),
            "track_uid": item.get("track_uid", ""),
            "public_ref": f"track_{item.get('track_id', 0)}",
            "title": item.get("title", "") or "",
            "artist": item.get("artist", ""),
            "album": item.get("album", ""),
            "album_key": item.get("album_key", ""),
            "duration": item.get("duration", 0),
            "format": item.get("format", ""),
            "cover_key": item.get("album_key", "") or item.get("cover_key", ""),
            "year": item.get("year", 0),
            "track_number": item.get("track_number", 0),
            "genre": item.get("genre", ""),
        }
