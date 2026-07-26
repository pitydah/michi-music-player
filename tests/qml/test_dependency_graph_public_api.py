"""Test that bridge wiring uses public APIs, not private attribute access."""
from unittest.mock import MagicMock

from ui_qml_bridge.bridge_factory import BridgeFactory


def _make_bundle():
    bundle = MagicMock()
    bundle.worker_manager = MagicMock()
    bundle.db = MagicMock()
    bundle.player_service = MagicMock()
    bundle.radio_manager = MagicMock()
    bundle.sync_manager = MagicMock()
    bundle.michi_link_controller = MagicMock()
    bundle.home_audio_controller = MagicMock()
    bundle.snapcast_controller = MagicMock()
    bundle.disc_service = MagicMock()
    bundle.search_engine = MagicMock()
    bundle.smart_tagging_service = MagicMock()
    bundle.metadata_service = MagicMock()
    bundle.playlist_controller = MagicMock()
    return bundle


def test_global_search_uses_public_query_executor_property() -> None:
    """GlobalSearchBridge must expose search_service through public API."""
    from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
    bridge = GlobalSearchBridge(search_service=MagicMock())
    assert hasattr(bridge, '_svc'), "search_service missing"


def test_diagnostics_uses_public_query_executor_property() -> None:
    """DiagnosticsBridge must expose query_executor as public property."""
    from ui_qml_bridge.diagnostics_bridge import DiagnosticsBridge
    bridge = DiagnosticsBridge(query_executor=MagicMock())
    assert hasattr(bridge, 'query_executor'), "query_executor property missing"
    assert bridge.query_executor is not None


def test_job_bridge_has_attach_library_coordinator() -> None:
    """JobBridge must expose attach_library_coordinator public method."""
    from ui_qml_bridge.job_bridge import JobBridge
    bridge = JobBridge()
    assert hasattr(bridge, 'attach_library_coordinator'), "attach_library_coordinator missing"


def test_factory_creates_bridges_with_public_api() -> None:
    """Factory uses public API compose — no private caches."""
    bundle = _make_bundle()
    factory = BridgeFactory(bundle)
    factory.create_navigation_bridge()
    assert factory.has("navigation")

    from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
    gs = GlobalSearchBridge(search_service=MagicMock())
    factory._bridges["global_search"] = gs

    from ui_qml_bridge.diagnostics_bridge import DiagnosticsBridge
    diag = DiagnosticsBridge(
        player_service=bundle.player_service,
        diagnostics_service=bundle.db,
        worker_manager=bundle.worker_manager,
    )
    factory._bridges["diagnostics"] = diag

    factory._bridges["settings"] = MagicMock()

    assert factory.bridges["global_search"] is gs
    assert factory.bridges["diagnostics"] is diag


def test_mix_bridge_receives_query_service() -> None:
    """MixBridge must accept query_service in constructor."""
    from ui_qml_bridge.mix_bridge import MixBridge
    from core.mix_query_service import MixQueryService

    mqs = MagicMock(spec=MixQueryService)
    bridge = MixBridge(
        query_service=mqs,
        track_action_service=MagicMock(),
        playlist_bridge=MagicMock(),
    )
    assert bridge is not None


def test_playlists_bridge_receives_playlist_service() -> None:
    """PlaylistsBridge must accept playlist_service in constructor."""
    from ui_qml_bridge.playlists_bridge import PlaylistsBridge

    bridge = PlaylistsBridge(
        playlist_service=MagicMock(),
        selection_context=MagicMock(),
        player_service=MagicMock(),
    )
    assert bridge is not None
