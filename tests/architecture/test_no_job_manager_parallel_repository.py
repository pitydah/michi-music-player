"""JobManager (LEGACY) must never be instantiated in productive paths
(ADR-004, audit §5: own JobRepository without DI, fake cancellation)."""
from __future__ import annotations

import re
from pathlib import Path

from tests.architecture._helpers import composition_source

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Files allowed to reference JobManager: the legacy module itself, its tests,
# and the unreachable diagnostics route that keeps it as an optional param.
ALLOWED_FILES = frozenset({
    "core/jobs/job_manager.py",
    "core/audio_lab/diagnostics_service.py",
})

SCAN_DIRS = ("core", "library", "streaming", "recognition", "integrations",
             "ui_qml_bridge", "sync", "audio")


def test_job_manager_not_in_composition() -> None:
    source = composition_source()
    assert "JobManager" not in source, (
        "JobManager must never appear in composition builders or bootstrap"
    )


def test_job_manager_not_instantiated_in_bridge_factory() -> None:
    source = (PROJECT_ROOT / "ui_qml_bridge" / "bridge_factory.py").read_text(
        encoding="utf-8"
    )
    assert "JobManager" not in source


def test_no_job_manager_instantiation_in_productive_code() -> None:
    offenders = []
    for directory in SCAN_DIRS:
        base = PROJECT_ROOT / directory
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            if "__pycache__" in str(path):
                continue
            relative = path.relative_to(PROJECT_ROOT).as_posix()
            if relative in ALLOWED_FILES:
                continue
            source = path.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"\bJobManager\(", source):
                offenders.append(relative)
    assert offenders == [], (
        f"JobManager instantiated outside legacy/test scope: {offenders}"
    )
