"""Vertical metadata pipeline: proposal -> preview -> confirm -> apply_batch
(DB + physical tags) -> readback -> undo, with real files and a real DB.

Uses REAL implementations: LibraryDB (tmp), the mutagen tag writer/reader
(FLAC fixtures generated with soundfile), LibraryMutationService,
ConfirmationService, UndoService and EventBus. No MagicMock of services.
"""
from __future__ import annotations

import os

import numpy as np
import pytest


def _make_flac(path, title: str, artist: str, album: str, genre: str):
    import soundfile as sf

    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, np.zeros(64, dtype=np.float32), 8000, format="FLAC")
    from mutagen.flac import FLAC

    audio = FLAC(str(path))
    audio["title"] = title
    audio["artist"] = artist
    audio["album"] = album
    audio["genre"] = genre
    audio.save()
    return str(path)


@pytest.fixture
def library(tmp_path):
    from library.library_db import LibraryDB

    db = LibraryDB(str(tmp_path / "library.db"))
    music = tmp_path / "music"
    tracks = []
    for i in range(3):
        fp = _make_flac(music / f"Artist{i}" / "Album" / f"track{i}.flac",
                        f"Old Title {i}", f"Artist {i}", "Album", "Rock")
        db.conn.execute(
            "INSERT INTO media_items "
            "(filepath, filename, directory, ext, kind, size, mtime, "
            "title, artist, album, year, genre, track_number, album_key) "
            "VALUES (?, ?, ?, ?, 'audio', 100, 1000, ?, ?, ?, 2020, ?, ?, ?)",
            (fp, os.path.basename(fp), os.path.dirname(fp), ".flac",
             f"Old Title {i}", f"Artist {i}", "Album", "Rock", i,
             f"album:{i}"),
        )
        tracks.append(fp)
    db.conn.commit()
    return db, tracks, music


@pytest.fixture
def editor(library):
    from core.confirmation_service import ConfirmationService
    from core.event_bus import EventBus
    from core.library_mutation_service import LibraryMutationService
    from core.metadata_editor_service import MetadataEditorService
    from core.undo_service import UndoService

    db, _tracks, _music = library
    eb = EventBus()
    events = []
    eb.on("metadata.batch.applied",
          lambda data: events.append(("batch.applied", data)))
    eb.on("undo.executed",
          lambda data: events.append(("undo.executed", data)))
    return (
        MetadataEditorService(
            db=db,
            mutation_service=LibraryMutationService(db=db, event_bus=eb),
            event_bus=eb,
            confirmation_service=ConfirmationService(),
            undo_service=UndoService(event_bus=eb),
        ),
        events,
    )


class TestMetadataApplyAndUndoVertical:
    def test_full_pipeline_writes_db_and_physical_tags_then_undo(self, library,
                                                                 editor):
        db, tracks, _music = library
        svc, events = editor

        proposal = svc.build_proposal(
            [{"filepath": fp} for fp in tracks], {"title": "New Title"})
        assert proposal["ok"] is True
        proposal_id = proposal["proposal_id"]

        preview = svc.preview_proposal(proposal_id)
        assert preview["ok"] is True
        assert preview["count"] == 3
        assert all(c["old_value"].startswith("Old Title")
                   for c in preview["changes"])

        conf = svc.confirm(proposal_id, selected_fields=["title"])
        assert conf["requires_confirmation"] is True
        token = conf["confirmation_token"]
        assert svc.approve(token)["ok"] is True

        result = svc.apply_batch(
            [{"proposal_id": proposal_id, "confirmation_token": token}])
        assert result["status"] == "COMPLETED", result
        assert result["applied"] == 3
        assert result["failed"] == 0
        assert result["conflicts"] == 0
        assert result["ok"] is True
        operation_id = result["operation_id"]
        assert operation_id

        readback = svc.readback(proposal_id)
        assert len(readback["results"]) == 3
        for entry in readback["results"]:
            assert entry["db"]["title"] == "New Title"
            from mutagen.flac import FLAC

            audio = FLAC(entry["filepath"])
            assert audio["title"][0] == "New Title"

        undo = svc.undo(operation_id)
        assert undo["ok"] is True, undo
        assert undo["status"] == "UNDONE"

        after = svc.readback(proposal_id)
        for i, entry in enumerate(after["results"]):
            assert entry["db"]["title"] == f"Old Title {i}"
            from mutagen.flac import FLAC

            audio = FLAC(entry["filepath"])
            assert audio["title"][0] == f"Old Title {i}"

        event_names = [name for name, _data in events]
        assert "batch.applied" in event_names
        assert "undo.executed" in event_names

    def test_conflict_track_yields_partial_success(self, library, editor):
        db, tracks, _music = library
        svc, _events = editor

        ghost = str(_music / "Ghost" / "ghost.flac")
        db.conn.execute(
            "INSERT INTO media_items "
            "(filepath, filename, directory, ext, kind, size, mtime, "
            "title, artist, album, genre) "
            "VALUES (?, 'ghost.flac', ?, '.flac', 'audio', 100, 1000, "
            "'Ghost', 'Ghost', 'Ghost', 'Rock')",
            (ghost, str(_music / "Ghost")),
        )
        db.conn.commit()

        proposal = svc.build_proposal(
            [{"filepath": fp} for fp in tracks + [ghost]],
            {"title": "Batch Title"})
        conf = svc.confirm(proposal["proposal_id"])
        token = conf["confirmation_token"]
        assert svc.approve(token)["ok"] is True

        result = svc.apply_batch(
            [{"proposal_id": proposal["proposal_id"],
              "confirmation_token": token}])
        assert result["status"] == "PARTIAL_SUCCESS", result
        assert result["applied"] == 3
        assert result["conflicts"] == 1
        assert result["ok"] is False
        conflict = [t for t in result["per_track"]
                    if t["status"] == "conflict"]
        assert conflict and conflict[0]["error"] == "FILE_NOT_FOUND"

    def test_missing_confirmation_is_never_applied(self, library, editor):
        db, tracks, _music = library
        svc, _events = editor

        proposal = svc.build_proposal(
            [{"filepath": fp} for fp in tracks], {"title": "Nope"})
        result = svc.apply_batch(
            [{"proposal_id": proposal["proposal_id"]}])
        assert result["missing_confirmations"] == 3
        assert result["applied"] == 0
        assert result["ok"] is False
        for fp in tracks:
            row = db.conn.execute(
                "SELECT title FROM media_items WHERE filepath=?", (fp,)
            ).fetchone()
            assert row[0].startswith("Old Title")

    def test_token_belongs_to_one_proposal(self, library, editor):
        """An approved token cannot authorize a different proposal."""
        db, tracks, _music = library
        svc, _events = editor

        proposal_a = svc.build_proposal(
            [{"filepath": fp} for fp in tracks], {"title": "Once"})
        token = svc.confirm(proposal_a["proposal_id"])["confirmation_token"]
        assert svc.approve(token)["ok"] is True

        proposal_b = svc.build_proposal(
            [{"filepath": fp} for fp in tracks], {"title": "Twice"})
        result = svc.apply_batch(
            [{"proposal_id": proposal_b["proposal_id"],
              "confirmation_token": token}])
        assert result["missing_confirmations"] == 3
        assert result["applied"] == 0
        assert result["ok"] is False
        for fp in tracks:
            row = db.conn.execute(
                "SELECT title FROM media_items WHERE filepath=?", (fp,)
            ).fetchone()
            assert row[0].startswith("Old Title")
