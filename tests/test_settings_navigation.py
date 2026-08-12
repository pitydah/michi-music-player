"""Tests for M10.3 — Settings navigation and bridge."""

from michi.application.navigation_service import NavigationService
from michi.application.settings_service import SettingsService
from michi.domain.navigation import AppRoute
from michi.domain.settings import SettingsState
from michi.presentation.navigation_bridge import NavigationBridge
from michi.presentation.settings_bridge import SettingsBridge
from tests.conftest import FakeSettingsRepo


class TestSettingsRoute:
    def test_route_exists(self):
        assert AppRoute.SETTINGS == "settings"

    def test_navigate_to_settings(self):
        svc = NavigationService()
        svc.navigate("settings")
        assert svc.state.current_route == AppRoute.SETTINGS

    def test_navigation_bridge_reports_settings(self):
        svc = NavigationService()
        bridge = NavigationBridge(svc)
        bridge.navigate("settings")
        assert bridge.property("currentRoute") == "settings"

    def test_repeated_navigation(self):
        svc = NavigationService()
        svc.navigate("settings")
        svc.navigate("settings")
        assert svc.state.current_route == AppRoute.SETTINGS

    def test_settings_does_not_break_existing_routes(self):
        svc = NavigationService()
        svc.navigate("library")
        assert svc.state.current_route == AppRoute.LIBRARY
        svc.navigate("settings")
        assert svc.state.current_route == AppRoute.SETTINGS
        svc.navigate("now_playing")
        assert svc.state.current_route == AppRoute.NOW_PLAYING
        svc.navigate("queue")
        assert svc.state.current_route == AppRoute.QUEUE

    def test_default_route_unchanged(self):
        svc = NavigationService()
        assert svc.state.current_route == AppRoute.LIBRARY


class TestSettingsBridge:
    def test_last_directory(self):
        repo = FakeSettingsRepo()
        repo.save(SettingsState(last_directory="/music"))
        settings = SettingsService(repo)
        settings.load()
        bridge = SettingsBridge(settings)
        assert bridge.property("lastDirectory") == "/music"

    def test_volume_read_only(self):
        repo = FakeSettingsRepo()
        repo.save(SettingsState(volume=42))
        settings = SettingsService(repo)
        settings.load()
        bridge = SettingsBridge(settings)
        assert bridge.property("volume") == 42

    def test_muted_read_only(self):
        repo = FakeSettingsRepo()
        repo.save(SettingsState(muted=True))
        settings = SettingsService(repo)
        settings.load()
        bridge = SettingsBridge(settings)
        assert bridge.property("muted") is True
