from __future__ import annotations
"""Macrofase F — 13.9: Audio integrity service tests."""

import sqlite3
import time

import pytest
from PySide6.QtCore import QCoreApplication

pytestmark = [pytest.mark.qml_module("audio_lab")]


def _process_events(duration=1.0):
    deadline = time.time() + duration
    while time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.02)


class TestAudioIntegrity:
    @pytest.fixture
    def app(self):
        return QCoreApplication.instance() or QCoreApplication()

    @pytest.fixture
    def db(self):
        return sqlite3.connect(":memory:")

    @pytest.fixture
    def wm(self):
        from core.worker_manager import WorkerManager
        wm = WorkerManager()
        yield wm
        wm.shutdown()

    def test_integrity_service_created(self, app, db, wm):
        from core.audio_lab.audio_integrity_service import AudioIntegrityService
        svc = AudioIntegrityService(db=db, wm=wm)
        assert svc is not None

    def test_integrity_missing_file(self, app, db, wm):
        from core.audio_lab.audio_integrity_service import AudioIntegrityService
        svc = AudioIntegrityService(db=db, wm=wm)
        result = svc.check("/nonexistent/file.flac")
        from core.audio_lab.audio_integrity_service import IntegrityStatus
        assert result.status == IntegrityStatus.ERROR
        assert not result.is_valid
        assert any(i["type"] == "FILE_NOT_FOUND" for i in result.issues)

    def _tmp_file(self, suffix, content=b""):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(content)
            path = f.name
        return path

    def test_integrity_unsupported_extension(self, app, db, wm):
        import os
        path = self._tmp_file(".xyz", b"test")
        try:
            from core.audio_lab.audio_integrity_service import AudioIntegrityService
            svc = AudioIntegrityService(db=db, wm=wm)
            result = svc.check(path)
            assert any("UNSUPPORTED_EXTENSION" in i["type"] for i in result.issues)
        finally:
            os.unlink(path)

    def test_integrity_mp3_header_invalid(self, app, db, wm):
        import os
        path = self._tmp_file(".mp3", b"\x00\x00\x00\x00")
        try:
            from core.audio_lab.audio_integrity_service import AudioIntegrityService
            svc = AudioIntegrityService(db=db, wm=wm)
            result = svc.check(path)
            assert any("INVALID_HEADER" in i["type"] for i in result.issues)
        finally:
            os.unlink(path)

    def test_integrity_flac_magic(self, app, db, wm):
        import os
        path = self._tmp_file(".flac", b"\x00\x00\x00\x00")
        try:
            from core.audio_lab.audio_integrity_service import AudioIntegrityService
            svc = AudioIntegrityService(db=db, wm=wm)
            result = svc.check(path)
            assert any("INVALID_FLAC_MAGIC" in i["type"] for i in result.issues)
        finally:
            os.unlink(path)

    def test_integrity_checksum(self, app, db, wm):
        import os
        path = self._tmp_file(".wav", b"\x00" * 1024)
        try:
            from core.audio_lab.audio_integrity_service import AudioIntegrityService
            svc = AudioIntegrityService(db=db, wm=wm)
            result = svc.check(path, quick=False)
            assert len(result.checksum) == 64
        finally:
            os.unlink(path)

    def test_integrity_duplicate_detection(self, app, db, wm):
        import os
        p1 = self._tmp_file(".wav", b"\x00" * 1024)
        p2 = self._tmp_file(".wav", b"\x00" * 1024)
        try:
            from core.audio_lab.audio_integrity_service import AudioIntegrityService
            svc = AudioIntegrityService(db=db, wm=wm)
            groups = svc.check_duplicate_content([p1, p2])
            assert len(groups) == 1
            assert len(groups[0]) == 2
        finally:
            os.unlink(p1)
            os.unlink(p2)

    def test_integrity_no_duplicates(self, app, db, wm):
        import os
        p1 = self._tmp_file(".wav", b"\x00" * 512)
        p2 = self._tmp_file(".wav", b"\xff" * 512)
        try:
            from core.audio_lab.audio_integrity_service import AudioIntegrityService

            svc = AudioIntegrityService(db=db, wm=wm)
            groups = svc.check_duplicate_content([p1, p2])
            assert len(groups) == 0
        finally:
            os.unlink(p1)
            os.unlink(p2)
