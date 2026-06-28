"""Tests for NavigationController — routes, history, header config, dispatch."""
from unittest.mock import MagicMock, patch

import pytest

from ui.controllers.navigation_controller import (
    NavigationController, NavigationHistory, resolve_section_config,
    SECTION_CONFIG, NAV_ROUTES,
)


class TestResolveSectionConfig:
    def test_known_key_returns_config(self):
        config = resolve_section_config("library")
        assert config["title"] == "Biblioteca"
        assert config["search"] is True

    def test_unknown_key_returns_default(self):
        config = resolve_section_config("nonexistent")
        assert "title" in config
        assert config["search"] is True

    def test_playlist_prefix_with_extra(self):
        config = resolve_section_config("pl:123", extra={"name": "My Playlist"})
        assert config["title"] == "My Playlist"

    def test_playlist_prefix_without_extra_uses_capitalized_key(self):
        config = resolve_section_config("pl:123")
        assert config["title"] == "Pl:123"  # falls back to capitalized key

    def test_server_prefix_navidrome(self):
        config = resolve_section_config("srv:1", extra={"name": "My Server", "type": "navidrome"})
        assert config["title"] == "My Server"
        assert "navidrome" in config["icon"]

    def test_server_prefix_jellyfin(self):
        config = resolve_section_config("srv:1", extra={"name": "Jelly", "type": "jellyfin"})
        assert "jellyfin" in config["icon"]

    def test_device_prefix_with_name(self):
        config = resolve_section_config("dev:usb", extra={"name": "USB Drive", "mount": "/media/usb"})
        assert config["title"] == "USB Drive"

    def test_device_prefix_falls_back_to_basename(self):
        config = resolve_section_config("dev:sda1", extra={"mount": "/media/sda1"})
        assert config["title"] == "sda1"

    def test_all_section_configs_have_required_keys(self):
        for key, cfg in SECTION_CONFIG.items():
            assert "title" in cfg, f"Missing title in {key}"
            assert "subtitle" in cfg, f"Missing subtitle in {key}"
            assert "icon" in cfg, f"Missing icon in {key}"
            assert "views" in cfg, f"Missing views in {key}"
            assert "search" in cfg, f"Missing search in {key}"

    def test_all_nav_routes_have_matching_method_suffix(self):
        for key, method_name in NAV_ROUTES.items():
            assert method_name.startswith("_show_"), f"Route {key}: {method_name} must start with _show_"

    def test_search_placeholders_for_common_sections(self):
        placeholders = [
            "library", "albums", "artists", "playlists", "folders", "radio"
        ]
        from ui.controllers.navigation_controller import _SEARCH_PLACEHOLDERS
        for section in placeholders:
            assert section in _SEARCH_PLACEHOLDERS, f"Missing search placeholder for {section}"


class TestNavigationHistory:
    def test_initial_state(self):
        h = NavigationHistory()
        assert h.can_go_back is False
        assert h.can_go_forward is False
        assert h.current_key is None
        assert h.is_restoring is False

    def test_push_adds_entry(self):
        h = NavigationHistory()
        h.push("albums")
        assert h.can_go_back is False
        assert h.current_key == "albums"

    def test_push_duplicate_skips(self):
        h = NavigationHistory()
        h.push("albums")
        h.push("albums")
        assert len(h._history) == 1

    def test_back_and_forward(self):
        h = NavigationHistory()
        h.push("albums")
        h.push("artists")
        assert h.can_go_back is True
        entry = h.back()
        assert entry[0] == "albums"
        assert h.can_go_forward is True
        entry = h.forward()
        assert entry[0] == "artists"

    def test_back_returns_none_when_at_start(self):
        h = NavigationHistory()
        assert h.back() is None

    def test_forward_returns_none_when_at_end(self):
        h = NavigationHistory()
        h.push("albums")
        assert h.forward() is None

    def test_push_truncates_forward_history(self):
        h = NavigationHistory()
        h.push("a")
        h.push("b")
        h.back()
        h.push("c")
        assert h._history == [("a", ""), ("c", "")]
        assert h.can_go_forward is False

    def test_push_stores_search_text(self):
        h = NavigationHistory()
        h.push("albums", "rock")
        assert h._history[0] == ("albums", "rock")

    def test_restore_call_sets_flag(self):
        h = NavigationHistory()
        calls = []
        def navigate_fn(key):
            calls.append(key)
            assert h.is_restoring is True
        h.restore_call("albums", navigate_fn)
        assert calls == ["albums"]
        assert h.is_restoring is False

    def test_restore_call_clears_flag_on_error(self):
        h = NavigationHistory()
        def broken_fn(key):
            raise ValueError("fail")
        with pytest.raises(ValueError):
            h.restore_call("albums", broken_fn)
        assert h.is_restoring is False


class TestNavigationController:
    @pytest.fixture
    def win(self, qapp):
        w = MagicMock()
        w._search_text = ""
        w._search = MagicMock()
        w._search.text.return_value = ""
        w._view_switcher = MagicMock()
        w._section_title = MagicMock()
        w._section_subtitle = MagicMock()
        w._section_icon = MagicMock()
        w._back_btn = MagicMock()
        w._forward_btn = MagicMock()
        w._album_sort_btn = MagicMock()
        w._album_filter_btn = MagicMock()
        w._current_section_key = ""
        w._view_mode = ""
        w._restore_central_opacity = MagicMock()
        w._on_sidebar_navigate = MagicMock()
        return w

    @pytest.fixture
    def ctrl(self, win):
        from PySide6.QtCore import QObject
        ctrl = NavigationController.__new__(NavigationController)
        QObject.__init__(ctrl)
        ctrl._win = win
        ctrl._history = NavigationHistory()
        return ctrl

    def test_init_creates_history(self, ctrl):
        assert ctrl._history is not None
        assert ctrl.can_go_back is False

    def test_push_uses_win_search_text(self, ctrl, win):
        win._search_text = "rock"
        ctrl.push("albums")
        assert ctrl._history.current_key == "albums"

    def test_configure_header_sets_title(self, ctrl, win):
        ctrl.configure_header("albums")
        win._section_title.setText.assert_called_with("Álbumes")
        assert win._current_section_key == "albums"

    def test_configure_header_shows_album_controls(self, ctrl, win):
        ctrl.configure_header("albums")
        win._album_sort_btn.setVisible.assert_called_with(True)
        win._album_filter_btn.setVisible.assert_called_with(True)

    def test_configure_header_hides_album_controls(self, ctrl, win):
        ctrl.configure_header("library")
        win._album_sort_btn.setVisible.assert_called_with(False)
        win._album_filter_btn.setVisible.assert_called_with(False)

    def test_configure_header_hides_search_when_disabled(self, ctrl, win):
        ctrl.configure_header("identifier")
        win._search.setVisible.assert_called_with(False)

    def test_dispatch_calls_configure_header(self, ctrl, win):
        with patch.object(ctrl, 'configure_header') as mock_cfg:
            ctrl.dispatch("library")
            mock_cfg.assert_called_with("library")

    def test_dispatch_clears_search(self, ctrl, win):
        ctrl.dispatch("library")
        win._search.clear.assert_called_once()

    def test_dispatch_calls_handler_for_known_key(self, ctrl, win):
        ctrl.dispatch("library")
        win._show_library_hub_page.assert_called_with("library")

    def test_dispatch_handles_playlist_prefix(self, ctrl, win):
        ctrl.dispatch("pl:123")
        win._show_playlist_detail.assert_called_with("pl:123")

    def test_dispatch_handles_server_prefix(self, ctrl, win):
        ctrl.dispatch("srv:my_server")
        win._show_server.assert_called_with("srv:my_server")

    def test_dispatch_handles_device_prefix(self, ctrl, win):
        ctrl.dispatch("dev:usb")
        win._show_device.assert_called_with("dev:usb")

    def test_dispatch_handles_mix_prefix(self, ctrl, win):
        ctrl.dispatch("mix_daily")
        win._show_smart_mix.assert_called_with("mix_daily")

    def test_dispatch_handles_mix_prefix_to_hub(self, ctrl, win):
        ctrl.dispatch("mix_hub")
        win._show_mix_hub_page.assert_called_with("mix_hub")

    def test_dispatch_pushes_to_history(self, ctrl, win):
        ctrl.dispatch("albums")
        assert ctrl._history.current_key == "albums"

    def test_navigate_back_restores_previous(self, ctrl, win):
        ctrl.dispatch("albums")
        ctrl.dispatch("artists")
        win._on_sidebar_navigate.reset_mock()
        ctrl.navigate_back()
        win._on_sidebar_navigate.assert_called_with("albums")

    def test_dispatch_saves_previous_search(self, ctrl, win):
        win._search_text = "rock"
        win._search.text.return_value = "rock"
        ctrl.dispatch("albums")
        ctrl.dispatch("artists")
        assert ctrl._history._history[0] == ("albums", "rock"), (
            "dispatch should save previous search before clearing")

    def test_navigate_back_restores_search_text(self, ctrl, win):
        win._search_text = "rock"
        win._search.text.return_value = "rock"
        ctrl.dispatch("albums")
        win._search_text = ""
        win._search.text.return_value = ""
        ctrl.dispatch("artists")
        ctrl.navigate_back()
        assert ctrl._history.current_key == "albums", "back should return to albums"
        win._search.setText.assert_any_call("rock")

