"""P5 — R16 Enrichment semantic convergence (V4 §22).

Behavioral seals:
- §22.1 offline policy OFF → zero provider network calls from any
  presentation intent (portrait prefetch, detail activation, refresh,
  review); cached knowledge stays readable;
- §22.2 the Settings policy persists and toggling ON alone never starts
  a provider operation;
- §22.3 with online ON and no cache, opening the detail is cache-only;
  network starts only from the explicit refresh intent;
- §22.4 cancellation stays truthful.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from enrichment_presentation_fakes import (  # noqa: E402
    make_bridge,
    process_events,
)


@pytest.fixture(scope="module")
def qapp():
    from enrichment_presentation_fakes import ensure_app

    app = ensure_app()
    yield app


def _count_calls(service, bridge=None):
    """Llamadas de red: el resolver del servicio es el proxy (calls)."""
    del bridge
    resolver = getattr(service, "_resolver", None)
    return getattr(resolver, "calls", 0) if resolver is not None else 0


def _wait_settled(bridge, rounds=25):
    del bridge
    process_events(rounds)


class TestOfflineZeroProviderCalls:
    def test_policy_off_blocks_every_presentation_intent(self, qapp, tmp_path):
        """§22.1: online OFF → cero llamadas de red ante los intents de
        presentación (prefetch, activación, refresh, review)."""
        bridge, service, _, _, _, _, _ = make_bridge(online=False)
        # El servicio de los detalles: los artistas del modelo.
        # Intents de presentación:
        bridge.prefetch_artist_portrait("artist a")
        bridge.prefetch_artist_portraits(["artist a", "artist b"])
        bridge.activate_artist("artist a")
        bridge.refresh_artist()
        bridge.open_album_cached("album-x")
        bridge.refresh_album()
        bridge.open_review("artist")
        _wait_settled(bridge)
        assert bridge.property("onlineEnabled") is False
        assert _count_calls(service) == 0, (
            "offline: cero llamadas de red desde la presentación"
        )

    def test_toggle_on_alone_starts_no_operation(self, qapp, tmp_path):
        """§22.2: toggling ON por sí solo no arranca ninguna operación."""
        bridge, service, _, _, _, _, _ = make_bridge(online=False)
        bridge.on_online_enrichment_changed(True)
        assert bridge.property("onlineEnabled") is True
        _wait_settled(bridge)
        assert _count_calls(service) == 0, (
            "el policy ON no dispara trabajo por sí mismo"
        )

    def test_detail_activation_with_online_on_is_cache_only(self, qapp, tmp_path):
        """§22.3: con online ON y sin caché, abrir el detail NO dispara
        red; el refresh explícito es el único inicio de red."""
        bridge, service, _, _, _, _, _ = make_bridge(online=True)
        _wait_settled(bridge)
        calls_before = _count_calls(service)
        # Abrir el detail (activación) NO inicia red.
        bridge.open_artist_cached("artist a")
        _wait_settled(bridge)
        assert _count_calls(service) == calls_before, (
            "abrir el detail del artista es cache-only (cero red)"
        )
        # El refresh explícito (Fetch) es la única puerta de red.
        bridge.refresh_artist()
        _wait_settled(bridge, 60)
        assert _count_calls(service) > calls_before, (
            "el Fetch explícito es la única puerta de red "
            f"(calls={_count_calls(service)})"
        )

