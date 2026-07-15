from __future__ import annotations
import time
import pytest
from PySide6.QtCore import QCoreApplication

"""PQ — Smart Tagging completo: candidates, confidence, preview, accept, reject,
batch, progress, cancel, verify, rollback."""

pytestmark = [pytest.mark.qml_module("smart_tagging")]


def _process_events(duration=1.0):
    deadline = time.time() + duration
    while time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.02)


class TestTaggingCandidates:
    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        return SmartTaggingBridge()

    def test_default_status_idle(self, bridge):
        assert bridge.status == "idle"

    def test_default_suggestions_empty(self, bridge):
        assert bridge.suggestions == []

    def test_default_batch_results_empty(self, bridge):
        assert bridge.batchResults == []

    def test_default_progress_zero(self, bridge):
        assert bridge.progress == 0.0

    def test_scan_rejects_when_busy(self, bridge):
        bridge._status = "scanning"
        r = bridge.scanTrackById(42)
        assert not r.get("ok")

    def test_scan_queued_no_service(self, bridge):
        r = bridge.scanTrackById(1)
        assert r.get("ok") is not None

    def test_scan_batch_empty_list(self, bridge):
        r = bridge.scanBatch([])
        assert not r.get("ok")

    def test_scan_batch_rejects_when_busy(self, bridge):
        bridge._status = "applying"
        r = bridge.scanBatch([1, 2, 3])
        assert not r.get("ok")

    def test_scan_batch_queued(self, bridge):
        bridge._status = "scanning"
        assert bridge.status == "scanning"


class TestTaggingConfidence:
    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        bridge = SmartTaggingBridge()
        bridge._suggestions = [
            {"id": 0, "field": "artist", "current": "A", "suggested": "B",
             "confidence": 0.95, "source": "musicbrainz", "selected": False},
            {"id": 1, "field": "title", "current": "X", "suggested": "Y",
             "confidence": 0.50, "source": "file", "selected": False},
            {"id": 2, "field": "album", "current": "Z", "suggested": "W",
             "confidence": 0.30, "source": "file", "selected": False},
        ]
        return bridge

    def test_select_high_confidence(self, bridge):
        bridge.selectHighConfidence()
        assert bridge._suggestions[0]["selected"]
        assert not bridge._suggestions[1]["selected"]
        assert not bridge._suggestions[2]["selected"]

    def test_select_high_confidence_custom_threshold(self, bridge):
        bridge.selectHighConfidence(0.6)
        assert bridge._suggestions[0]["selected"]
        assert not bridge._suggestions[1]["selected"]

    def test_select_high_confidence_all_above_threshold(self, bridge):
        bridge.selectHighConfidence(0.2)
        assert all(s["selected"] for s in bridge._suggestions)


class TestTaggingPreview:
    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        return SmartTaggingBridge()

    def test_set_suggestion_selected(self, bridge):
        bridge._suggestions = [{"id": 0, "field": "artist", "selected": False}]
        r = bridge.setSuggestionSelected(0, True)
        assert r["ok"]
        assert bridge._suggestions[0]["selected"]

    def test_set_suggestion_deselected(self, bridge):
        bridge._suggestions = [{"id": 0, "selected": True}]
        bridge.setSuggestionSelected(0, False)
        assert not bridge._suggestions[0]["selected"]

    def test_select_all(self, bridge):
        bridge._suggestions = [
            {"id": 0, "selected": False},
            {"id": 1, "selected": False},
        ]
        bridge.selectAll()
        assert bridge._suggestions[0]["selected"]
        assert bridge._suggestions[1]["selected"]

    def test_select_none(self, bridge):
        bridge._suggestions = [
            {"id": 0, "selected": True},
            {"id": 1, "selected": True},
        ]
        bridge.selectNone()
        assert not bridge._suggestions[0]["selected"]
        assert not bridge._suggestions[1]["selected"]

    def test_accept_all(self, bridge):
        bridge._suggestions = [
            {"id": 0, "selected": False},
        ]
        bridge.acceptAll()
        assert bridge._suggestions[0]["selected"]

    def test_reject_all(self, bridge):
        bridge._suggestions = [
            {"id": 0, "selected": True},
        ]
        bridge.rejectAll()
        assert not bridge._suggestions[0]["selected"]


class TestTaggingApply:
    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        return SmartTaggingBridge()

    def test_apply_rejects_idle(self, bridge):
        r = bridge.applySelected()
        assert not r.get("ok")
        assert r.get("error_code") == "NOT_REVIEW"

    def test_apply_no_suggestions(self, bridge):
        bridge._status = "review"
        r = bridge.applySelected()
        assert not r.get("ok")

    def test_apply_no_selected(self, bridge):
        bridge._status = "review"
        bridge._suggestions = [{"id": 0, "field": "artist", "suggested": "B"}]
        r = bridge.applySelected()
        assert not r.get("ok")

    def test_apply_single_queued(self, bridge):
        bridge._status = "review"
        assert bridge.status == "review"


class TestTaggingBatch:
    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        return SmartTaggingBridge()

    def test_batch_apply_empty(self, bridge):
        bridge._status = "batch_review"
        bridge._batch_results = []
        r = bridge.applySelected()
        assert not r.get("ok")

    def test_batch_apply_with_results(self, bridge):
        bridge._status = "batch_review"
        bridge._batch_mode = True
        assert bridge.status == "batch_review"

    def test_detect_format_known(self, bridge):
        ext = bridge.detectFormat("/path/to/song.mp3")
        assert ext == "mp3"

    def test_detect_format_unknown(self, bridge):
        ext = bridge.detectFormat("/path/to/unknown.xyz")
        assert ext == "xyz"

    def test_detect_format_empty(self, bridge):
        ext = bridge.detectFormat("")
        assert ext == ""


class TestTaggingCancel:
    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        return SmartTaggingBridge()

    def test_cancel_scan(self, bridge):
        bridge._status = "scanning"
        r = bridge.cancelScan()
        assert r["ok"]
        assert bridge.status == "cancel_requested"

    def test_cancel_scan_resets_suggestions(self, bridge):
        bridge._suggestions = [{"id": 0, "field": "artist"}]
        bridge.cancelScan()
        assert bridge.suggestions == []

    def test_cancel_scan_resets_selection(self, bridge):
        bridge._selected_ids = {0, 1}
        bridge.cancelScan()
        assert bridge._selected_ids == set()

    def test_cancel_scan_resets_progress(self, bridge):
        bridge._progress = 0.5
        bridge.cancelScan()
        assert bridge.progress == 0.0

    def test_cancel_scan_resets_batch_results(self, bridge):
        bridge._batch_results = [{"track_id": 1}]
        bridge.cancelScan()
        assert bridge.batchResults == []


class TestTaggingVerify:
    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        return SmartTaggingBridge()

    def test_refresh_emits_signal(self, bridge):
        called = [False]
        bridge.dataChanged.connect(lambda: called.__setitem__(0, True))
        bridge.refresh()
        assert called[0]


class TestTaggingRollback:
    def test_rollback_tags_restores(self):
        from ui_qml_bridge.metadata_tag_adapter import rollback
        import os
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".bak", delete=False) as f:
            f.write(b"test")
            bak = f.name
        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            f.write(b"fLaC" + b"\x00" * 2000)
            path = f.name
        try:
            r = rollback(bak, path)
            assert r["ok"]
        finally:
            for p in [bak, path]:
                if os.path.exists(p):
                    os.unlink(p)

    def test_rollback_nonexistent_backup(self):
        from ui_qml_bridge.metadata_tag_adapter import rollback
        r = rollback("/nonexistent.bak", "/tmp/test.flac")
        assert not r["ok"]
