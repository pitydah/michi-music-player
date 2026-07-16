"""Tests for Micro Server import cancel — rollback behavior."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


def _make_ctx():
    ctx = MagicMock()
    ctx.micro_server = MagicMock()
    return ctx


def _make_tracks(n=2):
    return [MagicMock(album="Test", filepath=f"/m/{i}.flac") for i in range(n)]


class TestMicroServerCancelRollback:

    def test_cancel_after_session_calls_rollback(self):
        from legacy_widgets.ui.controllers.legacy_controllers.album_controller import AlbumController

        w = MagicMock()
        w._workers = MagicMock()
        w._workers.run_task = MagicMock()

        ctrl = AlbumController(w)
        ctrl._ctx = _make_ctx()
        ctrl._toast = MagicMock()

        tracks = _make_tracks()
        svc_mock = MagicMock()
        svc_mock.create_session.return_value.ok = True
        svc_mock.create_session.return_value.data = {
            "session_id": "sid-123",
            "existing": 0,
            "needs_upload": 2,
        }

        dlg_mock = MagicMock()
        dlg_mock.exec.return_value = True
        dlg_mock.was_confirmed.return_value = False

        with patch(
            "integrations.michi_link.services.import_to_server_service.ImportToServerService",
            return_value=svc_mock,
        ), patch(
            "ui.dialogs.album_server_import_dialog.AlbumServerImportDialog",
            return_value=dlg_mock,
        ):
            ctrl.send_album_to_server(tracks)

        svc_mock.rollback.assert_called_once_with("sid-123")

    def test_cancel_without_session_does_not_call_rollback(self):
        from legacy_widgets.ui.controllers.legacy_controllers.album_controller import AlbumController

        w = MagicMock()
        w._workers = MagicMock()
        w._workers.run_task = MagicMock()

        ctrl = AlbumController(w)
        ctrl._ctx = _make_ctx()
        ctrl._toast = MagicMock()

        tracks = _make_tracks()
        svc_mock = MagicMock()
        svc_mock.create_session.return_value.ok = True
        svc_mock.create_session.return_value.data = {
            "session_id": "",
            "existing": 0,
            "needs_upload": 2,
        }

        dlg_mock = MagicMock()
        dlg_mock.exec.return_value = True
        dlg_mock.was_confirmed.return_value = False

        with patch(
            "integrations.michi_link.services.import_to_server_service.ImportToServerService",
            return_value=svc_mock,
        ), patch(
            "ui.dialogs.album_server_import_dialog.AlbumServerImportDialog",
            return_value=dlg_mock,
        ):
            ctrl.send_album_to_server(tracks)

        svc_mock.rollback.assert_not_called()

    def test_cancel_rollback_exception_is_suppressed(self):
        from legacy_widgets.ui.controllers.legacy_controllers.album_controller import AlbumController

        w = MagicMock()
        w._workers = MagicMock()

        ctrl = AlbumController(w)
        ctrl._ctx = _make_ctx()
        ctrl._toast = MagicMock()

        tracks = _make_tracks()
        svc_mock = MagicMock()
        svc_mock.create_session.return_value.ok = True
        svc_mock.create_session.return_value.data = {
            "session_id": "sid-err",
            "existing": 0,
            "needs_upload": 2,
        }
        svc_mock.rollback.side_effect = RuntimeError("server error")

        dlg_mock = MagicMock()
        dlg_mock.exec.return_value = True
        dlg_mock.was_confirmed.return_value = False

        with patch(
            "integrations.michi_link.services.import_to_server_service.ImportToServerService",
            return_value=svc_mock,
        ), patch(
            "ui.dialogs.album_server_import_dialog.AlbumServerImportDialog",
            return_value=dlg_mock,
        ):
            ctrl.send_album_to_server(tracks)

        svc_mock.rollback.assert_called_once_with("sid-err")

    def test_confirm_starts_worker_and_does_not_rollback(self):
        from legacy_widgets.ui.controllers.legacy_controllers.album_controller import AlbumController

        w = MagicMock()
        w._workers = MagicMock()
        w._workers.run_task = MagicMock()

        ctrl = AlbumController(w)
        ctrl._ctx = _make_ctx()
        ctrl._toast = MagicMock()

        tracks = _make_tracks()
        svc_mock = MagicMock()
        svc_mock.create_session.return_value.ok = True
        svc_mock.create_session.return_value.data = {
            "session_id": "sid-456",
            "existing": 0,
            "needs_upload": 2,
        }

        dlg_mock = MagicMock()
        dlg_mock.exec.return_value = True
        dlg_mock.was_confirmed.return_value = True

        with patch(
            "integrations.michi_link.services.import_to_server_service.ImportToServerService",
            return_value=svc_mock,
        ), patch(
            "ui.dialogs.album_server_import_dialog.AlbumServerImportDialog",
            return_value=dlg_mock,
        ), patch(
            "integrations.michi_link.services.album_import_worker.AlbumImportWorker",
            return_value=MagicMock(),
        ):
            ctrl.send_album_to_server(tracks)

        svc_mock.rollback.assert_not_called()
        assert ctrl._active_album_import_worker is not None

    def test_create_session_failure_shows_error(self):
        from legacy_widgets.ui.controllers.legacy_controllers.album_controller import AlbumController

        w = MagicMock()
        w._workers = MagicMock()

        ctrl = AlbumController(w)
        ctrl._ctx = _make_ctx()
        ctrl._toast = MagicMock()

        tracks = _make_tracks()
        svc_mock = MagicMock()
        svc_mock.create_session.return_value.ok = False
        svc_mock.create_session.return_value.message = "server unreachable"

        with patch(
            "integrations.michi_link.services.import_to_server_service.ImportToServerService",
            return_value=svc_mock,
        ):
            ctrl.send_album_to_server(tracks)

        svc_mock.rollback.assert_not_called()
        ctrl._toast.assert_called()
