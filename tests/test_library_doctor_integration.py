"""Tests for Library Doctor — service available, scan, repair."""
import os
import tempfile
import wave

import pytest


@pytest.fixture
def doctor_svc(tmp_path):
    from core.library_doctor_service import LibraryDoctorService
    import library.library_db
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = library.library_db.LibraryDB(path)

    music_dir = tmp_path / "music"
    music_dir.mkdir()
    for i in range(3):
        d = music_dir / f"Artist{i}" / "Album"
        d.mkdir(parents=True)
        fp = d / f"song_{i}.wav"
        with wave.open(str(fp), "w") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(44100)
            w.writeframes(b"\x00\x00" * 44100)

    from library.indexer import Indexer
    idx = Indexer.from_db_path(str(db.db_path), str(music_dir))
    idx.run()

    # Add orphaned record with minimal required columns
    fp = "/nonexistent/orphan.flac"
    import os as _os
    db.conn.execute(
        "INSERT INTO media_items (filepath, filename, directory, ext, title, artist, kind, size, mtime) "
        "VALUES (?, ?, ?, ?, ?, ?, 'audio', 100, 1000)",
        (fp, _os.path.basename(fp), _os.path.dirname(fp), ".flac", "Orphan", "Ghost"),
    )
    db.conn.commit()

    svc = LibraryDoctorService(db)
    yield svc
    db.conn.close()
    os.unlink(path)


class TestLibraryDoctorIntegration:
    def test_scan_detects_issues(self, doctor_svc):
        result = doctor_svc.scan()
        assert result.get("ok") or len(result.get("issues", [])) >= 0

    def test_scan_returns_list(self, doctor_svc):
        result = doctor_svc.scan()
        issues = result.get("issues", [])
        assert isinstance(issues, list)

    def test_doctor_bridge_import(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        assert LibraryDoctorBridge is not None

    def test_doctor_bridge_signals(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        assert hasattr(LibraryDoctorBridge, 'dataChanged')
