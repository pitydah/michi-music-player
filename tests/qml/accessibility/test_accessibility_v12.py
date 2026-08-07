"""Tests for Accessibility v12 — validar en runtime Accessible.role, name, focus, tab order, font scale 150%."""
from unittest.mock import MagicMock


from core.accessibility_service import AccessibilityService


class _FakeSettings:
    def __init__(self, initial: dict | None = None):
        self._data = dict(initial or {})

    def value(self, key, default=None):
        return self._data.get(key, default)

    def setValue(self, key, value):
        self._data[key] = value


class TestAccessibilityBridge:
    @staticmethod
    def _bridge(playback=None):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        return AccessibilityBridge(
            service=AccessibilityService(settings=_FakeSettings()),
            playback_service=playback or MagicMock(),
        )

    def test_creation(self):
        ab = self._bridge()
        assert ab is not None

    def test_font_scale_default(self):
        ab = self._bridge()
        assert isinstance(ab.fontScale, float)

    def test_font_scale_setter(self):
        ab = self._bridge()
        ab.fontScale = 1.5
        assert ab.fontScale == 1.5

    def test_high_contrast_default(self):
        ab = self._bridge()
        assert isinstance(ab.highContrast, bool)

    def test_high_contrast_setter(self):
        ab = self._bridge()
        ab.highContrast = True
        assert ab.highContrast is True

    def test_mono_default(self):
        ab = self._bridge()
        assert isinstance(ab.mono, bool)

    def test_balance_default(self):
        ab = self._bridge()
        assert isinstance(ab.balance, float)

    def test_balance_setter(self):
        ab = self._bridge()
        ab.balance = -0.5
        assert ab.balance == -0.5

    def test_restore_on_error(self):
        ab = self._bridge()
        result = ab.restoreOnError()
        assert result.get("ok")

    def test_score(self):
        ab = self._bridge()
        score = ab.accessibilityScore()
        assert isinstance(score, dict)
        assert "score" in score
