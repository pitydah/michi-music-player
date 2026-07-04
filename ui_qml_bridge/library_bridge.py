"""LibraryBridge — connects QML Library page to LibraryDB with pagination, filters, sort."""
from __future__ import annotations

import subprocess
import os
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Property, Slot


class LibraryBridge(QObject):
    dataChanged = Signal()

    def __init__(self, db=None, search_engine=None, playback_ctrl=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._search_engine = search_engine
        self._playback_ctrl = playback_ctrl
        self._base_songs = []
        self._albums = []
        self._artists = []
        self._folders = []
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
        self._cached_view: list | None = None
        self._cached_visible_count: int = 0
        self._view_dirty = True

    # ── Internal pipeline ──

    def _apply_search(self, items):
        q = self._search_query.lower().strip()
        if not q:
            return items
        result = []
        for s in items:
            title = (getattr(s, 'title', '') or '').lower()
            artist = (getattr(s, 'artist', '') or '').lower()
            album = (getattr(s, 'album', '') or '').lower()
            genre = (getattr(s, 'genre', '') or '').lower()
            fmt = (getattr(s, 'format', '') or '').lower()
            fp = (getattr(s, 'filepath', '') or '').lower()
            if q in title or q in artist or q in album or q in genre or q in fmt or q in fp:
                result.append(s)
        return result

    def _apply_filters(self, items):
        if self._filter_artist:
            items = [s for s in items if (getattr(s, 'artist', '') or '') == self._filter_artist]
        if self._filter_album:
            items = [s for s in items if (getattr(s, 'album_key', '') or getattr(s, 'album', '') or '') == self._filter_album]
        if self._filter_format:
            fmt = "." + self._filter_format.lower()
            items = [s for s in items if (getattr(s, 'ext', '') or '').lower() == fmt]
        if self._filter_missing_artist:
            items = [s for s in items if not (getattr(s, 'artist', '') or '')]
        if self._filter_missing_album:
            items = [s for s in items if not (getattr(s, 'album', '') or '')]
        if self._filter_folder:
            items = [s for s in items if self._path_matches(s, self._filter_folder)]
        return items

    def _path_matches(self, s, folder_path):
        fp = getattr(s, 'filepath', '') or ''
        norm_fp = Path(fp).as_posix().lower()
        norm_dir = Path(folder_path).as_posix().lower().rstrip("/") + "/"
        return norm_fp.startswith(norm_dir)

    def _apply_sort(self, items):
        reverse = not self._sort_asc
        k = self._sort_key
        if k == 'title':
            return sorted(items, key=lambda x: (getattr(x, 'title', '') or '').lower(), reverse=reverse)
        elif k == 'artist':
            return sorted(items, key=lambda x: (getattr(x, 'artist', '') or '').lower(), reverse=reverse)
        elif k == 'album':
            return sorted(items, key=lambda x: (getattr(x, 'album', '') or '').lower(), reverse=reverse)
        elif k == 'year':
            return sorted(items, key=lambda x: getattr(x, 'year', 0) or 0, reverse=reverse)
        elif k == 'duration':
            return sorted(items, key=lambda x: getattr(x, 'duration', 0) or 0, reverse=reverse)
        elif k == 'format':
            return sorted(items, key=lambda x: getattr(x, 'format', '') or '', reverse=reverse)
        return items

    def _invalidate_view(self):
        self._view_dirty = True
        self._cached_view = None

    def _rebuild_view(self):
        if not self._view_dirty and self._cached_view is not None:
            return self._cached_view
        items = self._base_songs[:]
        items = self._apply_search(items)
        items = self._apply_filters(items)
        items = self._apply_sort(items)
        self._cached_view = items
        self._cached_visible_count = len(items)
        self._view_dirty = False
        return items

    @property
    def _filtered_view(self):
        return self._rebuild_view()

    # ── Properties ──

    @Property(int, notify=dataChanged)
    def songCount(self):
        return len(self._base_songs)

    @Property(int, notify=dataChanged)
    def albumCount(self):
        return len(self._albums)

    @Property(int, notify=dataChanged)
    def artistCount(self):
        return len(self._artists)

    @Property(int, notify=dataChanged)
    def totalSongs(self):
        return len(self._base_songs)

    @Property(int, notify=dataChanged)
    def visibleCount(self):
        self._rebuild_view()
        return self._cached_visible_count

    @Property(int, notify=dataChanged)
    def loadedCount(self):
        return self._loaded_count

    @Property(bool, notify=dataChanged)
    def hasMoreSongs(self):
        return self._loaded_count < self.visibleCount

    @Property("QVariantList", notify=dataChanged)
    def songs(self):
        view = self._rebuild_view()
        page = view[:self._loaded_count]
        return [self._song_to_dict(s) for s in page]

    @Property("QVariantList", notify=dataChanged)
    def albums(self):
        result = []
        for a in self._albums[:200]:
            key = getattr(a, 'album_key', None) or getattr(a, 'album', '') or ''
            result.append({"title": getattr(a, 'album', '') or key, "artist": getattr(a, 'artist', '') or '', "album_key": key, "year": getattr(a, 'year', 0) or 0, "track_count": getattr(a, 'track_count', 0) or 0, "cover_key": key})
        return result

    @Property("QVariantList", notify=dataChanged)
    def artists(self):
        result = []
        for a in self._artists[:200]:
            name = getattr(a, 'artist', '') or getattr(a, 'album_artist', '') or ''
            if not name:
                continue
            result.append({"name": name, "track_count": getattr(a, 'track_count', 0) or 0, "album_count": getattr(a, 'album_count', 0) or 0, "cover_key": getattr(a, 'album_key', '') or ''})
        return sorted(result, key=lambda x: x["name"].lower())

    @Property("QVariantList", notify=dataChanged)
    def folders(self):
        result = []
        for f in self._folders[:200]:
            raw_path = getattr(f, "path", None) or str(f) if not isinstance(f, str) else f
            path = raw_path if raw_path else ""
            result.append({"path": path, "name": Path(path).name if path else (getattr(f, "name", "")), "track_count": getattr(f, "track_count", 0) or 0})
        return sorted(result, key=lambda x: x["name"].lower())

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
        view = self._rebuild_view()
        start = page * pageSize
        return [self._song_to_dict(s) for s in view[start:start + pageSize]]

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

    # ── Search ──

    @Slot(str, result=dict)
    def setSearchQuery(self, query: str):
        self._search_query = query
        self._invalidate_view()
        self._loaded_count = min(self._page_size, self.visibleCount)
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def clearSearch(self):
        self._search_query = ""
        self._invalidate_view()
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
        self._invalidate_view()
        self._loaded_count = min(self._page_size, self.visibleCount)
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(str, result=dict)
    def filterByArtist(self, artist: str):
        self._filter_artist = artist
        self._filter_album = ""
        self._invalidate_view()
        self._loaded_count = min(self._page_size, self.visibleCount)
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(str, result=dict)
    def setArtistFilter(self, artist: str):
        return self.filterByArtist(artist)

    @Slot(str, result=dict)
    def filterByAlbum(self, album_key: str):
        self._filter_album = album_key
        self._invalidate_view()
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
        self._invalidate_view()
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
        self._invalidate_view()
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
        self._invalidate_view()
        self._loaded_count = min(self._page_size, self.visibleCount)
        self.dataChanged.emit()
        return {"ok": True, "key": key, "asc": self._sort_asc}

    # ── Data loading ──

    @Slot(result=dict)
    def refresh(self):
        if self._db:
            if hasattr(self._db, 'fetch_all'):
                self._base_songs = self._db.fetch_all() or []
            elif hasattr(self._db, 'get_all'):
                self._base_songs = self._db.get_all() or []
        self._invalidate_view()
        self._refresh_albums_artists()
        self._loaded_count = min(self._page_size, self.visibleCount)
        self.dataChanged.emit()
        return {"ok": True, "count": len(self._base_songs)}

    # ── Playback actions (single) ──

    @Slot(str, result=dict)
    def play_song(self, filepath: str):
        if not filepath:
            return {"ok": False, "error": "EMPTY_FILEPATH"}
        if not self._playback_ctrl:
            return {"ok": False, "error": "NO_PLAYER_SERVICE"}
        if not filepath.startswith(("http://", "https://", "radio://", "stream://")) and not Path(filepath).is_file():
            return {"ok": False, "error": "FILE_NOT_FOUND"}
        track = self._track_for_filepath(filepath)
        title = getattr(track, "title", "") if track else ""
        artist = getattr(track, "artist", "") if track else ""
        album = getattr(track, "album", "") if track else ""
        try:
            if hasattr(self._playback_ctrl, 'play_file'):
                self._playback_ctrl.play_file(filepath)
            elif hasattr(self._playback_ctrl, 'play'):
                self._playback_ctrl.play(filepath, title, artist, album)
            elif hasattr(self._playback_ctrl, 'enqueue'):
                self._playback_ctrl.enqueue([filepath], play_now=True)
            else:
                return {"ok": False, "error": "NO_PLAY_METHOD"}
            return {"ok": True, "filepath": filepath, "title": title, "artist": artist, "album": album}
        except Exception as e:
            return {"ok": False, "error": f"PLAYBACK_ERROR: {e}"}

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
        tracks = [s for s in self._base_songs if (getattr(s, 'album_key', '') or '') == album_key]
        if not tracks:
            return {"ok": False, "error": "NOT_FOUND"}
        first = tracks[0]
        return {"ok": True, "title": getattr(first, 'album', '') or album_key,
                "artist": getattr(first, 'artist', '') or '',
                "year": getattr(first, 'year', 0) or 0,
                "track_count": len(tracks), "cover_key": album_key}

    @Slot(str, result="QVariantList")
    def getAlbumTracks(self, album_key: str):
        return [self._song_to_dict(s) for s in self._base_songs if (getattr(s, 'album_key', '') or '') == album_key]

    @Slot(str, result=dict)
    def playAlbum(self, album_key: str):
        tracks = self.getAlbumTracks(album_key)
        if not tracks:
            return {"ok": False, "error": "NO_TRACKS"}
        if not self._playback_ctrl:
            return {"ok": False, "error": "NO_PLAYER_SERVICE"}
        fps = [t["filepath"] for t in tracks if t.get("filepath")]
        if not fps:
            return {"ok": False, "error": "NO_VALID_TRACKS"}
        if hasattr(self._playback_ctrl, 'enqueue'):
            try:
                self._playback_ctrl.enqueue(fps, play_now=True)
                return {"ok": True, "count": len(fps)}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return self.play_song(fps[0])

    @Slot(str, result=dict)
    def enqueueAlbum(self, album_key: str):
        if not self._playback_ctrl:
            return {"ok": False, "error": "NO_PLAYER_SERVICE"}
        tracks = self.getAlbumTracks(album_key)
        if not tracks:
            return {"ok": False, "error": "NO_TRACKS"}
        if hasattr(self._playback_ctrl, 'enqueue'):
            try:
                fps = [t["filepath"] for t in tracks if t.get("filepath")]
                self._playback_ctrl.enqueue(fps, play_now=False)
                return {"ok": True, "count": len(fps)}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "UNSUPPORTED"}

    # ── Artist actions ──

    @Slot(str, result=dict)
    def getArtistDetail(self, artist_name: str):
        return {"ok": True, "name": artist_name, "track_count": len([s for s in self._base_songs if (getattr(s, 'artist', '') or '') == artist_name])}

    @Slot(str, result="QVariantList")
    def getArtistTracks(self, artist_name: str):
        return [self._song_to_dict(s) for s in self._base_songs if (getattr(s, 'artist', '') or '') == artist_name]

    @Slot(str, result="QVariantList")
    def getArtistAlbums(self, artist_name: str):
        seen = {}
        for s in self._base_songs:
            if (getattr(s, 'artist', '') or '') != artist_name:
                continue
            key = getattr(s, 'album_key', '') or ''
            if key and key not in seen:
                seen[key] = True
        return [{"album_key": k, "title": k} for k in seen]

    @Slot(str, result=dict)
    def playArtist(self, artist_name: str):
        tracks = self.getArtistTracks(artist_name)
        if not tracks:
            return {"ok": False, "error": "NO_TRACKS"}
        if not self._playback_ctrl:
            return {"ok": False, "error": "NO_PLAYER_SERVICE"}
        fps = [t["filepath"] for t in tracks if t.get("filepath")]
        if not fps:
            return {"ok": False, "error": "NO_VALID_TRACKS"}
        if hasattr(self._playback_ctrl, 'enqueue'):
            try:
                self._playback_ctrl.enqueue(fps, play_now=True)
                return {"ok": True, "count": len(fps)}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return self.play_song(fps[0])

    # ── Folder actions ──

    @Slot(str, result="QVariantList")
    def getFolderTracks(self, folder_path: str):
        norm_folder = Path(folder_path).as_posix().lower().rstrip("/") + "/"
        result = []
        for s in self._base_songs:
            fp = Path(getattr(s, 'filepath', '') or '').as_posix().lower()
            if fp.startswith(norm_folder):
                result.append(self._song_to_dict(s))
        return result

    @Slot(str, result=dict)
    def filterByFolder(self, folder_path: str):
        return self.setFolderFilter(folder_path)

    @Slot(str, result=dict)
    def playFolder(self, folder_path: str):
        tracks = self.getFolderTracks(folder_path)
        if not tracks:
            return {"ok": False, "error": "NO_TRACKS"}
        if not self._playback_ctrl:
            return {"ok": False, "error": "NO_PLAYER_SERVICE"}
        fps = [t["filepath"] for t in tracks if t.get("filepath")]
        if not fps:
            return {"ok": False, "error": "NO_VALID_TRACKS"}
        if hasattr(self._playback_ctrl, 'enqueue'):
            try:
                self._playback_ctrl.enqueue(fps, play_now=True)
                return {"ok": True, "count": len(fps)}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return self.play_song(fps[0])

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
            _log.info("Indexer done, committing...")
            if hasattr(self._db, 'conn') and self._db.conn:
                self._db.conn.commit()
            self.refresh()
            _log.info("Refresh done, total=%d, visible=%d",
                      len(self._base_songs), self._cached_visible_count)
            return {"ok": True, "path": folder_path, "count": len(self._base_songs)}
        except Exception as e:
            import logging as _lg
            _lg.getLogger("michi.qml.addfolder").error(
                "addFolder failed: %s", e, exc_info=True)
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

    def _song_to_dict(self, s):
        return {
            "id": getattr(s, 'id', 0) or 0,
            "track_id": getattr(s, 'id', 0) or 0,
            "track_uid": getattr(s, 'track_uid', '') or '',
            "title": getattr(s, 'title', None) or Path(getattr(s, 'filepath', '')).stem or '',
            "artist": getattr(s, 'artist', '') or '',
            "album": getattr(s, 'album', '') or '',
            "album_key": getattr(s, 'album_key', '') or '',
            "duration": getattr(s, 'duration', 0) or 0,
            "filepath": getattr(s, 'filepath', '') or '',
            "format": getattr(s, 'format', '') or '',
            "cover_key": getattr(s, 'album_key', '') or getattr(s, 'filepath', '') or '',
            "year": getattr(s, 'year', 0) or 0,
            "track_number": getattr(s, 'track_number', 0) or 0,
            "genre": getattr(s, 'genre', '') or '',
        }

    def _track_for_filepath(self, filepath: str):
        for song in self._base_songs:
            if getattr(song, "filepath", "") == filepath:
                return song
        return None

    def _refresh_albums_artists(self):
        seen_albums = {}
        seen_artists = {}
        self._albums = []
        self._artists = []
        for s in self._base_songs:
            key = getattr(s, 'album_key', None) or getattr(s, 'album', '') or ''
            if key and key not in seen_albums:
                seen_albums[key] = True
                self._albums.append(s)
            artist_name = getattr(s, 'artist', '') or getattr(s, 'album_artist', '') or ''
            if artist_name and artist_name not in seen_artists:
                seen_artists[artist_name] = True
                self._artists.append(s)
