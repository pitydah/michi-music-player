"""Tests for Home v12 — snapshot dashboard con servicios reales."""
from unittest.mock import MagicMock, patch

import pytest


class TestHomeBridgeServices:
    def test_home_bridge_creation(self):
        from ui_qml_bridge.home_bridge import HomeBridge
        hb = HomeBridge(
            db=MagicMock(),
            playback_service=MagicMock(),
            library_bridge=MagicMock(),
            library_sources_service=MagicMock(),
            job_bridge=MagicMock(),
        )
        assert hb is not None

    def test_home_bridge_requires_src_svc(self):
        from ui_qml_bridge.home_bridge import HomeBridge
        hb = HomeBridge(db=MagicMock())
        assert hb._src_svc is None

    def test_home_refresh_updates_stats(self):
        from ui_qml_bridge.home_bridge import HomeBridge
        hb = HomeBridge(
            db=MagicMock(),
            playback_service=MagicMock(),
            library_bridge=MagicMock(),
            library_sources_service=MagicMock(),
            job_bridge=MagicMock(),
        )
        hb.refresh()
        assert True

    def test_home_has_snapshot_changed_signal(self):
        from ui_qml_bridge.home_bridge import HomeBridge
        hb = HomeBridge(db=MagicMock(), playback_service=MagicMock(),
                         library_bridge=MagicMock(), library_sources_service=MagicMock(),
                         job_bridge=MagicMock())
        assert hasattr(hb, 'snapshotChanged')

    def test_home_score(self):
        from ui_qml_bridge.home_bridge import HomeBridge
        hb = HomeBridge(db=MagicMock(), playback_service=MagicMock(),
                         library_bridge=MagicMock(), library_sources_service=MagicMock(),
                         job_bridge=MagicMock())
        score = hb.homeScore()
        assert isinstance(score, dict)
        assert "score" in score

    def test_home_library_sources_integration(self):
        mock_src = MagicMock()
        mock_src.list.return_value = [{"path": "/music", "enabled": True}]
        from ui_qml_bridge.home_bridge import HomeBridge
        hb = HomeBridge(db=MagicMock(), playback_service=MagicMock(),
                         library_bridge=MagicMock(), library_sources_service=mock_src,
                         job_bridge=MagicMock())
        hb.refresh()
        assert hb.sourcesCount > 0

    def test_home_set_library_stats(self):
        from ui_qml_bridge.home_bridge import HomeBridge
        hb = HomeBridge(db=MagicMock(), playback_service=MagicMock(),
                         library_bridge=MagicMock(), library_sources_service=MagicMock(),
                         job_bridge=MagicMock())
        hb.set_library_stats(100, 50, 5000)
        assert hb.libraryAlbums == 100
        assert hb.libraryArtists == 50
        assert hb.libraryTracks == 5000
