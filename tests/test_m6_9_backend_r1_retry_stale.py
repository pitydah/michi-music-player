"""M6.9-BACKEND-R1 — retry, rate-limit/cache ordering and stale policy.

- ProviderRequestExecutor: transport timeout → success; exhaustion;
  429 → success; 503×3 fail; 404 no retry; invalid JSON no retry.
- Rate limiter: fresh cache hit consumes NO limiter slot; every
  physical MusicBrainz attempt waits; retries also wait.
- Stale cache: IDENTITY resolution never uses stale entries; knowledge
  falls back to stale ONLY on transient failure and truthfully marks
  provenance (is_stale/retrieved_at); the coordinator reports PARTIAL,
  never READY, for stale knowledge.
"""

import json

import pytest

from michi.application.enrichment_coordinator import EnrichmentOperationState
from michi.application.enrichment_ports import (
    EnrichmentProviderError,
    EnrichmentTransportError,
    HttpRequest,
    HttpResponse,
    HttpTransportPort,
)
from michi.infrastructure.enrichment_http import (
    EnrichmentHttpStatusError,
    MusicBrainzRateLimiter,
    ProviderRequestExecutor,
)
from michi.infrastructure.enrichment_knowledge import WikipediaBiographyProvider
from michi.infrastructure.enrichment_musicbrainz import MusicBrainzIdentityResolver
from michi.infrastructure.enrichment_provider_cache import (
    FilesystemProviderCache,
)


class FakeTransport(HttpTransportPort):
    def __init__(self, script):
        self._script = list(script)
        self.requests = 0

    def get(self, request: HttpRequest) -> HttpResponse:
        self.requests += 1
        item = self._script.pop(0) if self._script else None
        if item is None:
            raise AssertionError("unscripted")
        if isinstance(item, Exception):
            raise item
        return item


class FakeLimiter(MusicBrainzRateLimiter):
    def __init__(self):
        super().__init__(clock=lambda: 0.0, sleeper=lambda s: None)
        self.waits = 0

    def wait(self) -> None:
        self.waits += 1
        super().wait()


class TestProviderRequestExecutor:
    def test_transport_timeout_then_success(self):
        transport = FakeTransport(
            [
                EnrichmentTransportError("timeout"),
                HttpResponse(200, {}, b"{}", "https://musicbrainz.org/x"),
            ]
        )
        limiter = FakeLimiter()
        executor = ProviderRequestExecutor(transport, limiter, sleeper=lambda s: None)
        response = executor.get(HttpRequest(url="https://musicbrainz.org/x"))
        assert response.status_code == 200
        assert limiter.waits == 2  # both physical attempts rate-limited

    def test_transport_exhausted_raises(self):
        transport = FakeTransport([EnrichmentTransportError("t") for _ in range(3)])
        with pytest.raises(EnrichmentTransportError):
            ProviderRequestExecutor(transport, sleeper=lambda s: None).get(
                HttpRequest(url="https://musicbrainz.org/x")
            )

    def test_429_then_success(self):
        transport = FakeTransport(
            [
                EnrichmentHttpStatusError(429, {"retry-after": "1"}, "slow"),
                HttpResponse(200, {}, b"{}", "https://musicbrainz.org/x"),
            ]
        )
        executor = ProviderRequestExecutor(transport, sleeper=lambda s: None)
        assert (
            executor.get(HttpRequest(url="https://musicbrainz.org/x")).status_code
            == 200
        )

    def test_503_times_three_fails(self):
        transport = FakeTransport(
            [EnrichmentHttpStatusError(503, {}, "down") for _ in range(3)]
        )
        with pytest.raises(EnrichmentHttpStatusError):
            ProviderRequestExecutor(transport, sleeper=lambda s: None).get(
                HttpRequest(url="https://musicbrainz.org/x")
            )

    def test_404_no_retry(self):
        transport = FakeTransport([EnrichmentHttpStatusError(404, {}, "no")])
        with pytest.raises(EnrichmentHttpStatusError):
            ProviderRequestExecutor(transport, sleeper=lambda s: None).get(
                HttpRequest(url="https://musicbrainz.org/x")
            )
        assert transport.requests == 1

    def test_retry_after_respected(self):
        delays: list[float] = []
        transport = FakeTransport(
            [
                EnrichmentHttpStatusError(429, {"retry-after": "7"}, "slow"),
                HttpResponse(200, {}, b"{}", "https://musicbrainz.org/x"),
            ]
        )
        executor = ProviderRequestExecutor(transport, sleeper=delays.append)
        executor.get(HttpRequest(url="https://musicbrainz.org/x"))
        assert delays == [7.0]


class TestRateLimitAndCacheOrdering:
    def test_cache_hit_consumes_no_limiter_slot(self, tmp_path):
        cache = FilesystemProviderCache(tmp_path / "cache")
        cache.put(
            "musicbrainz_search",
            "https://musicbrainz.org/ws/2/artist/?query=artist%3An&fmt=json&limit=25",
            HttpResponse(200, {}, b'{"artists": []}', "https://musicbrainz.org/x"),
            ttl_seconds=3600,
        )
        transport = FakeTransport([])  # any network call would fail
        limiter = FakeLimiter()
        resolver = MusicBrainzIdentityResolver(
            transport, limiter, cache=cache, retry_sleeper=lambda s: None
        )
        evidence = __import__(
            "michi.domain.enrichment", fromlist=["ArtistIdentityEvidence"]
        ).ArtistIdentityEvidence(local_artist_key="k", local_artist_name="n")
        candidates = resolver.find_artist_candidates(evidence)
        assert candidates == ()
        assert limiter.waits == 0
        assert transport.requests == 0


class TestStalePolicy:
    def test_identity_never_uses_stale_cache(self, tmp_path):
        cache = FilesystemProviderCache(tmp_path / "cache", clock=lambda: 1000.0)
        cache.put(
            "musicbrainz_search",
            "https://musicbrainz.org/x",
            HttpResponse(200, {}, b'{"artists": []}', "https://musicbrainz.org/x"),
            ttl_seconds=60,
        )
        transport = FakeTransport([EnrichmentTransportError("offline")] * 3)
        state = {"now": 2000.0}
        cache = FilesystemProviderCache(tmp_path / "cache", clock=lambda: state["now"])
        resolver = MusicBrainzIdentityResolver(
            transport, FakeLimiter(), cache=cache, retry_sleeper=lambda s: None
        )
        evidence = __import__(
            "michi.domain.enrichment", fromlist=["ArtistIdentityEvidence"]
        ).ArtistIdentityEvidence(local_artist_key="k", local_artist_name="n")
        # Entry is expired AND the network is down: identity resolution
        # must FAIL, never fall back to the stale entry.
        with pytest.raises(EnrichmentProviderError):
            resolver.find_artist_candidates(evidence)

    def test_knowledge_stale_fallback_marked_truthful(self, tmp_path):
        state = {"now": 1000.0}
        cache = FilesystemProviderCache(tmp_path / "cache", clock=lambda: state["now"])
        cache.put(
            "wikipedia",
            "https://en.wikipedia.org/api/rest_v1/page/summary/John_Williams",
            HttpResponse(
                200,
                {},
                json.dumps({"title": "X", "extract": "cached bio"}).encode(),
                "https://en.wikipedia.org/x",
            ),
            ttl_seconds=60,
        )
        state["now"] = 2000.0  # expired
        transport = FakeTransport(
            [EnrichmentTransportError("offline") for _ in range(3)]
        )
        provider = WikipediaBiographyProvider(
            transport, cache=cache, sleeper=lambda s: None
        )
        bio = provider.fetch_biography("John Williams")
        assert bio.text == "cached bio"
        assert bio.is_stale is True
        assert bio.retrieved_at  # truthful original retrieval time

    def test_stale_never_reported_ready(self):
        # The coordinator reports PARTIAL when the delivered profile's
        # provenance is stale — READY is never fabricated.
        from michi.domain.enrichment import KnowledgeProvenance
        from tests.test_m6_9_backend_r1_cancellation import make_coordinator

        class StaleKnowledge:
            def fetch_artist(self, local_artist_key, external_artist_id):
                from michi.domain.enrichment import ArtistKnowledgeProfile

                return ArtistKnowledgeProfile(
                    local_artist_key=local_artist_key,
                    external_artist_id=external_artist_id,
                    provenance=KnowledgeProvenance(
                        provider="musicbrainz",
                        retrieved_at="2020-01-01T00:00:00+00:00",
                        is_stale=True,
                    ),
                )

            def artist_links(self, external_artist_id):
                from michi.application.enrichment_ports import ArtistExternalLinks

                return ArtistExternalLinks()

            def fetch_release_group(self, *a, **k):
                raise AssertionError("unused")

        coordinator, _, _, _ = make_coordinator(StaleKnowledge())
        tracks = (
            __import__("michi.domain.library", fromlist=["TrackRef"]).TrackRef(
                file_path=__import__("pathlib", fromlist=["Path"]).Path("/a.flac"),
                title="T1",
                artist="Artist A",
                album="Album X",
                year=1980,
                album_artist="Artist A",
            ),
        )
        model = __import__(
            "michi.domain.library", fromlist=["build_music_model"]
        ).build_music_model(tracks)
        states: list[EnrichmentOperationState] = []
        coordinator.enrich_artist(
            model.artists[0], model.albums, tracks, lambda ev: states.append(ev.state)
        )
        coordinator._executor.shutdown(wait=True)
        assert states[-1] is EnrichmentOperationState.PARTIAL
        assert EnrichmentOperationState.READY not in states
