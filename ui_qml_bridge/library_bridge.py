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

    @Property(int, notify=dataChanged)
    def songCount(self):
        return len(self._songs)

    @Property(int, notify=dataChanged)
    def albumCount(self):
        return len(self._albums)

    @Property(int, notify=dataChanged)
    def artistCount(self):
        return len(self._artists)

    @Property("QVariantList", notify=dataChanged)
    def songs(self):
        items = self._songs[:500]
        if self._filter_artist:
            items = [s for s in items if (getattr(s, 'artist', '') or '') == self._filter_artist]
        if self._filter_album:
            items = [s for s in items if (getattr(s, 'album_key', '') or getattr(s, 'album', '') or '') == self._filter_album]
        items = self._sort_items(items)
        result = []
        for s in items:
            result.append(self._song_to_dict(s))
        return result

    @Property("QVariantList", notify=dataChanged)
    def albums(self):
        items = self._albums[:200]
        if self._filter_artist:
            items = [a for a in items if (getattr(a, 'artist', '') or '') == self._filter_artist]
        items = self._sort_items(items, key_attr='album')
        result = []
        for a in items:
            key = getattr(a, 'album_key', None) or getattr(a, 'album', '') or ''
            result.append({
                "title": getattr(a, 'album', '') or key,
                "artist": getattr(a, 'artist', '') or '',
                "album_key": key,
                "year": getattr(a, 'year', 0) or 0,
                "track_count": getattr(a, 'track_count', 0) or 0,
                "cover_key": key,
            })
        return result

    @Property("QVariantList", notify=dataChanged)
    def artists(self):
        result = []
        for a in self._artists[:200]:
            name = getattr(a, 'artist', '') or getattr(a, 'album_artist', '') or ''
            if not name:
                continue
            count = getattr(a, 'track_count', 0) or 0
            album_count = getattr(a, 'album_count', 0) or 0
            cover = getattr(a, 'album_key', '') or ''
            result.append({
                "name": name,
                "track_count": count,
                "album_count": album_count,
                "cover_key": cover,
            })
        return sorted(result, key=lambda x: x["name"].lower())

    @Property("QVariantList", notify=dataChanged)
    def folders(self):
        result = []
        for f in self._folders[:200]:
            raw_path = getattr(f, "path", None) or str(f) if not isinstance(f, str) else f
            path = raw_path if raw_path else ""
            name = Path(path).name if path else ""
            result.append({
                "path": path,
                "name": name or getattr(f, "name", ""),
                "track_count": getattr(f, "track_count", 0) or 0,
            })
        return sorted(result, key=lambda x: x["name"].lower())

    @Slot(str)
    def search(self, query: str):
        self._search_query = query
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

    @Slot(str)
    def filterByArtist(self, artist: str):
        self._filter_artist = artist
        self._filter_album = ""
        self.dataChanged.emit()

    @Slot(str)
    def filterByAlbum(self, album_key: str):
        self._filter_album = album_key
        self.dataChanged.emit()

    @Slot()
    def clearFilters(self):
        self._filter_artist = ""
        self._filter_album = ""
        self.dataChanged.emit()

    @Slot(str)
    def sortBy(self, key: str):
        if key == self._sort_key:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_key = key
            self._sort_asc = True
        self.dataChanged.emit()

    @Slot(str, result=dict)
    def play_song(self, filepath: str):
        if not filepath:
            return {"ok": False, "error": "EMPTY_FILEPATH"}
        if not self._playback_ctrl:
            return {"ok": False, "error": "NO_PLAYER_SERVICE"}
        if not filepath.startswith(("http://", "https://", "radio://", "stream://")):
            from pathlib import Path
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
