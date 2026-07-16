"""Tests for SongsController.send_to_micro_server."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestSongsMicroServerImport:

    def test_send_no_server_shows_toast(self):
        from legacy_widgets.ui.controllers.legacy_controllers.songs_controller import SongsController
        svc = MagicMock()
        svc.micro_server = None
        ctrl = SongsController(svc)
        ctrl.send_to_micro_server([MagicMock(filepath="/s.flac")])
        svc.toast.show.assert_called()

    def test_send_no_files_shows_toast(self):
        from legacy_widgets.ui.controllers.legacy_controllers.songs_controller import SongsController
        svc = MagicMock()
        svc.micro_server = MagicMock()
        ctrl = SongsController(svc)
        ctrl.send_to_micro_server([MagicMock(filepath="")])
        svc.toast.show.assert_called()

    def test_send_session_failure_shows_toast(self):
        from legacy_widgets.ui.controllers.legacy_controllers.songs_controller import SongsController
        svc = MagicMock()
        svc.micro_server = MagicMock()
        svc.toast = MagicMock()
        ctrl = SongsController(svc)

        with patch(
            "integrations.michi_link.services.import_to_server_service.ImportToServerService"
        ) as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.create_session.return_value.ok = False
            mock_svc.create_session.return_value.message = "fail"
            mock_svc_cls.return_value = mock_svc
            ctrl.send_to_micro_server([MagicMock(filepath="/s.flac")])

        svc.toast.show.assert_called()

    def test_cancel_after_session_calls_rollback(self):
        from legacy_widgets.ui.controllers.legacy_controllers.songs_controller import SongsController
        svc = MagicMock()
        svc.micro_server = MagicMock()
        svc.toast = MagicMock()
        svc.workers = MagicMock()
        ctrl = SongsController(svc)

        mock_import_svc = MagicMock()
        mock_import_svc.create_session.return_value.ok = True
        mock_import_svc.create_session.return_value.data = {
            "session_id": "sid-1", "existing": 0, "needs_upload": 1,
        }

        dlg_mock = MagicMock()
        dlg_mock.exec.return_value = True
        dlg_mock.was_confirmed.return_value = False

        with patch(
            "integrations.michi_link.services.import_to_server_service.ImportToServerService",
            return_value=mock_import_svc,
        ), patch(
            "ui.dialogs.album_server_import_dialog.AlbumServerImportDialog",
            return_value=dlg_mock,
        ):
            ctrl.send_to_micro_server([MagicMock(filepath="/s.flac")])

        mock_import_svc.rollback.assert_called_once_with("sid-1")

    def test_confirm_starts_worker(self):
        from legacy_widgets.ui.controllers.legacy_controllers.songs_controller import SongsController
        svc = MagicMock()
        svc.micro_server = MagicMock()
        svc.toast = MagicMock()
        svc.workers = MagicMock()
        ctrl = SongsController(svc)

        mock_import_svc = MagicMock()
        mock_import_svc.create_session.return_value.ok = True
        mock_import_svc.create_session.return_value.data = {
            "session_id": "sid-2", "existing": 0, "needs_upload": 1,
        }

        dlg_mock = MagicMock()
        dlg_mock.exec.return_value = True
        dlg_mock.was_confirmed.return_value = True

        with patch(
            "integrations.michi_link.services.import_to_server_service.ImportToServerService",
            return_value=mock_import_svc,
        ), patch(
            "ui.dialogs.album_server_import_dialog.AlbumServerImportDialog",
            return_value=dlg_mock,
        ), patch(
            "integrations.michi_link.services.album_import_worker.AlbumImportWorker",
            return_value=MagicMock(),
        ):
            ctrl.send_to_micro_server([MagicMock(filepath="/s.flac")])

        assert ctrl._active_import_worker is not None
