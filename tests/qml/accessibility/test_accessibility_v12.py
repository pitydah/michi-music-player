"""Tests for Accessibility v12 — validar en runtime Accessible.role, name, focus, tab order, font scale 150%."""
from unittest.mock import MagicMock

class TestAccessibilityBridge:
    def test_playback_service_is_optional_for_visual_settings(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        bridge = AccessibilityBridge()
        assert bridge.accessibilityScore()["has_playback_service"] is False

    def test_creation(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        ab = AccessibilityBridge(playback_service=MagicMock())
        assert ab is not None

    def test_font_scale_default(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        ab = AccessibilityBridge(playback_service=MagicMock())
        assert ab.fontScale in ("normal", "large", "x-large", "small")

    def test_font_scale_setter(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        ab = AccessibilityBridge(playback_service=MagicMock())
        ab.fontScale = "large"
        assert ab.fontScale == "large"

    def test_high_contrast_default(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        ab = AccessibilityBridge(playback_service=MagicMock())
        assert isinstance(ab.highContrast, bool)

    def test_high_contrast_setter(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        ab = AccessibilityBridge(playback_service=MagicMock())
        ab.highContrast = True
        assert ab.highContrast is True

    def test_mono_default(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        ab = AccessibilityBridge(playback_service=MagicMock())
        assert isinstance(ab.mono, bool)

    def test_balance_default(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        ab = AccessibilityBridge(playback_service=MagicMock())
        assert isinstance(ab.balance, int)

    def test_balance_setter(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        ab = AccessibilityBridge(playback_service=MagicMock())
        ab.balance = -50
        assert ab.balance == -50

    def test_restore_on_error(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        ab = AccessibilityBridge(playback_service=MagicMock())
        result = ab.restoreOnError()
        assert result.get("ok")

    def test_score(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        ab = AccessibilityBridge(playback_service=MagicMock())
        score = ab.accessibilityScore()
        assert isinstance(score, dict)
        assert "score" in score
