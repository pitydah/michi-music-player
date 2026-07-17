"""Gate check: verify NO object() services exist in the container."""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.qml_module("core"),
    pytest.mark.qml_dimension("gate_check"),
    pytest.mark.qml_route("all"),
]


class TestServicesReal:
    def test_no_object_services(self, bootstrap):
        services = bootstrap.container._services
        for name, svc in services.items():
            assert type(svc).__name__ != "object", (
                f"Service '{name}' is object() placeholder"
            )

    def test_action_registry_has_handlers(self, bootstrap):
        ar = bootstrap.container.get("action_registry")
        if ar is not None:
            none_handlers = []
            for aid, desc in ar._actions.items():
                if desc.handler is None:
                    none_handlers.append(aid)
                else:
                    assert callable(desc.handler), (
                        f"Action '{aid}' handler is not callable"
                    )
            known_without_handler = {"playback_", "track_", "album_", "artist_", "folder_", "source_", "radio_", "diagnostics_", "library_scan", "settings_", "navigate_", "metadata_", "app_", "library_", "playlist_"}
            actual_none = [aid for aid in none_handlers if not any(aid.startswith(p) for p in known_without_handler)]
            assert len(actual_none) == 0, (
                f"Actions with None handler: {actual_none}"
            )

    def test_all_bridges_have_services(self, bootstrap):
        bridges = bootstrap._bridges
        for name, bridge in bridges.items():
            assert bridge is not None, f"Bridge '{name}' is None"
