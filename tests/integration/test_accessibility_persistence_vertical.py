"""Vertical accessibility persistence test — real AccessibilityService.

Single write path: state set on the service persists; a NEW service instance
restores the persisted values; signals are emitted; a registered bridge
consumer is reflected in ``health()``.
"""
from __future__ import annotations


from core.accessibility_service import AccessibilityService


class _FakeSettings:
    def __init__(self, initial: dict | None = None):
        self._data = dict(initial or {})

    def value(self, key, default=None):
        return self._data.get(key, default)

    def setValue(self, key, value):
        self._data[key] = value


class TestAccessibilityPersistenceVertical:
    def test_high_contrast_set_readback_and_restore(self):
        backend = _FakeSettings()
        service = AccessibilityService(settings=backend)
        service.set_high_contrast(True)
        assert service.high_contrast is True
        assert backend.value("accessibility/high_contrast") is True

        restored = AccessibilityService(settings=backend)
        assert restored.high_contrast is True

    def test_reduced_motion_set_readback_and_restore(self):
        backend = _FakeSettings()
        service = AccessibilityService(settings=backend)
        service.set_reduced_motion(True)
        assert backend.value("accessibility/reduced_motion") is True

        restored = AccessibilityService(settings=backend)
        assert restored.reduced_motion is True

    def test_font_scale_set_readback_and_restore(self):
        backend = _FakeSettings()
        service = AccessibilityService(settings=backend)
        service.set_font_scale(1.5)
        assert service.font_scale == 1.5
        assert backend.value("accessibility/font_size") == 1.5

        restored = AccessibilityService(settings=backend)
        assert restored.font_scale == 1.5

    def test_font_scale_clamped(self):
        backend = _FakeSettings()
        service = AccessibilityService(settings=backend)
        service.set_font_scale(9.0)
        assert service.font_scale == 2.0
        service.set_font_scale(0.1)
        assert service.font_scale == 0.5

    def test_mono_and_balance_persist(self):
        backend = _FakeSettings()
        service = AccessibilityService(settings=backend)
        service.set_mono(True)
        service.set_balance(-0.5)
        restored = AccessibilityService(settings=backend)
        assert restored.mono is True
        assert restored.balance == -0.5

    def test_signals_emitted(self):
        backend = _FakeSettings()
        service = AccessibilityService(settings=backend)
        font_seen = []
        hc_seen = []
        rm_seen = []
        service.fontScaleChanged.connect(lambda v: font_seen.append(v))
        service.highContrastChanged.connect(lambda v: hc_seen.append(v))
        service.reducedMotionChanged.connect(lambda v: rm_seen.append(v))
        service.set_font_scale(1.25)
        service.set_high_contrast(True)
        service.set_reduced_motion(True)
        assert font_seen == [1.25]
        assert hc_seen == [True]
        assert rm_seen == [True]

    def test_noop_does_not_emit(self):
        backend = _FakeSettings()
        service = AccessibilityService(settings=backend)
        seen = []
        service.fontScaleChanged.connect(lambda v: seen.append(v))
        service.set_font_scale(1.0)
        assert seen == []

    def test_consumer_registration_reflected_in_health(self):
        backend = _FakeSettings()
        service = AccessibilityService(settings=backend)
        assert service.health()["consumers"] == 0
        service.register_consumer("accessibility_bridge")
        health = service.health()
        assert health["consumers"] == 1
        assert health["available"] is True
        assert health["settings_ok"] is True
        service.unregister_consumer("accessibility_bridge")
        assert service.health()["consumers"] == 0

    def test_health_reports_last_persisted(self):
        backend = _FakeSettings()
        service = AccessibilityService(settings=backend)
        service.set_high_contrast(True)
        health = service.health()
        assert health["last_persisted_ok"] is True
        assert health["last_persist_error"] == ""

    def test_bridge_consumer_wiring(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        backend = _FakeSettings()
        service = AccessibilityService(settings=backend)
        playback = MagicMock()
        bridge = AccessibilityBridge(service=service, playback_service=playback)
        assert service.health()["consumers"] >= 1
        bridge.highContrast = True
        assert service.high_contrast is True
        assert backend.value("accessibility/high_contrast") is True
        playback.set_mono.assert_called()
