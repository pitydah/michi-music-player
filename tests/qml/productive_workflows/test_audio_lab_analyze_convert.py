"""Workflow: Audio Lab → Analyze → Convert → Cancel."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("audio_lab"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestAudioLab:
    def test_audio_lab_bridge_exists(self, bootstrap):
        alb = bootstrap._bridges.get("audio_lab")
        assert alb is not None

    def test_audio_lab_service_exists(self, bootstrap):
        svc = bootstrap.container.get("audio_lab_service")
        assert svc is not None
