import threading

from core.worker_manager import (
    CancellationToken,
    TaskHandle,
    WorkerManager,
)


class TestWorkerManager:
    def test_create(self):
        mgr = WorkerManager()
        assert mgr is not None

    def test_cancellation_token(self):
        ct = CancellationToken()
        assert not ct._event.is_set()

    def test_progress_callback_is_invoked(self, qtbot):
        manager = WorkerManager()
        progress = []

        def run(context):
            context.report_progress(0.5, "Mitad")
            return "ok"

        handle = manager.run_task(
            "progress-test",
            run,
            pass_context=True,
            on_progress=lambda value, message: progress.append((value, message)),
        )
        qtbot.waitUntil(lambda: handle.state == TaskHandle.TASK_COMPLETED)

        assert progress == [(0.5, "Mitad")]
        manager.shutdown()

    def test_cancel_emits_cancel_requested_state(self, qtbot):
        manager = WorkerManager()
        started = threading.Event()
        release = threading.Event()
        states = []
        manager.taskStateChanged.connect(
            lambda task_id, state: states.append((task_id, state))
        )

        def run(context):
            started.set()
            release.wait(1)
            context.token.raise_if_cancelled()

        handle = manager.run_task(
            "cancel-test", run, pass_context=True, cancellable=True
        )
        assert started.wait(1)
        assert manager.cancel_task("cancel-test") is True

        assert handle.state == TaskHandle.TASK_CANCEL_REQUESTED
        assert ("cancel-test", TaskHandle.TASK_CANCEL_REQUESTED) in states

        release.set()
        qtbot.waitUntil(lambda: handle.state == TaskHandle.TASK_CANCELLED)
        manager.shutdown()

    def test_failure_preserves_exception_message(self, qtbot):
        manager = WorkerManager()
        errors = []

        def fail():
            raise RuntimeError("decode failed")

        handle = manager.run_task(
            "failure-test",
            fail,
            on_error=lambda code, message: errors.append((code, message)),
        )
        qtbot.waitUntil(lambda: handle.state == TaskHandle.TASK_FAILED)

        assert handle.message == "decode failed"
        assert errors == [("TASK_FAILED", "decode failed")]
        manager.shutdown()
