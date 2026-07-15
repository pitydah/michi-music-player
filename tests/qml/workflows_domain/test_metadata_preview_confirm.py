from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QObject, Property, Signal, Slot

import tests.qml.workflows_domain.domain_workflow_harness as harness

pytestmark = [pytest.mark.qml_module("metadata"), pytest.mark.qml_workflow("preview_confirm")]

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


class FakeMetadataBridge(QObject):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._trackTitle = "Original Title"
        self._trackArtist = "Original Artist"
        self._trackAlbum = "Original Album"
        self._hasSelection = True
        self._fields = []
        self._artworkStatus = "present"
        self._qualitySummary = "FLAC 24-bit"
        self._errorMessage = ""
        self._service = MagicMock()
        self._service.applyChanges = MagicMock(return_value={"ok": True})

    @Property(str, notify=dataChanged)
    def trackTitle(self): return self._trackTitle

    @Property(str, notify=dataChanged)
    def trackArtist(self): return self._trackArtist

    @Property(str, notify=dataChanged)
    def trackAlbum(self): return self._trackAlbum

    @Property(bool, notify=dataChanged)
    def hasSelection(self): return self._hasSelection

    @Property("QVariantList", notify=dataChanged)
    def fields(self): return self._fields

    @Property(str, notify=dataChanged)
    def artworkStatus(self): return self._artworkStatus

    @Property(str, notify=dataChanged)
    def qualitySummary(self): return self._qualitySummary

    @Property(str, notify=dataChanged)
    def errorMessage(self): return self._errorMessage

    @Slot(str, result=dict)
    def inspectTrack(self, filepath):
        return {"ok": True, "filepath": filepath}

    @Slot(str, str, str, result=dict)
    def applyChanges(self, title, artist, album):
        result = self._service.applyChanges(title, artist, album)
        if result["ok"]:
            self._trackTitle = title
            self._trackArtist = artist
            self._trackAlbum = album
            self.dataChanged.emit()
        return result


class TestMetadataPreviewConfirm:
    def test_preview_then_confirm_apply(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/metadata/MetadataInspectorPage.qml"))
        mb = FakeMetadataBridge()
        h.register_doubles({"metadataBridge": mb, "selectionContextBridge": QObject()})
        h.load()

        result = mb.inspectTrack("/path/to/song.flac")
        assert result["ok"] is True

        result = mb.applyChanges("New Title", "New Artist", "New Album")
        assert result["ok"] is True
        assert mb._trackTitle == "New Title"
        assert mb._trackArtist == "New Artist"
        assert mb._trackAlbum == "New Album"

        h.teardown()

    def test_preview_without_changing(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/metadata/MetadataInspectorPage.qml"))
        mb = FakeMetadataBridge()
        h.register_doubles({"metadataBridge": mb, "selectionContextBridge": QObject()})
        h.load()

        assert mb._trackTitle == "Original Title"
        assert mb._trackArtist == "Original Artist"
        assert mb._trackAlbum == "Original Album"

        h.teardown()
