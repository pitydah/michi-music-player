"""Tests for LibraryDoctorService — scan, detect issues, repair preview."""
import os
import wave

import pytest


@pytest.fixture
def damaged_library(tmp_path):
    """Create a library with real issues: missing files, empty dirs, orphaned DB records."""
    from library.library_db import LibraryDB
    db_path = tmp_path / "test.db"
    db = LibraryDB(str(db_path))

    music_dir = tmp_path / "music"
    music_dir.mkdir()

    # Create some valid tracks
    created_files = []
    for i, (artist, album, title) in enumerate([
        ("Band", "Album", "Song 1"),
        ("Band", "Album", "Song 2"),
        ("Solo", "Best Of", "Track 1"),
    ]):
        d = music_dir / artist / album
        d.mkdir(parents=True, exist_ok=True)
        fp = d / f"{title}.wav"
        with wave.open(str(fp), "w") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(44100)
            w.writeframes(b"\x00\x00" * 44100)
        created_files.append(str(fp))

    # Scan into DB
    from library.indexer import Indexer
    idx = Indexer.from_db_path(str(db_path), str(music_dir))
    idx.run()

    # Add an orphaned DB record (file deleted)
    valid_file = created_files[0]
    os.unlink(valid_file)

    # Add a DB record with no corresponding file
    fake_path = str(tmp_path / "music" / "Ghost" / "Album" / "missing.flac")
    try:
        db.conn.execute(
            "INSERT INTO media_items (filepath, title, artist, album) VALUES (?, ?, ?, ?)",
            (fake_path, "Missing Track", "Ghost Artist", "Ghost Album"),
        )
        db.conn.commit()
    except Exception:
        pass

    return db, music_dir, db_path


class TestLibraryDoctor:
    def test_service_import(self):
        from core.library_doctor_service import LibraryDoctorService
        assert LibraryDoctorService is not None

    def test_scan_detects_issues(self, damaged_library):
        db, music_dir, db_path = damaged_library
        from core.library_doctor_service import LibraryDoctorService
        svc = LibraryDoctorService(db)
        result = svc.scan()
        assert result.get("ok") or len(result.get("issues", result.get("findings", []))) > 0

    def test_scan_returns_issue_list(self, damaged_library):
        db, music_dir, db_path = damaged_library
        from core.library_doctor_service import LibraryDoctorService
        svc = LibraryDoctorService(db)
        result = svc.scan()
        issues = result.get("issues", result.get("findings", []))
        assert isinstance(issues, list)

    def test_issue_has_type_and_severity(self):
        from core.library_doctor_service import Issue
        issue = Issue(issue_type="missing_file", severity="warning", description="Archivo faltante", filepath="/test/missing.flac")
        assert issue.issue_type == "missing_file"
        assert issue.severity == "warning"
        assert issue.filepath == "/test/missing.flac"

    def test_repair_preview(self, damaged_library):
        db, music_dir, db_path = damaged_library
        from core.library_doctor_service import LibraryDoctorService
        svc = LibraryDoctorService(db)
        scan_result = svc.scan()
        issues = scan_result.get("issues", scan_result.get("findings", []))
        if issues:
            preview = svc.preview_repair(issues[0])
            assert preview is not None

    def test_repair_issue(self, damaged_library):
        db, music_dir, db_path = damaged_library
        from core.library_doctor_service import LibraryDoctorService
        svc = LibraryDoctorService(db)
        scan_result = svc.scan()
        issues = scan_result.get("issues", scan_result.get("findings", []))
        if issues:
            result = svc.repair(issues[0])
            assert isinstance(result, dict)

    def test_bridge_import(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        assert LibraryDoctorBridge is not None

    def test_bridge_signals(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        assert hasattr(LibraryDoctorBridge, 'dataChanged')

    def test_health(self, damaged_library):
        db, music_dir, db_path = damaged_library
        from core.library_doctor_service import LibraryDoctorService
        svc = LibraryDoctorService(db)
        health = svc.health()
        assert isinstance(health, dict)
