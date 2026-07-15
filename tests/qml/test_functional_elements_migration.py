"""Contracts for the functional-elements migration."""

from __future__ import annotations

from pathlib import Path

from core.connection_service import ConnectionService
from core.home_audio_service import HomeAudioService
from integrations.connections.connection_manager import ConnectionManager

REPO = Path(__file__).resolve().parents[2]


class _Groups:
    def __init__(self):
        self.items = []

    def groups(self):
        return list(self.items)

    def add_group(self, name, members):
        self.items.append({"id": "group", "name": name, "members": members})
        return "group"

    def remove_group(self, group_id):
        self.items = [item for item in self.items if item["id"] != group_id]

    def rename_group(self, group_id, name):
        for item in self.items:
            if item["id"] == group_id:
                item["name"] = name

    def set_volume(self, group_id, volume):
        for item in self.items:
            if item["id"] == group_id:
                item["volume_level"] = volume


def test_qml_launcher_uses_application_bootstrap():
    source = (REPO / "michi/qml_app.py").read_text(encoding="utf-8")
    assert "ApplicationBootstrap" in source
    assert "bootstrap.run(engine)" in source


def test_playlist_service_no_longer_imports_legacy_widgets():
    source = (REPO / "core/playlist_service.py").read_text(encoding="utf-8")
    assert "core.playlist_io" in source
    assert "legacy_widgets" not in source


def test_connection_profiles_are_managed_without_widgets(tmp_path):
    manager = ConnectionManager(store_path=str(tmp_path / "connections.json"))
    service = ConnectionService(connection_manager=manager)

    result = service.connect_manual("127.0.0.1", 53318, "Local")

    assert result["ok"] is True
    assert service.state == "detected"
    assert service.get_connections()[0]["name"] == "Local"


def test_home_audio_group_lifecycle_is_core_owned():
    groups = _Groups()
    service = HomeAudioService(snapcast_group_manager=groups)

    created = service.group("living,kitchen")
    renamed = service.set_group_name("group", "Downstairs")
    volume = service.set_volume("group", 0.75)
    removed = service.ungroup("group")

    assert created["ok"] is True
    assert renamed["ok"] is True
    assert volume["ok"] is True
    assert removed["ok"] is True
    assert service.get_groups() == []
