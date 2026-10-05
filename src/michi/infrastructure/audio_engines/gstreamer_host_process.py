"""Real GStreamer OUTPUT HOST process entry point (``python -m ... --fd N``).

This process owns ALL native GStreamer lifecycle objects. It is disposable:
the parent supervises it, bounds every request with a parent-side deadline,
and kills/reaps it when it wedges. It never owns playback/output/Direct/
Signal Truth semantics — it executes typed commands and reports primitive
facts, states and events.

Fresh interpreter only (spawned by the supervisor); GStreamer initializes
INSIDE this process. No live Qt/GLib/Gst object ever crosses the boundary.
The canonical port runs here unchanged; Qt event delivery inside the child
is serviced by a QCoreApplication loop owned by this process.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import platform
import socket
import sys
import threading
from collections.abc import Callable
from typing import Any

from michi.infrastructure.audio_engines.gstreamer_host_protocol import (
    GST_HOST_PROTOCOL_VERSION,
    FrameDecoder,
    HostEvent,
    HostOperation,
    HostProtocolError,
    MessageKind,
    encode_message,
    error_payload,
    make_message,
)
from michi.infrastructure.audio_engines.gstreamer_host_session import (
    HostEngineSession,
    default_gstreamer_port_factory,
)


class GStreamerHostRuntime:
    """Lazy native runtime information owned entirely by this process."""

    def __init__(self) -> None:
        self._loaded = False
        self._gstreamer_version: str | None = None
        self._playbin3_available: bool | None = None
        self._failure: str | None = None

    def describe(self) -> dict[str, Any]:
        self._ensure_loaded()
        return {
            "protocol_version": GST_HOST_PROTOCOL_VERSION,
            "python_version": platform.python_version(),
            "pid": os.getpid(),
            "gstreamer_version": self._gstreamer_version,
            "playbin3_available": bool(self._playbin3_available),
            "runtime_failure": self._failure,
        }

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        try:
            import gi

            gi.require_version("Gst", "1.0")
            from gi.repository import Gst

            Gst.init(None)
            self._gstreamer_version = str(Gst.version_string())
            self._playbin3_available = Gst.ElementFactory.find("playbin3") is not None
        except Exception as exc:  # noqa: BLE001 - reported, never fatal here
            self._failure = f"{type(exc).__name__}: {exc}"


class GStreamerHostMain:
    def __init__(
        self,
        channel: socket.socket,
        *,
        engine_port_factory: Callable[[], Any] | None = None,
        runtime: Any | None = None,
    ) -> None:
        self._channel = channel
        self._channel.settimeout(0.05)
        self._decoder = FrameDecoder()
        self._runtime = runtime if runtime is not None else GStreamerHostRuntime()
        self._host_generation = 0
        self._command_generation = 0
        self._shutdown_requested = False
        self._send_lock = threading.Lock()
        self._app = None  # QCoreApplication when the real engine runs here
        if engine_port_factory is None:
            engine_port_factory = default_gstreamer_port_factory
            self._app = self._ensure_qt_application()
        self._engine = HostEngineSession(
            port_factory=engine_port_factory,
            emit=self._emit_event,
        )

    # ── loop ──────────────────────────────────────────────────────────
    def serve(self) -> int:
        while not self._shutdown_requested:
            try:
                chunk = self._channel.recv(65536)
            except TimeoutError:
                self._pump_qt()
                continue
            except OSError:
                self._engine.close()
                return 2
            if not chunk:
                self._engine.close()
                return 0
            try:
                frames = self._decoder.feed(chunk)
            except HostProtocolError as exc:
                with contextlib.suppress(Exception):
                    self._emit_fault(
                        request_id=None,
                        code="OUTPUT_HOST_PROTOCOL_ERROR",
                        detail=exc.detail,
                    )
                return 3
            for frame in frames:
                self._route(frame)
            self._pump_qt()
        return 0

    def _pump_qt(self) -> None:
        if self._app is not None:
            with contextlib.suppress(Exception):
                self._app.processEvents()

    @staticmethod
    def _ensure_qt_application():
        try:
            from PySide6.QtCore import QCoreApplication

            app = QCoreApplication.instance()
            if app is None:
                app = QCoreApplication([])
            return app
        except Exception:  # noqa: BLE001 - absence is reported by the engine
            return None

    def _route(self, frame: dict[str, Any]) -> None:
        self._host_generation = int(frame.get("host_generation", 0))
        self._command_generation = int(frame.get("command_generation", 0))
        if frame["kind"] != MessageKind.COMMAND.value:
            return
        request_id = frame.get("request_id")
        operation = frame.get("operation")
        payload = frame.get("payload") or {}
        try:
            if operation == HostOperation.HELLO.value:
                self._respond(MessageKind.HELLO, request_id, self._runtime.describe())
                return
            if operation == HostOperation.PING.value:
                self._respond(
                    MessageKind.RESULT,
                    request_id,
                    {"pong": True, "host_generation": self._host_generation},
                )
                return
            if operation == HostOperation.SHUTDOWN.value:
                self._engine.close()
                self._respond(
                    MessageKind.SHUTDOWN_COMPLETE,
                    request_id,
                    {"termination": "GRACEFUL"},
                )
                self._shutdown_requested = True
                return
            ok, result = self._engine.handle(
                str(operation), payload, self._command_generation
            )
            if ok:
                self._respond(MessageKind.RESULT, request_id, result)
            else:
                self._respond(MessageKind.REJECTED, request_id, result)
        except Exception as exc:  # noqa: BLE001 - typed fault response
            self._respond(
                MessageKind.FAULT,
                request_id,
                error_payload("OUTPUT_HOST_COMMAND_FAILED", str(exc)),
            )

    # ── frames ────────────────────────────────────────────────────────
    def _respond(
        self, kind: MessageKind, request_id: str | None, payload: dict[str, Any]
    ) -> None:
        frame = make_message(
            kind,
            host_generation=self._host_generation,
            command_generation=self._command_generation,
            request_id=request_id,
            payload=payload,
        )
        self._send(frame)

    def _emit_event(self, event: HostEvent, payload: dict[str, Any]) -> None:
        frame = make_message(
            MessageKind.EVENT,
            host_generation=self._host_generation,
            command_generation=self._command_generation,
            payload={"event": str(event), **payload},
        )
        with contextlib.suppress(Exception):
            self._send(frame)

    def _emit_fault(self, *, request_id: str | None, code: str, detail: str) -> None:
        frame = make_message(
            MessageKind.FAULT,
            host_generation=self._host_generation,
            command_generation=self._command_generation,
            request_id=request_id,
            payload=error_payload(code, detail),
        )
        with contextlib.suppress(Exception):
            self._send(frame)

    def _send(self, frame: dict[str, Any]) -> None:
        encoded = encode_message(frame)
        with self._send_lock:
            self._channel.sendall(encoded)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Michi GStreamer output host")
    parser.add_argument("--fd", type=int, required=True)
    args = parser.parse_args(argv)
    channel = socket.socket(fileno=args.fd)
    channel.setblocking(True)
    return GStreamerHostMain(channel).serve()


if __name__ == "__main__":  # pragma: no cover - process entry
    sys.exit(main())
