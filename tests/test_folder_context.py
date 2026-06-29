"""Tests: folder context events — FOLDER_SELECTED, FOLDER_QUEUED, FOLDER_SCANNED."""

from unittest.mock import MagicMock
from core.context.context_events import AppEvent


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
        called = any(
            c[0][0] == AppEvent.FOLDER_SELECTED
            for c in ctx_svc.record_event.call_args_list
        )
        assert called

    def test_on_folder_queued_emits_event(self):
        ctx_svc = MagicMock()
        win = MagicMock()
        win._context_svc = ctx_svc

        from ui.window import MainWindow
        MainWindow._on_folder_queued(win, ["/music/a.flac"])
        called = any(
            c[0][0] == AppEvent.FOLDER_QUEUED
            for c in ctx_svc.record_event.call_args_list
        )
        assert called

    def test_on_folder_scan_requested_emits_event(self):
        ctx_svc = MagicMock()
        win = MagicMock()
        win._context_svc = ctx_svc

        from ui.window import MainWindow
        MainWindow._on_folder_scan_requested(win, "/home/user/Music")
        called = any(
            c[0][0] == AppEvent.FOLDER_SCANNED
            for c in ctx_svc.record_event.call_args_list
        )
        assert called

    def test_no_full_path_in_event(self):
        ctx_svc = MagicMock()
        win = MagicMock()
        win._context_svc = ctx_svc

        from ui.window import MainWindow
        MainWindow._on_folder_scan_requested(win, "/home/user/Music/Rock")
        for call in ctx_svc.record_event.call_args_list:
            payload = call[0][1]
            if payload and payload.get("folder_name"):
                assert "/" not in payload["folder_name"]
