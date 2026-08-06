from ui_qml_bridge.theme_bridge import ThemeBridge
from core.theme_service import ThemeService
from core.accessibility_service import AccessibilityService


class _FakeSettings:
    def __init__(self, initial: dict | None = None):
        self._data = dict(initial or {})

    def value(self, key, default=None):
        return self._data.get(key, default)

    def setValue(self, key, value):
        self._data[key] = value


class TestThemeBridge:
    def test_create(self):
        bridge = ThemeBridge(service=ThemeService(settings=_FakeSettings()))
        assert bridge is not None

    def test_create_degrades_without_service(self):
        bridge = ThemeBridge()
        assert bridge is not None
        assert bridge.theme == "dark"
        assert bridge.accentColor == "#8FB7FF"
        assert bridge.darkMode is True

    def test_animation_scale_tracks_reduced_motion(self):
        a11y = AccessibilityService(settings=_FakeSettings())
        bridge = ThemeBridge(
            service=ThemeService(settings=_FakeSettings()),
            accessibility_service=a11y,
        )

        a11y.set_reduced_motion(False)
        assert bridge.animationScale == 1.0

        a11y.set_reduced_motion(True)
        assert bridge.animationScale == 0.0

    def test_theme_change_delegates_to_service(self):
        service = ThemeService(settings=_FakeSettings())
        bridge = ThemeBridge(service=service)
        bridge.theme = "light"
        assert service.theme == "light"
        assert bridge.darkMode is False

    def test_accent_change_delegates_to_service(self):
        service = ThemeService(settings=_FakeSettings())
        bridge = ThemeBridge(service=service)
        bridge.accentColor = "#FF0000"
        assert service.accent_color == "#FF0000"
        assert bridge.accentColor == "#FF0000"
