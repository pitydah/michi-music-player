"""M6.9-BACKEND-R1.2 — operation events + executor lifecycle + transport
limits + tag compatibility seals.

- every event carries operation_id + generation; old generations are
  distinguishable; policy notices (DISABLED) carry generation 0
- executor admission: submit after shutdown -> False, no RuntimeError;
  enrich_artist/enrich_album rejected deterministically after shutdown
- oversized responses: EnrichmentResponseLimitError, non-transient,
  ONE attempt, no stale fallback; responses always closed
- MUSICBRAINZ_TRACKID -> recording; ASF attribute values strict
"""

import threading
from pathlib import Path

import pytest

from michi.application.enrichment_coordinator import (
    EnrichmentCoordinator,
    EnrichmentOperationEvent,
    EnrichmentOperationState,
)
from michi.application.enrichment_executor import ThreadPoolEnrichmentExecutor
from michi.application.enrichment_ports import (
    EnrichmentResponseLimitError,
    HttpRequest,
    is_transient_provider_failure,
)
from michi.infrastructure.enrichment_http import (
    MAX_PROVIDER_BODY_BYTES,
    ProviderRequestExecutor,
    UrllibHttpTransport,
)


class TestOperationEvents:
    def test_events_carry_generation(self):
        from tests.test_m6_9_backend_r1_2_request_correlation import Harness

        harness = Harness()
        model = __import__(
            "michi.domain.library", fromlist=["build_music_model"]
        ).build_music_model(
            __import__(
                "tests.test_m6_9_backend_r1_2_request_correlation",
                fromlist=["_tracks"],
            )._tracks()
        )
        events: list[EnrichmentOperationEvent] = []
        done = threading.Event()

        def on_state(ev):
            events.append(ev)
            if ev.state in (
                EnrichmentOperationState.READY,
                EnrichmentOperationState.PARTIAL,
                EnrichmentOperationState.FAILED,
                EnrichmentOperationState.CANCELLED,
            ):
                done.set()

        harness.coordinator.enrich_artist(
            model.artists[0],
            model.albums,
            model.artists and model.albums or [],
            on_state,
        )
        assert done.wait(timeout=10)
        assert all(ev.generation == 1 for ev in events)
        assert all(ev.operation_id for ev in events)
        assert all(ev.entity_kind.name == "ARTIST" for ev in events)
        harness.coordinator._executor.shutdown(wait=True)

    def test_two_generations_distinguishable(self):
        from michi.domain.library import build_music_model
        from tests.test_m6_9_backend_r1_2_request_correlation import (
            Harness,
            _tracks,
        )

        harness = Harness(hintless=True)
        model = build_music_model(_tracks())
        gen1: list[int] = []
        gen2: list[int] = []
        done2 = threading.Event()

        def on1(ev):
            gen1.append(ev.generation)

        def on2(ev):
            gen2.append(ev.generation)
            if ev.state in (
                EnrichmentOperationState.READY,
                EnrichmentOperationState.PARTIAL,
                EnrichmentOperationState.FAILED,
                EnrichmentOperationState.CANCELLED,
            ):
                done2.set()

        harness.coordinator.enrich_artist(
            model.artists[0], model.albums, _tracks(), on1
        )
        assert harness.resolver.entered.wait(timeout=5)
        harness.coordinator.enrich_artist(
            model.artists[0], model.albums, _tracks(), on2
        )
        harness.resolver.release.set()
        assert done2.wait(timeout=10)
        harness.coordinator._executor.shutdown(wait=True)
        # A's late terminal state carries generation 1; B's events carry
        # generation 2 — stale states are distinguishable.
        assert set(gen1) == {1}
        assert set(gen2) == {2}

    def test_disabled_policy_event_generation_zero(self):
        from enrichment_fakes import (
            InMemoryIdentityRepository,
            RecordingKnowledgeRepository,
        )

        from michi.application.enrichment_evidence import (
            LibraryEnrichmentEvidenceBuilder,
        )
        from michi.application.enrichment_ports import (
            ExternalIdentityResolverPort,
        )
        from michi.application.enrichment_service import EnrichmentService
        from michi.domain.library import TrackRef, build_music_model

        service = EnrichmentService(
            resolver=None,
            artist_provider=None,
            album_provider=None,
            repository=RecordingKnowledgeRepository(),
            identity_repository=InMemoryIdentityRepository(),
        )

        class R(ExternalIdentityResolverPort):
            def find_artist_candidates(self, e):
                return ()

            def find_release_group_candidates(self, e):
                return ()

            def find_release_edition_candidates(self, e):
                return ()

        class Hints:
            def extract_hints(self, p):
                from michi.domain.enrichment import ExternalIdentityHints

                return ExternalIdentityHints()

        coordinator = EnrichmentCoordinator(
            service=service,
            resolver=R(),
            evidence_builder=LibraryEnrichmentEvidenceBuilder(Hints()),
            mb_knowledge=None,
            wikidata=None,
            wikipedia=None,
            commons=None,
            coverart=None,
            asset_store=None,
            executor=ThreadPoolEnrichmentExecutor(max_workers=1),
            transport=None,
            enabled=lambda: False,
        )
        events: list[EnrichmentOperationEvent] = []
        tracks = (
            TrackRef(
                file_path=Path("/a.flac"),
                title="T1",
                artist="Artist A",
                album="Album X",
                year=1980,
                album_artist="Artist A",
            ),
        )
        model = build_music_model(tracks)
        coordinator.enrich_artist(
            model.artists[0],
            model.albums,
            tracks,
            lambda ev: events.append(ev),
        )
        assert len(events) == 1
        assert events[0].state is EnrichmentOperationState.DISABLED
        assert events[0].generation == 0
        coordinator._executor.shutdown(wait=True)


class TestExecutorLifecycle:
    def test_submit_after_shutdown_false_no_runtime_error(self):
        executor = ThreadPoolEnrichmentExecutor(max_workers=1)
        executor.shutdown()
        assert executor.submit(lambda: None) is False

    def test_enrich_after_shutdown_rejected(self):
        from tests.test_m6_9_backend_r1_2_request_correlation import Harness

        harness = Harness()
        harness.coordinator.shutdown()
        model = __import__(
            "michi.domain.library", fromlist=["build_music_model"]
        ).build_music_model(
            __import__(
                "tests.test_m6_9_backend_r1_2_request_correlation",
                fromlist=["_tracks"],
            )._tracks()
        )
        events: list[EnrichmentOperationEvent] = []
        harness.coordinator.enrich_artist(
            model.artists[0],
            model.albums,
            model.artists and model.albums or [],
            lambda ev: events.append(ev),
        )
        assert events
        assert events[0].state is EnrichmentOperationState.CANCELLED
        assert harness.repository.write_count == 0


class TestTransportLimits:
    class BigResponse:
        def __init__(self):
            self.status = 200
            self.headers = {}
            self.closed = False
            self._sent = False

        def read(self, size=-1):
            if not self._sent:
                self._sent = True
                return b"x" * (MAX_PROVIDER_BODY_BYTES + 1)
            return b""

        def getcode(self):
            return 200

        def geturl(self):
            return "https://musicbrainz.org/x"

        def close(self):
            self.closed = True

    class Opener:
        def __init__(self):
            self.calls = 0

        def open(self, req, timeout=None):
            self.calls += 1
            return TestTransportLimits.BigResponse()

    def test_oversized_non_transient_one_attempt(self):
        opener = self.Opener()
        transport = UrllibHttpTransport(opener=opener)
        executor = ProviderRequestExecutor(transport, sleeper=lambda s: None)
        with pytest.raises(EnrichmentResponseLimitError):
            executor.get(HttpRequest(url="https://musicbrainz.org/x"))
        assert opener.calls == 1  # never retried

    def test_oversized_not_transient_classifier(self):
        assert is_transient_provider_failure(EnrichmentResponseLimitError("x")) is False

    def test_response_closed_on_oversized(self):
        response = self.BigResponse()
        transport = UrllibHttpTransport(
            opener=type("O", (), {"open": lambda self, req, timeout=None: response})()
        )
        with pytest.raises(EnrichmentResponseLimitError):
            transport.get(HttpRequest(url="https://musicbrainz.org/x"))
        assert response.closed is True


class TestTagCompatibility:
    def test_vorbis_trackid_recording_isolated(self):
        from mutagen.oggvorbis import VCommentDict

        from michi.infrastructure.enrichment_identity_hints import (
            MutagenIdentityHintExtractor,
        )

        tags = VCommentDict()
        tags["MUSICBRAINZ_TRACKID"] = ["recording-x"]
        hints = MutagenIdentityHintExtractor().extract_hints_from_tags(tags)
        assert hints.musicbrainz_recording_ids == ("recording-x",)
        assert hints.musicbrainz_release_track_ids == ()

    def test_vorbis_trackid_vs_releasetrackid_separate(self):
        from mutagen.oggvorbis import VCommentDict

        from michi.infrastructure.enrichment_identity_hints import (
            MutagenIdentityHintExtractor,
        )

        tags = VCommentDict()
        tags["MUSICBRAINZ_TRACKID"] = ["rec"]
        tags["MUSICBRAINZ_RELEASETRACKID"] = ["release-track"]
        hints = MutagenIdentityHintExtractor().extract_hints_from_tags(tags)
        assert hints.musicbrainz_recording_ids == ("rec",)
        assert hints.musicbrainz_release_track_ids == ("release-track",)

    def test_asf_attribute_values_extracted(self):
        from mutagen.asf import ASFUnicodeAttribute

        from michi.infrastructure.enrichment_identity_hints import (
            MutagenIdentityHintExtractor,
        )

        class FakeAsfTags:
            def items(self):
                return {
                    "MusicBrainz/Artist Id": [ASFUnicodeAttribute("mb-artist")],
                    "MusicBrainz/Album Artist Id": [ASFUnicodeAttribute("mb-aa")],
                    "MusicBrainz/Album Id": [ASFUnicodeAttribute("mb-release")],
                    "MusicBrainz/Release Group Id": [ASFUnicodeAttribute("rg-1")],
                    "MusicBrainz/Track Id": [ASFUnicodeAttribute("mb-track")],
                    "MusicBrainz/Release Track Id": [ASFUnicodeAttribute("mb-rt")],
                }.items()

        hints = MutagenIdentityHintExtractor().extract_hints_from_tags(FakeAsfTags())
        assert hints.musicbrainz_artist_ids == ("mb-artist",)
        assert hints.musicbrainz_album_artist_ids == ("mb-aa",)
        assert hints.musicbrainz_release_ids == ("mb-release",)
        assert hints.musicbrainz_release_group_ids == ("rg-1",)
        assert hints.musicbrainz_recording_ids == ("mb-track",)
        assert hints.musicbrainz_release_track_ids == ("mb-rt",)

    def test_no_generic_coercion(self):
        from michi.infrastructure.enrichment_identity_hints import (
            _extract_text_value,
        )

        class Opaque:
            pass

        assert _extract_text_value(Opaque()) == []
        assert _extract_text_value(12345) == []
        assert _extract_text_value({"x": 1}) == []
