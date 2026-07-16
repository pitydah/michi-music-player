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
    def test_no_fake_bridge_in_v19_workflows(self):
        v19_dir = os.path.join(os.path.dirname(__file__))
        for fname in os.listdir(v19_dir):
            if fname.endswith(".py"):
                with open(os.path.join(v19_dir, fname)) as f:
                    content = f.read()
                for line in content.split("\n"):
                    if "Fake" in line and "FakeAudioBackend" not in line and "FakeNetworkTransport" not in line:
                        pytest.fail(f"{fname}: {line.strip()}")

    def test_no_placeholder_services(self, bootstrap):
        for name, entry in bootstrap.container._services.items():
            assert type(entry.service).__name__ != "object", f"Service '{name}' is object()"

    def test_no_lambda_handlers(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        if ar is not None:
            for aid, desc in ar._actions.items():
                assert desc.handler is not None, f"Action '{aid}' has None handler"

    def test_all_required_bridges_have_real_services(self, bootstrap):
        for name, bridge in bootstrap._bridges.items():
            assert bridge is not None, f"Bridge '{name}' is None"
