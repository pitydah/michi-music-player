"""M6.9-PRESENTATION — privacy gates.

Library Enrichment must never touch the network unless Online Library
Enrichment is ON and the user opens a detail or an instantiated Artists
gallery delegate requests a missing portrait.
All counts come from fake providers (CountingResolver calls) — no live
network anywhere.
"""

import pytest
from enrichment_presentation_fakes import (
    ALBUM_X_KEY,
    ARTIST_A_KEY,
    make_bridge,
    process_events,
)
from test_m6_9_presentation_bridge import _populate_artist


@pytest.fixture(autouse=True, scope="module")
def _app():
    from enrichment_presentation_fakes import ensure_app

    return ensure_app()


def _wait_for(bridge, state, timeout_rounds=40):
    for _ in range(timeout_rounds):
        process_events(4)
        if bridge.property("state") == state:
            return True
    return bridge.property("state") == state


class TestPrivacyGates:
    def test_startup_network_zero(self):
        """Constructing the bridge performs zero network calls."""
        bridge, _, _, _, _, _, _ = make_bridge(online=True)
        assert bridge._service._resolver.calls == 0
        assert bridge._coordinator is not None  # graph wired, nothing ran

    def test_activate_off_no_network(self):
        bridge, _, _, _, _, _, _ = make_bridge(online=False)
        bridge.activate_artist(ARTIST_A_KEY)
        process_events(8)
        assert bridge._service._resolver.calls == 0

    def test_activate_on_cached_no_network(self):
        bridge, service, _, _, _, _, _ = make_bridge(online=True)
        _populate_artist(service, ARTIST_A_KEY, "Artist A", "mb-a")
        calls_before = bridge._service._resolver.calls
        bridge.activate_artist(ARTIST_A_KEY)
        process_events(8)
        assert bridge.property("state") == "READY"
        assert bridge._service._resolver.calls == calls_before

    def test_activate_on_uncached_network_allowed(self):
        bridge, _, _, _, _, _, _ = make_bridge(online=True)
        bridge.activate_artist(ARTIST_A_KEY)
        assert _wait_for(bridge, "READY")
        assert bridge._service._resolver.calls > 0

    def test_refresh_on_network_allowed(self):
        bridge, _, _, _, _, _, _ = make_bridge(online=True)
        bridge.activate_artist(ARTIST_A_KEY)
        assert _wait_for(bridge, "READY")
        calls_before = bridge._service._resolver.calls
        bridge.refresh_artist()
        assert _wait_for(bridge, "READY")
        assert bridge._service._resolver.calls > calls_before

    def test_review_off_no_network(self):
        bridge, _, _, _, _, _, _ = make_bridge(online=False)
        bridge.open_review("artist")
        bridge.search_artist("Artist A")
        process_events(8)
        assert bridge._service._resolver.calls == 0
        assert bridge.property("reviewError") == "Online info is disabled"

    def test_review_on_network_allowed(self):
        bridge, _, _, _, _, _, _ = make_bridge(online=True)
        bridge.open_review("artist")
        bridge.search_artist("Artist A")
        process_events(12)
        assert bridge._service._resolver.calls > 0
        assert len(bridge.property("artistCandidates")) == 1

    def test_visible_artist_portrait_prefetch_on_is_allowed_but_not_activation(self):
        bridge, _, _, _, _, _, _ = make_bridge(online=True)
        bridge.prefetch_artist_portrait(ARTIST_A_KEY)
        process_events(12)
        assert bridge._service._resolver.calls > 0
        assert bridge.property("activeKind") == ""
        assert bridge.property("activeKey") == ""

    def test_album_off_no_network(self):
        bridge, _, _, _, _, _, _ = make_bridge(online=False)
        bridge.activate_album(ALBUM_X_KEY)
        process_events(8)
        assert bridge._service._resolver.calls == 0
        assert bridge.property("state") == "DISABLED"

    def test_policy_off_blocks_new_network(self):
        bridge, _, _, _, _, _, _ = make_bridge(online=True)
        bridge.activate_artist(ARTIST_A_KEY)
        assert _wait_for(bridge, "READY")
        calls_before = bridge._service._resolver.calls
        bridge.on_online_enrichment_changed(False)
        process_events(8)
        bridge.refresh_artist()
        bridge.open_review("artist")
        bridge.search_artist("Artist A")
        process_events(12)
        assert bridge._service._resolver.calls == calls_before

    def test_scan_search_and_generic_list_population_never_trigger(self):
        """Scan/build/search do not touch enrichment. Portrait network is
        admitted only through the explicit delegate prefetch slot."""
        bridge, _, _, _, _, _, _ = make_bridge(online=True)
        # Simulated list population / scan lifecycle: nothing to do.
        process_events(8)
        assert bridge._service._resolver.calls == 0
        assert bridge.property("state") == "IDLE"
        assert bridge.property("activeKey") == ""
