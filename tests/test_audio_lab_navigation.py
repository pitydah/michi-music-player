"""Tests: Audio Lab navigation — routes, sidebar, AudioLabController."""

from unittest.mock import MagicMock

_ALL_SUBPAGES = (
    "audio_lab_diagnostics", "audio_lab_identifier", "audio_lab_backup",
    "audio_lab_output", "audio_lab_intelligence", "audio_lab_musicbrainz",
    "audio_lab_artwork", "audio_lab_lyrics", "audio_lab_organize",
    "audio_lab_conversion", "audio_lab_vinyl_lab",
)
_ALL_HANDLER_METHODS = tuple(f"show_{k}" for k in _ALL_SUBPAGES)
_ALL_WINDOW_METHODS = tuple(f"_show_{k}" for k in _ALL_SUBPAGES)
_AUDIO_LAB_CTRL_METHODS = (
    "show_audio_lab", "show_diagnostics", "show_identifier",
    "show_backup", "show_output", "show_intelligence", "show_lyrics",
    "show_artwork", "show_musicbrainz", "show_organize",
    "show_conversion", "show_vinyl_lab", "show_disc_lab",
)


class TestAudioLabNavigation:

    def _mock_win(self):
        import types
        views = types.SimpleNamespace(
            widget=lambda n: None,
            register=lambda n, p: None,
        )
        playback = types.SimpleNamespace(
            state_changed=types.SimpleNamespace(connect=lambda f: None),
        )
        return types.SimpleNamespace(
            _views=views, _playback=playback, _on_sidebar_navigate=lambda k: None,
            _current_ref=None, _player=None, _ctx=None, _db=None, _encoder=None,
            _fade_content=lambda t: None,
        )

    def test_nav_routes_contain_all_subpages(self):
        from legacy_widgets.ui.controllers.legacy_controllers.navigation_controller import NAV_ROUTES
        for key in _ALL_SUBPAGES:
            assert key in NAV_ROUTES

    def test_section_config_contains_all_subpages(self):
        from legacy_widgets.ui.controllers.legacy_controllers.navigation_controller import SECTION_CONFIG
        for key in _ALL_SUBPAGES:
            assert key in SECTION_CONFIG

    def test_resolve_sidebar_active_key(self):
        from legacy_widgets.ui.controllers.legacy_controllers.navigation_controller import resolve_sidebar_active_key
        for key in _ALL_SUBPAGES:
            assert resolve_sidebar_active_key(key) == "audio_lab"

    def test_hub_route_controller_has_all_show_methods(self):
        from legacy_widgets.ui.controllers.legacy_controllers.hub_route_controller import HubRouteController
        for method in _ALL_HANDLER_METHODS:
            assert hasattr(HubRouteController, method)

    def test_window_has_all_handler_methods(self):
        for method in _ALL_WINDOW_METHODS:
            assert hasattr(ui.window.MainWindow, method)

    def test_no_orphan_routes_in_nav_routes(self):
        from legacy_widgets.ui.controllers.legacy_controllers.navigation_controller import NAV_ROUTES
        for _key, method_name in NAV_ROUTES.items():
            assert hasattr(ui.window.MainWindow, method_name)

    def test_audio_lab_controller_has_all_methods(self):
        from legacy_widgets.ui.controllers.legacy_controllers.audio_lab_controller import AudioLabController
        for method in _AUDIO_LAB_CTRL_METHODS:
            assert hasattr(AudioLabController, method)

    def test_show_diagnostics_calls_lazy(self):
        """Verify show_diagnostics() calls self._lazy() with correct key.
        Mocks _lazy to avoid widget instantiation."""
        import types
        from legacy_widgets.ui.controllers.legacy_controllers.audio_lab_controller import AudioLabController

        lazy_calls = []

        win = types.SimpleNamespace(
            _workers=None, _db=None, _on_sidebar_navigate=lambda k: None,
            _views=types.SimpleNamespace(
                widget=lambda n: None, register=lambda n, p: None,
            ),
            _fade_content=lambda t: None,
            _playback=types.SimpleNamespace(
                state_changed=types.SimpleNamespace(connect=lambda f: None),
            ),
            _current_ref=None, _player=None, _ctx=None, _encoder=None,
            _hub_route_ctrl=MagicMock(),
        )
        ctrl = AudioLabController(win)
        ctrl._lazy = lambda name, factory: lazy_calls.append(name)
        ctrl.show_diagnostics()

        assert "audio_lab_diagnostics" in lazy_calls, (
            "show_diagnostics() must call self._lazy('audio_lab_diagnostics', _build)"
        )

    def test_hub_route_delegates_to_audio_lab_controller(self):
        """Verify HubRouteController.show_audio_lab_diagnostics delegates."""
        import types
        from legacy_widgets.ui.controllers.legacy_controllers.hub_route_controller import HubRouteController

        diag_called = []
        win = types.SimpleNamespace(
            _audio_lab_ctrl=types.SimpleNamespace(
                show_diagnostics=lambda k: diag_called.append(k),
            ),
        )
        ctrl = HubRouteController(win)
        ctrl.show_audio_lab_diagnostics("test_key")
        assert diag_called == ["test_key"], (
            "HubRouteController should delegate to audio_lab_ctrl.show_diagnostics"
        )
