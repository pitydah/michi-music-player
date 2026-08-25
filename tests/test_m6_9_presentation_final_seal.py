"""M6.9-PRESENTATION-FINAL-SEAL — corrective regression matrix.

Deterministic tests (threading.Event, Qt event delivery; no sleeps) for
the audited P0 + P1 defects:

P0-01 manual review correlation (review session + kind + key)
P1-01 settings policy runtime value propagation
P1-02 artist evidence uses the track-artist role
P1-03 knowledge card factual function scope
P1-04 artwork asset provenance projection
P1-05 review delegate interaction (no overlay trap)
"""

import pytest
from enrichment_presentation_fakes import (
    ALBUM_B_KEY,
    ALBUM_X_KEY,
    ARTIST_A_KEY,
    ARTIST_B_KEY,
    BlockingMbKnowledge,
    InlineExecutor,
    make_bridge,
    process_events,
)

from michi.application.enrichment_coordinator import (
    ArtistIdentityCandidateView,
)
from michi.domain.enrichment import EnrichmentAssetRecord, EnrichmentEntityKind


@pytest.fixture(autouse=True, scope="module")
def _app():
    from enrichment_presentation_fakes import ensure_app

    return ensure_app()


@pytest.fixture(scope="module")
def qapp():
    """Local offscreen GUI app (the repository QML pattern) — shadows the
    pytest-qt plugin fixture so no QApplication mismatch warning fires."""
    import os
    import sys as _sys

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(_sys.argv)
    yield app


def _wait_for(bridge, state, timeout_rounds=40):
    for _ in range(timeout_rounds):
        process_events(4)
        if bridge.property("state") == state:
            return True
    return bridge.property("state") == state


class _BlockingSearchCoordinator:
    """Wraps a real coordinator: search callbacks can be held and
    released deterministically."""

    def __init__(self, coordinator):
        self._inner = coordinator
        self._pending: list = []
        self.confirmations: list[tuple] = []

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def search_artist_candidates_async(self, name, on_result, on_error=None):
        def release(candidates):
            on_result(candidates)

        self._pending.append(("artist", release))
        return True

    def search_album_candidates_async(self, title, artist, on_result, on_error=None):
        def release(candidates):
            on_result(candidates)

        self._pending.append(("album", release))
        return True

    def release_next(self, candidates):
        kind, release = self._pending.pop(0)
        release(candidates)

    def confirm_artist_identity(self, key, external_id):
        self.confirmations.append(("artist", key, external_id))
        return self._inner.confirm_artist_identity(key, external_id)

    def confirm_album_identity(self, key, group_id, release_id=""):
        self.confirmations.append(("album", key, group_id))
        return self._inner.confirm_album_identity(key, group_id, release_id)

    def shutdown(self):
        self._inner.shutdown()


# ----------------------------------------------------------------------
# P0-01 — manual review correlation
# ----------------------------------------------------------------------


class TestManualReviewCorrelation:
    def _make_blocking_bridge(self):
        bridge, service, idr, repo, store, coordinator, library = make_bridge(
            online=True, executor=InlineExecutor()
        )
        blocking = _BlockingSearchCoordinator(coordinator)
        bridge._coordinator = blocking
        return bridge, service, idr, blocking, library

    def test_fs01_stale_artist_result_cannot_appear_for_other_artist(self):
        """P0-A: A's late search result is ignored after switching to B."""
        bridge, _, _, blocking, _ = self._make_blocking_bridge()
        bridge.activate_artist(ARTIST_A_KEY)
        process_events(4)
        bridge.open_review("artist")
        bridge.search_artist("Artist A")
        # close review + navigate to B + open a NEW review
        bridge.close_review()
        bridge.activate_artist(ARTIST_B_KEY)
        process_events(4)
        bridge.open_review("artist")

        # A's result arrives late (same epoch counter, OLD session)
        blocking.release_next(
            (ArtistIdentityCandidateView("mb-old", "Old A", "", "musicbrainz"),)
        )
        process_events(8)
        assert bridge.property("artistCandidates") == []
        assert bridge.property("reviewLoading") is False

    def test_fs02_stale_artist_candidate_cannot_be_confirmed_on_b(self):
        """P0-C: a stale A candidate can never become MANUAL identity
        for B — confirm_artist_identity for B is never called with A id."""
        bridge, service, identity_repo, blocking, _ = self._make_blocking_bridge()
        bridge.activate_artist(ARTIST_A_KEY)
        process_events(4)
        bridge.open_review("artist")
        bridge.search_artist("Artist A")
        bridge.close_review()
        bridge.activate_artist(ARTIST_B_KEY)
        process_events(4)
        bridge.open_review("artist")

        # A's result arrives after B is active: not visible, not confirmable.
        blocking.release_next(
            (ArtistIdentityCandidateView("mb-old", "Old A", "", "musicbrainz"),)
        )
        process_events(8)
        assert bridge.property("artistCandidates") == []
        bridge.confirm_artist_candidate("mb-old")
        process_events(4)
        assert blocking.confirmations == []
        assert identity_repo.load_artist_identity(ARTIST_B_KEY) is None

    def test_fs03_stale_album_candidate_isolated(self):
        """P0-D: album matrix — stale album result ignored after switch."""
        bridge, _, identity_repo, blocking, _ = self._make_blocking_bridge()
        bridge.activate_album(ALBUM_X_KEY)
        process_events(4)
        bridge.open_review("album")
        bridge.search_album("Album X", "Artist A")
        bridge.close_review()
        bridge.activate_album(ALBUM_B_KEY)
        process_events(4)
        bridge.open_review("album")
        blocking.release_next(
            (
                __import__(
                    "michi.application.enrichment_coordinator",
                    fromlist=["AlbumIdentityCandidateView"],
                ).AlbumIdentityCandidateView("rg-old", "Old Album", "Artist A", 1999),
            )
        )
        process_events(8)
        assert bridge.property("albumCandidates") == []
        bridge.confirm_album_candidate("rg-old")
        process_events(4)
        assert blocking.confirmations == []
        assert identity_repo.load_album_identity(ALBUM_B_KEY) is None

    def test_fs04_close_review_invalidates_search_session(self):
        """Close invalidates the session: a result arriving after close is
        dropped even if a new review for the SAME entity is open."""
        bridge, _, _, blocking, _ = self._make_blocking_bridge()
        bridge.activate_artist(ARTIST_A_KEY)
        process_events(4)
        bridge.open_review("artist")
        bridge.search_artist("Artist A")
        bridge.close_review()
        bridge.open_review("artist")  # NEW session, same entity
        blocking.release_next(
            (ArtistIdentityCandidateView("mb-stale", "Stale", "", "musicbrainz"),)
        )
        process_events(8)
        assert bridge.property("artistCandidates") == []

    def test_fs14_confirm_fires_exactly_once(self):
        """A visible candidate confirmed exactly once, and only within
        its own review session."""
        bridge, _, identity_repo, blocking, _ = self._make_blocking_bridge()
        bridge.activate_artist(ARTIST_A_KEY)
        process_events(4)
        bridge.open_review("artist")
        bridge.search_artist("Artist A")
        blocking.release_next(
            (ArtistIdentityCandidateView("mb-a", "Artist A", "", "musicbrainz"),)
        )
        process_events(8)
        assert len(bridge.property("artistCandidates")) == 1
        bridge.confirm_artist_candidate("mb-a")
        process_events(8)
        # close_review() inside confirm invalidates the session: a second
        # confirm attempt is a no-op (and never reaches the coordinator).
        bridge.confirm_artist_candidate("mb-a")
        process_events(4)
        assert len(blocking.confirmations) == 1
        assert blocking.confirmations[0] == ("artist", ARTIST_A_KEY, "mb-a")


# ----------------------------------------------------------------------
# P1-01 — settings policy runtime propagation
# ----------------------------------------------------------------------


class TestSettingsPolicyWiring:
    def test_fs05_policy_on_to_off_reaches_bridge_truthfully(self):
        """Real SettingsBridge → (composition lambda) → EnrichmentBridge:
        OFF persists, the bridge receives False and cancels live work."""

        from michi.application.settings_service import SettingsService
        from michi.presentation.settings_bridge import SettingsBridge

        repo = _PersistentFakeRepo()
        service = SettingsService(repo)
        sb = SettingsBridge(service)
        bridge, _, _, _, _, coordinator, _ = make_bridge(online=True)

        cancels = []
        original_cancel = coordinator.cancel_all
        coordinator.cancel_all = lambda: cancels.append(True) or original_cancel()

        sb.onlineEnrichmentChanged.connect(
            lambda: bridge.on_online_enrichment_changed(
                bool(sb.property("onlineEnrichment"))
            )
        )
        # ON: bridge sees True, no network starts from toggling alone.
        sb.set_online_enrichment(True)
        process_events(4)
        assert bridge.property("onlineEnabled") is True
        resolver = bridge._service._resolver
        calls_before = resolver.calls
        process_events(8)
        assert resolver.calls == calls_before  # no auto network on toggle

        # ON → OFF: persisted False, bridge False, cancel_all exactly once.
        sb.set_online_enrichment(False)
        process_events(4)
        assert service.state.online_enrichment is False
        assert repo.persisted is False
        assert bridge.property("onlineEnabled") is False
        assert len(cancels) == 1

    def test_fs06_policy_off_cancels_live_operation(self):
        bridge, _, _, _, _, _, _ = make_bridge(online=True)
        bridge.activate_artist(ARTIST_A_KEY)
        assert _wait_for(bridge, "READY")
        bridge.on_online_enrichment_changed(False)
        process_events(8)
        # Cached data remains visible; state converges without stale UI.
        assert bridge.property("artistHasKnowledge") is True
        assert bridge.property("state") == "READY"
        resolver = bridge._service._resolver
        calls_before = resolver.calls
        bridge.refresh_artist()
        process_events(8)
        assert resolver.calls == calls_before  # no new network while OFF


class _PersistentFakeRepo:
    """SettingsRepository preserving online_enrichment (fake_settings_repo
    in conftest does NOT preserve it — this one does)."""

    def __init__(self):
        from michi.domain.settings import SettingsState

        self._state = SettingsState()
        self.persisted = None

    def load(self):
        return self._state

    def save(self, state):
        self._state = state
        self.persisted = state.online_enrichment


# ----------------------------------------------------------------------
# P1-02 — artist evidence uses the track-artist role
# ----------------------------------------------------------------------


class TestArtistRoleEvidence:
    def _library_with_tracks(self, tracks):
        from michi.application.library_service import LibraryService
        from tests.test_library_metadata import FakeExtractor, FakeScanner

        class _Scanner(FakeScanner):
            def __init__(self, paths):
                self.paths = paths

            def scan(self, directory, on_progress=None, on_complete=None):
                if on_complete:
                    on_complete()

        scanner = FakeScanner([])
        scanner.paths = []
        library = LibraryService(
            scanner,
            metadata_extractor=FakeExtractor(factory=lambda p: _meta_for(p, tracks)),
        )
        return library

    def test_fs07_compilation_track_belongs_to_track_artist(self, tmp_path):
        """TRACKARTIST 'Artist A' with ALBUMARTIST 'Various Artists' —
        the track belongs to Artist A's evidence."""
        from michi.application.library_service import LibraryService
        from michi.domain.library import TrackRef
        from tests.test_library_metadata import FakeExtractor, FakeScanner

        path = tmp_path / "t1.flac"
        path.write_bytes(b"x")
        track = TrackRef(
            file_path=path,
            title="T1",
            artist="Artist A",
            album="Compilation",
            album_artist="Various Artists",
        )

        library = LibraryService(
            FakeScanner([path]),
            metadata_extractor=FakeExtractor(factory=lambda p: _meta_for(p, [track])),
        )
        library.scan(str(tmp_path))
        assert len(library.state.tracks) == 1  # one canonical track

        tracks = library.tracks_for_artist("artist a")
        assert len(tracks) == 1
        assert tracks[0].artist == "Artist A"

    def test_fs08_blank_album_artist_keeps_track(self, tmp_path):
        """TRACKARTIST 'Artist A' with blank album_artist: still included."""
        from michi.application.library_service import LibraryService
        from michi.domain.library import TrackRef
        from tests.test_library_metadata import FakeExtractor, FakeScanner

        path = tmp_path / "t2.flac"
        path.write_bytes(b"x")
        track = TrackRef(
            file_path=path,
            title="T2",
            artist="Artist A",
            album="Solo",
            album_artist="",
        )

        library = LibraryService(
            FakeScanner([path]),
            metadata_extractor=FakeExtractor(factory=lambda p: _meta_for(p, [track])),
        )
        library.scan(str(tmp_path))
        tracks = library.tracks_for_artist("artist a")
        assert len(tracks) == 1

    def test_fs09_guest_track_under_guest_artist(self, tmp_path):
        """GUEST artist track on a MAIN artist album: the guest evidence
        contains the track; the main artist evidence does not."""
        from michi.application.library_service import LibraryService
        from michi.domain.library import TrackRef
        from tests.test_library_metadata import FakeExtractor, FakeScanner

        path = tmp_path / "t3.flac"
        path.write_bytes(b"x")
        track = TrackRef(
            file_path=path,
            title="Feat.",
            artist="Guest Artist",
            album="Main Album",
            album_artist="Main Album Artist",
        )

        library = LibraryService(
            FakeScanner([path]),
            metadata_extractor=FakeExtractor(factory=lambda p: _meta_for(p, [track])),
        )
        library.scan(str(tmp_path))
        guest = library.tracks_for_artist("guest artist")
        main = library.tracks_for_artist("main album artist")
        assert len(guest) == 1
        assert main == ()


def _meta_for(path, tracks):
    from michi.domain.library import TrackMetadata

    track = next(
        (t for t in tracks if t.file_path == path),
        tracks[0] if tracks else None,
    )
    return TrackMetadata(
        title=track.title,
        artist=track.artist,
        album=track.album,
        album_artist=track.album_artist,
        duration_ms=track.duration_ms,
    )


# ----------------------------------------------------------------------
# P1-04 — artwork asset provenance
# ----------------------------------------------------------------------


class TestArtworkAssetProvenance:
    def test_fs11_asset_record_projected_truthfully(self):
        """Commons-style asset record: creator/license/licenseUrl/
        attribution/sourceUrl all projected; no invented fields."""
        from enrichment_presentation_fakes import RecordingAssetStore

        bridge, service, _, _, asset_store, _, _ = make_bridge(
            online=True, asset_store=RecordingAssetStore()
        )
        # Seed an artist profile whose artwork carries a manifest record.
        record = EnrichmentAssetRecord(
            asset_id="asset-1",
            entity_kind=EnrichmentEntityKind.ARTIST,
            external_entity_id="mb-a",
            mime_type="image/jpeg",
            provider="commons",
            source_url="https://commons.wikimedia.org/wiki/File:X.jpg",
            creator="Photographer X",
            license="CC BY-SA 4.0",
            license_url="https://creativecommons.org/licenses/by-sa/4.0/",
            attribution="Photographer X, via Wikimedia Commons",
        )
        asset_store.store(record, b"jpg-data")
        _seed_artist_profile(service, bridge, artwork_asset_id="asset-1")

        attributions = bridge.property("artistAttributions")
        asset_row = next(
            (a for a in attributions if a.get("provider") == "commons"), None
        )
        assert asset_row is not None
        assert asset_row["creator"] == "Photographer X"
        assert asset_row["license"] == "CC BY-SA 4.0"
        assert (
            asset_row["licenseUrl"] == "https://creativecommons.org/licenses/by-sa/4.0/"
        )
        assert asset_row["attribution"] == "Photographer X, via Wikimedia Commons"
        assert asset_row["sourceUrl"] == "https://commons.wikimedia.org/wiki/File:X.jpg"
        assert asset_row["isStale"] is False
        assert bridge.property("artistArtworkPath") != ""

    def test_fs12_missing_fields_stay_missing(self):
        """A record without license/creator must NOT invent them."""
        from enrichment_presentation_fakes import RecordingAssetStore

        bridge, service, _, _, asset_store, _, _ = make_bridge(
            online=True, asset_store=RecordingAssetStore()
        )
        record = EnrichmentAssetRecord(
            asset_id="asset-2",
            entity_kind=EnrichmentEntityKind.ARTIST,
            external_entity_id="mb-a",
            mime_type="image/jpeg",
            provider="coverartarchive",
            source_url="https://coverartarchive.org/release/x/front",
        )
        asset_store.store(record, b"jpg-data")
        _seed_artist_profile(service, bridge, artwork_asset_id="asset-2")

        attributions = bridge.property("artistAttributions")
        asset_row = next(
            (a for a in attributions if a.get("provider") == "coverartarchive"),
            None,
        )
        assert asset_row is not None
        assert "license" not in asset_row
        assert "creator" not in asset_row
        assert "attribution" not in asset_row
        assert asset_row["sourceUrl"] == "https://coverartarchive.org/release/x/front"

    def test_fs13_no_asset_record_no_fabricated_attribution(self):
        bridge, _, _, _, _, _, _ = make_bridge(online=True)
        # profile without artwork: nothing fabricated
        _seed_artist_profile(
            service=bridge._service, bridge=bridge, artwork_asset_id=""
        )
        assert bridge.property("artistArtworkPath") == ""


def _seed_artist_profile(service, bridge, artwork_asset_id):
    from michi.domain.enrichment import (
        ArtistIdentityEvidence,
        ArtistIdentityHints,
        ArtistKnowledgeProfile,
        DeliveryVerdict,
        EnrichmentEntityKind,
        KnowledgeProvenance,
    )

    gen = service.begin_operation(EnrichmentEntityKind.ARTIST, ARTIST_A_KEY)
    out = service.request_artist_enrichment(
        ArtistIdentityEvidence(
            local_artist_key=ARTIST_A_KEY,
            local_artist_name="Artist A",
            identity_hints=ArtistIdentityHints(artist_ids=("mb-a",)),
        ),
        generation=gen,
    )
    profile = ArtistKnowledgeProfile(
        local_artist_key=ARTIST_A_KEY,
        external_artist_id="mb-a",
        biography="Biography.",
        artwork_asset_id=artwork_asset_id,
        provenance=KnowledgeProvenance(provider="musicbrainz"),
    )
    assert (
        service.deliver_artist_profile(out.request, profile)
        is DeliveryVerdict.COMMITTED
    )
    bridge.activate_artist(ARTIST_A_KEY)
    process_events(8)


# ----------------------------------------------------------------------
# P1-03 / P1-05 — QML structural seals
# ----------------------------------------------------------------------


class TestQmlStructuralSeals:
    def test_fs10_knowledge_card_factual_scope(self):
        """Factual functions live on the Flow (facts.*), not on root."""
        content = Path(
            "src/michi/presentation/qml/enrichment/EnrichmentKnowledgeCard.qml"
        ).read_text()
        assert "id: facts" in content
        assert "facts.hasFactualFields()" in content
        assert "facts.fact(" in content
        assert "root.fact(" not in content
        assert "root.hasFactualFields(" not in content

    def test_fs13b_review_delegate_has_no_overlay_trap(self):
        """The delegate must NOT stack a full-row MouseArea above the
        confirm button."""
        content = Path(
            "src/michi/presentation/qml/enrichment/ReviewMatchesDialog.qml"
        ).read_text()
        assert "ItemDelegate" in content
        assert "MouseArea {" not in content  # no overlay block anywhere

    def test_fs15_queue_playback_authority_firewall(self):
        """QueueService must stay content-only: no PlaybackService import,
        no navigation, no repeat/shuffle/EOM ownership."""
        queue_src = Path("src/michi/application/queue_service.py").read_text()
        # QueueService must stay content-only: no playback import, no
        # repeat/shuffle/EOM ownership (docstring negations are fine).
        # structural: no playback import statement, no ownership fields
        assert "from michi.application.playback" not in queue_src
        assert "import PlaybackService" not in queue_src
        assert "repeat_mode" not in queue_src
        assert "shuffle_mode" not in queue_src
        assert "end_of_media" not in queue_src
        assert "queue.subscribe_changed(session" not in queue_src


from pathlib import Path  # noqa: E402

# ----------------------------------------------------------------------
# P1 residual — presentation intent barrier for OFF / CLEAR / RESET
# ----------------------------------------------------------------------


class TestPresentationIntentBarrier:
    """A REAL worker parked mid-flight: after OFF/CLEAR/RESET the late
    events of the old operation must never change the UI, and CLEAR must
    never let the old worker resurrect the deleted profile."""

    def _start_blocked_worker(self, knowledge):
        from michi.application.enrichment_executor import (
            ThreadPoolEnrichmentExecutor,
        )

        bridge, service, idr, repo, store, coordinator, library = make_bridge(
            online=True,
            mb_knowledge=knowledge,
            executor=ThreadPoolEnrichmentExecutor(max_workers=2),
        )
        bridge.activate_artist(ARTIST_A_KEY)
        assert knowledge.entered_fetch.wait(timeout=5)  # worker parked
        return bridge, service, idr, coordinator

    def _settle(self, bridge, rounds=60):
        """Deliver queued events until the bridge state stabilizes."""
        for _ in range(rounds):
            process_events(6)
        return bridge.property("state")

    def test_fs16_off_keeps_disabled_after_late_cancelled(self):
        """worker parked -> OFF -> worker released: the late CANCELLED
        (old intent) is ignored; the UI stays DISABLED, never flips to
        CANCELLED."""
        knowledge = BlockingMbKnowledge()
        bridge, service, _, coordinator = self._start_blocked_worker(knowledge)
        bridge.on_online_enrichment_changed(False)
        process_events(6)
        assert bridge.property("state") == "DISABLED"
        knowledge.release_fetch.set()  # worker wakes -> CANCELLED (stale)
        coordinator.shutdown()
        assert self._settle(bridge) == "DISABLED"
        assert bridge.property("stateMessage") == "Online info is disabled"

    def test_fs17_clear_cancels_worker_and_profile_stays_deleted(self):
        """worker parked -> CLEAR -> worker released: the late delivery is
        STALE (generation retired by the cancel) — the profile does NOT
        resurrect and the UI stays IDLE."""
        knowledge = BlockingMbKnowledge()
        bridge, service, _, coordinator = self._start_blocked_worker(knowledge)
        assert service.get_artist_knowledge(ARTIST_A_KEY) is None

        bridge.clear_knowledge()
        process_events(6)
        assert bridge.property("state") == "IDLE"
        assert bridge.property("artistHasKnowledge") is False

        knowledge.release_fetch.set()  # worker tries to deliver late
        coordinator.shutdown()
        assert self._settle(bridge) == "IDLE"
        # the explicit Clear action is NOT reverted by the late worker
        assert service.get_artist_knowledge(ARTIST_A_KEY) is None
        assert service.pending_count() == 0

    def test_fs18_reset_ignores_late_events(self):
        """worker parked -> RESET -> worker released: identity stays
        deleted, late events never change the IDLE projection."""
        knowledge = BlockingMbKnowledge()
        bridge, service, identity_repo, coordinator = self._start_blocked_worker(
            knowledge
        )
        bridge.reset_identity()
        process_events(6)
        assert bridge.property("state") == "IDLE"
        knowledge.release_fetch.set()
        coordinator.shutdown()
        assert self._settle(bridge) == "IDLE"
        assert identity_repo.load_artist_identity(ARTIST_A_KEY) is None


# ----------------------------------------------------------------------
# P1 residual — KnowledgeCard factual-presence semantics
# ----------------------------------------------------------------------


class TestKnowledgeCardPresenceSemantics:
    def test_fs19_factual_presence_boolean_and_no_undefined(self, qapp):
        """country='Chile' + beginYear + genres -> hasFactualFields() is
        TRUE (no string concatenation trap); absent fields never render
        'undefined' (fact() treats undefined/null/"" as absent)."""
        from pathlib import Path

        from enrichment_presentation_fakes import ensure_app
        from PySide6.QtCore import QUrl
        from PySide6.QtQml import QQmlComponent, QQmlEngine, QQmlExpression

        qml_dir = (
            Path(__file__).resolve().parent.parent
            / "src"
            / "michi"
            / "presentation"
            / "qml"
        )
        ensure_app()
        engine = QQmlEngine()
        engine.addImportPath(str(qml_dir))
        component = QQmlComponent(engine)
        component.setData(
            b"""
            import QtQuick
            import "../enrichment"
            EnrichmentKnowledgeCard {
                objectName: "card"
                hasKnowledge: true
                knowledge: {
                    "country": "Chile",
                    "beginYear": 1990,
                    "genres": ["Rock"],
                }
            }
            """,
            QUrl.fromLocalFile(str(qml_dir / "enrichment/__presence_test.qml")),
        )
        assert component.status() == QQmlComponent.Ready, component.errorString()
        root = component.create()
        assert root is not None
        qapp.processEvents()

        from PySide6.QtCore import QObject

        facts = root.findChild(QObject, "factsFlow")
        assert facts is not None

        # hasFactualFields() on the Flow itself: boolean TRUE with
        # country + beginYear + genres (no concatenation trap).
        expr = QQmlExpression(engine.rootContext(), facts, "hasFactualFields()")
        value, undefined = expr.evaluate()
        assert undefined is False and value is True

        # fact() with a real value renders the pair; the QJSValue
        # carries label + value (QML ids are not resolvable from an
        # external QQmlExpression scope, so values are passed literally —
        # the in-QML Repeater binding passes root.knowledge.* directly).
        expr2 = QQmlExpression(engine.rootContext(), facts, "fact('Country', 'Chile')")
        val, undef2 = expr2.evaluate()
        assert undef2 is False
        assert val.property("label").toString() == "Country"
        assert val.property("value").toString() == "Chile"

        # absent fields: undefined/null/"" are ALL null facts — never
        # rendered as "undefined".
        for absent in ("undefined", "null", "''"):
            expr = QQmlExpression(engine.rootContext(), facts, f"fact('X', {absent})")
            value, undefined = expr.evaluate()
            assert undefined is False and value is None, absent
        engine.deleteLater()
