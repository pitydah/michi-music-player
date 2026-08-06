"""Notification undo must run a REAL compensation (metadata apply reverted via
UndoService), and undoing must work even after the notification was deleted —
deleting the notification is NOT the undo.
"""
from __future__ import annotations

import numpy as np
import pytest


@pytest.fixture
def env(tmp_path):
    from core.confirmation_service import ConfirmationService
    from core.event_bus import EventBus
    from core.library_mutation_service import LibraryMutationService
    from core.metadata_editor_service import MetadataEditorService
    from core.notification_action_service import NotificationActionService
    from core.notification_service import NotificationService
    from core.undo_service import UndoService
    from library.library_db import LibraryDB

    import soundfile as sf

    db = LibraryDB(str(tmp_path / "lib.db"))
    music = tmp_path / "music"
    fp = music / "track.flac"
    music.mkdir(parents=True)
    sf.write(fp, np.zeros(64, dtype=np.float32), 8000, format="FLAC")
    from mutagen.flac import FLAC

    audio = FLAC(str(fp))
    audio["title"] = "Original Title"
    audio["artist"] = "Artist"
    audio.save()
    db.conn.execute(
        "INSERT INTO media_items "
        "(filepath, filename, directory, ext, kind, size, mtime, "
        "title, artist, album, genre) "
        "VALUES (?, ?, ?, ?, 'audio', 100, 1000, 'Original Title', "
        "'Artist', 'Album', 'Rock')",
        (str(fp), "track.flac", str(music), ".flac"),
    )
    db.conn.commit()

    eb = EventBus()
    undo = UndoService(event_bus=eb)
    editor = MetadataEditorService(
        db=db,
        mutation_service=LibraryMutationService(db=db, event_bus=eb),
        event_bus=eb,
        confirmation_service=ConfirmationService(),
        undo_service=undo,
    )
    ns = NotificationService(persistence_path=str(tmp_path / "notif.json"))
    action_svc = NotificationActionService(undo_service=undo)
    return db, fp, editor, ns, action_svc


class TestNotificationUndoRealMutation:
    def _apply_metadata(self, editor, fp):
        proposal = editor.build_proposal(
            [{"filepath": str(fp)}], {"title": "Changed Title"})
        token = editor.confirm(proposal["proposal_id"])["confirmation_token"]
        assert editor.approve(token)["ok"] is True
        result = editor.apply_batch(
            [{"proposal_id": proposal["proposal_id"],
              "confirmation_token": token}])
        assert result["status"] == "COMPLETED", result
        return result["operation_id"]

    def test_undo_action_reverts_real_mutation(self, env):
        db, fp, editor, ns, action_svc = env
        operation_id = self._apply_metadata(editor, fp)

        from core.notification_service import (
            Notification, NotificationType,
        )

        ns.notify(Notification(
            type=NotificationType.INFO, title="Metadatos editados",
            message="Cambio aplicado", actions=["undo"],
            persistent=True, entity=str(fp),
        ))
        notif = ns.list_persistent()[0]
        assert notif.actions == ["undo"]

        result = action_svc.route("undo", {"operation_id": operation_id})
        assert result["ok"] is True, result
        assert result["status"] == "UNDONE"

        row = db.conn.execute(
            "SELECT title FROM media_items WHERE filepath=?",
            (str(fp),),
        ).fetchone()
        assert row[0] == "Original Title"
        from mutagen.flac import FLAC

        audio = FLAC(str(fp))
        assert audio["title"][0] == "Original Title"

    def test_undo_works_after_notification_deleted(self, env):
        db, fp, editor, ns, action_svc = env
        operation_id = self._apply_metadata(editor, fp)

        from core.notification_service import Notification, NotificationType

        notif = ns.notify(Notification(
            type=NotificationType.INFO, title="Edición", message="",
            actions=["undo"], persistent=True,
        ))
        assert ns.dismiss(notif.id) is True
        assert ns.list_persistent() == []

        result = action_svc.route("undo", {"operation_id": operation_id})
        assert result["ok"] is True, "deleting the notification is not the undo"
        row = db.conn.execute(
            "SELECT title FROM media_items WHERE filepath=?",
            (str(fp),),
        ).fetchone()
        assert row[0] == "Original Title"

    def test_undo_unknown_operation_is_target_unavailable(self, env):
        _db, _fp, _editor, _ns, action_svc = env
        result = action_svc.route("undo", {"operation_id": "nope"})
        assert result["ok"] is False
        assert result["status"] == "UNDO_NOT_FOUND"

    def test_persistent_notification_survives_restart(self, env, tmp_path):
        _db, _fp, editor, ns, action_svc = env
        from core.notification_service import (
            Notification, NotificationService, NotificationType,
        )

        ns.notify(Notification(
            type=NotificationType.WARNING, title="Alerta persistente",
            message="mensaje", persistent=True,
        ))
        assert len(ns.list_persistent()) == 1

        reloaded = NotificationService(
            persistence_path=ns._persistence_path)
        assert len(reloaded.list_persistent()) == 1
        assert reloaded.list_persistent()[0].title == "Alerta persistente"

        reloaded.dismiss(reloaded.list_persistent()[0].id)
        after = NotificationService(persistence_path=ns._persistence_path)
        assert after.list_persistent() == []
