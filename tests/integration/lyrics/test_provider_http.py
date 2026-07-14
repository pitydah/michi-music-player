import pytest
import threading
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

from core.lyrics.models import TrackIdentity
from infrastructure.lyrics.providers.lrclib_provider import LrcLibProvider


class _LyricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/get"):
            if "track_name=Existing" in self.path:
                self._json(200, {
                    "id": 1,
                    "trackName": "Existing",
                    "artistName": "Artist",
                    "albumName": "Album",
                    "duration": 240,
                    "syncedLyrics": "[01:00.00]Line one\n[02:00.00]Line two",
                    "plainLyrics": "Line one\nLine two",
                })
            elif "track_name=Plain" in self.path:
                self._json(200, {
                    "id": 2,
                    "trackName": "Plain",
                    "artistName": "Artist",
                    "syncedLyrics": "",
                    "plainLyrics": "Only plain lyrics\nLine two",
                })
            elif "track_name=NotFound" in self.path:
                self.send_response(404)
                self.end_headers()
            elif "track_name=ServerError" in self.path:
                self.send_response(500)
                self.end_headers()
            elif "track_name=Slow" in self.path:
                time.sleep(3)
                self._json(200, {
                    "id": 3,
                    "trackName": "Slow",
                    "syncedLyrics": "[01:00.00]Slow response",
                    "plainLyrics": "Slow response",
                })
            elif "track_name=Instrumental" in self.path:
                self._json(200, {
                    "id": 4,
                    "trackName": "Instrumental",
                    "artistName": "Artist",
                    "syncedLyrics": "",
                    "plainLyrics": "",
                })
            else:
                self._json(200, {
                    "id": 5,
                    "trackName": "Default",
                    "syncedLyrics": "[01:00.00]Default",
                    "plainLyrics": "Default",
                })
        elif self.path.startswith("/api/search"):
            q = self.path.split("q=")[-1] if "q=" in self.path else ""
            if "Existing" in q:
                self._json(200, [
                    {"id": 1, "trackName": "Existing", "artistName": "Artist",
                     "syncedLyrics": "[01:00.00]Found", "plainLyrics": "Found"},
                    {"id": 2, "trackName": "Candidate", "artistName": "Artist2",
                     "syncedLyrics": "", "plainLyrics": "Candidate lyrics"},
                ])
            else:
                self._json(200, [])
        elif self.path == "/invalid":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"not json")
        else:
            self.send_response(404)
            self.end_headers()

    def _json(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_request(self, *args):
        pass


@pytest.fixture(scope="module")
def server():
    srv = HTTPServer(("127.0.0.1", 0), _LyricsHandler)
    port = srv.server_address[1]
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield port
    srv.shutdown()


class _PatchedProvider(LrcLibProvider):
    def __init__(self, port, cache=None):
        super().__init__(cache=cache)
        self._port = port

    def _fetch(self, identity, timeout_ms=10000):
        import urllib.parse
        import urllib.request
        import urllib.error
        import json
        params = {}
        if identity.artist:
            params["artist_name"] = identity.artist
        if identity.title:
            params["track_name"] = identity.title
        if identity.album:
            params["album_name"] = identity.album
        if identity.duration_ms > 0:
            params["duration"] = str(int(identity.duration_ms / 1000))
        url = f"http://127.0.0.1:{self._port}/api/get?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "MichiMusicPlayer/1.0 (lyrics)")
        try:
            with urllib.request.urlopen(req, timeout=timeout_ms / 1000) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            code = "not_found" if e.code == 404 else "provider_unavailable"
            return type("R", (), {"ok": False, "code": code, "document": None, "source": None, "retryable": e.code >= 500, "message": f"HTTP {e.code}"})()
        doc = self._entry_to_doc(data, identity)
        if doc is None:
            return type("R", (), {"ok": False, "code": "not_found", "document": None, "source": None, "retryable": False, "message": ""})()
        return type("R", (), {"ok": True, "document": doc, "code": "ok", "source": None, "retryable": False, "message": ""})()

    def search(self, identity, timeout_ms=10000):
        import urllib.parse
        import urllib.request
        import json
        query = f"{identity.artist} {identity.title}".strip() or identity.title or ""
        url = f"http://127.0.0.1:{self._port}/api/search?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "MichiMusicPlayer/1.0 (lyrics)")
        with urllib.request.urlopen(req, timeout=timeout_ms / 1000) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        candidates = []
        if isinstance(data, list):
            for entry in data:
                doc = self._entry_to_doc(entry, identity)
                if doc:
                    candidates.append(doc)
        return type("R", (), {"ok": True, "candidates": candidates, "code": "ok"})()


class TestLrcLibProviderHTTP:
    def test_resolve_existing(self, server):
        provider = _PatchedProvider(server)
        identity = TrackIdentity(title="Existing", artist="Artist")
        result = provider.resolve(identity, timeout_ms=5000)
        assert result.ok is True
        assert result.document is not None
        assert len(result.document.lines) == 2

    def test_resolve_plain_only(self, server):
        provider = _PatchedProvider(server)
        identity = TrackIdentity(title="Plain", artist="Artist")
        result = provider.resolve(identity)
        assert result.ok is True
        assert result.document.plain_text == "Only plain lyrics\nLine two"

    def test_resolve_not_found(self, server):
        provider = _PatchedProvider(server)
        identity = TrackIdentity(title="NotFound")
        result = provider.resolve(identity)
        assert result.ok is False

    def test_search_returns_candidates(self, server):
        provider = _PatchedProvider(server)
        identity = TrackIdentity(title="Existing")
        result = provider.search(identity)
        assert result.ok is True
        assert len(result.candidates) > 0

    def test_search_empty(self, server):
        provider = _PatchedProvider(server)
        identity = TrackIdentity(title="NoResults")
        result = provider.search(identity)
        assert result.ok is True
        assert len(result.candidates) == 0

    def test_cache_hit(self, server):
        from infrastructure.lyrics.cache_repository import SqliteLyricsCacheRepository
        import tempfile
        import os
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.unlink(path)
        cache = SqliteLyricsCacheRepository(path)
        cache.initialize()

        provider = _PatchedProvider(server, cache=cache)
        identity = TrackIdentity(title="Existing", artist="Artist")
        result1 = provider.resolve(identity)
        assert result1.ok is True

        result2 = provider.resolve(identity)
        assert result2.ok is True

        os.unlink(path)

    def test_cached_negative(self, server):
        from infrastructure.lyrics.cache_repository import SqliteLyricsCacheRepository
        import tempfile
        import os
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.unlink(path)
        cache = SqliteLyricsCacheRepository(path)
        cache.initialize()

        provider = _PatchedProvider(server, cache=cache)
        identity = TrackIdentity(title="NotFound")
        result = provider.resolve(identity)
        assert result.ok is False
        assert cache.get_negative("lrclib:notfound|") is True

        os.unlink(path)
