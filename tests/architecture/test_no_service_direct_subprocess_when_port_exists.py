"""MPD subprocess must be lifecycle-managed via ProcessController.

No bare ``subprocess.Popen`` in ``audio/mpd/``: daemon spawning goes through
``core.process_controller.ProcessController`` (registered as
``process_controller``) so the process is tracked, terminated and cleaned up
through the app's process management layer.
"""
from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MPD_DIR = PROJECT_ROOT / "audio" / "mpd"

_BARE_SUBPROCESS_RE = re.compile(
    r"^\s*(?:import\s+subprocess|from\s+subprocess\s+import)",
    re.M,
)
_POPEN_RE = re.compile(r"subprocess\.Popen\b")


def _mpd_py_files() -> list[Path]:
    return sorted(MPD_DIR.rglob("*.py"))


def test_mpd_package_never_imports_subprocess_directly() -> None:
    offenders = []
    for path in _mpd_py_files():
        source = path.read_text(encoding="utf-8")
        if _BARE_SUBPROCESS_RE.search(source) or _POPEN_RE.search(source):
            offenders.append(str(path))
    assert offenders == [], (
        f"audio/mpd/ must not spawn subprocesses directly; "
        f"use core.process_controller.ProcessController: {offenders}"
    )


def test_mpd_service_manager_spawns_via_process_controller() -> None:
    manager_source = (MPD_DIR / "mpd_service_manager.py").read_text(
        encoding="utf-8")
    assert "ProcessController" in manager_source, (
        "MpdServiceManager must use ProcessController for daemon lifecycle"
    )
    assert "spawn_sync" in manager_source, (
        "MpdServiceManager must spawn through ProcessController.spawn_sync"
    )


def test_process_controller_has_sync_daemon_api() -> None:
    controller_source = (PROJECT_ROOT / "core" / "process_controller.py").read_text(
        encoding="utf-8")
    for method in ("spawn_sync", "terminate_sync", "cleanup_sync",
                   "is_alive", "get_sync_process"):
        assert method in controller_source, (
            f"ProcessController must expose {method}() for daemon processes"
        )


def test_mpd_service_manager_tracks_owned_pid_only() -> None:
    manager_source = (MPD_DIR / "mpd_service_manager.py").read_text(
        encoding="utf-8")
    assert "cleanup_sync" in manager_source
    assert "terminate_sync" in manager_source
    assert "own" in manager_source.lower() or "external" in manager_source.lower(), (
        "stop() must document it only terminates owned processes"
    )
