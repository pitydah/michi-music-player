"""Library doctor repairs must route through the handler registry; no
"Repair attempted" nominal success; repair with no handler returns
NO_REPAIR_HANDLER (ADR-005).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _read_doctor_source() -> str:
    path = PROJECT_ROOT / "core" / "library_doctor_service.py"
    return path.read_text(encoding="utf-8")


def test_no_repair_attempted_nominal_success() -> None:
    source = _read_doctor_source()
    assert "Repair attempted" not in source
    assert "repair_attempted" not in source


def test_repair_routes_through_registry() -> None:
    source = _read_doctor_source()
    assert "self._handlers.get(issue_type)" in source
    assert "NO_REPAIR_HANDLER" in source


def test_repair_with_no_handler_returns_no_repair_handler() -> None:
    from core.library_doctor_service import LibraryDoctorService

    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE media_items (id INTEGER PRIMARY KEY)")
    db = type("FakeDB", (), {"conn": conn})
    svc = LibraryDoctorService(db=db)
    result = svc.repair({"type": "unknown_issue", "id": 1})
    assert result["ok"] is False
    assert result["code"] == "NO_REPAIR_HANDLER"
    conn.close()


def test_destructive_repair_requires_confirmation() -> None:
    from core.confirmation_service import ConfirmationService
    from core.library_doctor_service import LibraryDoctorService
    from core.library_mutation_service import LibraryMutationService

    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE media_items (id INTEGER PRIMARY KEY, filepath TEXT, "
        "deleted_at REAL)")
    conn.execute(
        "INSERT INTO media_items (id, filepath) VALUES (1, '/gone.flac')")
    conn.commit()
    db = type("FakeDB", (), {"conn": conn})
    svc = LibraryDoctorService(
        db=db,
        mutation_service=LibraryMutationService(db=db),
        confirmation_service=ConfirmationService(),
    )
    issue = {"type": "missing_file", "filepath": "/gone.flac",
             "details": {"track_id": 1}}
    first = svc.repair(issue)
    assert first["ok"] is False
    assert first["code"] == "CONFIRMATION_REQUIRED"
    assert first["confirmation_token"]
    conn.close()
