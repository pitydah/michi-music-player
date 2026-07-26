from __future__ import annotations
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.michi_ai_bridge import MichiAIBridge

pytestmark = [pytest.mark.qml_module("michi_ai")]


class TestMichiaiUsesActionRegistry:
    def test_play_fails_without_engine(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("reproduce canción 42")
        assert bridge.status == "FAILED"

    def test_queue_fails_without_engine(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("encolar canción 7")
        assert bridge.status == "FAILED"

    def test_bridge_accepts_action_registry(self):
        registry = MagicMock()
        bridge = MichiAIBridge(action_registry=registry)
        assert bridge._registry is registry

    def test_bridge_accepts_navigation_bridge(self):
        nav = MagicMock()
        bridge = MichiAIBridge(navigation_bridge=nav)
        assert bridge._nav is nav

    def test_cancel_works(self):
        bridge = MichiAIBridge()
        bridge.cancel()
        assert bridge.status == "CANCELLED"

    def test_ai_score_returns_dict(self):
        bridge = MichiAIBridge()
        score = bridge.aiScore()
        assert "score" in score
