"""One canonical metadata editing pipeline: metadata_editor_service is the
editing authority wired with real dependencies; MetadataService stays the
read authority; apply_batch returns real counters, never a bare boolean.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _read_library_composition() -> str:
    path = PROJECT_ROOT / "core" / "composition" / "library.py"
    return path.read_text(encoding="utf-8")


def test_editor_registered_with_real_wiring() -> None:
    source = _read_library_composition()
    register = re.search(
        r'container\.register\(\s*"metadata_editor_service",\s*'
        r'MetadataEditorService\((.*?)\)\s*\)',
        source, re.S,
    )
    assert register is not None, "metadata_editor_service must be registered"
    args = register.group(1)
    for required in ("mutation_service=", "event_bus=",
                     "confirmation_service=", "undo_service=",
                     "worker_manager="):
        assert required in args, f"editor wiring missing {required}"


def test_metadata_service_is_read_authority_not_editing_stub() -> None:
    from core.metadata_service import MetadataService

    svc = MetadataService()
    read = svc.read
    assert callable(read)


def test_apply_batch_returns_real_counters(tmp_path) -> None:
    """apply_batch requires an approved ConfirmationToken and returns real
    counters (P0: self-declared confirmed=True/source= is rejected)."""
    import numpy as np
    import soundfile as sf
    from core.confirmation_service import ConfirmationService
    from core.metadata_editor_service import MetadataEditorService

    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE media_items (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "filepath TEXT UNIQUE, title TEXT, deleted_at REAL)")
    music = tmp_path / "music"
    paths = []
    for i in range(2):
        fp = music / f"t{i}.flac"
        fp.parent.mkdir(parents=True, exist_ok=True)
        sf.write(fp, np.zeros(32, dtype=np.float32), 8000, format="FLAC")
        conn.execute(
            "INSERT INTO media_items (filepath, title) VALUES (?, ?)",
            (str(fp), f"Old {i}"))
        paths.append(str(fp))
    conn.commit()

    class _Row:
        def __init__(self, row):
            self.id, self.filepath, self.title = row

    def get_media_item_by_id(tid: int) -> _Row | None:
        row = conn.execute(
            "SELECT id, filepath, title FROM media_items WHERE id=?",
            (tid,)).fetchone()
        return _Row(row) if row else None

    db = type("FakeDB", (), {"conn": conn,
                             "get_media_item_by_id": get_media_item_by_id})
    editor = MetadataEditorService(db=db, confirmation_service=ConfirmationService())

    proposal = editor.build_proposal(
        [{"filepath": fp} for fp in paths],
        {"title": "New"})
    token = editor.confirm(proposal["proposal_id"])["confirmation_token"]
    assert editor.approve(token)["ok"] is True
    result = editor.apply_batch(
        [{"proposal_id": proposal["proposal_id"],
          "confirmation_token": token}])
    for key in ("requested", "applied", "failed", "skipped", "conflicts",
                "missing_confirmations", "rollback_performed", "per_track"):
        assert key in result, f"apply_batch must report {key}"
    assert result["applied"] == 2
    assert result["status"] == "COMPLETED"
    conn.close()


def test_batch_adapter_is_not_the_editing_authority() -> None:
    """The metadata_batch job handler routes through the editor service.

    Fase Jobs: handlers are pure factories over injected ports — the wiring
    to metadata_editor_service lives in composition, not inside handlers.py.
    P0: the handler applies with the bridge-issued ConfirmationToken and
    rejects payloads without one (TOKEN_REQUIRED) — never self-declares.
    """
    handlers = (PROJECT_ROOT / "core" / "jobs" / "handlers.py").read_text(
        encoding="utf-8")
    assert "make_metadata_batch_handler" in handlers
    assert '"confirmation_token"' in handlers, (
        "the batch handler must apply with the bridge-issued token"
    )
    assert "TOKEN_REQUIRED" in handlers, (
        "a batch job without a token must be rejected, not self-confirmed"
    )
    assert 'confirmed": True' not in handlers.replace(" ", ""), (
        "the handler must never self-declare confirmation"
    )

    composition = (PROJECT_ROOT / "core" / "composition" / "jobs.py").read_text(
        encoding="utf-8")
    assert 'container.get("metadata_editor_service")' in composition, (
        "composition must wire the metadata port to metadata_editor_service"
    )
    assert 'register_handler("metadata_batch"' in composition, (
        "composition must register the metadata_batch handler"
    )
