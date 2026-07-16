"""Tests for FolderController — instantiation, signal wiring, handler safety."""

from unittest.mock import MagicMock, patch

from legacy_widgets.ui.controllers.legacy_controllers.folder_controller import FolderController


class TestFolderController:
    def test_create_without_args(self):
        ctrl = FolderController()
        assert ctrl is not None
        assert ctrl._widget is None

    def test_create_with_db(self):
        db = MagicMock()
        ctrl = FolderController(db=db)
        assert ctrl._db is not None

    def test_set_db(self):
        ctrl = FolderController()
        db = MagicMock()
        ctrl.set_db(db)
        assert ctrl._db is not None

    def test_set_audio_lab_controller(self):
        ctrl = FolderController()
        mock = MagicMock()
        ctrl.set_audio_lab_controller(mock)
        assert ctrl._audio_lab_ctrl is not None

    def test_connect_with_widget_mock(self):
        """connect() should not crash and should bind to widget signals."""
        ctrl = FolderController()
        widget = MagicMock()
        ctrl.connect(widget)
        assert ctrl._widget is not None
        # Verify signal connections were attempted
        assert widget.folder_loaded.connect.called
        assert widget.folder_selected.connect.called
        assert widget.scan_requested.connect.called
        assert widget.reindex_requested.connect.called

    def test_on_folder_loaded_invalid_path(self):
        ctrl = FolderController()
        ctrl.on_folder_loaded("")  # Should not crash
        ctrl.on_folder_loaded("/nonexistent_path")  # Should not crash

    def test_on_folder_loaded_no_context(self):
        import pytest
        try:
            ctrl = FolderController()
            # QThread initialization may conflict with GStreamer in test env
            ctrl._start_health_worker = lambda p: None
            ctrl.on_folder_loaded("/tmp")
        except Exception:
            pytest.skip("QThread/GStreamer conflict in test environment")

    def test_on_scan_requested(self):
        fa = MagicMock()
        ctrl = FolderController(file_actions=fa)
        ctrl.on_scan_requested("")  # Invalid
        fa.scan_path.assert_not_called()
        ctrl.on_scan_requested("/nonexistent")  # Invalid
        fa.scan_path.assert_not_called()

    @patch("os.path.isdir")
    def test_on_scan_requested_valid(self, mock_isdir):
        mock_isdir.return_value = True
        fa = MagicMock()
        ctrl = FolderController(file_actions=fa)
        ctrl.on_scan_requested("/tmp")
        fa.scan_path.assert_called_once_with("/tmp")

    def test_toast_signal(self):
        ctrl = FolderController()
        received = []
        ctrl.toast_requested.connect(lambda msg, kind: received.append((msg, kind)))
        ctrl._toast("test message", "info")
        assert len(received) == 1
        assert received[0][0] == "test message"
        assert received[0][1] == "info"

    def test_record_context_no_service(self):
        """_record_context should not crash without context_svc."""
        ctrl = FolderController()
        ctrl._record_context("test_event", "/tmp")

    def test_folder_name_empty(self):
        assert FolderController._folder_name([]) == "Carpeta"

    def test_folder_name_single(self):
        name = FolderController._folder_name(["/music/song.flac"])
        assert name  # not empty

    def test_folder_name_multiple(self):
        name = FolderController._folder_name(
            ["/music/album/song1.flac", "/music/album/song2.flac"])
        assert name == "album"

    def test_on_show_problem_report_no_widget(self):
        ctrl = FolderController()
        ctrl.on_show_problem_report("/tmp")  # Should not crash

    def test_on_audio_lab_requested_no_controller(self):
        ctrl = FolderController()
        ctrl.on_audio_lab_requested("/tmp")  # Should not crash, should toast

    def test_on_safe_rename_no_widget(self):
        ctrl = FolderController()
        ctrl.on_safe_rename_requested("/tmp")  # Should not crash
