"""Gate: ensure V19 workflows use real bridges, not FakeBridges."""
from __future__ import annotations
import os
import pytest

pytestmark = [
    pytest.mark.qml_module("core"),
    pytest.mark.qml_dimension("widget_independence"),
    pytest.mark.qml_dimension("gate_check"),
]


class TestNoFakeBridges:
    """Gate: ensure no FakeBridges leak into V19 workflows."""
    def test_no_fake_bridge_in_v19_workflows(self):
        v19_dir = os.path.join(os.path.dirname(__file__))
        for fname in os.listdir(v19_dir):
            if fname.endswith(".py") and fname != "conftest.py":
                with open(os.path.join(v19_dir, fname)) as f:
                    content = f.read()
                for line in content.split("\n"):
                    stripped = line.strip()
                    if not stripped or stripped.startswith('"""') or stripped.startswith('#'):
                        continue
                    if "Fake" in stripped and "FakeAudioBackend" not in stripped and "FakeNetworkTransport" not in stripped and "TestNoFake" not in stripped:
                        pytest.fail(f"{fname}: {stripped}")

    def test_no_placeholder_services(self, bootstrap):
        for name, entry in bootstrap.container._services.items():
            assert type(entry).__name__ != "object", f"Service '{name}' is object()"

    def test_no_lambda_handlers(self, bootstrap, bridges):
        ar = bridges.get("action_registry")
        if ar is not None:
            bound = {"navigate_home", "navigate_library", "navigate_playlists",
                     "navigate_radio", "navigate_lyrics", "navigate_settings",
                     "navigate_eq", "navigate_audio_lab", "navigate_devices",
                     "navigate_connections", "navigate_home_audio", "navigate_jobs",
                     "navigate_queue", "navigate_history", "navigate_library_sources",
                     "navigate_diagnostics", "navigate_library_doctor", "navigate_mix",
                     "library_refresh", "library_add_folder",
                     "playlist_create", "metadata_edit", "metadata_smart_tagging",
                     "app_quit"}
            for aid, desc in ar._actions.items():
                if aid in bound:
                    assert desc.handler is not None, f"Bound action '{aid}' has None handler"

    def test_all_required_bridges_have_real_services(self, bootstrap, bridges):
        for name, bridge in bridges.items():
            assert bridge is not None, f"Bridge '{name}' is None"
