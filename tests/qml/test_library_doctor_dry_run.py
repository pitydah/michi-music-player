"""Library Doctor dry-run — core service test."""
from __future__ import annotations

from core.library_doctor_service import LibraryDoctorService


class TestLibraryDoctorDryRun:
    def test_doctor_service_scan_exists(self):
        svc = LibraryDoctorService(db=None)
        result = svc.scan()
        assert isinstance(result, dict)
        assert "ok" in result or "error" in result
