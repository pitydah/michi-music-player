"""Tests for CrashReporter — capture, metadata, rotation."""

import contextlib
import glob
import json
import os
import tempfile

from PySide6.QtWidgets import QApplication


def _ensure_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestCrashReporter:

    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp(prefix="michi_crash_test_")
        os.environ["MICHI_TEST_DATA_DIR"] = self._tmpdir
        os.environ["MICHI_TEST_CACHE_DIR"] = self._tmpdir
        os.environ["MICHI_TEST_CONFIG_DIR"] = self._tmpdir
        _ensure_app()

    def teardown_method(self):
        for root, _dirs, files in os.walk(self._tmpdir, topdown=False):
            for fn in files:
                os.unlink(os.path.join(root, fn))
            with contextlib.suppress(OSError):
                os.rmdir(root)

    def _logs_dir(self):
        from core.paths import logs_dir
        return logs_dir()

    def test_build_report_contains_all_fields(self):
        from core.crash_reporter import CrashReporter
        reporter = CrashReporter()
        report = reporter._build_report(
            exc_type="TypeError",
            exc_value="test error",
            traceback="  File \"x.py\", line 1\n    raise TypeError()",
            thread_name="worker-1",
            signal="SIGSEGV",
        )
        expected_keys = {
            "timestamp", "type", "message", "traceback", "thread",
            "signal", "version", "python", "platform", "cwd", "argv",
            "qt_messages", "worker_errors", "env",
        }
        assert expected_keys.issubset(report.keys()), f"Missing keys: {expected_keys - report.keys()}"
        assert report["type"] == "TypeError"
        assert report["message"] == "test error"
        assert report["thread"] == "worker-1"
        assert report["signal"] == "SIGSEGV"

    def test_save_report_creates_file(self):
        from core.crash_reporter import CrashReporter
        reporter = CrashReporter()
        report = reporter._build_report(exc_type="Error", exc_value="x", traceback="")
        path = reporter._save_report(report)
        assert os.path.isfile(path), f"Report not saved: {path}"
        with open(path) as f:
            data = json.load(f)
            assert data["type"] == "Error"

    def test_rotation_keeps_max_reports(self):
        from core.crash_reporter import CrashReporter, MAX_REPORTS
        reporter = CrashReporter()
        logs = self._logs_dir()
        for i in range(MAX_REPORTS + 5):
            report = reporter._build_report(
                exc_type="Error", exc_value=f"test {i}", traceback="",
            )
            reporter._save_report(report)
        reports = sorted(glob.glob(os.path.join(logs, "crash_*.json")))
        assert len(reports) <= MAX_REPORTS, f"Too many reports: {len(reports)} > {MAX_REPORTS}"

    def test_qt_messages_buffer(self):
        from core.crash_reporter import CrashReporter
        reporter = CrashReporter()
        from PySide6.QtCore import QtMsgType
        for i in range(60):
            reporter._on_qt_message(QtMsgType.QtWarningMsg, None, f"msg {i}")
        assert len(reporter._qt_messages) <= 50

    def test_worker_error_logging(self):
        from core.crash_reporter import CrashReporter
        reporter = CrashReporter()
        reporter._on_worker_error("task_1", "ffmpeg not found")
        assert len(reporter._worker_errors) == 1
        assert reporter._worker_errors[0]["task_id"] == "task_1"

    def test_on_unhandled_exception_creates_report(self):
        from core.crash_reporter import CrashReporter
        # Obtener exc_info sin que el hook se dispare
        import sys as _sys
        exc_info = None
        try:
            _sys.excepthook = _sys.__excepthook__
            raise ValueError("unhandled test")
        except ValueError:
            exc_info = _sys.exc_info()
        # Re-instalar reporter hook
        reporter = CrashReporter()
        reporter._on_unhandled_exception(*exc_info)
        logs = self._logs_dir()
        reports = glob.glob(os.path.join(logs, "crash_*.json"))
        assert len(reports) >= 1


class TestSanitization:

    def test_redact_env_tokens(self):
        from core.crash_reporter import _redact_env
        env = {"HOME": "/home/user", "HA_TOKEN": "secret", "PATH": "/usr/bin", "API_KEY": "abc123"}
        clean = _redact_env(env)
        assert clean["HA_TOKEN"] == "[REDACTED]"
        assert clean["API_KEY"] == "[REDACTED]"
        assert "[USER]" in clean["HOME"] or "/home/user" not in clean["HOME"]

    def test_redact_home_paths(self):
        from core.crash_reporter import _redact_home_path
        result = _redact_home_path("/home/user/music/file.flac: error")
        assert "[USER]" in result
        result2 = _redact_home_path("/Users/john/Music/song.mp3")
        assert "[USER]" in result2
        result3 = _redact_home_path("/usr/bin/python3")
        assert "[USER]" not in result3

    def test_redact_sensitive_strings(self):
        from core.crash_reporter import _redact_sensitive_strings
        result = _redact_sensitive_strings("token=abc123def456 and /home/user/file.flac")
        assert "abc123def456" not in result
        assert "[USER]" in result

    def test_build_report_redacts_env(self):
        from core.crash_reporter import CrashReporter
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["MY_TOKEN"] = "should_be_redacted"
            reporter = CrashReporter()
            reporter._logs_dir = lambda: tmp
            report = reporter._build_report(exc_type="Test", exc_value="", traceback="")
            assert report["env"].get("MY_TOKEN") == "[REDACTED]"

    def test_worker_errors_redacted(self):
        from core.crash_reporter import CrashReporter
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            reporter = CrashReporter()
            reporter._logs_dir = lambda: tmp
            reporter.log_worker_error("t1", "/home/user/secret.txt not found")
            report = reporter._build_report(exc_type="Test", exc_value="", traceback="")
            error = report["worker_errors"][0]["error"]
            assert "/home/user/secret.txt" not in error
            assert "[USER]" in error

    def test_qt_messages_redacted(self):
        from core.crash_reporter import CrashReporter
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            reporter = CrashReporter()
            reporter._logs_dir = lambda: tmp
            reporter._qt_messages.append("token=abc123def456")
            reporter._qt_messages.append("/home/user/file.flac not found")
            report = reporter._build_report(exc_type="Test", exc_value="", traceback="")
            msgs = " ".join(report["qt_messages"])
            assert "abc123def456" not in msgs
            assert "[USER]" in msgs
