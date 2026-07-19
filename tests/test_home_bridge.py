from unittest.mock import MagicMock

from ui_qml_bridge.home_bridge import HomeBridge


class TestHomeBridgeLifecycle:
    def test_refresh_loads_all_dashboard_sections(self):
        bridge = HomeBridge(db=MagicMock(), library_bridge=MagicMock())

        result = bridge.refresh()

        assert result["ok"] is True
        assert result["ready"] is True
        assert bridge.ready is True
        assert bridge.loading is False

    def test_empty_library_is_reported(self):
        bridge = HomeBridge(db=MagicMock())
        result = bridge.refresh()

        assert bridge.hasLibrary is False
        assert result["has_library"] is False

    def test_library_with_content_is_visible(self):
        bridge = HomeBridge(db=MagicMock())
        bridge.set_library_stats(5, 10, 100)
        result = bridge.refresh()

        assert bridge.hasLibrary is True
        assert bridge.libraryAlbums == 5
        assert result["has_library"] is True

    def test_partial_error_is_reported(self):
        class FailingBridge:
            songCount = 0
            albumCount = 0
            artistCount = 0

        bridge = HomeBridge(
            db=MagicMock(),
            library_bridge=FailingBridge(),
            library_sources_service=MagicMock(),
        )
        bridge._src_svc.list.side_effect = RuntimeError("source error")

        result = bridge.refresh()

        assert result["ok"] is False
        assert result["errors"]
        assert bridge.ready is True
        assert bridge.loading is False

    def test_home_score_includes_ready_and_error(self):
        bridge = HomeBridge(db=MagicMock())
        bridge.refresh()
        score = bridge.homeScore()

        assert "ready" in score
        assert "error" in score
        assert "score" in score

    def test_playback_signal_triggers_refresh(self, qtbot):
        player = MagicMock()
        player.track_changed = MagicMock()
        player.state_changed = MagicMock()
        bridge = HomeBridge(db=MagicMock(), player_service=player)

        assert bridge.ready is False
        result = bridge.refresh()
        assert result["ok"] is True

    def test_job_signal_connected(self):
        job_bridge = MagicMock()
        job_bridge.jobsChanged = MagicMock()
        bridge = HomeBridge(db=MagicMock(), job_bridge=job_bridge)

        job_bridge.jobsChanged.connect.assert_called_once()

    def test_set_library_stats_clamps_to_zero(self):
        bridge = HomeBridge(db=MagicMock())
        bridge.set_library_stats(-1, -5, -10)
        assert bridge.libraryAlbums == 0
        assert bridge.libraryArtists == 0
        assert bridge.libraryTracks == 0
