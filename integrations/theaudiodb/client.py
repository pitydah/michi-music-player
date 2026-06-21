"""TheAudioDB REST client — non-blocking via QNetworkAccessManager."""
import json
from urllib.parse import quote

from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from integrations.theaudiodb.models import ArtistExternalInfo

BASE_URL = "https://www.theaudiodb.com/api/v1/json"


class TheAudioDBClient(QObject):
    artist_found = Signal(object)         # ArtistExternalInfo | None
    artists_found = Signal(list)          # list[ArtistExternalInfo]
    error_occurred = Signal(str)

    def __init__(self, api_key: str = "2", parent=None):
        super().__init__(parent)
        self._nam = QNetworkAccessManager(self)
        self._api_key = api_key
        self._base = BASE_URL

    def set_api_key(self, key: str):
        self._api_key = key

    def search_artist(self, name: str):
        url = f"{self._base}/{self._api_key}/search.php?s={quote(name)}"
        self._get(url, self._on_search_result)

    def get_artist_by_id(self, artist_id: str):
        url = f"{self._base}/{self._api_key}/artist.php?i={quote(artist_id)}"
        self._get(url, self._on_artist_result)

    def get_discography(self, name: str):
        url = f"{self._base}/{self._api_key}/discography.php?s={quote(name)}"
        self._get(url, self._on_disco_result)

    def _get(self, url: str, callback):
        req = QNetworkRequest(QUrl(url))
        reply = self._nam.get(req)
        reply.finished.connect(lambda r=reply, cb=callback: self._handle(r, cb))

    def _handle(self, reply: QNetworkReply, callback):
        err = reply.error()
        if err != QNetworkReply.NoError:
            self.error_occurred.emit(reply.errorString())
            reply.deleteLater()
            return
        try:
            data = json.loads(bytes(reply.readAll()).decode("utf-8"))
        except json.JSONDecodeError:
            self.error_occurred.emit("Invalid JSON from TheAudioDB")
            reply.deleteLater()
            return
        reply.deleteLater()
        callback(data)

    def _on_search_result(self, data: dict):
        artists_data = data.get("artists")
        if not artists_data:
            self.artists_found.emit([])
            return
        results = [_parse_artist(a) for a in artists_data if a]
        self.artists_found.emit(results)

    def _on_artist_result(self, data: dict):
        artists_data = data.get("artists")
        if not artists_data:
            self.artist_found.emit(None)
            return
        a = artists_data[0]
        if a:
            self.artist_found.emit(_parse_artist(a))
        else:
            self.artist_found.emit(None)

    def _on_disco_result(self, data: dict):
        albums_data = data.get("album")
        if not albums_data:
            self.artists_found.emit([])
            return
        results = [_parse_artist(a) for a in albums_data if a]
        self.artists_found.emit(results)


def _parse_artist(raw: dict) -> ArtistExternalInfo:
    """Parse raw TheAudioDB JSON into ArtistExternalInfo."""
    fanart = []
    for i in range(1, 10):
        url = raw.get(f"strArtistFanart{i}", "")
        if url:
            fanart.append(url)

    return ArtistExternalInfo(
        provider="theaudiodb",
        artist_id=raw.get("idArtist", ""),
        name=raw.get("strArtist", ""),
        mbid=raw.get("strMusicBrainzID", ""),
        biography=raw.get("strBiographyEN", ""),
        biography_en=raw.get("strBiographyEN", ""),
        biography_es=raw.get("strBiographyES", ""),
        genre=raw.get("strGenre", ""),
        style=raw.get("strStyle", ""),
        mood=raw.get("strMood", ""),
        country=raw.get("strCountry", ""),
        formed_year=raw.get("intFormedYear", ""),
        website=raw.get("strWebsite", ""),
        facebook=raw.get("strFacebook", ""),
        twitter=raw.get("strTwitter", ""),
        thumb_url=raw.get("strArtistThumb", "") or raw.get("strArtistThumbHQ", ""),
        clearart_url=raw.get("strArtistClearart", ""),
        logo_url=raw.get("strArtistLogo", "") or raw.get("strArtistLogoHD", ""),
        banner_url=raw.get("strArtistBanner", ""),
        fanart_urls=fanart,
    )
