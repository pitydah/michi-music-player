"""Library doctor real repair flow: scan -> preview -> confirm -> repair ->
readback -> undo, plus the genre fragmentation path via GenreCleanupService.

Real implementations: LibraryDB (tmp), LibraryDoctorScanRepository,
LibraryMutationService, ConfirmationService, UndoService, GenreCleanupService
+ GenreRepository. No MagicMock of services.
"""
from __future__ import annotations

import os

import pytest


@pytest.fixture
def doctor(tmp_path):
    from core.confirmation_service import ConfirmationService
    from core.library_doctor.repositories.scan_repository import (
        LibraryDoctorScanRepository,
    )
    from core.library_doctor_service import LibraryDoctorService
    from core.library_mutation_service import LibraryMutationService
    from core.undo_service import UndoService
    from library.genre_repository import GenreRepository
    from core.genre.genre_cleanup_service import GenreCleanupService
    from library.library_db import LibraryDB

    db = LibraryDB(str(tmp_path / "doctor.db"))
    scan_repo = LibraryDoctorScanRepository(db)
    mutation = LibraryMutationService(db=db)
    confirmation = ConfirmationService()
    undo = UndoService()
    genre_cleanup = GenreCleanupService(
        db=db, genre_repo=GenreRepository(db.conn))
    svc = LibraryDoctorService(
        db=db,
        scan_repository=scan_repo,
        mutation_service=mutation,
        confirmation_service=confirmation,
        undo_service=undo,
        genre_cleanup=genre_cleanup,
    )
    yield svc, db, confirmation, undo
    db.conn.close()


def _insert_track(db, filepath: str, title: str, artist: str = "Artist",
                  genre: str = "Rock"):
    db.conn.execute(
        "INSERT INTO media_items "
        "(filepath, filename, directory, ext, kind, size, mtime, "
        "title, artist, album, genre) "
        "VALUES (?, ?, ?, ?, 'audio', 100, 1000, ?, ?, 'Album', ?)",
        (filepath, os.path.basename(filepath), os.path.dirname(filepath),
         os.path.splitext(filepath)[1], title, artist, genre),
    )
    db.conn.commit()
    row = db.conn.execute(
        "SELECT id FROM media_items WHERE filepath=?", (filepath,)
    ).fetchone()
    return row[0]


class TestLibraryDoctorPreviewRepairUndo:
    def test_missing_file_scan_preview_repair_readback_undo(self, doctor):
        svc, db, confirmation, _undo = doctor
        ghost = "/nonexistent/music/ghost.flac"
        track_id = _insert_track(db, ghost, "Ghost Track", "Ghost Artist")

        scan = svc.scan()
        assert scan["ok"] is True
        missing = [i for i in scan["issues"]
                   if i["type"] == "missing_file"
                   and i["details"].get("track_id") == track_id]
        assert missing, "scan must find the missing-file issue"
        issue = missing[0]

        preview = svc.preview_repair(issue)
        assert preview["ok"] is True
        assert preview["changes"][0]["action"] == "soft_delete_track"

        first = svc.repair(issue)
        assert first["code"] == "CONFIRMATION_REQUIRED"
        token = first["confirmation_token"]
        assert confirmation.approve(token) is not None

        result = svc.repair(issue, confirmation_token=token)
        assert result["ok"] is True, result
        assert result["status"] == "COMPLETED"
        assert result["readback_verified"] is True
        row = db.conn.execute(
            "SELECT deleted_at FROM media_items WHERE id=?",
            (track_id,),
        ).fetchone()
        assert row[0] is not None, "repair must soft-delete the track"

        rollback = svc.rollback(issue)
        assert rollback["ok"] is True, rollback
        row = db.conn.execute(
            "SELECT deleted_at FROM media_items WHERE id=?",
            (track_id,),
        ).fetchone()
        assert row[0] is None, "rollback must restore the track"

    def test_no_handler_issue_reports_honestly(self, doctor):
        svc, _db, _confirmation, _undo = doctor
        result = svc.repair({"type": "totally_unknown_issue", "id": 1})
        assert result["ok"] is False
        assert result["code"] == "NO_REPAIR_HANDLER"

    def test_real_handlers_registered(self, doctor):
        svc, _db, _confirmation, _undo = doctor
        assert "missing_file" in svc.handler_ids
        assert "orphan_playlist_item" in svc.handler_ids
        assert "orphan_history" in svc.handler_ids
        assert "duplicate_path" in svc.handler_ids
        assert "duplicate_uid" in svc.handler_ids
        assert "missing_metadata" in svc.handler_ids
        assert "genre_fragmentation" in svc.handler_ids
        health = svc.health()
        assert health["handlers"] == 7

    def test_orphan_playlist_item_repair_and_undo(self, doctor):
        svc, db, confirmation, _undo = doctor

        db.conn.execute(
            "CREATE TABLE IF NOT EXISTS playlists "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)")
        db.conn.execute("INSERT INTO playlists (name) VALUES ('Mix')")
        db.conn.execute(
            "INSERT INTO playlist_items (playlist_id, filepath, position) "
            "VALUES (1, '/gone/track.flac', 0)")
        db.conn.commit()
        rowid = db.conn.execute(
            "SELECT rowid FROM playlist_items LIMIT 1").fetchone()[0]

        scan = svc.scan()
        issue = [i for i in scan["issues"]
                 if i["type"] == "orphan_playlist_item"
                 and i["details"].get("rowid") == rowid][0]
        token = svc.repair(issue)["confirmation_token"]
        assert confirmation.approve(token) is not None
        result = svc.repair(issue, confirmation_token=token)
        assert result["ok"] is True, result
        assert svc.rollback(issue)["ok"] is True
        row = db.conn.execute(
            "SELECT COUNT(*) FROM playlist_items WHERE rowid=?",
            (rowid,),
        ).fetchone()
        assert row[0] == 1, "undo must restore the playlist item"


class TestDoctorGenreFragmentation:
    def _seed_fragmented_genres(self, db):
        t1 = _insert_track(db, "/music/one.flac", "One", genre="Rock")
        t2 = _insert_track(db, "/music/two.flac", "Two", genre="rock")
        from library.genre_repository import GenreRepository

        repo = GenreRepository(db.conn)
        repo.ensure_track_genre(t1, "Rock", canonical="Rock")
        repo.ensure_track_genre(t2, "rock", canonical="Rock")
        return t1, t2

    def test_genre_fragmentation_preview_apply_undo(self, doctor):
        svc, db, confirmation, _undo = doctor
        t1, t2 = self._seed_fragmented_genres(db)

        scan = svc.scan()
        issue = next((i for i in scan["issues"]
                      if i["type"] == "genre_fragmentation"), None)
        assert issue is not None, "scan must detect fragmented genres"
        assert set(issue["details"]["raw_values"]) == {"Rock", "rock"}

        preview = svc.preview_repair(issue)
        assert preview["ok"] is True
        assert preview["changes"][0]["action"] == "merge_genres"

        token = svc.repair(issue)["confirmation_token"]
        assert confirmation.approve(token) is not None
        result = svc.repair(issue, confirmation_token=token)
        assert result["ok"] is True, result
        assert result["applied"] >= 2

        leftover_tracks = db.conn.execute(
            "SELECT COUNT(*) FROM media_items WHERE genre='rock'"
        ).fetchone()[0]
        assert leftover_tracks == 0, "readback: no fragmented media genre may remain"
        leftover_genres = db.conn.execute(
            "SELECT COUNT(*) FROM track_genres WHERE genre='rock'"
        ).fetchone()[0]
        assert leftover_genres == 0

        assert svc.rollback(issue)["ok"] is True
        restored = db.conn.execute(
            "SELECT COUNT(*) FROM media_items WHERE genre IN ('Rock','rock')"
        ).fetchone()[0]
        assert restored == 2, "undo must restore the original genres"
