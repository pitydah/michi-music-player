"""Regression tests for the ModelManager lifecycle shutdown contract.

The auto-unload worker used to be an unstoppable daemon loop (`while True`
+ `time.sleep`), one per construction. Repeated constructions (tests,
assistant compositions) leaked threads that piled up concurrently and
crashed pytest-qt's event processing with a segmentation fault on Python
3.12. These tests pin the deterministic lifecycle contract: shutdown()
joins the worker promptly, is idempotent, repeated constructions leave no
running threads, and a stopped manager never processes again.
"""
from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import MagicMock

from core.ai.model_manager import ModelManager

SHUTDOWN_TIMEOUT = 5.0


def _alive_idents() -> set[int]:
    """Idents of every alive thread, so tests only count their own."""
    return {t.ident for t in threading.enumerate() if t.ident is not None}


def test_shutdown_terminates_worker_within_bounded_timeout(tmp_path: Path) -> None:
    mm = ModelManager(storage_dir=tmp_path)
    worker = mm._worker
    assert worker is not None and worker.is_alive()

    mm.shutdown()

    worker.join(SHUTDOWN_TIMEOUT)
    assert not worker.is_alive(), "worker must terminate within the bounded timeout"


def test_shutdown_is_idempotent(tmp_path: Path) -> None:
    mm = ModelManager(storage_dir=tmp_path)
    worker = mm._worker

    mm.shutdown()
    mm.shutdown()
    mm.shutdown()

    assert worker is not None
    assert not worker.is_alive()


def test_repeated_constructions_leave_no_running_threads_after_shutdown(tmp_path: Path) -> None:
    baseline = _alive_idents()
    managers = [ModelManager(storage_dir=tmp_path) for _ in range(5)]
    assert len(_alive_idents() - baseline) >= 5

    for mm in managers:
        mm.shutdown()

    leftover = _alive_idents() - baseline
    assert leftover == set(), f"leaked worker threads still running: {leftover}"


def test_stopped_manager_does_not_keep_processing(tmp_path: Path, monkeypatch) -> None:
    mm = ModelManager(storage_dir=tmp_path)
    mm._loaded_models["fake"] = object()
    mm._last_activity["fake"] = 0.0
    unload = MagicMock()
    monkeypatch.setattr(mm, "_unload", unload)

    mm.shutdown()
    unload.reset_mock()
    mm._auto_unload_check()

    unload.assert_not_called()


def test_assistant_composition_exposes_model_manager_shutdown() -> None:
    from core.assistant_initializer import create_assistant_composition

    comp = create_assistant_composition()
    mm = comp.model_manager
    assert mm is not None
    assert callable(getattr(mm, "shutdown", None))
    mm.shutdown()
