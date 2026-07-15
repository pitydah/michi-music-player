from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QObject, Property, Signal, Slot

import tests.qml.workflows_domain.domain_workflow_harness as harness

pytestmark = [pytest.mark.qml_module("playlists"), pytest.mark.qml_workflow("create_export")]

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


class FakePlaylistsBridge(QObject):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._playlists = []
        self._service = MagicMock()
        self._service.create = MagicMock(return_value={"ok": True, "id": 1})
        self._service.add_tracks = MagicMock(return_value={"ok": True})
        self._service.reorder = MagicMock(return_value={"ok": True})
        self._service.export = MagicMock(return_value={"ok": True, "path": "/tmp/export.m3u"})

    @Property("QVariantList", notify=dataChanged)
    def playlists(self): return self._playlists

    @Slot(str, result=dict)
    def create(self, name):
        result = self._service.create(name)
        if result["ok"]:
            self._playlists.append({"id": result["id"], "name": name, "tracks": []})
            self.dataChanged.emit()
        return result

    @Slot(int, "QVariantList", result=dict)
    def addTracks(self, playlist_id, track_ids):
        result = self._service.add_tracks(playlist_id, track_ids)
        for pl in self._playlists:
            if pl["id"] == playlist_id:
                pl["tracks"].extend(track_ids)
        return result

    @Slot(int, int, int, result=dict)
    def reorder(self, playlist_id, from_idx, to_idx):
        return self._service.reorder(playlist_id, from_idx, to_idx)

    @Slot(int, result=dict)
    def export(self, playlist_id):
        return self._service.export(playlist_id)

    @Slot()
    def refresh(self): self.dataChanged.emit()


class TestPlaylistCreateExport:
    def test_create_add_reorder_export(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/playlists/PlaylistsPage.qml"))
        pb = FakePlaylistsBridge()
        h.register_doubles({"playlistsBridge": pb, "notificationBridge": QObject()})
        h.load()

        result = pb.create("Favoritos")
        assert result["ok"] is True
        assert len(pb._playlists) == 1

        result = pb.addTracks(1, [10, 20, 30])
        assert result["ok"] is True
        pb._service.add_tracks.assert_called_with(1, [10, 20, 30])

        result = pb.reorder(1, 0, 2)
        assert result["ok"] is True
        pb._service.reorder.assert_called_with(1, 0, 2)

        result = pb.export(1)
        assert result["ok"] is True
        pb._service.export.assert_called_with(1)

        h.teardown()

    def test_create_empty_playlist_then_add_tracks(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/playlists/PlaylistsPage.qml"))
        pb = FakePlaylistsBridge()
        h.register_doubles({"playlistsBridge": pb, "notificationBridge": QObject()})
        h.load()

        result = pb.create("Nueva")
        assert result["ok"] is True

        result = pb.addTracks(1, [1, 2, 3, 4, 5])
        assert result["ok"] is True
        assert len(pb._playlists[0]["tracks"]) == 5

        h.teardown()
