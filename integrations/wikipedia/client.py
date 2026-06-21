"""Wikipedia / Wikidata client — non-blocking biography and artist image fetcher."""
import json
from urllib.parse import quote, urlencode

from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply


class WikipediaClient(QObject):
    bio_loaded = Signal(str, str)        # artist_key, bio_text
    image_url_found = Signal(str, str)   # artist_key, image_url
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._nam = QNetworkAccessManager(self)

    def fetch_bio(self, artist_key: str, name: str, lang: str = "es"):
        """Fetch artist biography from Wikipedia. Falls back to English."""
        params = urlencode({
            "action": "query", "prop": "extracts",
            "exintro": "1", "explaintext": "1",
            "titles": name, "format": "json",
            "redirects": "1",
        })
        url = f"https://{lang}.wikipedia.org/w/api.php?{params}"
        self._get(url, lambda data: self._on_bio_result(data, artist_key, name, lang))

    def fetch_image(self, artist_key: str, name: str, lang: str = "es"):
        """Fetch artist image URL from Wikidata via Wikipedia sitelink."""
        params = urlencode({
            "action": "wbgetentities",
            "sites": f"{lang}wiki",
            "titles": name,
            "props": "claims",
            "format": "json",
        })
        url = f"https://www.wikidata.org/w/api.php?{params}"
        self._get(url, lambda data: self._on_image_result(data, artist_key))

    def _get(self, url: str, callback):
        req = QNetworkRequest(QUrl(url))
        req.setRawHeader(b"User-Agent",
                         b"AstraMusicPlayer/0.1")
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
            self.error_occurred.emit("Invalid JSON from Wikipedia")
            reply.deleteLater()
            return
        reply.deleteLater()
        callback(data)

    def _on_bio_result(self, data: dict, artist_key: str, name: str, lang: str):
        pages = data.get("query", {}).get("pages", {})
        for _pid, page in pages.items():
            extract = page.get("extract", "")
            if extract:
                self.bio_loaded.emit(artist_key, extract)
                return

        # Fallback to English if primary language failed
        if lang != "en":
            self.fetch_bio(artist_key, name, "en")
        else:
            self.bio_loaded.emit(artist_key, "")

    def _on_image_result(self, data: dict, artist_key: str):
        entities = data.get("entities", {})
        for _eid, entity in entities.items():
            claims = entity.get("claims", {})
            # P18 = image property in Wikidata
            p18 = claims.get("P18", [])
            if p18:
                filename = p18[0].get("mainsnak", {}).get("datavalue", {}).get("value", "")
                if filename:
                    # Convert filename to Commons URL
                    fn = filename.replace(" ", "_")
                    fn_enc = quote(fn, safe="")
                    img_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{fn_enc}?width=500"
                    self.image_url_found.emit(artist_key, img_url)
                    return

        self.image_url_found.emit(artist_key, "")
