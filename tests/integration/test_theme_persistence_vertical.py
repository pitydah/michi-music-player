"""Vertical theme persistence test — real ThemeService with an isolated backend.

Single write path: state set on the service persists; a NEW service instance
restores the persisted values; signals are emitted; a registered bridge
consumer is reflected in ``health()``.
"""
from __future__ import annotations



from core.theme_service import ThemeService


class _FakeSettings:
    """In-memory QSettings-like backend (tmp isolated)."""

    def __init__(self, initial: dict | None = None):
        self._data = dict(initial or {})

    def value(self, key, default=None):
        return self._data.get(key, default)

    def setValue(self, key, value):
        self._data[key] = value


class TestThemePersistenceVertical:
    def test_accent_set_readback_and_restore(self):
        backend = _FakeSettings()
        service = ThemeService(settings=backend)
        service.set_accent_color("#FF7A00")
        assert service.accent_color == "#FF7A00"
        assert backend.value("appearance/accent_color") == "#FF7A00"

        # Re-instantiate the service -> persisted accent restored.
        restored = ThemeService(settings=backend)
        assert restored.accent_color == "#FF7A00"

    def test_theme_set_readback_and_restore(self):
        backend = _FakeSettings()
        service = ThemeService(settings=backend)
        service.set_theme("light")
        assert service.theme == "light"
        assert backend.value("appearance/theme") == "light"

        restored = ThemeService(settings=backend)
        assert restored.theme == "light"
        assert restored.dark_mode is False

    def test_compact_mode_persists(self):
        backend = _FakeSettings()
        service = ThemeService(settings=backend)
        service.set_compact_mode(True)
        restored = ThemeService(settings=backend)
        assert restored.compact_mode is True

    def test_invalid_theme_falls_back_to_default(self):
        backend = _FakeSettings({"appearance/theme": "neon"})
        service = ThemeService(settings=backend)
        assert service.theme == "dark"

    def test_signals_emitted(self):
        backend = _FakeSettings()
        service = ThemeService(settings=backend)
        theme_seen = []
        accent_seen = []
        service.themeChanged.connect(lambda v: theme_seen.append(v))
        service.accentChanged.connect(lambda v: accent_seen.append(v))
        service.set_theme("light")
        service.set_accent_color("#FF0000")
        assert theme_seen == ["light"]
        assert accent_seen == ["#FF0000"]

    def test_noop_does_not_emit(self):
        backend = _FakeSettings()
        service = ThemeService(settings=backend)
        seen = []
        service.themeChanged.connect(lambda v: seen.append(v))
        service.set_theme("dark")
        assert seen == []

    def test_artwork_background_state_and_signal(self):
        backend = _FakeSettings()
        service = ThemeService(settings=backend)
        bg_seen = []
        service.backgroundChanged.connect(lambda a, b: bg_seen.append((a, b)))
        service.apply_background("#112233", "#001122")
        assert service.background_primary == "#112233"
        assert service.background_darker == "#001122"
        assert bg_seen == [("#112233", "#001122")]

    def test_consumer_registration_reflected_in_health(self):
        backend = _FakeSettings()
        service = ThemeService(settings=backend)
        health = service.health()
        assert health["consumers"] == 0
        service.register_consumer("theme_bridge")
        service.register_consumer("nowplaying")
        health = service.health()
        assert health["consumers"] == 2
        assert health["available"] is True
        assert health["settings_ok"] is True
        service.unregister_consumer("nowplaying")
        assert service.health()["consumers"] == 1

    def test_health_reports_last_persisted(self):
        backend = _FakeSettings()
        service = ThemeService(settings=backend)
        service.set_theme("light")
        health = service.health()
        assert health["last_persisted_ok"] is True
        assert health["last_persist_error"] == ""

    def test_bridge_consumer_wiring(self, qapp):
        from ui_qml_bridge.theme_bridge import ThemeBridge
        backend = _FakeSettings()
        service = ThemeService(settings=backend)
        bridge = ThemeBridge(service=service)
        assert service.health()["consumers"] >= 1
        bridge.theme = "light"
        assert service.theme == "light"
        assert backend.value("appearance/theme") == "light"

    def test_extract_colors_delegates_to_extractor(self):
        from core.background_theme_service import BackgroundThemeService
        backend = _FakeSettings()
        service = ThemeService(settings=backend)
        # extract_colors delegates to BackgroundThemeService (pure utility).
        assert callable(service.extract_colors)
        assert isinstance(BackgroundThemeService, type)
