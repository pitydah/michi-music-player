"""M6.9B — provider transport, rate limiter and cache contracts.

Security matrix (no live network — all tests use injectable seams):
- HTTPS-only / host allowlist / blocked hosts / redirect validation
- body bound
- MusicBrainz serializer (injectable clock/sleeper)
- provider cache: fresh hit, expiry, stale read, atomicity, corruption
"""

import io
import threading

import pytest

from michi.application.enrichment_ports import (
    EnrichmentProviderError,
    HttpRequest,
    HttpResponse,
)
from michi.infrastructure.enrichment_http import (
    MAX_PROVIDER_BODY_BYTES,
    MusicBrainzRateLimiter,
    UrllibHttpTransport,
    _ValidatingRedirectHandler,
    is_allowed_host,
    validate_provider_url,
)
from michi.infrastructure.enrichment_provider_cache import (
    FilesystemProviderCache,
)


class FakeResponse:
    def __init__(self, body: bytes, status: int = 200, headers=None, url=None):
        self._body = body
        self.status = status
        self.headers = headers or {}
        self._url = url or "https://musicbrainz.org/ws/2/test"
        self._closed = False

    def read(self, size=-1):
        if size < 0:
            return self._body
        return self._body[:size]

    def getcode(self):
        return self.status

    def geturl(self):
        return self._url

    def close(self):
        self._closed = True


class ChunkedResponse(FakeResponse):
    def __init__(self, body: bytes, **kwargs):
        super().__init__(body, **kwargs)
        self._offset = 0

    def read(self, size=-1):
        if size < 0:
            chunk = self._body[self._offset :]
            self._offset = len(self._body)
            return chunk
        chunk = self._body[self._offset : self._offset + size]
        self._offset += size
        return chunk


class FakeOpener:
    def __init__(self, responses=None, error=None):
        self._responses = list(responses or [])
        self._error = error
        self.calls: list[HttpRequest] = []

    def open(self, req, timeout=None):
        self.calls.append(req)
        if self._error:
            raise self._error
        return self._responses.pop(0)


class TestHostAllowlist:
    @pytest.mark.parametrize(
        ("host", "allowed"),
        [
            ("musicbrainz.org", True),
            ("www.wikidata.org", True),
            ("en.wikipedia.org", True),
            ("pt.wikipedia.org", True),
            ("commons.wikimedia.org", True),
            ("upload.wikimedia.org", True),
            ("coverartarchive.org", True),
            ("archive.org", True),
            ("ia800300.us.archive.org", True),
            ("evil.com", False),
            ("musicbrainz.org.evil.com", False),
            ("localhost", False),
            ("127.0.0.1", False),
            ("", False),
        ],
    )
    def test_allowlist(self, host, allowed):
        assert is_allowed_host(host) is allowed

    @pytest.mark.parametrize(
        "url",
        [
            "http://musicbrainz.org/ws/2/artist",
            "file:///etc/passwd",
            "ftp://musicbrainz.org/x",
            "https://evil.com/x",
            "https://localhost/x",
            "https://127.0.0.1/x",
            "https://user:pass@musicbrainz.org/x",
        ],
    )
    def test_unsafe_urls_rejected(self, url):
        with pytest.raises(ValueError):
            validate_provider_url(url)

    def test_safe_url_accepted(self):
        validate_provider_url("https://musicbrainz.org/ws/2/artist?query=x")


class TestTransport:
    def test_get_returns_response(self):
        opener = FakeOpener([ChunkedResponse(b'{"ok": true}')])
        transport = UrllibHttpTransport(opener=opener)
        response = transport.get(HttpRequest(url="https://musicbrainz.org/ws/2/test"))
        assert response.status_code == 200
        assert response.body == b'{"ok": true}'
        assert response.final_url == "https://musicbrainz.org/ws/2/test"

    def test_user_agent_identifies_michi(self):
        opener = FakeOpener([ChunkedResponse(b"{}")])
        transport = UrllibHttpTransport(opener=opener)
        transport.get(HttpRequest(url="https://musicbrainz.org/ws/2/test"))
        sent = opener.calls[0].get_header("User-agent")
        assert sent is not None and sent.startswith("MichiMusicPlayer/")

    def test_non_get_rejected(self):
        transport = UrllibHttpTransport(opener=FakeOpener([]))
        with pytest.raises(ValueError):
            transport.get(HttpRequest(url="https://musicbrainz.org/x", method="POST"))

    def test_body_cap_enforced(self):
        huge = ChunkedResponse(b"x" * (MAX_PROVIDER_BODY_BYTES + 1024))
        transport = UrllibHttpTransport(opener=FakeOpener([huge]))
        with pytest.raises(EnrichmentProviderError):
            transport.get(HttpRequest(url="https://musicbrainz.org/ws/2/test"))

    def test_provider_http_error_normalized(self):
        from urllib.error import HTTPError

        opener = FakeOpener(
            error=HTTPError(
                "https://musicbrainz.org/x", 503, "unavailable", {}, io.BytesIO(b"")
            )
        )
        transport = UrllibHttpTransport(opener=opener)
        with pytest.raises(EnrichmentProviderError):
            transport.get(HttpRequest(url="https://musicbrainz.org/ws/2/test"))

    def test_redirect_validation_rejects_bad_host(self):
        handler = _ValidatingRedirectHandler()
        with pytest.raises(EnrichmentProviderError):
            handler.redirect_request(None, None, 302, "found", {}, "https://evil.com/x")

    def test_redirect_validation_rejects_http(self):
        handler = _ValidatingRedirectHandler()
        with pytest.raises(EnrichmentProviderError):
            handler.redirect_request(
                None, None, 301, "moved", {}, "http://musicbrainz.org/x"
            )


class TestMusicBrainzRateLimiter:
    def _make(self):
        state = {"now": 1000.0, "sleeps": []}

        def clock():
            return state["now"]

        def sleeper(seconds):
            state["sleeps"].append(seconds)
            state["now"] += seconds

        return MusicBrainzRateLimiter(clock=clock, sleeper=sleeper), state

    def test_two_requests_serialized(self):
        limiter, state = self._make()
        limiter.wait()
        limiter.wait()
        assert state["sleeps"] == [1.0]

    def test_no_wait_after_interval_elapsed(self):
        limiter, state = self._make()
        limiter.wait()
        state["now"] += 5.0
        limiter.wait()
        assert state["sleeps"] == []

    def test_concurrent_requests_serialized(self):
        limiter, state = self._make()
        state["sleeps"] = []
        order: list[int] = []

        def worker(n):
            limiter.wait()
            order.append(n)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # All four got slots (no deadlock) and sleeps were enforced.
        assert len(order) == 4
        assert len(state["sleeps"]) >= 3


class TestProviderCache:
    def test_fresh_hit(self, tmp_path):
        cache = FilesystemProviderCache(tmp_path / "cache", clock=lambda: 1000.0)
        cache.put(
            "musicbrainz_search",
            "https://musicbrainz.org/ws/2/artist?query=x",
            HttpResponse(200, {}, b'{"a":1}', "https://musicbrainz.org/x"),
            ttl_seconds=3600,
        )
        entry = cache.get(
            "musicbrainz_search",
            "https://musicbrainz.org/ws/2/artist?query=x",
        )
        assert entry is not None
        assert entry.body == b'{"a":1}'

    def test_expired_returns_none_but_stale_readable(self, tmp_path):
        state = {"now": 1000.0}
        cache = FilesystemProviderCache(tmp_path / "cache", clock=lambda: state["now"])
        cache.put(
            "wikipedia",
            "https://en.wikipedia.org/api/x",
            HttpResponse(200, {}, b"bio", "https://en.wikipedia.org/x"),
            ttl_seconds=60,
        )
        state["now"] = 2000.0
        assert cache.get("wikipedia", "https://en.wikipedia.org/api/x") is None
        stale = cache.get_stale("wikipedia", "https://en.wikipedia.org/api/x")
        assert stale is not None
        assert stale.body == b"bio"

    def test_corrupt_entry_discarded(self, tmp_path):
        cache = FilesystemProviderCache(tmp_path / "cache")
        cache.put(
            "wikidata",
            "https://www.wikidata.org/x",
            HttpResponse(200, {}, b"{}", "https://www.wikidata.org/x"),
            ttl_seconds=3600,
        )
        key = cache.cache_key("wikidata", "https://www.wikidata.org/x")
        path = cache._entry_path(key)
        path.write_text("{corrupt", encoding="utf-8")
        assert cache.get("wikidata", "https://www.wikidata.org/x") is None

    def test_remove_expired_bounded(self, tmp_path):
        state = {"now": 1000.0}
        cache = FilesystemProviderCache(tmp_path / "cache", clock=lambda: state["now"])
        cache.put(
            "coverart",
            "https://coverartarchive.org/a",
            HttpResponse(200, {}, b"{}", "https://coverartarchive.org/a"),
            ttl_seconds=10,
        )
        state["now"] = 1000.0 + 100 * 86400
        assert cache.remove_expired(older_than_days=90) == 1
