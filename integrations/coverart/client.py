"""Cover Art Archive client — album cover images by MusicBrainz release-group ID."""
from urllib.parse import quote

from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply


BASE_URL = "https://coverartarchive.org"


class CoverArtClient(QObject):
    cover_found = Signal(str, str)        # album_key, image_url
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._nam = QNetworkAccessManager(self)

    def fetch_cover(self, album_key: str, mbid: str):
        """Fetch front cover for a release-group. Returns URL or empty."""
        url = f"{BASE_URL}/release-group/{quote(mbid)}/front"
        self._get(url, lambda data: self._on_response(album_key, data))

    def fetch_front_cover(self, album_key: str, release_mbid: str):
        """Fetch front cover for a specific release."""
        url = f"{BASE_URL}/release/{quote(release_mbid)}/front"
        self._get(url, lambda data: self._on_response(album_key, data))

    def _get(self, url: str, callback):
        req = QNetworkRequest(QUrl(url))
        req.setRawHeader(b"User-Agent",
                         b"AstraMusicPlayer/0.1")
        req.setRawHeader(b"Accept", b"image/*")
        reply = self._nam.get(req)
        reply.finished.connect(lambda r=reply, cb=callback: self._handle(r, cb))

    def _handle(self, reply: QNetworkReply, callback):
        err = reply.error()
        if err != QNetworkReply.NoError:
            callback(None)
            reply.deleteLater()
            return
        # Check for redirect (307) and for raw image
        status = reply.attribute(
            QNetworkRequest.HttpStatusCodeAttribute)
        redirect_url = reply.attribute(
            QNetworkRequest.RedirectionTargetAttribute)
        content_type = reply.rawHeader(b"Content-Type") or b""

        if redirect_url and status in (301, 302, 307, 308):
            image_url = redirect_url.toString()
            callback(image_url)
        elif b"image" in content_type or not content_type:
            # Direct image — use the request URL (Cover Art Archive
            # returns 307 with redirect; this branch is fallback)
            image_url = reply.url().toString()
            callback(image_url)
        else:
            callback(None)
        reply.deleteLater()

    def _on_response(self, album_key: str, image_url: str | None):
        if image_url:
            self.cover_found.emit(album_key, image_url)
