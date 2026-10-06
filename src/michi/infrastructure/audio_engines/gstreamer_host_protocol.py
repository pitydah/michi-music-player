"""Versioned, bounded IPC protocol for the GStreamer output host.

The productive GStreamer native lifecycle (pipeline construction, state
transitions, bus observation) will run in a supervised child process; the
parent keeps every semantic authority (playback session, output session,
engine policy, generation, Direct receipts, Signal Truth).

This module is stdlib-only and shared by both sides:

* the parent supervisor (``gstreamer_host_client``),
* the real host process (``gstreamer_host_process``),
* test doubles.

Wire format: 4-byte big-endian length prefix + UTF-8 JSON object, over a
private ``AF_UNIX`` socket pair created by the parent. Every frame is
size-bounded and strictly validated; a protocol violation is a typed
``HostProtocolError``, never an unbounded read or an exception leak.
"""

from __future__ import annotations

import json
import struct
from enum import StrEnum
from typing import Any

#: Exact supported protocol version. A mismatch fails closed on both ends.
GST_HOST_PROTOCOL_VERSION = 1

#: Hard frame ceiling (length prefix included) for every direction.
MAX_FRAME_BYTES = 262_144

_LENGTH = struct.Struct(">I")

#: Envelope keys every frame must carry.
REQUIRED_ENVELOPE_KEYS = (
    "protocol_version",
    "kind",
    "request_id",
    "host_generation",
    "command_generation",
    "operation",
    "payload",
)


class HostProtocolError(RuntimeError):
    """Typed protocol boundary failure (malformed, oversized, version...)."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


class MessageKind(StrEnum):
    # parent -> host commands
    COMMAND = "command"
    # host -> parent responses to a command
    ACK = "ack"
    RESULT = "result"
    REJECTED = "rejected"
    FAULT = "fault"
    HELLO = "hello"
    SHUTDOWN_COMPLETE = "shutdown_complete"
    # host -> parent asynchronous events (never a response)
    EVENT = "event"
    # host -> parent synchronous reverse callback (bounded wait), parent -> host
    CALLBACK = "callback"
    CALLBACK_RESULT = "callback_result"
    CALLBACK_REJECTED = "callback_rejected"


class HostOperation(StrEnum):
    HELLO = "hello"
    PING = "ping"
    OPEN = "open"
    LOAD = "load"
    PLAY = "play"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"
    SEEK = "seek"
    SET_VOLUME = "set_volume"
    SET_MUTED = "set_muted"
    QUERY_POSITION = "query_position"
    QUERY_DURATION = "query_duration"
    QUERY_RESYNC_EVIDENCE = "query_resync_evidence"
    STAGE_DIRECT = "stage_direct"
    DISCARD_DIRECT = "discard_direct"
    ABORT_CANDIDATE = "abort_candidate"
    CLOSE_PIPELINE = "close_pipeline"
    SHUTDOWN = "shutdown"


class HostEvent(StrEnum):
    STATE_CHANGED = "state_changed"
    MEDIA_ACCEPTED = "media_accepted"
    MEDIA_REJECTED = "media_rejected"
    POSITION = "position"
    DURATION = "duration"
    EOS = "eos"
    ERROR = "error"
    ASYNC_DONE = "async_done"
    RUNTIME_SNAPSHOT = "runtime_snapshot"
    PREVIOUS_SOURCE_RELEASED = "previous_source_released"
    HOST_HEARTBEAT = "host_heartbeat"
    HOST_FAULT = "host_fault"


class HostCallback(StrEnum):
    """Host -> parent reversals that need a parent-side verdict."""

    VERIFY_PREROLL = "verify_preroll"
    RELEASE = "release"
    BEGIN_RUNTIME = "begin_runtime"
    OBSERVE_RUNTIME = "observe_runtime"
    RECORD_RUNTIME_ANOMALY = "record_runtime_anomaly"
    ABORT = "abort"
    RECIPE_FOR_LOAD = "recipe_for_load"


def make_message(
    kind: MessageKind,
    *,
    host_generation: int = 0,
    command_generation: int = 0,
    request_id: str | None = None,
    operation: HostOperation | None = None,
    payload: dict[str, Any] | None = None,
    protocol_version: int = GST_HOST_PROTOCOL_VERSION,
) -> dict[str, Any]:
    """Build a canonical envelope (still validated by the codec)."""
    return {
        "protocol_version": int(protocol_version),
        "kind": str(kind),
        "request_id": request_id,
        "host_generation": int(host_generation),
        "command_generation": int(command_generation),
        "operation": None if operation is None else str(operation),
        "payload": {} if payload is None else payload,
    }


def validate_message(message: Any) -> dict[str, Any]:
    """Strict envelope + payload validation. Raises ``HostProtocolError``."""
    if not isinstance(message, dict):
        raise HostProtocolError("HOST_PROTOCOL_MALFORMED", "frame is not a JSON object")
    missing = [key for key in REQUIRED_ENVELOPE_KEYS if key not in message]
    if missing:
        raise HostProtocolError(
            "HOST_PROTOCOL_MALFORMED", f"missing envelope keys: {missing}"
        )
    version = message["protocol_version"]
    if not isinstance(version, int) or isinstance(version, bool):
        raise HostProtocolError(
            "HOST_PROTOCOL_MALFORMED", "protocol_version must be an integer"
        )
    if version != GST_HOST_PROTOCOL_VERSION:
        raise HostProtocolError(
            "HOST_PROTOCOL_VERSION",
            f"unsupported protocol_version {version!r}",
        )
    kind = message["kind"]
    try:
        MessageKind(kind)
    except ValueError as exc:
        raise HostProtocolError(
            "HOST_PROTOCOL_UNKNOWN_KIND", f"unknown message kind {kind!r}"
        ) from exc
    request_id = message["request_id"]
    if request_id is not None and not isinstance(request_id, str):
        raise HostProtocolError(
            "HOST_PROTOCOL_INVALID_FIELD", "request_id must be a string or null"
        )
    for field in ("host_generation", "command_generation"):
        value = message[field]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise HostProtocolError(
                "HOST_PROTOCOL_INVALID_FIELD",
                f"{field} must be a non-negative integer",
            )
    operation = message["operation"]
    if operation is not None:
        if not isinstance(operation, str):
            raise HostProtocolError(
                "HOST_PROTOCOL_INVALID_FIELD", "operation must be a string or null"
            )
        try:
            HostOperation(operation)
        except ValueError as exc:
            raise HostProtocolError(
                "HOST_PROTOCOL_UNKNOWN_OPERATION",
                f"unknown operation {operation!r}",
            ) from exc
    if not isinstance(message["payload"], dict):
        raise HostProtocolError(
            "HOST_PROTOCOL_INVALID_FIELD", "payload must be an object"
        )
    return message


def encode_message(message: dict[str, Any]) -> bytes:
    """Validate + frame a message. Never emit an invalid or oversized frame."""
    validate_message(message)
    body = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    if len(body) + _LENGTH.size > MAX_FRAME_BYTES:
        raise HostProtocolError(
            "HOST_PROTOCOL_OVERSIZED",
            f"encoded frame of {len(body)} bytes exceeds the protocol ceiling",
        )
    return _LENGTH.pack(len(body)) + body


class FrameDecoder:
    """Incremental byte-stream decoder with a strict size ceiling."""

    __slots__ = ("_buffer",)

    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, chunk: bytes) -> list[dict[str, Any]]:
        if not chunk:
            return []
        self._buffer.extend(chunk)
        frames: list[dict[str, Any]] = []
        while True:
            if len(self._buffer) < _LENGTH.size:
                break
            (length,) = _LENGTH.unpack_from(self._buffer, 0)
            if length == 0:
                raise HostProtocolError("HOST_PROTOCOL_MALFORMED", "zero-length frame")
            if length + _LENGTH.size > MAX_FRAME_BYTES:
                raise HostProtocolError(
                    "HOST_PROTOCOL_OVERSIZED",
                    f"declared frame length {length} exceeds the ceiling",
                )
            if len(self._buffer) < _LENGTH.size + length:
                break
            body = bytes(self._buffer[_LENGTH.size : _LENGTH.size + length])
            del self._buffer[: _LENGTH.size + length]
            try:
                decoded = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise HostProtocolError(
                    "HOST_PROTOCOL_MALFORMED", f"invalid JSON frame: {exc}"
                ) from exc
            frames.append(validate_message(decoded))
        return frames


def event_is_current(
    message: dict[str, Any],
    *,
    expected_host_generation: int,
    expected_command_generation: int,
) -> bool:
    """Two-domain generation fence.

    An event/result is current only when BOTH the host incarnation and the
    command/pipeline generation match. A new host incarnation (new process)
    invalidates every earlier frame even if the command generation repeats.
    """
    return (
        message.get("host_generation") == expected_host_generation
        and message.get("command_generation") == expected_command_generation
    )


def error_payload(code: str, detail: str) -> dict[str, Any]:
    return {"code": str(code), "detail": str(detail)[:2000]}
