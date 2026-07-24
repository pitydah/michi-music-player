from types import SimpleNamespace

from PySide6.QtCore import QObject, Signal

from ui_qml_bridge.audio_lab_bridge import AudioLabBridge


class StubJobAdapter(QObject):
    jobProgress = Signal(str, float)
    jobCompleted = Signal(str, str, object)
    jobFailed = Signal(str, str)
    jobCancelled = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.jobs = {}
        self.calls = []

    def _submit(self, job_id: str, job_type: str, request: dict) -> str:
        self.calls.append((job_type, request))
        self.jobs[job_id] = {
            "id": job_id,
            "type": job_type,
            "status": "running",
            "request": request,
        }
        return job_id

    def submit_analysis(self, filepath: str) -> str:
        return self._submit("analysis_1", "analysis", {"filepath": filepath})

    def submit_replaygain(self, filepath: str) -> str:
        return self._submit("rg_1", "replaygain", {"filepath": filepath})

    def submit_integrity(self, filepath: str) -> str:
        return self._submit("integrity_1", "integrity", {"filepath": filepath})

    def submit_comparison(self, file_a: str, file_b: str) -> str:
        return self._submit(
            "compare_1", "comparison", {"file_a": file_a, "file_b": file_b}
        )

    def get(self, job_id: str):
        job = self.jobs.get(job_id)
        return dict(job) if job else None

    def list(self):
        return [dict(job) for job in self.jobs.values()]

    def cancel(self, job_id: str) -> bool:
        job = self.jobs.get(job_id)
        if not job or job["status"] != "running":
            return False
        job["status"] = "cancel_requested"
        return True

    def complete(self, job_id: str, result: dict) -> None:
        self.jobs[job_id]["status"] = "completed"
        self.jobCompleted.emit(job_id, "completed", result)


def _bridge_with_adapter() -> tuple[AudioLabBridge, StubJobAdapter]:
    adapter = StubJobAdapter()
    service = SimpleNamespace(jobs=adapter)
    return AudioLabBridge(audio_lab_service=service), adapter


def test_create() -> None:
    assert AudioLabBridge() is not None


def test_core_start_methods_delegate_to_canonical_adapter() -> None:
    bridge, adapter = _bridge_with_adapter()

    assert bridge.startAnalysis("/music/a.flac") == "analysis_1"
    assert bridge.startReplayGain("/music/a.flac") == "rg_1"
    assert bridge.startIntegrity("/music/a.flac") == "integrity_1"
    assert bridge.startComparison("/music/a.flac", "/music/b.flac") == "compare_1"

    assert [call[0] for call in adapter.calls] == [
        "analysis", "replaygain", "integrity", "comparison"
    ]
    assert bridge._active_jobs == {}


def test_adapter_completion_preserves_bridge_signal_contract() -> None:
    bridge, adapter = _bridge_with_adapter()
    completed = []
    bridge.jobCompleted.connect(
        lambda job_id, job_type, result: completed.append((job_id, job_type, result))
    )
    job_id = bridge.startAnalysis("/music/a.flac")

    adapter.complete(job_id, {"format": "FLAC", "status": "completed"})

    assert completed == [(
        job_id,
        "analysis",
        {
            "filepath": "/music/a.flac",
            "format": "FLAC",
            "status": "completed",
            "error": "",
        },
    )]


def test_adapter_owns_status_and_cancellation() -> None:
    bridge, _adapter = _bridge_with_adapter()
    job_id = bridge.startIntegrity("/music/a.flac")

    assert bridge.activeJobs() == {job_id: "running"}
    assert bridge.jobStatus(job_id)["status"] == "running"
    assert bridge.cancelJob(job_id) == {"ok": True, "job_id": job_id}
    assert bridge.jobStatus(job_id)["status"] == "cancel_requested"


def test_core_start_methods_do_not_fall_back_without_adapter() -> None:
    service = SimpleNamespace(
        jobs=None,
        analysis=SimpleNamespace(analyze_file=lambda _path: (_ for _ in ()).throw(
            AssertionError("must not execute synchronously")
        )),
    )
    bridge = AudioLabBridge(audio_lab_service=service)

    assert bridge.startAnalysis("/music/a.flac") == ""
