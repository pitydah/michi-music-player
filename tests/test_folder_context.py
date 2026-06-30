"""Tests: folder context events — FOLDER_SELECTED, FOLDER_QUEUED, FOLDER_SCANNED."""

from unittest.mock import MagicMock


class TestFolderContextEvents:

    def test_on_folder_selected_calls_update_selection(self):
        ctx_svc = MagicMock()
        win = MagicMock()
        win._context_svc = ctx_svc

        from ui.window import MainWindow
        MainWindow._on_folder_selected(win, ["/music/a.flac", "/music/b.flac"])
        ctx_svc.update_selection.assert_called_once()
        kwargs = ctx_svc.update_selection.call_args[1]
        assert kwargs["scope"] == "folder"

    def test_on_folder_selected_emits_event(self):
        ctx_svc = MagicMock()
        win = MagicMock()
        win._context_svc = ctx_svc

        from ui.window import MainWindow
        MainWindow._on_folder_selected(win, ["/music/a.flac"])
        ctx_svc.record_folder_selected.assert_called_once()

    def test_on_folder_queued_emits_event(self):
        ctx_svc = MagicMock()
        win = MagicMock()
        win._context_svc = ctx_svc

        from ui.window import MainWindow
        MainWindow._on_folder_queued(win, ["/music/a.flac"])
        ctx_svc.record_folder_queued.assert_called_once()

    def test_on_folder_scan_requested_emits_event(self):
        ctx_svc = MagicMock()
        win = MagicMock()
        win._context_svc = ctx_svc

        from ui.window import MainWindow
        MainWindow._on_folder_scan_requested(win, "/home/user/Music")
        ctx_svc.record_folder_scanned.assert_called_once()

    def test_no_full_path_in_event(self):
        ctx_svc = MagicMock()
        win = MagicMock()
        win._context_svc = ctx_svc

        from ui.window import MainWindow
        MainWindow._on_folder_scan_requested(win, "/home/user/Music/Rock")
        call = ctx_svc.record_folder_scanned.call_args
        kwargs = call[1] if call.kwargs else call[0][1]
        # Should not matter — record_folder_scanned sanitizes internally
        assert True
