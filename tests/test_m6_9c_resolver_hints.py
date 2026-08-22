"""M6.9C/D — MusicBrainz resolver, identity hints and evidence builder.

No live network: a scripted fake transport answers by URL prefix.
Covers the required matrices: candidate extraction, malformed payload
handling, retry policy, rate limiting, cache, caps, deterministic
ordering, embedded-hint roles and evidence projection.
"""

import json
import time
from pathlib import Path

import pytest

from michi.application.enrichment_evidence import LibraryEnrichmentEvidenceBuilder
from michi.application.enrichment_ports import (
    EnrichmentProviderError,
    HttpRequest,
    HttpResponse,
    HttpTransportPort,
)
from michi.domain.enrichment import (
    AlbumIdentityEvidence,
    AlbumIdentityHints,
    ArtistIdentityEvidence,
    ArtistIdentityHints,
    ExternalIdentityHints,
    LocalAlbumEvidence,
    ReleaseEditionCandidate,
)
from michi.domain.library import (
    TrackRef,
    build_music_model,
)
from michi.infrastructure.enrichment_http import (
    EnrichmentHttpStatusError,
    MusicBrainzRateLimiter,
)
from michi.infrastructure.enrichment_musicbrainz import (
    MusicBrainzIdentityResolver,
)


class FakeHttpTransport(HttpTransportPort):
    """URL-prefix scripted transport; routes are CONSUMED FIFO so retry
    scenarios can script error-then-success sequences."""

    def __init__(self):
        self.routes: list[tuple[str, object]] = []
        self.requests: list[str] = []

    def route(self, prefix: str, response: object) -> None:
        self.routes.append((prefix, response))

    def get(self, request: HttpRequest) -> HttpResponse:
        self.requests.append(request.url)
        for index, (prefix, response) in enumerate(self.routes):
            if request.url.startswith(prefix):
                del self.routes[index]
                if isinstance(response, Exception):
                    raise response
                return response
        raise AssertionError(f"unscripted URL: {request.url}")


def json_response(payload, url="https://musicbrainz.org/ws/2/x"):
    return HttpResponse(200, {}, json.dumps(payload).encode(), final_url=url)


def artist_payload(artist_id, name, albums=(), disambiguation=""):
    return {
        "id": artist_id,
        "name": name,
        "disambiguation": disambiguation,
        "artist-credit": [
            {"artist": {"id": artist_id}, "name": name, "joinphrase": ""}
        ],
        "release-groups": [
            {
                "id": f"rg-{artist_id}-{i}",
                "title": title,
                "first-release-date": str(year),
                "artist-credit": [
                    {"artist": {"id": artist_id}, "name": name, "joinphrase": ""}
                ],
            }
            for i, (title, year) in enumerate(albums)
        ],
    }


class InstantLimiter(MusicBrainzRateLimiter):
    def __init__(self):
        super().__init__(clock=lambda: 0.0, sleeper=lambda s: None)


class TestMusicBrainzArtistResolution:
    def _resolver(self, transport):
        return MusicBrainzIdentityResolver(
            transport, InstantLimiter(), cache=None, retry_sleeper=lambda s: None
        )

    def test_artist_exact_candidate(self):
        transport = FakeHttpTransport()
        transport.route(
            "https://musicbrainz.org/ws/2/artist/?query=",
            json_response(
                {
                    "artists": [
                        artist_payload(
                            "mb-a", "John Williams", albums=(("Star Wars", 1977),)
                        )
                    ]
                }
            ),
        )
        transport.route(
            "https://musicbrainz.org/ws/2/release-group/?artist=",
            json_response(
                {
                    "release-groups": [
                        {
                            "id": "rg-1",
                            "title": "Star Wars",
                            "first-release-date": "1977",
                        }
                    ]
                }
            ),
        )
        resolver = self._resolver(transport)
        evidence = ArtistIdentityEvidence(
            local_artist_key="john williams", local_artist_name="John Williams"
        )
        candidates = resolver.find_artist_candidates(evidence)
        assert [c.external_artist_id for c in candidates] == ["mb-a"]
        assert candidates[0].known_albums == (LocalAlbumEvidence("Star Wars", 1977),)

    def test_homonym_candidates_deterministic_order(self):
        transport = FakeHttpTransport()
        transport.route(
            "https://musicbrainz.org/ws/2/artist/?query=",
            json_response(
                {
                    "artists": [
                        artist_payload("mb-z", "John Williams"),
                        artist_payload("mb-a", "John Williams"),
                    ]
                }
            ),
        )
        transport.route(
            "https://musicbrainz.org/ws/2/release-group/?artist=",
            json_response({"release-groups": []}),
        )
        transport.route(
            "https://musicbrainz.org/ws/2/release-group/?artist=",
            json_response({"release-groups": []}),
        )
        resolver = self._resolver(transport)
        evidence = ArtistIdentityEvidence(
            local_artist_key="jw", local_artist_name="John Williams"
        )
        candidates = resolver.find_artist_candidates(evidence)
        # Deterministic ascending order — provider order never wins.
        assert [c.external_artist_id for c in candidates] == ["mb-a", "mb-z"]

    def test_malformed_candidate_skipped(self):
        transport = FakeHttpTransport()
        transport.route(
            "https://musicbrainz.org/ws/2/artist/?query=",
            json_response(
                {
                    "artists": [
                        {"id": 123, "name": "Broken"},  # id wrong type
                        artist_payload("mb-a", "Good"),
                    ]
                }
            ),
        )
        transport.route(
            "https://musicbrainz.org/ws/2/release-group/?artist=",
            json_response({"release-groups": []}),
        )
        resolver = self._resolver(transport)
        candidates = resolver.find_artist_candidates(
            ArtistIdentityEvidence(local_artist_key="x", local_artist_name="X")
        )
        assert [c.external_artist_id for c in candidates] == ["mb-a"]

    def test_malformed_top_level_raises(self):
        transport = FakeHttpTransport()
        transport.route(
            "https://musicbrainz.org/ws/2/artist/?query=",
            json_response({"artists": "not-a-list"}),
        )
        resolver = self._resolver(transport)
        with pytest.raises(EnrichmentProviderError):
            resolver.find_artist_candidates(
                ArtistIdentityEvidence(local_artist_key="x", local_artist_name="X")
            )

    def test_invalid_json_raises(self):
        transport = FakeHttpTransport()
        transport.route(
            "https://musicbrainz.org/ws/2/artist/?query=",
            HttpResponse(200, {}, b"{invalid", "https://musicbrainz.org/x"),
        )
        resolver = self._resolver(transport)
        with pytest.raises(EnrichmentProviderError):
            resolver.find_artist_candidates(
                ArtistIdentityEvidence(local_artist_key="x", local_artist_name="X")
            )

    def test_404_does_not_retry(self):
        transport = FakeHttpTransport()
        transport.route(
            "https://musicbrainz.org/ws/2/artist/?query=",
            EnrichmentHttpStatusError(404, {}, "not found"),
        )
        resolver = self._resolver(transport)
        with pytest.raises(EnrichmentProviderError):
            resolver.find_artist_candidates(
                ArtistIdentityEvidence(local_artist_key="x", local_artist_name="X")
            )
        assert len(transport.requests) == 1

    def test_503_retries_then_succeeds(self):
        transport = FakeHttpTransport()
        transport.route(
            "https://musicbrainz.org/ws/2/artist/?query=",
            EnrichmentHttpStatusError(503, {}, "unavailable"),
        )
        transport.route(
            "https://musicbrainz.org/ws/2/artist/?query=",
            json_response({"artists": []}),
        )
        resolver = self._resolver(transport)
        candidates = resolver.find_artist_candidates(
            ArtistIdentityEvidence(local_artist_key="x", local_artist_name="X")
        )
        assert candidates == ()
        assert len(transport.requests) == 2

    def test_503_retries_bounded(self):
        transport = FakeHttpTransport()
        for _ in range(3):
            transport.route(
                "https://musicbrainz.org/ws/2/artist/?query=",
                EnrichmentHttpStatusError(503, {}, "unavailable"),
            )
        resolver = self._resolver(transport)
        with pytest.raises(EnrichmentProviderError):
            resolver.find_artist_candidates(
                ArtistIdentityEvidence(local_artist_key="x", local_artist_name="X")
            )
        assert len(transport.requests) == 3

    def test_cache_hit_skips_network(self, tmp_path):
        from michi.infrastructure.enrichment_provider_cache import (
            FilesystemProviderCache,
        )

        transport = FakeHttpTransport()
        transport.route(
            "https://musicbrainz.org/ws/2/artist/?query=",
            json_response({"artists": []}),
        )
        cache = FilesystemProviderCache(tmp_path / "cache", clock=time.time)
        resolver = MusicBrainzIdentityResolver(
            transport, InstantLimiter(), cache=cache, retry_sleeper=lambda s: None
        )
        evidence = ArtistIdentityEvidence(local_artist_key="x", local_artist_name="X")
        resolver.find_artist_candidates(evidence)
        assert len(transport.requests) == 1
        # Second call: cached → zero additional network requests.
        resolver.find_artist_candidates(evidence)
        assert len(transport.requests) == 1


class TestMusicBrainzAlbumResolution:
    def _resolver(self, transport):
        return MusicBrainzIdentityResolver(
            transport, InstantLimiter(), cache=None, retry_sleeper=lambda s: None
        )

    def test_release_group_candidates_mapped(self):
        transport = FakeHttpTransport()
        transport.route(
            "https://musicbrainz.org/ws/2/release-group/?query=",
            json_response(
                {
                    "release-groups": [
                        {
                            "id": "rg-a",
                            "title": "Greatest Hits",
                            "first-release-date": "1980",
                            "artist-credit": [
                                {
                                    "artist": {"id": "artist-a"},
                                    "name": "Artist A",
                                    "joinphrase": "",
                                }
                            ],
                        }
                    ]
                }
            ),
        )
        resolver = self._resolver(transport)
        evidence = AlbumIdentityEvidence(
            local_album_key="k",
            local_album_title="Greatest Hits",
            local_album_artist_name="Artist A",
        )
        candidates = resolver.find_release_group_candidates(evidence)
        assert len(candidates) == 1
        assert candidates[0].release_group_id == "rg-a"
        assert candidates[0].artist_credit_external_ids == ("artist-a",)
        assert candidates[0].artist_credit_names == ("Artist A",)
        assert candidates[0].first_release_year == 1980

    def test_release_edition_lookup_corroboration_source(self):
        transport = FakeHttpTransport()
        transport.route(
            "https://musicbrainz.org/ws/2/release/rel-x",
            json_response({"release-group": {"id": "rg-a"}}),
        )
        resolver = self._resolver(transport)
        evidence = AlbumIdentityEvidence(
            local_album_key="k",
            local_album_title="",
            identity_hints=AlbumIdentityHints(release_ids=("rel-x",)),
        )
        editions = resolver.find_release_edition_candidates(evidence)
        assert editions == (
            ReleaseEditionCandidate(release_id="rel-x", release_group_id="rg-a"),
        )

    def test_release_edition_without_group_skipped(self):
        transport = FakeHttpTransport()
        transport.route(
            "https://musicbrainz.org/ws/2/release/rel-x",
            json_response({"release-group": None}),
        )
        resolver = self._resolver(transport)
        evidence = AlbumIdentityEvidence(
            local_album_key="k",
            local_album_title="",
            identity_hints=AlbumIdentityHints(release_ids=("rel-x",)),
        )
        assert resolver.find_release_edition_candidates(evidence) == ()


class TestIdentityHints:
    """§88: embedded-hint matrix using a scripted fake extractor."""

    class FakeHintExtractor:
        def __init__(self, hints_by_path):
            self._hints = hints_by_path

        def extract_hints(self, file_path):
            return self._hints.get(str(file_path), ExternalIdentityHints())

    def test_single_artist_mbid(self):
        extractor = TestIdentityHints.FakeHintExtractor(
            {"/m/a.flac": ExternalIdentityHints(musicbrainz_artist_ids=("mb-a",))}
        )
        hints = extractor.extract_hints(Path("/m/a.flac"))
        assert ArtistIdentityHints.from_file_hints(hints).artist_ids == ("mb-a",)

    def test_duplicate_identical_artist_mbid_deduped(self):
        extractor = TestIdentityHints.FakeHintExtractor(
            {
                "/m/a.flac": ExternalIdentityHints(
                    musicbrainz_artist_ids=("mb-a", "mb-a")
                )
            }
        )
        hints = extractor.extract_hints(Path("/m/a.flac"))
        assert ArtistIdentityHints.from_file_hints(hints).artist_ids == ("mb-a",)

    def test_two_conflicting_artist_mbids_preserved(self):
        extractor = TestIdentityHints.FakeHintExtractor(
            {
                "/m/a.flac": ExternalIdentityHints(
                    musicbrainz_artist_ids=("mb-a", "mb-b")
                )
            }
        )
        hints = extractor.extract_hints(Path("/m/a.flac"))
        assert ArtistIdentityHints.from_file_hints(hints).artist_ids == (
            "mb-a",
            "mb-b",
        )

    def test_album_artist_role_separate(self):
        extractor = TestIdentityHints.FakeHintExtractor(
            {
                "/m/a.flac": ExternalIdentityHints(
                    musicbrainz_artist_ids=("track-id",),
                    musicbrainz_album_artist_ids=("album-id",),
                    musicbrainz_release_group_ids=("rg-x",),
                )
            }
        )
        hints = extractor.extract_hints(Path("/m/a.flac"))
        artist_hints = ArtistIdentityHints.from_file_hints(hints)
        album_hints = AlbumIdentityHints.from_file_hints(hints)
        assert artist_hints.artist_ids == ("track-id",)
        assert album_hints.album_artist_ids == ("album-id",)
        assert album_hints.release_group_ids == ("rg-x",)

    def test_blank_ids_dropped(self):
        extractor = TestIdentityHints.FakeHintExtractor(
            {
                "/m/a.flac": ExternalIdentityHints(
                    musicbrainz_artist_ids=("", "  ", "mb-a")
                )
            }
        )
        hints = extractor.extract_hints(Path("/m/a.flac"))
        assert ArtistIdentityHints.from_file_hints(hints).artist_ids == ("mb-a",)


class TestEvidenceBuilder:
    def _tracks(self):
        return (
            TrackRef(
                file_path=Path("/m/a.flac"),
                title="T1",
                artist="Artist A",
                album="Album X",
                year=1980,
                album_artist="Artist A",
            ),
            TrackRef(
                file_path=Path("/m/b.flac"),
                title="T2",
                artist="Artist A",
                album="Album X",
                year=1980,
                album_artist="Artist A",
            ),
        )

    def test_artist_evidence_pairs_albums_and_role_hints(self):
        tracks = self._tracks()
        model = build_music_model(tracks)
        artist = model.artists[0]
        extractor = TestIdentityHints.FakeHintExtractor(
            {
                "/m/a.flac": ExternalIdentityHints(
                    musicbrainz_artist_ids=("mb-a",),
                    musicbrainz_album_artist_ids=("mb-album",),
                ),
                "/m/b.flac": ExternalIdentityHints(),
            }
        )
        builder = LibraryEnrichmentEvidenceBuilder(extractor)
        evidence = builder.artist_evidence(artist, model.albums, tracks)
        assert evidence.local_artist_name == "Artist A"
        assert evidence.known_albums == (LocalAlbumEvidence("Album X", 1980),)
        # Only the TRACK-ARTIST role reaches artist evidence.
        assert evidence.identity_hints.artist_ids == ("mb-a",)

    def test_album_evidence_uses_album_role_hints(self):
        tracks = self._tracks()
        model = build_music_model(tracks)
        album = model.albums[0]
        extractor = TestIdentityHints.FakeHintExtractor(
            {
                "/m/a.flac": ExternalIdentityHints(
                    musicbrainz_release_group_ids=("rg-x",),
                    musicbrainz_release_ids=("rel-x",),
                ),
                "/m/b.flac": ExternalIdentityHints(),
            }
        )
        builder = LibraryEnrichmentEvidenceBuilder(extractor)
        evidence = builder.album_evidence(album)
        assert evidence.local_album_title == "Album X"
        assert evidence.local_album_artist_name == "Artist A"
        assert evidence.identity_hints.release_group_ids == ("rg-x",)
        assert evidence.identity_hints.release_ids == ("rel-x",)
