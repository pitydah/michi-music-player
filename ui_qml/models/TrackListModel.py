"""TrackListModel — paged library tracks with complete query-state propagation."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Slot

from ui_qml.models.BasePagedListModel import BasePagedListModel


class TrackListModel(BasePagedListModel):
    TrackIdRole = Qt.UserRole + 1
    TrackUidRole = Qt.UserRole + 2
    TitleRole = Qt.UserRole + 3
    ArtistRole = Qt.UserRole + 4
    AlbumRole = Qt.UserRole + 5
    AlbumKeyRole = Qt.UserRole + 6
    DurationRole = Qt.UserRole + 7
    FormatRole = Qt.UserRole + 8
    YearRole = Qt.UserRole + 9
    GenreRole = Qt.UserRole + 10
    TrackNumberRole = Qt.UserRole + 11
    CoverKeyRole = Qt.UserRole + 12
    ArtistIdRole = Qt.UserRole + 13
    AlbumIdRole = Qt.UserRole + 14
    AlbumArtistRole = Qt.UserRole + 15
    DiscNumberRole = Qt.UserRole + 16
    ComposerRole = Qt.UserRole + 17
    CodecRole = Qt.UserRole + 18
    SampleRateRole = Qt.UserRole + 19
    BitDepthRole = Qt.UserRole + 20
    BitrateRole = Qt.UserRole + 21
    ChannelsRole = Qt.UserRole + 22
    FileSizeRole = Qt.UserRole + 23
    PlayCountRole = Qt.UserRole + 24
    LastPlayedRole = Qt.UserRole + 25
    DateAddedRole = Qt.UserRole + 26
    FavoriteRole = Qt.UserRole + 27
    MissingRole = Qt.UserRole + 28
    SourceIdRole = Qt.UserRole + 29
    FolderIdRole = Qt.UserRole + 30
    DirectoryRole = Qt.UserRole + 31
    PathRole = Qt.UserRole + 32
    ReplayGainRole = Qt.UserRole + 33
    PeakRole = Qt.UserRole + 34

    _QUERY_KEYS = (
        "search", "artist", "album", "fmt", "genre", "composer", "year",
        "folder", "favorites", "unplayed", "missing", "sort", "asc",
    )

    def __init__(self, query_service=None, query_executor=None, parent=None, page_size=250):
        super().__init__(page_size=page_size, query_executor=query_executor, parent=parent)
        self._qs = query_service
        self._search = ""
        self._artist_filter = ""
        self._album_filter = ""
        self._fmt_filter = ""
        self._genre_filter = ""
        self._composer_filter = ""
        self._year_filter = ""
        self._folder_filter = ""
        self._favorites_filter = False
        self._unplayed_filter = False
        self._missing_filter = False
        self._sort = "title"
        self._asc = True

    def _owner(self) -> str:
        return "tracks"

    def roleNames(self):
        return {self.TrackIdRole: b"trackId", self.TrackUidRole: b"trackUid",
                self.TitleRole: b"title", self.ArtistRole: b"artist",
                self.AlbumRole: b"album", self.AlbumKeyRole: b"albumKey",
                self.DurationRole: b"duration", self.FormatRole: b"format",
                self.YearRole: b"year", self.GenreRole: b"genre",
                self.TrackNumberRole: b"trackNumber", self.CoverKeyRole: b"coverKey",
                self.ArtistIdRole: b"artistId", self.AlbumIdRole: b"albumId",
                self.AlbumArtistRole: b"albumArtist", self.DiscNumberRole: b"discNumber",
                self.ComposerRole: b"composer", self.CodecRole: b"codec",
                self.SampleRateRole: b"sampleRate", self.BitDepthRole: b"bitDepth",
                self.BitrateRole: b"bitrate", self.ChannelsRole: b"channels",
                self.FileSizeRole: b"fileSize", self.PlayCountRole: b"playCount",
                self.LastPlayedRole: b"lastPlayed", self.DateAddedRole: b"dateAdded",
                self.FavoriteRole: b"favorite", self.MissingRole: b"missing",
                self.SourceIdRole: b"sourceId", self.FolderIdRole: b"folderId",
                self.DirectoryRole: b"directory", self.PathRole: b"path",
                self.ReplayGainRole: b"replayGain", self.PeakRole: b"peak"}

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        mapping = {self.TrackIdRole: "track_id", self.TrackUidRole: "track_uid",
                   self.TitleRole: "title", self.ArtistRole: "artist",
                   self.AlbumRole: "album", self.AlbumKeyRole: "album_key",
                   self.DurationRole: "duration", self.FormatRole: "format",
                   self.YearRole: "year", self.GenreRole: "genre",
                   self.TrackNumberRole: "track_number", self.CoverKeyRole: "cover_key",
                   self.ArtistIdRole: "artist_id", self.AlbumIdRole: "album_id",
                   self.AlbumArtistRole: "album_artist", self.DiscNumberRole: "disc_number",
                   self.ComposerRole: "composer", self.CodecRole: "codec",
                   self.SampleRateRole: "sample_rate", self.BitDepthRole: "bit_depth",
                   self.BitrateRole: "bitrate", self.ChannelsRole: "channels",
                   self.FileSizeRole: "file_size", self.PlayCountRole: "play_count",
                   self.LastPlayedRole: "last_played", self.DateAddedRole: "date_added",
                   self.FavoriteRole: "favorite", self.MissingRole: "missing",
                   self.SourceIdRole: "source_id", self.FolderIdRole: "folder_id",
                   self.DirectoryRole: "directory", self.PathRole: "filepath",
                   self.ReplayGainRole: "replay_gain", self.PeakRole: "peak"}
        key = mapping.get(role, "")
        if key:
            return item.get(key, "")
        if role == Qt.DisplayRole:
            return item.get("title", "")
        return None

    @Slot(str, str, str, str, str, str, str, str, bool, bool, bool, str, bool, result=dict)
    def refresh(self, search: str = "", artist: str = "", album: str = "",
                fmt: str = "", genre: str = "", composer: str = "", year: str = "",
                folder: str = "", favorites: bool = False, unplayed: bool = False,
                missing: bool = False, sort: str = "title", asc: bool = True):
        self._search = search
        self._artist_filter = artist
        self._album_filter = album
        self._fmt_filter = fmt
        self._genre_filter = genre
        self._composer_filter = composer
        self._year_filter = year
        self._folder_filter = folder
        self._favorites_filter = favorites
        self._unplayed_filter = unplayed
        self._missing_filter = missing
        self._sort = sort
        self._asc = asc
        query = dict(search=search, artist=artist, album=album, fmt=fmt,
                     genre=genre, composer=composer, year=year, folder=folder,
                     favorites=favorites, unplayed=unplayed, missing=missing,
                     sort=sort, asc=asc)
        super().refresh(**query)
        return {"ok": True, "query": query}

    @Slot(str, result=dict)
    def refreshForSort(self, sort_key: str, asc: bool = True):
        query = self._active_query()
        query.update(sort=sort_key, asc=asc)
        return self.refresh(**query)

    @Slot(str, result=dict)
    def refreshForArtist(self, artist: str):
        return self.refresh(artist=artist, sort="year", asc=True)

    @Slot(str, result=dict)
    def refreshForAlbum(self, album_key: str):
        return self.refresh(album=album_key, sort="track_number", asc=True)

    def _active_query(self) -> dict[str, Any]:
        return dict(search=self._search, artist=self._artist_filter,
                    album=self._album_filter, fmt=self._fmt_filter,
                    genre=self._genre_filter, composer=self._composer_filter,
                    year=self._year_filter, folder=self._folder_filter,
                    favorites=self._favorites_filter, unplayed=self._unplayed_filter,
                    missing=self._missing_filter, sort=self._sort, asc=self._asc)

    def _fetch_count(self, **kwargs) -> int:
        if not self._qs:
            return 0
        query = {key: kwargs.get(key) for key in self._QUERY_KEYS if key not in ("sort", "asc")}
        return self._qs.count_tracks(**query)

    def _fetch_page(self, offset: int, limit: int, **kwargs) -> list[dict[str, Any]]:
        if not self._qs:
            return []
        query = {key: kwargs.get(key) for key in self._QUERY_KEYS}
        return self._qs.fetch_tracks(offset=offset, limit=limit, **query)
