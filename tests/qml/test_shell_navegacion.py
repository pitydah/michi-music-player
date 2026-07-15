"""PK — Tests for Shell, navigation, Home shell components.

Covers: AppShell, Sidebar, Header, Breadcrumbs, Back, Forward,
Route title, Route errors, Loading overlay, Fatal state,
NowPlaying bar, Command Palette overlay, Notifications overlay,
responsive shell, keyboard shell.
"""
from __future__ import annotations

import pytest

from ui_qml_bridge.app_bridge import AppBridge
from ui_qml_bridge.navigation_bridge import NavigationBridge
from ui_qml_bridge.page_state_store import PageStateStore
from ui_qml_bridge.route_registry import ROUTES

pytestmark = [pytest.mark.qml_module("shell_navegacion")]


class TestShellNavigation:
    def test_initial_route_is_home(self):
        nav = NavigationBridge()
        assert nav.currentRoute == "home"
        assert nav.currentTitle == "Inicio"

    def test_navigate_changes_route(self):
        nav = NavigationBridge()
        nav.navigate("library")
        assert nav.currentRoute == "library"

    def test_navigate_emits_route_changed(self):
        nav = NavigationBridge()
        signals = []
        nav.routeChanged.connect(lambda r: signals.append(r))
        nav.navigate("radio")
        assert "radio" in signals

    def test_navigate_same_route_refreshes(self):
        nav = NavigationBridge()
        signals = []
        nav.routeRefreshRequested.connect(lambda r: signals.append(r))
        nav.navigate("home")
        assert signals == ["home"]

    def test_back_navigation(self):
        nav = NavigationBridge()
        nav.navigate("library")
        nav.navigate("radio")
        nav.back()
        assert nav.currentRoute == "library"

    def test_back_empty_stack_stays(self):
        nav = NavigationBridge()
        nav.back()
        assert nav.currentRoute == "home"

    def test_forward_navigation(self):
        nav = NavigationBridge()
        nav.navigate("library")
        nav.navigate("radio")
        nav.back()
        nav.forward()
        assert nav.currentRoute == "radio"

    def test_forward_empty_stack(self):
        nav = NavigationBridge()
        nav.forward()
        assert nav.currentRoute == "home"

    def test_back_stack_signals(self):
        nav = NavigationBridge()
        signals = []
        nav.backStackChanged.connect(lambda: signals.append(True))
        nav.navigate("library")
        assert len(signals) >= 1

    def test_forward_stack_cleared_on_new_navigate(self):
        nav = NavigationBridge()
        nav.navigate("library")
        nav.navigate("radio")
        nav.back()
        assert nav.canGoForward
        nav.navigate("mix")
        assert not nav.canGoForward

    def test_can_go_back_property(self):
        nav = NavigationBridge()
        assert not nav.canGoBack
        nav.navigate("library")
        assert nav.canGoBack

    def test_can_go_forward_property(self):
        nav = NavigationBridge()
        nav.navigate("library")
        nav.navigate("radio")
        nav.back()
        assert nav.canGoForward

    def test_replace_route(self):
        nav = NavigationBridge()
        nav.replace("radio")
        assert nav.currentRoute == "radio"
        assert not nav.canGoBack

    def test_replace_same_route_refreshes(self):
        nav = NavigationBridge()
        signals = []
        nav.routeRefreshRequested.connect(lambda r: signals.append(r))
        nav.replace("home")
        assert signals == ["home"]

    def test_clear_history(self):
        nav = NavigationBridge()
        nav.navigate("library")
        nav.navigate("radio")
        nav.clearHistory()
        assert not nav.canGoBack
        assert not nav.canGoForward

    def test_history_content(self):
        nav = NavigationBridge()
        nav.navigate("library")
        nav.navigate("radio")
        hist = nav.history
        assert any(h["route"] == "home" for h in hist)

    def test_invalid_route_becomes_placeholder(self):
        nav = NavigationBridge()
        nav.navigate("does_not_exist")
        assert nav.currentRoute == "placeholder"

    def test_invalid_route_emits_error(self):
        nav = NavigationBridge()
        errors = []
        nav.invalidRouteError.connect(lambda r, m: errors.append((r, m)))
        nav.navigate("does_not_exist")
        assert len(errors) >= 1

    def test_refresh_current(self):
        nav = NavigationBridge()
        signals = []
        nav.routeRefreshRequested.connect(lambda r: signals.append(r))
        nav.refreshCurrent()
        assert signals == ["home"]

    def test_navigate_with_params(self):
        nav = NavigationBridge()
        nav.navigateWithParams("library.album_detail", {"album_key": "abc"})
        assert nav.currentRoute == "library.album_detail"
        assert nav.currentParams["album_key"] == "abc"

    def test_params_type_conversion(self):
        nav = NavigationBridge()
        nav.navigateWithParams("mix_detail", {"mix_id": "42"})
        assert nav.currentParams["mix_id"] == "42"

    def test_deep_link(self):
        nav = NavigationBridge()
        result = nav.deepLink("/library")
        assert result["ok"]
        assert nav.currentRoute == "library"

    def test_deep_link_with_params(self):
        nav = NavigationBridge()
        result = nav.deepLink("/library.album_detail?album_key=xyz")
        assert result["ok"]
        assert nav.currentParams["album_key"] == "xyz"

    def test_save_restore_state(self):
        nav = NavigationBridge()
        nav.navigate("library")
        nav.navigateWithParams("library.album_detail", {"album_key": "saved"})
        state = nav.saveState()
        nav2 = NavigationBridge()
        nav2.restoreState(state["state"])
        assert nav2.currentRoute == "library.album_detail"
        assert nav2.currentParams["album_key"] == "saved"

    def test_capability_restricts_route(self):
        nav = NavigationBridge()
        nav.set_capabilities(set())
        nav.navigate("audio_lab.overview")
        assert nav.currentRoute == "home"

    def test_capability_allows_route(self):
        nav = NavigationBridge()
        nav.set_capabilities({"audio_lab"})
        nav.navigate("audio_lab.overview")
        assert nav.currentRoute == "audio_lab.overview"

    def test_capability_map_coverage(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge as NB
        nb = NB()
        nb.set_capabilities({"audio_lab", "metadata"})
        for route in ["audio_lab.overview", "metadata.inspector"]:
            assert nb._route_matches_capability(route)

    def test_route_title_all_routes(self):
        for route, info in ROUTES.items():
            assert "title" in info, f"Route {route} missing title"
            assert info["title"], f"Route {route} has empty title"

    def test_route_source_all_routes(self):
        for route, info in ROUTES.items():
            assert "source" in info, f"Route {route} missing source"

    def test_route_category_all_routes(self):
        for route, info in ROUTES.items():
            assert "category" in info, f"Route {route} missing category"

    def test_route_status_all_routes(self):
        for route, info in ROUTES.items():
            assert "status" in info, f"Route {route} missing status"

    def test_detail_routes_have_params(self):
        exempt = {"group_editor", "mix_generator", "mix_result", "mix_rule_editor",
                   "audio_lab.profiles", "audio_lab.integrity", "audio_lab.comparison",
                   "audio_lab.normalization", "audio_lab.replaygain",
                   "audio_lab_job_detail", "library.folder_detail",
                   "devices.pairing"}
        for route, info in ROUTES.items():
            if info.get("category") == "detail" and route not in exempt:
                assert "params" in info, f"Detail route {route} missing params"

    def test_no_duplicate_routes(self):
        assert len(ROUTES) == len(set(ROUTES.keys()))

    def test_placeholder_route_exists(self):
        assert "placeholder" in ROUTES

    def test_navigate_to_all_routes(self):
        nav = NavigationBridge()
        param_routes = {
            "library.album_detail": {"album_key": "test"},
            "library.artist_detail": {"artist": "test"},
            "library.folder_detail": {"folder_id": "test"},
            "playlist_detail": {"playlist_id": 1},
            "mix_detail": {"mix_id": "test"},
            "connections.detail": {"connection_id": "test"},
            "devices.detail": {"device_id": "test"},
            "devices.pairing": {},
        }
        for route in ROUTES:
            if route == "placeholder":
                continue
            if route in param_routes:
                nav.navigateWithParams(route, param_routes[route])
            else:
                nav.navigate(route)
            assert nav.currentRoute in (route, "home"), f"Failed to navigate to {route}"


class TestPageStateStore:
    def test_save_state(self):
        store = PageStateStore()
        store.saveState("home", {"scroll": 100})
        assert store.hasState("home")

    def test_restore_state(self):
        store = PageStateStore()
        store.saveState("home", {"scroll": 100})
        state = store.restoreState("home")
        assert state["scroll"] == 100

    def test_restore_unknown(self):
        store = PageStateStore()
        assert store.restoreState("unknown") == {}

    def test_has_state_false(self):
        store = PageStateStore()
        assert not store.hasState("nowhere")

    def test_history_tracks_routes(self):
        store = PageStateStore()
        store.saveState("home", {})
        store.saveState("library", {})
        assert "home" in store.history
        assert "library" in store.history

    def test_previous_route(self):
        store = PageStateStore()
        store.saveState("home", {})
        store.saveState("radio", {})
        assert store.previousRoute() == "home"

    def test_previous_route_default(self):
        store = PageStateStore()
        assert store.previousRoute() == "home"

    def test_clear_removes_all(self):
        store = PageStateStore()
        store.saveState("home", {"x": 1})
        store.clear()
        assert not store.hasState("home")
        assert len(store.history) == 0

    def test_history_limit(self):
        store = PageStateStore()
        for i in range(30):
            store.saveState(f"route{i}", {})
        assert len(store.history) <= 20

    def test_save_twice_same_route(self):
        store = PageStateStore()
        store.saveState("home", {"a": 1})
        store.saveState("home", {"b": 2})
        state = store.restoreState("home")
        assert state == {"b": 2}

    def test_no_duplicate_consecutive(self):
        store = PageStateStore()
        store.saveState("home", {})
        store.saveState("home", {})
        assert store.history.count("home") == 1


class TestAppBridge:
    def test_initial_phase_bootstrap(self):
        bridge = AppBridge()
        assert bridge.phase == AppBridge.BOOTSTRAP

    def test_initial_not_ready(self):
        bridge = AppBridge()
        assert not bridge.ready

    def test_initial_not_shutting_down(self):
        bridge = AppBridge()
        assert not bridge.shuttingDown

    def test_set_phase(self):
        bridge = AppBridge()
        bridge.setPhase(AppBridge.READY)
        assert bridge.phase == AppBridge.READY

    def test_set_ready(self):
        bridge = AppBridge()
        bridge.setReady()
        assert bridge.ready
        assert bridge.phase == AppBridge.READY

    def test_ready_emits_signal(self):
        bridge = AppBridge()
        signals = []
        bridge.statusChanged.connect(lambda s: signals.append(s))
        bridge.setReady()
        assert "ready" in signals

    def test_quit_sets_shutting_down(self):
        bridge = AppBridge()
        bridge.quit()
        assert bridge.shuttingDown

    def test_quit_reaches_stopped(self):
        bridge = AppBridge()
        bridge.quit()
        assert bridge.phase == AppBridge.STOPPED

    def test_app_name(self):
        bridge = AppBridge()
        assert bridge.appName == "Michi Music Player"

    def test_version_string(self):
        bridge = AppBridge()
        assert isinstance(bridge.version, str)
        assert len(bridge.version) > 0

    def test_experimental_qml(self):
        bridge = AppBridge()
        assert bridge.experimentalQml

    def test_safe_mode_default(self):
        bridge = AppBridge()
        assert isinstance(bridge.safeMode, bool)

    def test_restart_required_default(self):
        bridge = AppBridge()
        assert not bridge.restartRequired

    def test_notify_restart(self):
        bridge = AppBridge()
        bridge.notifyRestartRequired()
        assert bridge.restartRequired

    def test_request_restart_slot(self):
        bridge = AppBridge()
        result = bridge.requestRestart()
        assert result["ok"]
        assert bridge.restartRequired

    def test_copy_version_info(self):
        bridge = AppBridge()
        result = bridge.copyVersionInfo()
        assert result["ok"]
        assert "Michi" in result["text"]

    def test_paths_return_strings(self):
        bridge = AppBridge()
        assert isinstance(bridge.dataPath, str)
        assert isinstance(bridge.cachePath, str)
        assert isinstance(bridge.configPath, str)
        assert isinstance(bridge.logPath, str)

    def test_cancel_all_tasks(self):
        bridge = AppBridge()
        bridge.cancelAllTasks()

    def test_app_score_initial(self):
        bridge = AppBridge()
        score = bridge.appScore()
        assert score["score"] == 0

    def test_app_score_after_ready(self):
        bridge = AppBridge()
        bridge.setReady()
        score = bridge.appScore()
        assert score["ready"]
        assert score["score"] > 0

    def test_shutdown_has_steps(self):
        bridge = AppBridge()
        assert hasattr(bridge, '_ordered_shutdown')
        bridge.quit()
        assert bridge.phase == AppBridge.STOPPED

    def test_shutdown_tolerates_missing_services(self):
        bridge = AppBridge()
        bridge.quit()
        assert bridge.shuttingDown

    def test_double_quit_idempotent(self):
        bridge = AppBridge()
        bridge.quit()
        bridge.quit()
        assert bridge.shuttingDown
