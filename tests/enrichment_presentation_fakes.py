"""Shared fakes for the M6.9 Presentation test suite (no live network).

The production composition (bootstrap) is exercised separately; here the
EnrichmentBridge is driven through the real EnrichmentCoordinator over
fake providers, with a duck-typed library projection.
"""

from enrichment_fakes import (
    FakeIdentityResolver,
    InMemoryIdentityRepository,
    RecordingAssetStore,
    RecordingKnowledgeRepository,
)

from michi.application.enrichment_coordinator import EnrichmentCoordinator
from michi.application.enrichment_evidence import LibraryEnrichmentEvidenceBuilder
from michi.application.enrichment_ports import (
    ArtistExternalLinks,
    EnrichmentExecutorPort,
    EnrichmentProviderError,
    EnrichmentTransportError,
    HttpRequest,
    HttpResponse,
    HttpTransportPort,
    MusicBrainzKnowledgeProviderPort,
)
from michi.application.enrichment_service import EnrichmentService
from michi.domain.enrichment import (
    ArtistKnowledgeProfile,
    KnowledgeProvenance,
)
from michi.domain.library import TrackRef, build_music_model
from michi.presentation.enrichment_bridge import EnrichmentBridge


def _tracks():
    return (
        TrackRef(
            file_path=Path("/music/a1.flac"),
            title="Track One",
            artist="Artist A",
            album="Album X",
            album_artist="Artist A",
            year=1980,
            duration_ms=240000,
            track_number=1,
            disc_number=1,
        ),
        TrackRef(
            file_path=Path("/music/a2.flac"),
            title="Track Two",
            artist="Artist A",
            album="Album X",
            album_artist="Artist A",
            year=1980,
            duration_ms=250000,
            track_number=2,
            disc_number=1,
        ),
        TrackRef(
            file_path=Path("/music/a3.flac"),
            title="Track Three",
            artist="Artist A",
            album="Album Y",
            album_artist="Artist A",
            year=1982,
            duration_ms=200000,
            track_number=1,
            disc_number=1,
        ),
        TrackRef(
            file_path=Path("/music/b1.flac"),
            title="Track Bee",
            artist="Artist B",
            album="Album Bee",
            album_artist="Artist B",
            year=1990,
            duration_ms=180000,
            track_number=1,
            disc_number=1,
        ),
    )


ARTIST_A_KEY = "artist a"
ARTIST_B_KEY = "artist b"
ALBUM_X_KEY = "7::album x::artist a"
ALBUM_Y_KEY = "7::album y::artist a"
ALBUM_B_KEY = "7::album bee::artist b"


def make_model():
    return build_music_model(_tracks())


class InlineExecutor(EnrichmentExecutorPort):
    """Runs work synchronously on the CALLING thread (deterministic
    bridge tests); the production composition uses the real
    ThreadPoolEnrichmentExecutor."""

    def __init__(self):
        self.shutdown_calls = 0

    def submit(self, work) -> bool:
        work()
        return True

    def shutdown(self, wait=True) -> None:
        self.shutdown_calls += 1


class NoopHttpTransport(HttpTransportPort):
    """Fail-closed transport: any request is an error (never live)."""

    def request(self, request: HttpRequest, timeout_ms: int = 0) -> HttpResponse:
        raise EnrichmentProviderError("no network in tests")

    def get(self, request: HttpRequest, timeout_ms: int = 0) -> HttpResponse:
        raise EnrichmentProviderError("no network in tests")


class FakeMbKnowledge(MusicBrainzKnowledgeProviderPort):
    def __init__(self, offline=False):
        self.offline = offline
        self.calls = 0

    def fetch_artist(self, local_artist_key, external_artist_id):
        self.calls += 1
        if self.offline:
            raise EnrichmentTransportError("transport offline")
        return ArtistKnowledgeProfile(
            local_artist_key=local_artist_key,
            external_artist_id=external_artist_id,
            biography="A composer biography.",
            external_genres=("Classical",),
            begin_year=1950,
            end_year=2000,
            official_website="https://example.org/artist",
            area="Area X",
            country_qid="Q30",
            country_label="United States",
            provenance=KnowledgeProvenance(
                provider="musicbrainz",
                source_url="https://musicbrainz.org/artist/mb-a",
                license="CC BY-NC-SA 3.0",
                retrieved_at="2026-08-23T00:00:00Z",
            ),
            biography_provenance=KnowledgeProvenance(
                provider="wikipedia",
                source_url="https://en.wikipedia.org/wiki/Artist_A",
                language="en",
                attribution="Wikipedia contributors",
            ),
        )

    def artist_links(self, external_artist_id):
        return ArtistExternalLinks()

    def fetch_release_group(self, local_album_key, release_group_id, release_id=""):
        self.calls += 1
        if self.offline:
            raise EnrichmentTransportError("transport offline")
        from michi.domain.enrichment import AlbumKnowledgeProfile

        return AlbumKnowledgeProfile(
            local_album_key=local_album_key,
            release_group_id=release_group_id,
            release_id=release_id,
            external_genres=("Rock",),
            first_release_year=1980,
            release_year=1980 if release_id else 0,
            label="Label X" if release_id else "",
            provenance=KnowledgeProvenance(
                provider="musicbrainz",
                source_url="https://musicbrainz.org/release-group/rg-x",
                license="CC BY-NC-SA 3.0",
            ),
        )


class CountingResolver(FakeIdentityResolver):
    """FakeIdentityResolver + call counter (network proxy in tests)."""

    def __init__(self, artists=(), groups=(), editions=()):
        super().__init__(artists, groups, editions)
        self.calls = 0

    def find_artist_candidates(self, evidence):
        self.calls += 1
        return super().find_artist_candidates(evidence)

    def find_release_group_candidates(self, evidence):
        self.calls += 1
        return super().find_release_group_candidates(evidence)

    def find_release_edition_candidates(self, evidence):
        self.calls += 1
        return super().find_release_edition_candidates(evidence)


class FakePresentationLibrary:
    """Duck-typed LibraryService projection used by the bridge."""

    def __init__(self, model, tracks=None):
        self._artists = model.artists
        self._albums = model.albums
        self._tracks = tracks if tracks is not None else _tracks()

    def artist_by_key(self, artist_key):
        for artist in self._artists:
            if artist.key == artist_key:
                return artist
        return None

    def albums_for_artist(self, artist_key):
        from michi.domain.library import make_artist_key

        return tuple(
            album
            for album in self._albums
            if make_artist_key(album.artist) == artist_key
        )

    def tracks_for_artist(self, artist_key):
        from michi.domain.library import make_artist_key

        return tuple(
            track
            for track in self._tracks
            if make_artist_key(track.artist.strip() or "Unknown Artist") == artist_key
        )

    def album_by_key(self, album_key):
        for album in self._albums:
            if album.key == album_key:
                return album
        return None


def make_bridge(
    online=False,
    resolver=None,
    mb_knowledge=None,
    asset_store=None,
    executor=None,
):
    """Real coordinator + real service over fakes + EnrichmentBridge."""
    from michi.domain.enrichment import (
        ArtistCandidate,
        LocalAlbumEvidence,
        ReleaseGroupCandidate,
    )

    if resolver is None:
        # Resolvable fake: single candidate for "Artist A" / "Album X".
        resolver = CountingResolver(
            artists=(
                ArtistCandidate(
                    "mb-a",
                    canonical_name="Artist A",
                    known_albums=(LocalAlbumEvidence("Album X", 1980),),
                ),
            ),
            groups=(
                ReleaseGroupCandidate(
                    release_group_id="rg-x",
                    title="Album X",
                    artist_credit_names=("Artist A",),
                    first_release_year=1980,
                ),
                ReleaseGroupCandidate(
                    release_group_id="rg-y",
                    title="Album Y",
                    artist_credit_names=("Artist A",),
                    first_release_year=1982,
                ),
            ),
        )
    mb_knowledge = mb_knowledge if mb_knowledge is not None else FakeMbKnowledge()
    asset_store = asset_store if asset_store is not None else RecordingAssetStore()
    repository = RecordingKnowledgeRepository()
    identity_repo = InMemoryIdentityRepository()
    service = EnrichmentService(
        resolver=resolver,
        artist_provider=None,
        album_provider=None,
        repository=repository,
        identity_repository=identity_repo,
        asset_store=asset_store,
    )
    coordinator = EnrichmentCoordinator(
        service=service,
        resolver=resolver,
        evidence_builder=LibraryEnrichmentEvidenceBuilder(_NoHintsExtractor()),
        mb_knowledge=mb_knowledge,
        wikidata=None,
        wikipedia=None,
        commons=None,
        coverart=None,
        asset_store=asset_store,
        executor=executor if executor is not None else InlineExecutor(),
        transport=NoopHttpTransport(),
        enabled=lambda: True,
    )
    library = FakePresentationLibrary(make_model())
    bridge = EnrichmentBridge(
        coordinator=coordinator,
        service=service,
        library=library,
        asset_store=asset_store,
    )
    bridge.on_online_enrichment_changed(online)
    return bridge, service, identity_repo, repository, asset_store, coordinator, library


class _NoHintsExtractor:
    def extract_hints(self, file_path):
        from michi.domain.enrichment import ExternalIdentityHints

        return ExternalIdentityHints()


def ensure_app():
    """Create ONE GUI application (offscreen) — relay QueuedConnection
    needs a running dispatcher, and QML components require a
    QGuiApplication. A plain QCoreApplication would prevent the QML
    suite from creating the GUI app later (Qt abort)."""
    import os

    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance()
    if app is None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        app = QGuiApplication([])
    return app


def process_events(times: int = 4) -> None:
    """Deliver queued relay signals without sleeping (safety bound)."""
    app = ensure_app()
    for _ in range(times):
        app.processEvents()


class Waiter:
    """Deterministic wait on a predicate with a safety timeout (no sleeps)."""

    def __init__(self, timeout_s: float = 5.0):
        self._timeout_s = timeout_s
        self._deadline = _now() + timeout_s

    def until(self, predicate) -> bool:
        while not predicate():
            if _now() > self._deadline:
                return False
            process_events(2)
        return True


def _now():
    import time

    return time.monotonic()


# keep path import available for track builders
from pathlib import Path  # noqa: E402
