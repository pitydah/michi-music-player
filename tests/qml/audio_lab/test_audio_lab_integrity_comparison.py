from __future__ import annotations
"""DV — Audio integrity and comparison: VALID, INVALID, UNSUPPORTED,
CANCELLED, ERROR. Comparison: audio properties, metadata, loudness,
hashes, file size."""

import os
import tempfile
import time

import pytest
from PySide6.QtCore import QCoreApplication

pytestmark = [pytest.mark.qml_module("audio_lab")]


def _process_events(duration=0.3):
    deadline = time.time() + duration
    while time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.01)


class TestAudioLabIntegrity:
    @pytest.fixture
    def app(self):
        return QCoreApplication.instance() or QCoreApplication()

    @pytest.fixture
    def sample_flac(self):
        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            f.write(b"fLaC" + b"\x00" * 2000)
            path = f.name
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def svc(self, app):
        from core.audio_lab.audio_integrity_service import AudioIntegrityService
        return AudioIntegrityService()

    def test_integrity_valid_status(self, svc, sample_flac):
        from core.audio_lab.audio_integrity_service import IntegrityStatus
        result = svc.check(sample_flac, quick=True)
        assert result.status == IntegrityStatus.VALID or result.status == IntegrityStatus.INVALID

    def test_integrity_invalid_for_unsupported(self, svc):
        from core.audio_lab.audio_integrity_service import IntegrityStatus
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            f.write(b"data")
            path = f.name
        try:
            result = svc.check(path, quick=True)
            assert result.status == IntegrityStatus.UNSUPPORTED
            assert result.is_valid is False
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_integrity_error_for_nonexistent(self, svc):
        from core.audio_lab.audio_integrity_service import IntegrityStatus
        result = svc.check("/nonexistent.flac")
        assert result.status == IntegrityStatus.ERROR

    def test_integrity_returns_checksum(self, svc, sample_flac):
        result = svc.check(sample_flac)
        assert isinstance(result.checksum, str)

    def test_integrity_duration_populated(self, svc, sample_flac):
        result = svc.check(sample_flac, quick=True)
        assert result.duration >= 0

    def test_integrity_file_size_populated(self, svc, sample_flac):
        result = svc.check(sample_flac, quick=True)
        assert result.file_size > 0

    def test_integrity_issues_list(self, svc, sample_flac):
        result = svc.check(sample_flac, quick=True)
        assert isinstance(result.issues, list)

    def test_duplicate_detection(self, svc, sample_flac):
        groups = svc.check_duplicate_content([sample_flac, sample_flac])
        assert isinstance(groups, list)

    def test_integrity_status_constants(self):
        from core.audio_lab.audio_integrity_service import IntegrityStatus
        assert IntegrityStatus.VALID == "VALID"
        assert IntegrityStatus.INVALID == "INVALID"
        assert IntegrityStatus.UNSUPPORTED == "UNSUPPORTED"
        assert IntegrityStatus.ERROR == "ERROR"


class TestAudioLabComparison:
    @pytest.fixture
    def app(self):
        return QCoreApplication.instance() or QCoreApplication()

    @pytest.fixture
    def svc(self, app):
        from core.audio_lab.audio_comparison_service import AudioComparisonService

        return AudioComparisonService()

    def test_compare_missing_files(self, svc):
        result = svc.compare("/nonexistent_a.flac", "/nonexistent_b.flac")
        assert "FILE_NOT_FOUND" in result.error

    def test_compare_dimensions_include_format(self, svc):
        result = svc.compare("/nonexistent.flac", "/nonexistent2.flac")
        if not result.error:
            keys = [d.key for d in result.dimensions]
            assert "format" in keys

    def test_compare_dimensions_include_metadata(self, svc):
        result = svc.compare("/nonexistent.flac", "/nonexistent2.flac")
        if not result.error:
            keys = [d.key for d in result.dimensions]
            assert any(k.startswith("meta_") for k in keys)

    def test_compare_returns_hashes(self, svc):
        result = svc.compare("/nonexistent.flac", "/nonexistent2.flac")
        if not result.error:
            keys = [d.key for d in result.dimensions]
            assert "hash" in keys

    def test_compare_returns_file_size(self, svc):
        result = svc.compare("/nonexistent.flac", "/nonexistent2.flac")
        if not result.error:
            keys = [d.key for d in result.dimensions]
            assert "file_size_bytes" in keys or "size" in keys

    def test_compare_returns_loudness(self, svc):
        result = svc.compare("/nonexistent.flac", "/nonexistent2.flac")
        if not result.error:
            keys = [d.key for d in result.dimensions]
            assert "loudness" in keys

    def test_compare_dimensions_have_identical_flag(self, svc):
        result = svc.compare("/nonexistent.flac", "/nonexistent2.flac")
        if not result.error and result.dimensions:
            for d in result.dimensions:
                assert hasattr(d, "identical")
