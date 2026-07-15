"""Tests for artwork operations."""
from __future__ import annotations

import time

import pytest
from PySide6.QtCore import QCoreApplication

pytestmark = [pytest.mark.qml_module("metadata")]


def _process_events(duration=1.0):
    deadline = time.time() + duration
    while time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.02)


class TestMetadataArtwork:
    @pytest.fixture
    def app(self):
        return QCoreApplication.instance() or QCoreApplication()

    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        return MetadataBridge(worker_manager=None)

    def test_has_artwork_no_file(self, bridge):
        result = bridge.hasArtwork()
        assert result.get("ok")
        assert "has_artwork" in result

    def test_replace_artwork_no_file_selected(self, bridge):
        result = bridge.replaceArtwork("/fake/image.png")
        assert not result.get("ok")

    def test_replace_artwork_nonexistent_image(self, bridge):
        bridge._current_filepath = "/fake/file.flac"
        result = bridge.replaceArtwork("/nonexistent/image.png")
        assert not result.get("ok")

    def test_remove_artwork_no_file(self, bridge):
        result = bridge.removeArtwork()
        assert not result.get("ok")

    def test_remove_artwork_sets_status(self, bridge):
        bridge._current_filepath = "/fake/file.flac"
        result = bridge.removeArtwork()
        assert result.get("ok") is not None

    def test_artwork_status_property(self, bridge):
        bridge._artwork_status = "Con carátula"
        assert bridge.artworkStatus == "Con carátula"
        bridge._artwork_status = "Sin carátula"
        assert bridge.artworkStatus == "Sin carátula"

    def test_detect_mime_png(self, bridge):
        mime = bridge._detect_mime("/fake/image.png")
        assert mime == "image/png"

    def test_detect_mime_jpg(self, bridge):
        mime = bridge._detect_mime("/fake/image.jpg")
        assert mime == "image/jpeg"

    def test_detect_mime_webp(self, bridge):
        mime = bridge._detect_mime("/fake/image.webp")
        assert mime == "image/webp"

    def test_detect_mime_default(self, bridge):
        mime = bridge._detect_mime("/fake/image.unknown")
        assert mime == "image/jpeg"

    def test_artwork_status_after_remove(self, bridge):
        bridge._current_filepath = "/fake/file.flac"
        bridge._artwork_status = "Carátula actualizada"
        bridge.removeArtwork()
        assert bridge._artwork_status != ""
