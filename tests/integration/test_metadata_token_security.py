"""P0 Fase Metadata — token security for the canonical editing pipeline.

Verifies the ConfirmationService token contract end to end with REAL
implementations: LibraryDB (tmp), real FLAC fixtures (soundfile), mutagen
tag reader/writer, LibraryMutationService, ConfirmationService, UndoService
(persisted) and the MetadataEditorService pipeline. No MagicMock of services
except where the test explicitly simulates divergence (readback failures).

Contract under test (P0): destructive/sensitive metadata operations ONLY
execute with a verifiable token issued by ConfirmationService. Self-declared
``confirmed=True`` + ``source=`` intents are rejected with TOKEN_REQUIRED.
"""
from __future__ import annotations

import os
import time

import numpy as np
import pytest

from core.confirmation_service import (
    TOKEN_COMMAND_MISMATCH,
    TOKEN_EXPIRED,
    TOKEN_FIELD_MISMATCH,
    TOKEN_REQUIRED,
    TOKEN_TARGET_MISMATCH,
)


def _make_flac(path, title: str, artist: str = "Artist",
               album: str = "Album", year: int = 2020, genre: str = "Rock"):
    sf = pytest.importorskip(
        "soundfile",
        reason="audio-analysis extra required to build FLAC fixtures",
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, np.zeros(64, dtype=np.float32), 8000, format="FLAC")
    from mutagen.flac import FLAC

    audio = FLAC(str(path))
    audio["title"] = title
    audio["artist"] = artist
    audio["album"] = album
    audio["date"] = str(year)
    audio["genre"] = genre
    audio.save()
    return str(path)


def _insert_track(db, fp: str, title: str, artist: str = "Artist",
                  album: str = "Album", year: int = 2020):
    db.conn.execute(
        "INSERT INTO media_items "
        "(filepath, filename, directory, ext, kind, size, mtime, "
        "title, artist, album, year, genre, track_number, album_key) "
        "VALUES (?, ?, ?, ?, 'audio', 100, 1000, ?, ?, ?, ?, 'Rock', 1, 'alb:1')",
        (fp, os.path.basename(fp), os.path.dirname(fp),
         os.path.splitext(fp)[1], title, artist, album, year),
    )
    db.conn.commit()
    return db.conn.execute(
        "SELECT id FROM media_items WHERE filepath=?", (fp,)).fetchone()[0]


@pytest.fixture
def env(tmp_path):
    """Real editor: LibraryDB + mutation service + ConfirmationService +
    persisted UndoService + EventBus."""
    from core.confirmation_service import ConfirmationService
    from core.event_bus import EventBus
    from core.library_mutation_service import LibraryMutationService
    from core.metadata_editor_service import MetadataEditorService
    from core.undo_service import UndoService
    from library.library_db import LibraryDB

    db = LibraryDB(str(tmp_path / "lib.db"))
    eb = EventBus()
    mutation = LibraryMutationService(db=db, event_bus=eb)
    cs = ConfirmationService()
    undo = UndoService(
        persistence_path=str(tmp_path / "undo.jsonl"),
        event_bus=eb, db=db, mutation_service=mutation)
    editor = MetadataEditorService(
        db=db,
        mutation_service=mutation,
        event_bus=eb,
        confirmation_service=cs,
        undo_service=undo,
    )
    return db, editor, cs, undo, mutation, tmp_path


def _confirm_apply(editor, proposal_id: str, token: str) -> dict:
    assert editor.approve(token)["ok"] is True
    return editor.apply_batch([{
        "proposal_id": proposal_id,
        "confirmation_token": token,
    }])


class TestTokenAuthorization:
    def test_confirmed_true_bypass_rejected(self, env):
        """confirmed=True + source="ui" WITHOUT a token → TOKEN_REQUIRED."""
        db, editor, _cs, _undo, _mutation, tmp_path = env
        fp = _make_flac(tmp_path / "m" / "a.flac", "Old")
        _insert_track(db, fp, "Old")
        proposal = editor.build_proposal([{"filepath": fp}], {"title": "New"})
        result = editor.apply_batch([{
            "proposal_id": proposal["proposal_id"],
            "confirmed": True,
            "source": "ui",
        }])
        assert result["ok"] is False
        assert result["applied"] == 0
        assert result["missing_confirmations"] == 1
        assert result["per_track"][0]["reason"] == TOKEN_REQUIRED
        assert result["code"] == TOKEN_REQUIRED
        row = db.conn.execute(
            "SELECT title FROM media_items WHERE filepath=?", (fp,)).fetchone()
        assert row[0] == "Old"

    @pytest.mark.parametrize("source", ["doctor", "durable_job", "ai_plan"])
    def test_forged_source_rejected(self, env, source):
        """source="doctor"/"durable_job"/"ai_plan" without token → TOKEN_REQUIRED."""
        db, editor, _cs, _undo, _mutation, tmp_path = env
        fp = _make_flac(tmp_path / "m" / "a.flac", "Old")
        _insert_track(db, fp, "Old")
        proposal = editor.build_proposal([{"filepath": fp}], {"title": "New"})
        result = editor.apply_batch([{
            "proposal_id": proposal["proposal_id"],
            "confirmed": True,
            "source": source,
        }])
        assert result["ok"] is False
        assert result["applied"] == 0
        assert result["per_track"][0]["reason"] == TOKEN_REQUIRED

    def test_field_subset_enforced(self, env):
        """Token for {title, artist} → request for album → TOKEN_FIELD_MISMATCH."""
        db, editor, _cs, _undo, _mutation, tmp_path = env
        fp = _make_flac(tmp_path / "m" / "a.flac", "Old", album="OldAlbum")
        _insert_track(db, fp, "Old", album="OldAlbum")
        proposal = editor.build_proposal(
            [{"filepath": fp}],
            {"title": "New", "artist": "NewArtist", "album": "NewAlbum"})
        token = editor.confirm(
            proposal["proposal_id"], selected_fields=["title", "artist"]
        )["confirmation_token"]
        assert editor.approve(token)["ok"] is True
        result = editor.apply_batch([{
            "proposal_id": proposal["proposal_id"],
            "confirmation_token": token,
            "fields": ["album"],
        }])
        assert result["ok"] is False
        assert result["applied"] == 0
        assert result["per_track"][0]["reason"] == TOKEN_FIELD_MISMATCH
        row = db.conn.execute(
            "SELECT title, artist, album FROM media_items WHERE filepath=?",
            (fp,)).fetchone()
        assert (row[0], row[1], row[2]) == ("Old", "Artist", "OldAlbum")

    def test_expired_token_rejected(self, env):
        """Token past expires_at → TOKEN_EXPIRED."""
        db, editor, cs, _undo, _mutation, tmp_path = env
        fp = _make_flac(tmp_path / "m" / "a.flac", "Old")
        _insert_track(db, fp, "Old")
        proposal = editor.build_proposal([{"filepath": fp}], {"title": "New"})
        token = editor.confirm(proposal["proposal_id"])["confirmation_token"]
        assert editor.approve(token)["ok"] is True
        cs.get_token(token).expires_at = time.time() - 10
        result = editor.apply_batch([{
            "proposal_id": proposal["proposal_id"],
            "confirmation_token": token,
        }])
        assert result["ok"] is False
        assert result["applied"] == 0
        assert result["per_track"][0]["reason"] == TOKEN_EXPIRED

    def test_other_proposal_token_rejected(self, env):
        """Token for proposal P1 (track 1) used with P2 (track 2,
        different target_hash) → TOKEN_TARGET_MISMATCH."""
        db, editor, _cs, _undo, _mutation, tmp_path = env
        fp1 = _make_flac(tmp_path / "m" / "a.flac", "Old A")
        fp2 = _make_flac(tmp_path / "m" / "b.flac", "Old B")
        _insert_track(db, fp1, "Old A")
        _insert_track(db, fp2, "Old B")

        p1 = editor.build_proposal([{"filepath": fp1}], {"title": "New A"})
        token = editor.confirm(p1["proposal_id"])["confirmation_token"]
        assert editor.approve(token)["ok"] is True

        p2 = editor.build_proposal([{"filepath": fp2}], {"title": "New B"})
        result = editor.apply_batch([{
            "proposal_id": p2["proposal_id"],
            "confirmation_token": token,
        }])
        assert result["ok"] is False
        assert result["applied"] == 0
        assert result["per_track"][0]["reason"] == TOKEN_TARGET_MISMATCH
        row = db.conn.execute(
            "SELECT title FROM media_items WHERE filepath=?", (fp2,)).fetchone()
        assert row[0] == "Old B"

    def test_same_refs_different_fields_command_mismatch(self, env):
        """Same targets but a different field set → TOKEN_COMMAND_MISMATCH."""
        db, editor, _cs, _undo, _mutation, tmp_path = env
        fp = _make_flac(tmp_path / "m" / "a.flac", "Old")
        _insert_track(db, fp, "Old")
        p1 = editor.build_proposal([{"filepath": fp}], {"title": "Once"})
        token = editor.confirm(p1["proposal_id"])["confirmation_token"]
        assert editor.approve(token)["ok"] is True
        p2 = editor.build_proposal([{"filepath": fp}], {"title": "Twice"})
        result = editor.apply_batch([{
            "proposal_id": p2["proposal_id"],
            "confirmation_token": token,
        }])
        assert result["ok"] is False
        assert result["per_track"][0]["reason"] == TOKEN_COMMAND_MISMATCH

    def test_single_use_token_consumed_after_apply(self, env):
        """A successful apply consumes the single-use token."""
        db, editor, _cs, _undo, _mutation, tmp_path = env
        fp = _make_flac(tmp_path / "m" / "a.flac", "Old")
        _insert_track(db, fp, "Old")
        proposal = editor.build_proposal([{"filepath": fp}], {"title": "New"})
        token = editor.confirm(proposal["proposal_id"])["confirmation_token"]
        result = _confirm_apply(editor, proposal["proposal_id"], token)
        assert result["ok"] is True
        tok = _cs.get_token(token)
        assert tok.consumed is True
        second = editor.apply_batch([{
            "proposal_id": proposal["proposal_id"],
            "confirmation_token": token,
        }])
        assert second["ok"] is False
        assert second["per_track"][0]["reason"] == "TOKEN_USED"

    def test_audit_log_persists_token_trail(self, env, tmp_path):
        """Issued/approved/consumed events are recorded in the audit log."""
        db, editor, cs, _undo, _mutation, tmp_path = env
        fp = _make_flac(tmp_path / "m" / "a.flac", "Old")
        _insert_track(db, fp, "Old")
        proposal = editor.build_proposal([{"filepath": fp}], {"title": "New"})
        token = editor.confirm(proposal["proposal_id"])["confirmation_token"]
        editor.approve(token)
        editor.apply_batch([{
            "proposal_id": proposal["proposal_id"],
            "confirmation_token": token,
        }])
        log = cs.audit_log()
        events = [entry["event"] for entry in log
                  if entry["token_id"] == token]
        assert "issued" in events
        assert "approved" in events
        assert "consumed" in events


class TestReadbackVerification:
    def test_db_readback_mismatch_failure(self, env):
        """DB diverges after the write → DB_MISMATCH → ok=False + rollback."""
        db, editor, _cs, _undo, mutation, tmp_path = env
        fp = _make_flac(tmp_path / "m" / "a.flac", "Old")
        _insert_track(db, fp, "Old")

        class _CorruptingMutation:
            def __init__(self, inner):
                self._inner = inner
                self._corrupted = False

            def update_media_fields(self, track_id, data):
                result = self._inner.update_media_fields(track_id, data)
                if not self._corrupted:
                    self._corrupted = True
                    with db.conn:
                        db.conn.execute(
                            "UPDATE media_items SET title='CORRUPTED' "
                            "WHERE id=?", (track_id,))
                return result

        editor._mutation = _CorruptingMutation(mutation)
        proposal = editor.build_proposal([{"filepath": fp}], {"title": "New"})
        token = editor.confirm(proposal["proposal_id"])["confirmation_token"]
        result = _confirm_apply(editor, proposal["proposal_id"], token)
        assert result["ok"] is False
        failed = [t for t in result["per_track"] if t["status"] == "failed"]
        assert failed and failed[0]["error"] == "DB_MISMATCH"
        assert failed[0]["rolled_back"] is True
        assert failed[0]["readback"]["fields"]["title"]["db"] == "DB_MISMATCH"
        row = db.conn.execute(
            "SELECT title FROM media_items WHERE filepath=?", (fp,)).fetchone()
        assert row[0] == "Old"

    def test_physical_tag_mismatch_failure(self, env):
        """Physical tag write diverges → TAG_MISMATCH → ok=False."""
        db, editor, _cs, _undo, _mutation, tmp_path = env
        fp = _make_flac(tmp_path / "m" / "a.flac", "Old")
        _insert_track(db, fp, "Old")

        def divergent_writer(tags):
            from mutagen.flac import FLAC
            audio = FLAC(tags.filepath)
            audio["title"] = "CORRUPTED_TAG"
            audio.save()
            return True

        editor._tag_writer = divergent_writer
        proposal = editor.build_proposal([{"filepath": fp}], {"title": "New"})
        token = editor.confirm(proposal["proposal_id"])["confirmation_token"]
        result = _confirm_apply(editor, proposal["proposal_id"], token)
        assert result["ok"] is False
        failed = [t for t in result["per_track"] if t["status"] == "failed"]
        assert failed and failed[0]["error"] == "TAG_MISMATCH"
        assert failed[0]["readback"]["fields"]["title"]["tag"] == "TAG_MISMATCH"

    def test_ok_only_when_all_fields_verified(self, env):
        """A fully verified apply reports ok=True with per-field VERIFIED."""
        db, editor, _cs, _undo, _mutation, tmp_path = env
        fp = _make_flac(tmp_path / "m" / "a.flac", "Old")
        _insert_track(db, fp, "Old")
        proposal = editor.build_proposal([{"filepath": fp}], {"title": "New"})
        token = editor.confirm(proposal["proposal_id"])["confirmation_token"]
        result = _confirm_apply(editor, proposal["proposal_id"], token)
        assert result["ok"] is True
        assert result["status"] == "COMPLETED"
        readback = result["per_track"][0]["readback"]
        assert readback["code"] == "VERIFIED"
        assert readback["fields"]["title"]["db"] == "VERIFIED"
        assert readback["fields"]["title"]["tag"] == "VERIFIED"


class TestSelectedFieldsEndToEnd:
    def test_selected_fields_respected_end_to_end(self, env):
        """Token with selected {title, artist} → album/year NEVER applied."""
        db, editor, _cs, _undo, _mutation, tmp_path = env
        fp = _make_flac(tmp_path / "m" / "a.flac", "Old", album="OldAlbum",
                        year=1999)
        _insert_track(db, fp, "Old", album="OldAlbum", year=1999)
        proposal = editor.build_proposal(
            [{"filepath": fp}],
            {"title": "New", "artist": "NewArtist",
             "album": "NewAlbum", "year": 2025})
        token = editor.confirm(
            proposal["proposal_id"], selected_fields=["title", "artist"]
        )["confirmation_token"]
        result = _confirm_apply(editor, proposal["proposal_id"], token)
        assert result["ok"] is True
        row = db.conn.execute(
            "SELECT title, artist, album, year FROM media_items "
            "WHERE filepath=?", (fp,)).fetchone()
        assert row[0] == "New"
        assert row[1] == "NewArtist"
        assert row[2] == "OldAlbum"
        assert row[3] == 1999
        from mutagen.flac import FLAC

        audio = FLAC(fp)
        assert audio["title"][0] == "New"
        assert audio["artist"][0] == "NewArtist"
        assert audio["album"][0] == "OldAlbum"
        assert audio["date"][0] == "1999"


class TestLegacyAndUndoAndBackup:
    def test_legacy_api_delegates_or_disabled(self, env):
        """Legacy DB-only update_metadata is disabled (LEGACY_OPERATION_DISABLED);
        no production consumer exists."""
        _db, editor, _cs, _undo, _mutation, tmp_path = env
        result = editor.update_metadata(1, {"title": "X"})
        assert result["ok"] is False
        assert result["code"] == "LEGACY_OPERATION_DISABLED"
        batch = editor.batch_update([{"track_id": 1, "data": {"title": "X"}}])
        assert batch["ok"] is False
        assert batch["code"] == "LEGACY_OPERATION_DISABLED"

    def test_undo_after_restart(self, env, tmp_path):
        """apply → record persisted → NEW UndoService (same store) →
        undo(operation_id) compensates DB and physical file."""
        db, editor, _cs, _undo, mutation, tmp_path = env
        fp = _make_flac(tmp_path / "m" / "a.flac", "Old")
        _insert_track(db, fp, "Old")
        proposal = editor.build_proposal([{"filepath": fp}], {"title": "New"})
        token = editor.confirm(proposal["proposal_id"])["confirmation_token"]
        result = _confirm_apply(editor, proposal["proposal_id"], token)
        assert result["ok"] is True
        operation_id = result["operation_id"]
        assert _undo.describe(operation_id)["compensation_data"]["tracks"]

        from core.undo_service import UndoService

        restarted = UndoService(
            persistence_path=str(tmp_path / "undo.jsonl"),
            db=db, mutation_service=mutation)
        outcome = restarted.undo(operation_id)
        assert outcome.ok, outcome.message
        row = db.conn.execute(
            "SELECT title FROM media_items WHERE filepath=?", (fp,)).fetchone()
        assert row[0] == "Old"
        from mutagen.flac import FLAC

        audio = FLAC(fp)
        assert audio["title"][0] == "Old"

    def test_backup_cleanup_policy(self, env):
        """Backups older than the policy are removed by cleanup_backups."""
        from core.metadata_editor_service import MetadataEditorService

        backup_dir = MetadataEditorService.backup_dir()
        os.makedirs(backup_dir, exist_ok=True)
        created = []
        for name in ("cleanup_old_1.bak", "cleanup_old_2.bak"):
            path = os.path.join(backup_dir, name)
            with open(path, "w") as handle:
                handle.write("x")
            old = time.time() - 10 * 86400
            os.utime(path, (old, old))
            created.append(path)
        fresh = os.path.join(backup_dir, "cleanup_fresh.bak")
        with open(fresh, "w") as handle:
            handle.write("x")
        try:
            removed = MetadataEditorService.cleanup_backups(max_age_days=7)
            assert removed == 2
            assert not os.path.exists(created[0])
            assert not os.path.exists(created[1])
            assert os.path.exists(fresh)
        finally:
            for path in created + [fresh]:
                if os.path.exists(path):
                    os.unlink(path)

    def test_backup_created_and_used_by_undo(self, env, tmp_path):
        """Physical backup snapshot exists after apply and restores on undo."""
        db, editor, _cs, undo, _mutation, tmp_path = env
        fp = _make_flac(tmp_path / "m" / "a.flac", "Old")
        _insert_track(db, fp, "Old")
        proposal = editor.build_proposal([{"filepath": fp}], {"title": "New"})
        token = editor.confirm(proposal["proposal_id"])["confirmation_token"]
        result = _confirm_apply(editor, proposal["proposal_id"], token)
        operation_id = result["operation_id"]
        backup = undo.describe(operation_id)["compensation_data"]["tracks"][0]["backup_path"]
        assert backup and os.path.isfile(backup)
        assert undo.undo(operation_id).ok
        from mutagen.flac import FLAC

        assert FLAC(fp)["title"][0] == "Old"


def test_batch_job_lost_state_non_retryable(tmp_path):
    """A metadata_batch job whose proposal/token no longer exist (in-memory
    state lost after restart) must fail closed as NON-retryable — it can
    never succeed and must not loop forever."""
    from core.jobs.handlers import make_metadata_batch_handler
    from core.jobs.job_service import DurableJobService

    class _LostStatePort:
        def apply_batch(self, confirmations, ctx=None):
            return {"ok": False, "code": "PROPOSAL_NOT_FOUND",
                    "message": "Unknown proposal"}

    svc = DurableJobService(db_path=str(tmp_path / "jobs.db"))
    handler = make_metadata_batch_handler(_LostStatePort())
    svc.register_handler("metadata_batch", handler)
    job_id = svc.create_job(
        "metadata_batch", owner="metadata_bridge",
        payload={"proposal_id": "gone", "confirmation_token": "gone",
                 "filepaths": ["/x.flac"]})
    svc.start_job(job_id)
    job = svc.get_job(job_id)
    assert job.state.value == "FAILED"
    assert job.retryable is False
    assert any("PROPOSAL_NOT_FOUND" in e for e in job.errors)
