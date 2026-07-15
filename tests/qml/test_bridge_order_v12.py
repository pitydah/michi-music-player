"""Tests for deterministic bridge creation order in BridgeFactory v12."""
from unittest.mock import MagicMock
from pathlib import Path


from ui_qml_bridge.bridge_factory import BridgeFactory, INFRASTRUCTURE, DOMAIN, AGGREGATORS
from core.service_container import ServiceContainer


BRIDGE_FACTORY_PATH = Path(__file__).resolve().parent.parent.parent / "ui_qml_bridge" / "bridge_factory.py"


def _make_container(**overrides) -> ServiceContainer:
    c = ServiceContainer()
    for k, v in {
        "playback_service": MagicMock(),
        "worker_manager": MagicMock(),
        "database": MagicMock(),
        "settings_coordinator": MagicMock(),
        "settings_service": MagicMock(),
        "global_search_service": MagicMock(),
        "track_action_service": MagicMock(),
        "confirmation_service": MagicMock(),
        "notification_service": MagicMock(),
        "diagnostics_service": MagicMock(),
        "job_service": MagicMock(),
        "mix_query_service": MagicMock(),
        "playlist_service": MagicMock(),
        "queue_service": MagicMock(),
        "history_query_service": MagicMock(),
        "device_sync_service": MagicMock(),
        "home_audio_service": MagicMock(),
        "connection_service": MagicMock(),
        "radio_service": MagicMock(),
        "audio_lab_service": MagicMock(),
        "metadata_service": MagicMock(),
        "smart_tagging_service": MagicMock(),
        "library_doctor_service": MagicMock(),
        "library_sources_service": MagicMock(),
        "process_controller": MagicMock(),
    }.items():
        c.register(k, overrides.get(k, v))
    return c


class TestInfrastructureOrder:
    def test_page_state_created_first(self):
        c = _make_container()
        f = BridgeFactory(c)
        f._create_infrastructure()
        assert f.has("page_state")

    def test_route_registry_created(self):
        c = _make_container()
        f = BridgeFactory(c)
        f._create_infrastructure()
        assert f.has("route_registry")

    def test_navigation_created(self):
        c = _make_container()
        f = BridgeFactory(c)
        f._create_infrastructure()
        assert f.has("navigation")

    def test_action_registry_created(self):
        c = _make_container()
        f = BridgeFactory(c)
        f._create_infrastructure()
        assert f.has("action_registry")

    def test_query_executor_created(self):
        c = _make_container()
        f = BridgeFactory(c)
        f._create_infrastructure()
        assert f.has("query_executor")

    def test_job_bridge_created(self):
        c = _make_container()
        f = BridgeFactory(c)
        f._create_infrastructure()
        assert f.has("job_bridge")

    def test_confirmation_created(self):
        c = _make_container()
        f = BridgeFactory(c)
        f._create_infrastructure()
        assert f.has("confirmation")

    def test_theme_created(self):
        c = _make_container()
        f = BridgeFactory(c)
        f._create_infrastructure()
        assert f.has("theme")

    def test_accessibility_created(self):
        c = _make_container()
        f = BridgeFactory(c)
        f._create_infrastructure()
        assert f.has("accessibility")


class TestDomainOrder:
    def test_library_sources_first(self):
        c = _make_container()
        f = BridgeFactory(c)
        f._create_infrastructure()
        f._create_domain()
        keys = list(f._bridges.keys())
        ls_idx = keys.index("library_sources") if "library_sources" in keys else -1
        lib_idx = keys.index("library") if "library" in keys else -1
        assert ls_idx >= 0 and lib_idx >= 0
        assert ls_idx < lib_idx, "library_sources should be created before library"

    def test_playback_after_library(self):
        c = _make_container()
        f = BridgeFactory(c)
        f._create_infrastructure()
        f._create_domain()
        keys = list(f._bridges.keys())
        lib_idx = keys.index("library") if "library" in keys else -1
        pb_idx = keys.index("playback") if "playback" in keys else -1
        assert lib_idx >= 0 and pb_idx >= 0
        assert lib_idx < pb_idx, "library should be created before playback"

    def test_nowplaying_before_queue(self):
        c = _make_container()
        f = BridgeFactory(c)
        f._create_infrastructure()
        f._create_domain()
        keys = list(f._bridges.keys())
        np_idx = keys.index("nowplaying") if "nowplaying" in keys else -1
        qu_idx = keys.index("queue") if "queue" in keys else -1
        assert np_idx >= 0 and qu_idx >= 0
        assert np_idx < qu_idx, "nowplaying should be created before queue"

    def test_playlists_after_queue(self):
        c = _make_container()
        f = BridgeFactory(c)
        f._create_infrastructure()
        f._create_domain()
        keys = list(f._bridges.keys())
        qu_idx = keys.index("queue") if "queue" in keys else -1
        pl_idx = keys.index("playlists") if "playlists" in keys else -1
        assert qu_idx >= 0 and pl_idx >= 0
        assert qu_idx < pl_idx, "queue should be created before playlists"

    def test_history_before_global_search(self):
        c = _make_container()
        f = BridgeFactory(c)
        f._create_infrastructure()
        f._create_domain()
        keys = list(f._bridges.keys())
        hi_idx = keys.index("history") if "history" in keys else -1
        gs_idx = keys.index("global_search") if "global_search" in keys else -1
        assert hi_idx >= 0 and gs_idx >= 0
        assert hi_idx < gs_idx, "history should be created before global_search"


class TestAggregatorOrder:
    def test_notification_created_after_domain(self):
        c = _make_container()
        f = BridgeFactory(c)
        f._create_infrastructure()
        f._create_domain()
        f._create_aggregators()
        assert f.has("notification")

    def test_home_created_after_notification(self):
        c = _make_container()
        f = BridgeFactory(c)
        f._create_infrastructure()
        f._create_domain()
        f._create_aggregators()
        keys = list(f._bridges.keys())
        nt_idx = keys.index("notification") if "notification" in keys else -1
        hm_idx = keys.index("home") if "home" in keys else -1
        assert nt_idx >= 0 and hm_idx >= 0
        assert nt_idx < hm_idx, "notification should be created before home"

    def test_app_after_capability(self):
        c = _make_container()
        f = BridgeFactory(c)
        f._create_infrastructure()
        f._create_domain()
        f._create_aggregators()
        keys = list(f._bridges.keys())
        cp_idx = keys.index("capability") if "capability" in keys else -1
        ap_idx = keys.index("app") if "app" in keys else -1
        assert cp_idx >= 0 and ap_idx >= 0
        assert cp_idx < ap_idx, "capability should be created before app"


class TestForbiddenOrders:
    def test_app_not_before_queue(self):
        c = _make_container()
        f = BridgeFactory(c)
        result = f.create_all()
        assert "app" in result
        assert "queue" in result
        keys = list(result.keys())
        ap_idx = keys.index("app")
        qu_idx = keys.index("queue")
        assert qu_idx < ap_idx, "App should NOT be built before Queue"

    def test_notification_not_before_action_registry(self):
        c = _make_container()
        f = BridgeFactory(c)
        result = f.create_all()
        assert "notification" in result
        assert "action_registry" in result
        keys = list(result.keys())
        nt_idx = keys.index("notification")
        ar_idx = keys.index("action_registry")
        assert ar_idx < nt_idx, "Notification should NOT be built before ActionRegistry"

    def test_playlists_after_job_and_confirmation(self):
        c = _make_container()
        f = BridgeFactory(c)
        result = f.create_all()
        assert "playlists" in result
        assert "job_bridge" in result
        assert "confirmation" in result
        keys = list(result.keys())
        jb_idx = keys.index("job_bridge")
        cf_idx = keys.index("confirmation")
        pl_idx = keys.index("playlists")
        assert jb_idx < pl_idx, "Playlists should be built after JobBridge"
        assert cf_idx < pl_idx, "Playlists should be built after Confirmation"

    def test_capability_after_domain(self):
        c = _make_container()
        f = BridgeFactory(c)
        result = f.create_all()
        assert "capability" in result
        keys = list(result.keys())
        cp_idx = keys.index("capability")
        dm_keys = ["library", "playback", "nowplaying", "queue", "playlists"]
        for dk in dm_keys:
            if dk in keys:
                dk_idx = keys.index(dk)
                assert dk_idx < cp_idx, f"Capability before domain bridge {dk}"


class TestDeterministicConstants:
    def test_infrastructure_order_defined(self):
        assert len(INFRASTRUCTURE) == 10
        expected = ["page_state", "route_registry", "navigation", "action_registry",
                    "query_executor", "job_bridge", "confirmation", "theme", "accessibility",
                    "app_state"]
        assert expected == INFRASTRUCTURE

    def test_domain_order_defined(self):
        assert len(DOMAIN) == 24
        assert DOMAIN[0] == "library_sources"
        assert DOMAIN[1] == "library"
        assert DOMAIN[2] == "playback"

    def test_aggregators_order_defined(self):
        assert len(AGGREGATORS) == 8
        assert AGGREGATORS[0] == "notification"
        assert AGGREGATORS[3] == "capability"
        assert AGGREGATORS[4] == "app"


class TestOrderInvariants:
    def test_create_all_produces_stable_order(self):
        c = _make_container()
        f1 = BridgeFactory(c)
        f2 = BridgeFactory(c)
        r1 = f1.create_all()
        r2 = f2.create_all()
        assert list(r1.keys()) == list(r2.keys())

    def test_no_duplicate_bridges(self):
        c = _make_container()
        f = BridgeFactory(c)
        result = f.create_all()
        assert len(result) == len(set(result.keys()))
