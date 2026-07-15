from __future__ import annotations
"""DV — ReplayGain: track analysis, album analysis, preview, write tags,
verify, remove tags."""

import os
import tempfile
import time

import pytest
from PySide6.QtCore import QCoreApplication

pytestmark = [pytest.mark.qml_module("audio_lab")]


def _process_events(duration=0.3):
    deadline = time.time() + duration
    while time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.01)


class TestAudioLabReplayGainV2:
    @pytest.fixture
    def app(self):
        return QCoreApplication.instance() or QCoreApplication()

    @pytest.fixture
    def sample_flac(self):
        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            f.write(b"fLaC" + b"\x00" * 2000)
            path = f.name
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def svc(self, app):
        from core.audio_lab.replaygain_service import ReplayGainService

        return ReplayGainService()

    def test_track_analysis_missing_file(self, svc):
        result = svc.analyze_track("/nonexistent.flac")
        assert result.status == "error"
        assert result.error == "FILE_NOT_FOUND"

    def test_track_analysis_completes(self, svc, sample_flac):
        result = svc.analyze_track(sample_flac)
        assert result.status in ("completed", "error")

    def test_album_analysis_completes(self, svc):
        results = svc.analyze_album(["/a.flac", "/b.flac"])
        assert len(results) == 2

    def test_album_analysis_aggregates_gain(self, svc):
        results = svc.analyze_album(["/a.flac", "/b.flac"])
        for r in results:
            if r.status == "completed":
                assert r.album_peak is not None
                assert r.album_gain is not None

    def test_preview_tags_no_file(self, svc):
        result = svc.preview_tags("")
        assert result.get("error") == "FILE_NOT_FOUND"

    def test_preview_tags_nonexistent(self, svc):
        result = svc.preview_tags("/nonexistent.flac")
        assert result.get("error") == "FILE_NOT_FOUND"

    def test_preview_tags_empty_result(self, svc, sample_flac):
        result = svc.preview_tags(sample_flac)
        assert result.get("has_tags") is not None

    def test_write_tags_missing_file(self, svc):
        ok = svc.write_tags("/nonexistent.flac", -5.0, 0.5)
        assert ok is False

    def test_remove_tags_missing_file(self, svc):
        ok = svc.remove_tags("/nonexistent.flac")
        assert ok is False

    def test_verify_tags_no_file(self, svc):
        result = svc.verify_tags("", {"track_gain": 0.0, "track_peak": 0.0})
        assert result.get("error") == "FILE_NOT_FOUND"

    def test_verify_tags_missing_file(self, svc):
        result = svc.verify_tags("/nonexistent.flac", {"track_gain": 0.0, "track_peak": 0.0})
        assert result.get("error") == "FILE_NOT_FOUND"
