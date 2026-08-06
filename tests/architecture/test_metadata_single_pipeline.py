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


def test_apply_batch_returns_real_counters() -> None:
    from core.metadata_editor_service import MetadataEditorService

    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE media_items (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "filepath TEXT UNIQUE, title TEXT)")
    conn.execute(
        "INSERT INTO media_items (filepath, title) VALUES "
        "('/a.flac', 'A'), ('/b.flac', 'B')")
    conn.commit()
    db = type("FakeDB", (), {"conn": conn})
    editor = MetadataEditorService(db=db)

    proposal = editor.build_proposal(
        [{"track_id": 1}, {"track_id": 2}],
        {"title": "New"})
    result = editor.apply_batch(
        [{"proposal_id": proposal["proposal_id"],
          "confirmed": True, "source": "ui"}])
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
    """
    handlers = (PROJECT_ROOT / "core" / "jobs" / "handlers.py").read_text(
        encoding="utf-8")
    assert "make_metadata_batch_handler" in handlers
    assert 'source": "ui"' in handlers, (
        "the batch handler must route through the editor's apply_batch"
    )

    composition = (PROJECT_ROOT / "core" / "composition" / "jobs.py").read_text(
        encoding="utf-8")
    assert 'container.get("metadata_editor_service")' in composition, (
        "composition must wire the metadata port to metadata_editor_service"
    )
    assert 'register_handler("metadata_batch"' in composition, (
        "composition must register the metadata_batch handler"
    )
