"""LibraryBridge — connects QML Library page to LibraryDB with pagination, filters, sort."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot
from pathlib import Path


class LibraryBridge(QObject):
    dataChanged = Signal()

    def __init__(self, db=None, search_engine=None, playback_ctrl=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._search_engine = search_engine
        self._playback_ctrl = playback_ctrl
        self._songs = []
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
        self._page_size = 100
        self._current_page = 0
        self._error_message = ""

    @Property(int, notify=dataChanged)
    def songCount(self): return len(self._songs)

    @Property(int, notify=dataChanged)
    def albumCount(self): return len(self._albums)

    @Property(int, notify=dataChanged)
    def artistCount(self): return len(self._artists)

    @Property("QVariantList", notify=dataChanged)
    def songs(self): return self._get_songs_page(0, self._page_size)

    @Property(int, notify=dataChanged)
    def totalSongs(self): return len(self._songs)

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
            if not name: continue
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
    def visibleCount(self): return len(self._get_filtered_sorted())

    @Property(bool, notify=dataChanged)
    def hasMoreSongs(self):
        total = len(self._get_filtered_sorted())
        return (self._current_page + 1) * self._page_size < total

    @Property(int, notify=dataChanged)
    def currentPage(self): return self._current_page

    @Property(int, notify=dataChanged)
    def pageSize(self): return self._page_size

    @Property(str, notify=dataChanged)
    def errorMessage(self): return self._error_message

    @Property(str, notify=dataChanged)
    def activeSortKey(self): return self._sort_key

    @Property(bool, notify=dataChanged)
    def activeSortAscending(self): return self._sort_asc

    @Property(str, notify=dataChanged)
    def activeFormatFilter(self): return self._filter_format

    # ── Private helpers ──

    def _get_filtered_sorted(self):
        items = self._songs
        if self._filter_artist:
            items = [s for s in items if (getattr(s, 'artist', '') or '') == self._filter_artist]
        if self._filter_album:
            items = [s for s in items if (getattr(s, 'album_key', '') or getattr(s, 'album', '') or '') == self._filter_album]
        if self._filter_format:
            fmt = self._filter_format.lower()
            items = [s for s in items if (getattr(s, 'format', '') or '').lower() == fmt]
        return self._sort_items(items)

    def _get_songs_page(self, page, page_size):
        filtered = self._get_filtered_sorted()
        start = page * page_size
        end = start + page_size
        return [self._song_to_dict(s) for s in filtered[start:end]]

    @Slot(int, int, result="QVariantList")
    def getSongsPage(self, page: int, pageSize: int):
        return self._get_songs_page(page, pageSize)

    @Slot(result=dict)
    def loadNextPage(self):
        self._current_page += 1
        self.dataChanged.emit()
        return {"ok": True, "page": self._current_page}

    @Slot(result=dict)
    def resetPaging(self):
        self._current_page = 0
        self.dataChanged.emit()
        return {"ok": True}

    # ── Filters ──

    @Slot(str)
    def setFormatFilter(self, fmt: str):
        self._filter_format = fmt
        self._current_page = 0
        self.dataChanged.emit()

    @Slot(str)
    def filterByArtist(self, artist: str):
        self._filter_artist = artist
        self._filter_album = ""
        self._current_page = 0
        self.dataChanged.emit()

    @Slot(str)
    def filterByAlbum(self, album_key: str):
        self._filter_album = album_key
        self._current_page = 0
        self.dataChanged.emit()

    @Slot(result=dict)
    def clearFilters(self):
        self._filter_artist = ""
        self._filter_album = ""
        self._filter_format = ""
        self._filter_folder = ""
        self._current_page = 0
        self._error_message = ""
        self.dataChanged.emit()
        return {"ok": True}

    # ── Search ──

    @Slot(str)
    def search(self, query: str):
        self._search_query = query
        self._current_page = 0
        if self._search_engine and query:
            results = self._search_engine.search(query)
            self._songs = results if results else []
            self._refresh_albums_artists()
        elif self._db and not query:
            if hasattr(self._db, 'fetch_all'):
                self._songs = self._db.fetch_all() or []
            self._refresh_albums_artists()
        else:
            self._songs = []
            self._refresh_albums_artists()
        self.dataChanged.emit()

    @Slot()
    def refresh(self):
        if self._db and hasattr(self._db, 'fetch_all'):
            self._songs = self._db.fetch_all() or []
        self._refresh_albums_artists()
        self.dataChanged.emit()

    # ── Sort ──

    @Slot(str, result=dict)
    def sortBy(self, key: str):
        if key == self._sort_key:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_key = key
            self._sort_asc = True
        self._current_page = 0
        self.dataChanged.emit()
        return {"ok": True, "key": key, "asc": self._sort_asc}

    # ── Playback actions ──

    @Slot(str, result=dict)
    def play_song(self, filepath: str):
        if not filepath:
            return {"ok": False, "error": "EMPTY_FILEPATH"}
        if not self._playback_ctrl:
            return {"ok": False, "error": "NO_PLAYER_SERVICE"}
        if not filepath.startswith(("http://", "https://", "radio://", "stream://")):
            if not Path(filepath).is_file():
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
        import subprocess
        import os
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
        tracks = [s for s in self._songs if (getattr(s, 'album_key', '') or '') == album_key]
        if not tracks:
            return {"ok": False, "error": "NOT_FOUND"}
        first = tracks[0]
        return {"ok": True, "title": getattr(first, 'album', '') or album_key,
                "artist": getattr(first, 'artist', '') or '',
                "year": getattr(first, 'year', 0) or 0,
                "track_count": len(tracks),
                "cover_key": album_key}

    @Slot(str, result="QVariantList")
    def getAlbumTracks(self, album_key: str):
        return [self._song_to_dict(s) for s in self._songs if (getattr(s, 'album_key', '') or '') == album_key]

    @Slot(str, result=dict)
    def playAlbum(self, album_key: str):
        tracks = self.getAlbumTracks(album_key)
        if not tracks:
            return {"ok": False, "error": "NO_TRACKS"}
        return self.play_song(tracks[0].get("filepath", ""))

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
        tracks = [s for s in self._songs if (getattr(s, 'artist', '') or '') == artist_name]
        return {"ok": True, "name": artist_name, "track_count": len(tracks)}

    @Slot(str, result="QVariantList")
    def getArtistTracks(self, artist_name: str):
        return [self._song_to_dict(s) for s in self._songs if (getattr(s, 'artist', '') or '') == artist_name]

    @Slot(str, result="QVariantList")
    def getArtistAlbums(self, artist_name: str):
        seen = {}
        for s in self._songs:
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
        return self.play_song(tracks[0].get("filepath", ""))

    # ── Folder actions ──

    @Slot(str, result="QVariantList")
    def getFolderTracks(self, folder_path: str):
        return [self._song_to_dict(s) for s in self._songs if (getattr(s, 'filepath', '') or '').startswith(folder_path)]

    @Slot(str, result=dict)
    def filterByFolder(self, folder_path: str):
        self._filter_folder = folder_path
        self._current_page = 0
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(str, result=dict)
    def playFolder(self, folder_path: str):
        tracks = self.getFolderTracks(folder_path)
        if not tracks:
            return {"ok": False, "error": "NO_TRACKS"}
        return self.play_song(tracks[0].get("filepath", ""))

    @Slot(str, result=dict)
    def openFolder(self, folder_path: str):
        import subprocess
        import os
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

    # ── Internal ──

    def _song_to_dict(self, s):
        return {
            "title": getattr(s, 'title', None) or Path(getattr(s, 'filepath', '')).stem or '',
            "artist": getattr(s, 'artist', '') or '',
            "album": getattr(s, 'album', '') or '',
            "album_key": getattr(s, 'album_key', '') or '',
            "duration": getattr(s, 'duration', 0) or 0,
            "filepath": getattr(s, 'filepath', '') or '',
            "track_id": getattr(s, 'id', 0) or 0,
            "track_uid": getattr(s, 'track_uid', '') or '',
            "format": getattr(s, 'format', '') or '',
            "cover_key": getattr(s, 'album_key', '') or getattr(s, 'filepath', '') or '',
            "year": getattr(s, 'year', 0) or 0,
            "track_number": getattr(s, 'track_number', 0) or 0,
            "genre": getattr(s, 'genre', '') or '',
        }

    def _sort_items(self, items, key_attr='title'):
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

    def _track_for_filepath(self, filepath: str):
        for song in self._songs:
            if getattr(song, "filepath", "") == filepath:
                return song
        return None

    def _refresh_albums_artists(self):
        seen_albums = {}
        seen_artists = {}
        self._albums = []
        self._artists = []
        for s in self._songs:
            key = getattr(s, 'album_key', None) or getattr(s, 'album', '') or ''
            if key and key not in seen_albums:
                seen_albums[key] = True
                self._albums.append(s)
            artist_name = getattr(s, 'artist', '') or getattr(s, 'album_artist', '') or ''
            if artist_name and artist_name not in seen_artists:
                seen_artists[artist_name] = True
                self._artists.append(s)
