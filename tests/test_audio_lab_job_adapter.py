from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import MagicMock

from core.audio_lab.audio_lab_contracts import AudioLabErrorCode
from core.audio_lab.audio_lab_job_adapter import AudioLabJobAdapter
from core.worker_manager import ERR_FAILED, TaskContext, TaskHandle


class ControlledWorkerManager:
    def __init__(self) -> None:
        self.handle: TaskHandle | None = None
        self.fn = None
        self.callbacks: dict = {}

    def run_task(self, task_id, fn, *args, **kwargs) -> TaskHandle:
        del args
        self.handle = TaskHandle(task_id, owner=kwargs["owner"], cancellable=True)
        self.handle.state = TaskHandle.TASK_RUNNING
        self.handle.started_at = time.time()
        self.fn = fn
        self.callbacks = kwargs
        return self.handle

    def execute(self) -> None:
        assert self.handle is not None
        context = TaskContext(
            self.handle.task_id, self.handle.owner, self.handle.token
        )
        context._progress_cb = self.callbacks["on_progress"]
        try:
            result = self.fn(context)
        except Exception as exc:
            self.handle.state = TaskHandle.TASK_FAILED
            self.handle.error_code = ERR_FAILED
            self.handle.message = str(exc)
            self.handle.finished_at = time.time()
            self.callbacks["on_error"](ERR_FAILED, str(exc))
            return
        self.handle.state = TaskHandle.TASK_COMPLETED
        self.handle.result = result
        self.handle.finished_at = time.time()
        self.callbacks["on_done"](result)

    def report_progress(self, value: float, message: str = "") -> None:
        self.callbacks["on_progress"](value, message)

    def cancel_task(self, task_id: str) -> bool:
        if not self.handle or self.handle.task_id != task_id:
            return False
        return self.handle.cancel()

    def finish_cancellation(self) -> None:
        assert self.handle is not None
        self.handle.state = TaskHandle.TASK_CANCELLED
        self.handle.finished_at = time.time()
        self.callbacks["on_cancelled"]()


def test_missing_worker_manager_creates_terminal_failure_without_running_service() -> None:
    probe = MagicMock()
    adapter = AudioLabJobAdapter(probe=probe)

    job = adapter.get(adapter.submit_probe("/music/test.flac"))

    assert job is not None
    assert job["status"] == "failed"
    assert job["error_code"] == AudioLabErrorCode.INFRASTRUCTURE_UNAVAILABLE.value
    probe.probe.assert_not_called()


def test_retains_task_handle_but_returns_an_isolated_public_snapshot() -> None:
    manager = ControlledWorkerManager()
    analysis = MagicMock()
    adapter = AudioLabJobAdapter(wm=manager, analysis=analysis)

    job_id = adapter.submit_analysis("/music/test.flac")
    snapshot = adapter.get(job_id)

    assert snapshot is not None
    assert snapshot["status"] == "running"
    assert snapshot["task_id"].startswith("alab_analysis_")
    assert "handle" not in snapshot
    snapshot["request"]["filepath"] = "changed"
    assert adapter.get(job_id)["request"]["filepath"] == "/music/test.flac"


def test_progress_is_monotonic_and_forwarded() -> None:
    manager = ControlledWorkerManager()
    adapter = AudioLabJobAdapter(wm=manager, analysis=MagicMock())
    progress_events = []
    adapter.jobProgress.connect(lambda job_id, value: progress_events.append((job_id, value)))
    job_id = adapter.submit_analysis("/music/test.flac")

    manager.report_progress(0.6, "Analizando")
    manager.report_progress(0.2, "Atrasado")

    assert adapter.get(job_id)["progress"] == 0.6
    assert progress_events == [(job_id, 0.6), (job_id, 0.6)]


def test_replaygain_service_runs_once_and_completes() -> None:
    manager = ControlledWorkerManager()
    replaygain = MagicMock()
    replaygain.analyze_track.return_value = SimpleNamespace(
        track_gain=-5.2, status="completed", error=""
    )
    adapter = AudioLabJobAdapter(wm=manager, replaygain=replaygain)
    job_id = adapter.submit_replaygain("/music/test.flac")

    manager.execute()

    job = adapter.get(job_id)
    replaygain.analyze_track.assert_called_once_with("/music/test.flac")
    assert job["status"] == "completed"
    assert job["progress"] == 1.0
    assert job["result"] == {"track_gain": -5.2, "status": "completed"}


def test_service_error_result_becomes_failed_job() -> None:
    manager = ControlledWorkerManager()
    analysis = MagicMock()
    analysis.analyze_file.return_value = {"status": "error", "error": "decode failed"}
    adapter = AudioLabJobAdapter(wm=manager, analysis=analysis)
    job_id = adapter.submit_analysis("/music/bad.flac")

    manager.execute()

    job = adapter.get(job_id)
    assert job["status"] == "failed"
    assert job["error_code"] == ERR_FAILED
    assert "decode failed" in job["error"]


def test_cancellation_projects_handle_state_and_emits_only_when_terminal() -> None:
    manager = ControlledWorkerManager()
    adapter = AudioLabJobAdapter(wm=manager, analysis=MagicMock())
    cancelled = []
    adapter.jobCancelled.connect(cancelled.append)
    job_id = adapter.submit_analysis("/music/test.flac")

    assert adapter.cancel(job_id) is True
    assert adapter.get(job_id)["status"] == "cancel_requested"
    assert cancelled == []

    manager.finish_cancellation()

    assert adapter.get(job_id)["status"] == "cancelled"
    assert cancelled == [job_id]
