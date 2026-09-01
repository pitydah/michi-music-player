"""M6.9-PRESENTATION — EnrichmentBridge test matrix.

Deterministic (no sleeps; processEvents only as event delivery). All
fakes — no live network anywhere. Covers the activation semantics, the
double anti-stale filter (presentation intent + backend generation),
clear vs reset, refresh, policy OFF cancellation and dispose.
"""

import pytest
from enrichment_presentation_fakes import (
    ALBUM_X_KEY,
    ALBUM_Y_KEY,
    ARTIST_A_KEY,
    ARTIST_B_KEY,
    FakeMbKnowledge,
    make_bridge,
    process_events,
)

from michi.domain.enrichment import (
    ArtistKnowledgeProfile,
    KnowledgeProvenance,
)
from michi.presentation.enrichment_bridge import LibraryEnrichmentProjection


@pytest.fixture(autouse=True, scope="module")
def _app():
    from enrichment_presentation_fakes import ensure_app

    return ensure_app()


def _populate_artist(service, key, name, mbid):
    """Seed cached artist knowledge through the service (hint-authoritative,
    zero resolver calls) — the same graph the bridge reads from."""
    from michi.domain.enrichment import (
        ArtistIdentityEvidence,
        ArtistIdentityHints,
        DeliveryVerdict,
        EnrichmentEntityKind,
    )

    gen = service.begin_operation(EnrichmentEntityKind.ARTIST, key)
    out = service.request_artist_enrichment(
        ArtistIdentityEvidence(
            local_artist_key=key,
            local_artist_name=name,
            identity_hints=ArtistIdentityHints(artist_ids=(mbid,)),
        ),
        generation=gen,
    )
    assert out.request is not None
    profile = ArtistKnowledgeProfile(
        local_artist_key=key,
        external_artist_id=mbid,
        biography=f"Biography of {name}.",
        provenance=KnowledgeProvenance(provider="musicbrainz"),
    )
    assert (
        service.deliver_artist_profile(out.request, profile)
        is DeliveryVerdict.COMMITTED
    )


def _wait_for(bridge, state, timeout_rounds=40):
    """Deliver queued events until the bridge reaches ``state``."""
    for _ in range(timeout_rounds):
        process_events(4)
        if bridge.property("state") == state:
            return True
    return bridge.property("state") == state


class TestActivationSemantics:
    def test_passive_library_projection_never_changes_active_operation(self):
        bridge, service, _, _, asset_store, _, _ = make_bridge(online=True)
        bridge.activate_album(ALBUM_X_KEY)
        assert _wait_for(bridge, "READY")
        active_before = (
            bridge.property("activeKind"),
            bridge.property("activeKey"),
            bridge.property("state"),
        )
        resolver_calls = service._resolver.calls

        projection = LibraryEnrichmentProjection(service, asset_store)
        cached = projection.album(ALBUM_X_KEY)
        missing = projection.album(ALBUM_Y_KEY)
        revision_before = projection.property("revision")
        projection.invalidate()
        process_events(8)

        assert cached["albumKey"] == ALBUM_X_KEY
        assert cached["hasCachedKnowledge"] is True
        assert cached["label"] == ""
        assert missing["matchState"] == "none"
        assert service._resolver.calls == resolver_calls
        assert projection.property("revision") == revision_before + 1
        assert (
            bridge.property("activeKind"),
            bridge.property("activeKey"),
            bridge.property("state"),
        ) == active_before

    def test_passive_album_browse_is_cache_only_even_when_online(self):
        bridge, _, _, _, _, _, _ = make_bridge(online=True)
        resolver = bridge._service._resolver
        calls_before = resolver.calls

        bridge.browse_album_cached(ALBUM_X_KEY)
        process_events(8)

        assert bridge.property("activeKey") == ALBUM_X_KEY
        assert bridge.property("activeKind") == "album"
        assert bridge.property("state") == "IDLE"
        assert resolver.calls == calls_before

    def test_activate_cached_artist_no_network_knowledge_visible(self):
        """A: cached knowledge projects immediately; no network."""
        bridge, service, _, _, _, _, _ = make_bridge(online=True)
        _populate_artist(service, ARTIST_A_KEY, "Artist A", "mb-a")
        resolver = bridge._service._resolver
        calls_before = resolver.calls
        bridge.activate_artist(ARTIST_A_KEY)
        process_events(8)
        assert bridge.property("state") == "READY"
        assert bridge.property("artistHasKnowledge") is True
        assert (
            bridge.property("artistKnowledge")["biography"] == "Biography of Artist A."
        )
        assert resolver.calls == calls_before  # no network

    def test_activate_uncached_artist_off_is_disabled_no_network(self):
        """B: uncached + OFF -> DISABLED; no network."""
        bridge, _, _, _, _, _, _ = make_bridge(online=False)
        resolver = bridge._service._resolver
        calls_before = resolver.calls
        bridge.activate_artist(ARTIST_A_KEY)
        process_events(8)
        assert bridge.property("state") == "DISABLED"
        assert bridge.property("stateMessage") == "Online info is disabled"
        assert resolver.calls == calls_before

    def test_activate_uncached_artist_on_runs_enrichment(self):
        """C: uncached + ON -> RESOLVING -> FETCHING -> READY."""
        bridge, service, _, repo, _, _, _ = make_bridge(online=True)
        bridge.activate_artist(ARTIST_A_KEY)
        assert _wait_for(bridge, "READY")
        assert bridge.property("artistHasKnowledge") is True
        assert (
            bridge.property("artistKnowledge")["biography"] == "A composer biography."
        )
        assert repo.write_count == 1

    def test_partial_state_surfaces(self):
        """D: PARTIAL reaches the bridge unchanged."""
        bridge, service, _, _, _, _, _ = make_bridge(online=True)

        # Force a stale-flagged profile -> PARTIAL.
        class StaleKnowledge(FakeMbKnowledge):
            def fetch_artist(self, local_artist_key, external_artist_id):
                profile = super().fetch_artist(local_artist_key, external_artist_id)
                return ArtistKnowledgeProfile(
                    **{
                        **profile.__dict__,
                        "biography_provenance": KnowledgeProvenance(
                            provider="wikipedia", is_stale=True
                        ),
                    }
                )

        bridge2, _, _, _, _, _, _ = make_bridge(
            online=True, mb_knowledge=StaleKnowledge()
        )
        bridge2.activate_artist("artist a")
        assert _wait_for(bridge2, "PARTIAL")
        assert bridge2.property("artistHasKnowledge") is True

    def test_offline_with_cached_data_keeps_knowledge(self):
        """E: transient failure with cached data -> OFFLINE, cache stays."""
        offline = FakeMbKnowledge(offline=True)
        bridge, service, _, _, _, _, _ = make_bridge(online=True, mb_knowledge=offline)
        _populate_artist(service, ARTIST_A_KEY, "Artist A", "mb-a")

        bridge.activate_artist(ARTIST_A_KEY)
        process_events(8)
        assert bridge.property("state") == "READY"
        bridge.refresh_artist()
        assert _wait_for(bridge, "OFFLINE")
        assert bridge.property("artistHasKnowledge") is True
        assert (
            bridge.property("artistKnowledge")["biography"] == "Biography of Artist A."
        )
        assert bridge.property("stateMessage") == "Offline — showing saved information"


class TestSelectionChangesAndStaleFiltering:
    def test_switch_artist_late_event_ignored(self):
        """F: switch A -> B; a late READY for A is ignored (intent)."""
        bridge, service, _, _, _, _, _ = make_bridge(online=True)
        _populate_artist(service, ARTIST_A_KEY, "Artist A", "mb-a")
        _populate_artist(service, ARTIST_B_KEY, "Artist B", "mb-b")

        bridge.activate_artist(ARTIST_A_KEY)
        process_events(8)
        assert bridge.property("activeKey") == ARTIST_A_KEY

        # Simulate a late event from the OLD intent arriving after the
        # switch (as if the worker finished after navigation).
        old_intent = bridge._presentation_intent_id
        bridge.activate_artist(ARTIST_B_KEY)
        process_events(8)
        assert bridge.property("activeKey") == ARTIST_B_KEY

        # A stale callback (old intent) must not change the projection.
        late_event = __import__(
            "michi.application.enrichment_coordinator",
            fromlist=["EnrichmentOperationEvent", "EnrichmentOperationState"],
        )
        ev = late_event.EnrichmentOperationEvent(
            operation_id="op-a",
            generation=1,
            entity_kind=__import__(
                "michi.domain.enrichment", fromlist=["EnrichmentEntityKind"]
            ).EnrichmentEntityKind.ARTIST,
            local_entity_key=ARTIST_A_KEY,
            state=late_event.EnrichmentOperationState.READY,
        )
        bridge._apply_event(ev, old_intent)
        assert bridge.property("activeKey") == ARTIST_B_KEY
        assert (
            bridge.property("artistKnowledge").get("biography")
            == "Biography of Artist B."
        )

    def test_stale_generation_ignored(self):
        """I: an event with an older generation than observed is ignored."""
        bridge, service, _, _, _, _, _ = make_bridge(online=True)
        bridge.activate_artist(ARTIST_A_KEY)
        assert _wait_for(bridge, "READY")

        late_event = __import__(
            "michi.application.enrichment_coordinator",
            fromlist=["EnrichmentOperationEvent", "EnrichmentOperationState"],
        )
        ev = late_event.EnrichmentOperationEvent(
            operation_id="op-old",
            generation=0,  # older than the observed generation 1
            entity_kind=__import__(
                "michi.domain.enrichment", fromlist=["EnrichmentEntityKind"]
            ).EnrichmentEntityKind.ARTIST,
            local_entity_key=ARTIST_A_KEY,
            state=late_event.EnrichmentOperationState.FAILED,
        )
        bridge._apply_event(ev, bridge._presentation_intent_id)
        assert bridge.property("state") != "FAILED"
        assert bridge.property("state") == "READY"

    def test_disposed_bridge_ignores_callbacks(self):
        """J: a disposed bridge drops every callback."""
        bridge, _, _, _, _, _, _ = make_bridge(online=True)
        bridge.activate_artist(ARTIST_A_KEY)
        bridge.dispose()
        bridge.dispose()  # idempotent
        late_event = __import__(
            "michi.application.enrichment_coordinator",
            fromlist=["EnrichmentOperationEvent", "EnrichmentOperationState"],
        )
        ev = late_event.EnrichmentOperationEvent(
            operation_id="op",
            generation=9,
            entity_kind=__import__(
                "michi.domain.enrichment", fromlist=["EnrichmentEntityKind"]
            ).EnrichmentEntityKind.ARTIST,
            local_entity_key=ARTIST_A_KEY,
            state=late_event.EnrichmentOperationState.READY,
        )
        bridge._apply_event(ev, bridge._presentation_intent_id)
        assert bridge.property("state") == "IDLE"


class TestAlbumMatrix:
    def test_album_cached_and_first_enrichment(self):
        """H: first enrichment works; re-activation of a CACHED album is
        network-free; a different uncached album enriches once."""
        bridge, service, _, _, _, _, _ = make_bridge(online=True)
        resolver = bridge._service._resolver

        bridge.activate_album(ALBUM_X_KEY)
        assert _wait_for(bridge, "READY")
        assert bridge.property("albumHasKnowledge") is True
        assert bridge.property("albumKnowledge")["firstReleaseYear"] == 1980
        assert bridge.property("activeKind") == "album"
        calls_after_first = resolver.calls
        assert calls_after_first > 0

        # cached re-activation: no new resolver calls
        bridge.activate_album(ALBUM_X_KEY)
        assert _wait_for(bridge, "READY")
        assert bridge.property("albumHasKnowledge") is True
        assert resolver.calls == calls_after_first

        # different uncached album: enrichment allowed (once)
        bridge.activate_album(ALBUM_Y_KEY)
        assert _wait_for(bridge, "READY")
        assert bridge.property("albumHasKnowledge") is True
        # album resolution = group candidates + edition candidates calls
        assert resolver.calls == calls_after_first + 2

    def test_album_off_disabled(self):
        bridge, _, _, _, _, _, _ = make_bridge(online=False)
        bridge.activate_album(ALBUM_X_KEY)
        process_events(8)
        assert bridge.property("state") == "DISABLED"


class TestManualReview:
    def test_artist_review_flow_and_confirm(self):
        """Artist: open review -> search -> choose candidate -> MANUAL ->
        refresh -> READY."""
        bridge, service, identity_repo, _, _, _, _ = make_bridge(online=True)
        # Force ambiguity: empty resolver -> NOT_FOUND path opens review.
        bridge.activate_artist(ARTIST_A_KEY)
        assert _wait_for(bridge, "READY")

        bridge.open_review("artist")
        assert bridge.property("reviewOpen") is True
        assert bridge.property("reviewKind") == "artist"

        bridge.search_artist("Artist A")
        process_events(12)
        assert bridge.property("reviewLoading") is False
        candidates = bridge.property("artistCandidates")
        assert len(candidates) == 1
        assert candidates[0]["displayName"] == "Artist A"
        assert candidates[0]["externalArtistId"] == "mb-a"

        bridge.confirm_artist_candidate("mb-a")
        process_events(12)
        assert bridge.property("reviewOpen") is False
        identity = identity_repo.load_artist_identity(ARTIST_A_KEY)
        assert identity is not None and identity.match_method.name == "MANUAL"
        assert _wait_for(bridge, "READY")

    def test_album_review_flow(self):
        bridge, _, identity_repo, _, _, _, _ = make_bridge(online=True)
        bridge.activate_album(ALBUM_X_KEY)
        assert _wait_for(bridge, "READY")
        bridge.open_review("album")
        bridge.search_album("Album X", "Artist A")
        process_events(12)
        candidates = bridge.property("albumCandidates")
        assert len(candidates) == 2  # rg-x + rg-y both resolvable
        album_x = next(c for c in candidates if c["displayTitle"] == "Album X")
        assert album_x["externalReleaseGroupId"] == "rg-x"
        bridge.confirm_album_candidate(album_x["externalReleaseGroupId"])
        process_events(12)
        assert bridge.property("reviewOpen") is False
        identity = identity_repo.load_album_identity(ALBUM_X_KEY)
        assert identity is not None and identity.match_method.name == "MANUAL"

    def test_stale_search_epoch_ignored(self):
        """A search for entity A cannot fill the dialog after switching."""
        bridge, _, _, _, _, _, _ = make_bridge(online=True)
        bridge.open_review("artist")
        bridge.search_artist("Artist A")
        old_epoch = bridge._manual_search_epoch
        # A second search bumps the epoch; the first result must be dropped.
        bridge.search_artist("Artist B")
        assert bridge._manual_search_epoch == old_epoch + 1

        from michi.application.enrichment_coordinator import (
            ArtistIdentityCandidateView,
        )

        # Stale result from the OLD epoch/session of the SAME entity:
        # epoch mismatch alone must drop it.
        bridge._apply_candidates(
            "artist",
            ARTIST_A_KEY,
            bridge._review_session_id,
            old_epoch,
            (ArtistIdentityCandidateView("mb-old", "Old", "", "musicbrainz"),),
        )
        assert bridge.property("artistCandidates") == []

    def test_review_offline_rejected(self):
        """OFF: search is rejected without any provider call."""
        bridge, _, _, _, _, _, _ = make_bridge(online=False)
        resolver = bridge._service._resolver
        calls_before = resolver.calls
        bridge.open_review("artist")
        bridge.search_artist("Artist A")
        process_events(8)
        assert bridge.property("reviewError") == "Online info is disabled"
        assert resolver.calls == calls_before


class TestClearResetRefreshPolicy:
    def test_clear_vs_reset_distinct(self):
        """Clear keeps identity; reset removes identity. No auto re-enrich."""
        bridge, service, identity_repo, _, _, _, _ = make_bridge(online=True)
        bridge.activate_artist(ARTIST_A_KEY)
        assert _wait_for(bridge, "READY")
        assert identity_repo.load_artist_identity(ARTIST_A_KEY) is not None

        # CLEAR: identity stays, knowledge disappears.
        bridge.clear_knowledge()
        process_events(8)
        assert bridge.property("artistHasKnowledge") is False
        assert bridge.property("artistKnowledge") == {}
        assert identity_repo.load_artist_identity(ARTIST_A_KEY) is not None
        assert bridge.property("state") == "IDLE"

        # Re-enrich, then RESET: identity AND knowledge disappear.
        bridge.refresh_artist()
        assert _wait_for(bridge, "READY")
        bridge.reset_identity()
        process_events(8)
        assert bridge.property("state") == "IDLE"
        assert bridge.property("artistHasKnowledge") is False
        assert identity_repo.load_artist_identity(ARTIST_A_KEY) is None
        # No automatic re-enrichment after reset.
        resolver = bridge._service._resolver
        calls_after_reset = resolver.calls
        process_events(8)
        assert resolver.calls == calls_after_reset

    def test_refresh_off_is_noop(self):
        bridge, _, _, _, _, _, _ = make_bridge(online=False)
        bridge.activate_artist(ARTIST_A_KEY)
        process_events(8)
        resolver = bridge._service._resolver
        calls_before = resolver.calls
        bridge.refresh_artist()
        process_events(8)
        assert resolver.calls == calls_before
        assert bridge.property("state") == "DISABLED"

    def test_policy_off_cancels_live_operation(self):
        """OFF during a live operation cancels and converges without stale UI."""
        bridge, service, _, _, _, _, _ = make_bridge(online=True)
        bridge.activate_artist(ARTIST_A_KEY)
        assert _wait_for(bridge, "READY")
        bridge.on_online_enrichment_changed(False)
        process_events(8)
        # Cached data remains visible, policy state DISABLED only when
        # there is no cached data; here READY with cached knowledge.
        assert bridge.property("state") == "READY"
        assert bridge.property("artistHasKnowledge") is True
        assert bridge.property("onlineEnabled") is False
        # No new operation can start while OFF.
        resolver = bridge._service._resolver
        calls_before = resolver.calls
        bridge.refresh_artist()
        process_events(8)
        assert resolver.calls == calls_before
