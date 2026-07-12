"""CrashReporter — captura integral de errores para diagnostico preciso.

Captura:
1. Excepciones Python no manejadas (sys.excepthook)
2. Excepciones en hilos Python (threading.excepthook)
3. Mensajes Qt (qInstallMessageHandler) — qWarning, qCritical, qFatal
4. Errores de workers Qt (WorkerManager.task_error)
5. Senales del sistema (SIGSEGV, SIGABRT, SIGFPE) via signal.signal
6. Estado del sistema al momento del error

PRIVACIDAD:
- Se redactan claves sensibles en env (token, key, secret, password, auth, bearer, credential).
- Se redacta cwd si contiene /home/, /Users/ o rutas personales.
- Se redactan tokens/rutas en argv, traceback, qt_messages y worker_errors.
- No se almacena env completo sin redaccion.
"""

from __future__ import annotations

import datetime
import faulthandler
import json
import logging
import os
import re
import signal
import sys
import threading
import traceback
import types
from typing import Any

from PySide6.QtCore import QObject, Signal
from PySide6.QtCore import qInstallMessageHandler, QtMsgType

MAX_REPORTS = 10
MAX_QT_MSGS = 50

_SENSITIVE_ENV_RE = re.compile(r"(token|key|secret|password|auth|bearer|credential)", re.IGNORECASE)
_HOME_PATH_RE = re.compile(r"/(home|Users)/[^/\"'\s)]+")
_TOKEN_RE = re.compile(r"(token|key|secret|password|auth|bearer|credential)[=:]\s*\S+", re.IGNORECASE)
_HEX_TOKEN_RE = re.compile(r"\b[a-fA-F0-9]{32,}\b")


def _redact_env(env: dict[str, str]) -> dict[str, str]:
    out = {}
    for k, v in env.items():
        if _SENSITIVE_ENV_RE.search(k):
            out[k] = "[REDACTED]"
        else:
            out[k] = _redact_sensitive_strings(str(v))[:500]
    return out


def _redact_home_path(text: str) -> str:
    return _HOME_PATH_RE.sub(r"/\1/[USER]", text)


def _redact_sensitive_strings(text: str) -> str:
    text = _TOKEN_RE.sub("[REDACTED]", text)
    text = _HEX_TOKEN_RE.sub("[TOKEN]", text)
    text = _redact_home_path(text)
    return text


class CrashReporter(QObject):
    crash_occurred = Signal(str)

    def __init__(self, worker_mgr=None, parent=None):
        super().__init__(parent)
        self._log = logging.getLogger("michi.crash")
        self._worker_mgr = worker_mgr
        self._qt_messages: list[str] = []
        self._worker_errors: list[dict] = []
        self._original_excepthook: types.FunctionType | None = None
        self._original_qt_handler: Any = None
        self._install_all_hooks()

    def _install_all_hooks(self):
        faulthandler.enable()
        self._original_excepthook = sys.excepthook
        sys.excepthook = self._on_unhandled_exception
        self._original_thread_hook = threading.excepthook
        threading.excepthook = self._on_thread_exception
        for sig in (signal.SIGSEGV, signal.SIGABRT, signal.SIGFPE):
            import contextlib
            with contextlib.suppress(ValueError, OSError):
                signal.signal(sig, self._on_system_signal)
        self._original_qt_handler = qInstallMessageHandler(self._on_qt_message)
        if self._worker_mgr and hasattr(self._worker_mgr, 'task_error'):
            self._worker_mgr.task_error.connect(self._on_worker_error)

    def _on_unhandled_exception(self, exc_type, exc_value, exc_tb):
        if getattr(self, '_handling_exception', False):
            return
        self._handling_exception = True
        try:
            report = self._build_report(exc_type=exc_type.__name__, exc_value=str(exc_value), traceback="".join(traceback.format_tb(exc_tb)))
            path = self._save_report(report)
            self.crash_occurred.emit(path)
        finally:
            self._handling_exception = False
        if self._original_excepthook and self._original_excepthook != sys.excepthook:
            self._original_excepthook(exc_type, exc_value, exc_tb)

    def _on_thread_exception(self, args):
        report = self._build_report(exc_type=args.exc_type.__name__ if args.exc_type else "Unknown", exc_value=str(args.exc_value) if args.exc_value else "", traceback="".join(traceback.format_tb(args.exc_tb)) if args.exc_tb else "", thread_name=args.thread.name if args.thread else "unknown")
        self._save_report(report)

    def _on_system_signal(self, signum, frame):
        sig_names = {signal.SIGSEGV: "SIGSEGV", signal.SIGABRT: "SIGABRT", signal.SIGFPE: "SIGFPE"}
        sig_name = sig_names.get(signum, f"Signal {signum}")
        try:
            report = self._build_report(exc_type=sig_name, exc_value="Native signal received", traceback="", signal=sig_name)
            path = self._save_report(report)
            self.crash_occurred.emit(path)
        except Exception:
            pass
        os._exit(128 + signum)

    def _on_qt_message(self, msg_type, context, message):
        if msg_type >= QtMsgType.QtWarningMsg:
            self._qt_messages.append(f"[{msg_type}] {message}")
            if len(self._qt_messages) > MAX_QT_MSGS:
                self._qt_messages.pop(0)
        if msg_type == QtMsgType.QtFatalMsg:
            report = self._build_report(exc_type="QtFatal", exc_value=message, traceback="")
            self._save_report(report)
        if self._original_qt_handler:
            self._original_qt_handler(msg_type, context, message)

    def _on_worker_error(self, task_id: str, error: str, code: str = ""):
        self._worker_errors.append({"task_id": task_id, "error": error, "code": code,
                                    "timestamp": datetime.datetime.now().isoformat()})
        self._log.error("Worker task '%s' failed [%s]: %s", task_id, code, error)

    def log_worker_error(self, task_id: str, error: str, code: str = ""):
        self._on_worker_error(task_id, error, code)

    def _build_report(self, *, exc_type="", exc_value="", traceback="", thread_name="main", signal="") -> dict:
        cwd_raw = os.getcwd()
        argv_raw = " ".join(sys.argv)
        env_raw = {k: v for k, v in sorted(os.environ.items()) if not k.startswith("MICHI_TEST_")}
        info = {
            "timestamp": datetime.datetime.now().isoformat(),
            "type": exc_type,
            "message": _redact_sensitive_strings(str(exc_value)),
            "traceback": _redact_sensitive_strings(traceback),
            "thread": thread_name,
            "signal": signal,
            "version": _get_version(),
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "cwd": _redact_home_path(cwd_raw),
            "argv": _redact_sensitive_strings(argv_raw),
            "qt_messages": [_redact_sensitive_strings(m) for m in self._qt_messages],
            "worker_errors": [{"task_id": e["task_id"], "error": _redact_sensitive_strings(e["error"]), "timestamp": e["timestamp"]} for e in self._worker_errors],
            "env": _redact_env(env_raw),
        }
        if info["qt_messages"]:
            self._qt_messages.clear()
        return info

    def _save_report(self, report: dict) -> str:
        from core.paths import logs_dir
        logs = logs_dir()
        if not os.path.isdir(logs):
            try:
                os.makedirs(logs, exist_ok=True)
            except OSError:
                self._log.error("Cannot create logs dir: %s", logs)
                return ""
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"crash_{ts}.json"
        path = os.path.join(logs, filename)
        try:
            _rotate_reports(logs, max_reports=MAX_REPORTS)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, default=str, ensure_ascii=False)
            self._log.critical("Crash report saved: %s", path)
        except Exception as e:
            self._log.error("Failed to save crash report: %s", e)
        return path


def _get_version() -> str:
    try:
        version_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "VERSION")
        if os.path.isfile(version_path):
            with open(version_path) as f:
                return f.read().strip()
    except Exception:
        pass
    return "unknown"


def _rotate_reports(logs_dir: str, max_reports: int = 10):
    import glob
    reports = sorted(glob.glob(os.path.join(logs_dir, "crash_*.json")))
    while len(reports) > max_reports:
        os.remove(reports.pop(0))
