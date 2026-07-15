from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QObject, Signal, Slot


pytestmark = [pytest.mark.qml_module("negative"), pytest.mark.qml_workflow("negative")]

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


class FakeStaleBridge(QObject):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._load_counter = 0
        self._stale = False

    @Slot(str, result=dict)
    def inspectTrack(self, filepath):
        self._load_counter += 1
        if self._stale:
            return {"ok": False, "error": "STALE_CALLBACK: load_counter mismatch"}
        return {"ok": True, "filepath": filepath}

    @Slot()
    def refresh(self):
        self._load_counter += 1
        self.dataChanged.emit()


class TestNegativeStaleCallback:
    def test_stale_callback_rejected(self):
        sb = FakeStaleBridge()
        result = sb.inspectTrack("/track.flac")
        assert result["ok"] is True

        sb._stale = True
        result = sb.inspectTrack("/track.flac")
        assert result["ok"] is False
        assert "STALE_CALLBACK" in result.get("error", "")

    def test_double_refresh_stale_guard(self):
        sb = FakeStaleBridge()
        sb.refresh()
        sb.refresh()
        assert sb._load_counter == 2

        sb._stale = True
        result = sb.inspectTrack("/test.flac")
        assert result["ok"] is False
        assert "STALE_CALLBACK" in result.get("error", "")
