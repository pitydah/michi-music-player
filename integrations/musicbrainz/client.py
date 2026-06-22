"""MusicBrainz REST client — non-blocking via QNetworkAccessManager."""
import json
from urllib.parse import quote

from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

BASE_URL = "https://musicbrainz.org/ws/2"
USER_AGENT = "MichiMusicPlayer/0.1 (https://github.com/pitydah/michi-music-player)"


def _parse_mb_artist(raw: dict) -> dict:
    """Parse raw MusicBrainz artist JSON into a flat dict."""
    tags = []
    if raw.get("tags"):
        for t in raw["tags"]:
            tags.append(t.get("name", ""))
    genres_list = [t for t in tags if t]
    genres_list.extend([
        g.get("name", "") for g in (raw.get("genres") or []) if g.get("name")
    ])

    life = raw.get("life-span", {}) or {}
    begin = life.get("begin", "") or ""
    country = raw.get("country", "") or ""

    # Build fanart-like from relations (Wikidata/Wikipedia links)
    relations = []
    for rel in raw.get("relations", []):
        rtype = rel.get("type", "")
        rurl = rel.get("url", {}).get("resource", "")
        if "wikidata" in rtype and rurl:
            relations.append(("wikidata", rurl))
        elif "wikipedia" in rtype and rurl:
            relations.append(("wikipedia", rurl))

    return {
        "provider": "musicbrainz",
        "artist_id": raw.get("id", ""),
        "name": raw.get("name", ""),
        "mbid": raw.get("id", ""),
        "sort_name": raw.get("sort-name", ""),
        "biography": "",
        "biography_en": "",
        "biography_es": "",
        "genre": ", ".join(genres_list),
        "style": "",
        "mood": "",
        "country": country.upper() if country else "",
        "formed_year": begin[:4] if begin else "",
        "website": "",
        "facebook": "",
        "twitter": "",
        "thumb_url": "",
        "clearart_url": "",
        "logo_url": "",
        "banner_url": "",
        "fanart_urls": [],
        "relations": relations,
    }


def _parse_mb_artists(data: list) -> list[dict]:
    """Parse raw MusicBrainz artist search results."""
    results = []
    for a in (data or []):
        info = _parse_mb_artist(a)
        if info.get("name"):
            results.append(info)
    return results


def _parse_mb_releases(data: list) -> list[dict]:
    """Parse raw MusicBrainz release-group results."""
    albums = []
    for rg in (data or []):
        first_date = (rg.get("first-release-date") or "")
        albums.append({
            "id": rg.get("id", ""),
            "title": rg.get("title", ""),
            "type": rg.get("primary-type", "Album"),
            "year": first_date[:4] if first_date else "",
            "first_release": first_date,
        })
    return albums


class MusicBrainzClient(QObject):
    artist_found = Signal(object)        # dict with artist info
    artists_found = Signal(list)         # list[dict]
    albums_found = Signal(list)          # list[dict]
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._nam = QNetworkAccessManager(self)
        self._last_call = 0.0
        self._rate_limit = 1.0

    def search_artist(self, name: str):
        url = f"{BASE_URL}/artist?query=artist:{quote(name)}&fmt=json&limit=5"
        self._get(url, self._on_search_results)

    def get_artist_by_mbid(self, mbid: str):
        url = f"{BASE_URL}/artist/{quote(mbid)}?inc=tags+genres+url-rels+aliases&fmt=json"
        self._get(url, self._on_artist_result)

    def get_release_groups(self, mbid: str):
        url = f"{BASE_URL}/release-group?artist={quote(mbid)}&type=Album&limit=50&fmt=json"
        self._get(url, self._on_albums_result)

    def _get(self, url: str, callback):
        import time
        now = time.time()
        if now - self._last_call < self._rate_limit:
            return  # rate limited — enrichment timer already gates
        self._last_call = now

        req = QNetworkRequest(QUrl(url))
        req.setRawHeader(b"User-Agent", USER_AGENT.encode())
        req.setRawHeader(b"Accept", b"application/json")
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
            self.error_occurred.emit("Invalid JSON from MusicBrainz")
            reply.deleteLater()
            return
        reply.deleteLater()
        callback(data)

    def _on_search_results(self, data: dict):
        artists_data = data.get("artists")
        if not artists_data:
            self.artists_found.emit([])
            return
        self.artists_found.emit(_parse_mb_artists(artists_data))

    def _on_artist_result(self, data: dict):
        info = _parse_mb_artist(data)
        self.artist_found.emit(info if info.get("name") else None)

    def _on_albums_result(self, data: dict):
        releases = data.get("release-groups")
        if not releases:
            self.albums_found.emit([])
            return
        self.albums_found.emit(_parse_mb_releases(releases))
