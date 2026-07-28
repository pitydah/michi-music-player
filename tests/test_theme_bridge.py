from unittest.mock import MagicMock
from ui_qml_bridge.theme_bridge import ThemeBridge


class TestThemeBridge:
    def test_create(self):
        bridge = ThemeBridge(coordinator=MagicMock())
        assert bridge is not None

    def test_animation_scale_tracks_reduced_motion(self):
        bridge = ThemeBridge(coordinator=MagicMock())

        bridge._reduced_motion = False
        assert bridge.animationScale == 1.0

        bridge._reduced_motion = True
        assert bridge.animationScale == 0.0
