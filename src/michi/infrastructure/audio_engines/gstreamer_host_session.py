"""Child-side engine session for the GStreamer output host.

Runs INSIDE the host process and drives one AudioPort-like engine
(production: ``GStreamerAudioPort``). It executes typed commands and
converts the engine's public callbacks into host protocol events.

It NEVER owns semantic authority: no playback state, no output session,
no Direct receipts, no Signal Truth classification. It reports primitive
facts and state transitions; the parent decides what they mean.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from michi.application.ports import AudioLoadError
from michi.infrastructure.audio_engines.gstreamer_host_direct import (
    HostDirectCoordinator,
    handle_from_wire,
    preparation_from_wire,
)
from michi.infrastructure.audio_engines.gstreamer_host_protocol import (
    HostEvent,
    HostOperation,
)

EmitEvent = Callable[[HostEvent, dict[str, Any]], None]


class EnginePort(Protocol):
    """Duck-typed subset of the canonical AudioPort used by the host."""

    def activate(self) -> None: ...

    def load(self, file_path: Path) -> None: ...

    def play(self) -> None: ...

    def pause(self) -> None: ...

    def resume(self) -> None: ...

    def stop(self) -> None: ...

    def seek(self, position_ms: int) -> None: ...

    def set_volume(self, value: int) -> None: ...

    def set_muted(self, muted: bool) -> None: ...

    def position(self) -> int: ...

    def duration(self) -> int: ...

    def close(self) -> None: ...


def default_gstreamer_port_factory(
    coordinator: HostDirectCoordinator,
) -> EnginePort:
    """Production factory: the canonical in-process port, inside the child."""
    from michi.infrastructure.audio_engines.gstreamer import (
        GStreamerAudioPort,
        GStreamerBindings,
    )

    return GStreamerAudioPort(GStreamerBindings(), direct_executor=coordinator)


class HostEngineSession:
    """Deterministic command -> engine adapter (child side)."""

    def __init__(
        self,
        *,
        port_factory: Callable[[HostDirectCoordinator], EnginePort],
        emit: EmitEvent,
        request_callback: Callable[[str, dict, float], tuple[bool, dict]],
    ) -> None:
        self._port_factory = port_factory
        self._emit = emit
        self._port: EnginePort | None = None
        self._opened = False
        self._coordinator = HostDirectCoordinator(request_callback)

    @property
    def opened(self) -> bool:
        return self._opened

    # ── dispatch ──────────────────────────────────────────────────────
    def handle(
        self, operation: str, payload: dict[str, Any], command_generation: int
    ) -> tuple[bool, dict[str, Any]]:
        handler = _HANDLERS.get(operation)
        if handler is None:
            return False, {
                "code": "OUTPUT_HOST_COMMAND_FAILED",
                "detail": f"unsupported operation {operation!r}",
            }
        _ = command_generation  # generation stamping lives in the caller
        try:
            return handler(self, payload)
        except AudioLoadError as exc:
            return False, {
                "code": "AUDIO_LOAD_FAILED",
                "detail": exc.detail,
                "previous_source_preserved": bool(exc.previous_source_preserved),
            }
        except Exception as exc:  # noqa: BLE001 - typed rejection boundary
            code = getattr(exc, "code", None) or type(exc).__name__
            return False, {"code": str(code), "detail": str(exc)[:1000]}

    # ── operations ────────────────────────────────────────────────────
    def _op_open(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        if self._port is not None:
            return True, {"already_open": True}
        port = self._port_factory(self._coordinator)
        port.activate()
        self._wire_subscriptions(port)
        self._port = port
        self._opened = True
        return True, {"opened": True}

    def _op_close_pipeline(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        port = self._require_port()
        port.close()
        self._port = None
        self._opened = False
        return True, {"closed": True}

    def _op_load(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        port = self._require_port()
        path = self._require_path(payload)
        port.load(path)
        return True, {}

    def _op_play(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        self._require_port().play()
        return True, {}

    def _op_pause(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        self._require_port().pause()
        return True, {}

    def _op_resume(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        self._require_port().resume()
        return True, {}

    def _op_stop(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        self._require_port().stop()
        return True, {}

    def _op_seek(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        position = payload.get("position_ms")
        if not isinstance(position, int) or isinstance(position, bool) or position < 0:
            return False, {
                "code": "OUTPUT_HOST_PROTOCOL_INVALID_FIELD",
                "detail": "position_ms must be a non-negative integer",
            }
        self._require_port().seek(position)
        return True, {}

    def _op_set_volume(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        value = payload.get("value")
        if not isinstance(value, int) or isinstance(value, bool):
            return False, {
                "code": "OUTPUT_HOST_PROTOCOL_INVALID_FIELD",
                "detail": "value must be an integer",
            }
        self._require_port().set_volume(value)
        return True, {}

    def _op_set_muted(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        muted = payload.get("muted")
        if not isinstance(muted, bool):
            return False, {
                "code": "OUTPUT_HOST_PROTOCOL_INVALID_FIELD",
                "detail": "muted must be a boolean",
            }
        self._require_port().set_muted(muted)
        return True, {}

    def _op_query_position(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        return True, {"value": int(self._require_port().position())}

    def _op_query_duration(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        return True, {"value": int(self._require_port().duration())}

    def _op_query_resync_evidence(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        port = self._require_port()
        evidence = getattr(port, "resync_evidence", None)
        if evidence is None:
            return True, {"evidence": {}}
        raw = evidence() or {}
        clean: dict[str, Any] = {}
        for key, value in raw.items():
            if (
                value is None
                or isinstance(value, str)
                or isinstance(value, int)
                and not isinstance(value, bool)
            ):
                clean[str(key)] = value
            else:
                return False, {
                    "code": "OUTPUT_HOST_PROTOCOL_INVALID_FIELD",
                    "detail": f"resync evidence field {key!r} is not primitive",
                }
        return True, {"evidence": clean}

    def _op_stage_direct(self, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        preparation = preparation_from_wire(payload.get("preparation"))
        port = self._require_port()
        # The port validates the staged recipe against the coordinator mirror,
        # so the mirror is populated first; a failed port stage rolls it back.
        self._coordinator.stage(preparation)
        try:
            port.stage_direct_load(preparation, executor=self._coordinator)  # type: ignore[attr-defined]
        except Exception:
            self._coordinator.discard(preparation.handle)
            raise
        return True, {}

    def _op_discard_direct(
        self, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        handle = handle_from_wire(payload.get("handle"))
        port = self._require_port()
        discarded = False
        stage = getattr(port, "discard_direct_load", None)
        if stage is not None:
            discarded = bool(stage(handle, executor=self._coordinator))
        self._coordinator.discard(handle)
        return True, {"discarded": discarded}

    # ── help ──────────────────────────────────────────────────────────
    def _require_port(self) -> EnginePort:
        if self._port is None:
            raise RuntimeError("engine is not open in this host")
        return self._port

    @staticmethod
    def _require_path(payload: dict[str, Any]) -> Path:
        path = payload.get("path")
        if not isinstance(path, str) or not path:
            raise ValueError("path must be a non-empty string")
        return Path(path)

    def _wire_subscriptions(self, port: EnginePort) -> None:
        emit = self._emit

        def state_changed(status: object) -> None:
            # PlaybackStatus is a name-identified enum: transport the NAME.
            value = getattr(status, "name", None) or str(status)
            emit(HostEvent.STATE_CHANGED, {"status": value})

        def media_accepted(path: Path) -> None:
            emit(HostEvent.MEDIA_ACCEPTED, {"path": str(path)})

        def media_rejected(path: Path, reason: str) -> None:
            emit(HostEvent.MEDIA_REJECTED, {"path": str(path), "reason": reason})

        def end_of_media() -> None:
            emit(HostEvent.EOS, {})

        def position_changed(ms: int) -> None:
            emit(HostEvent.POSITION, {"ms": int(ms)})

        def duration_changed(ms: int) -> None:
            emit(HostEvent.DURATION, {"ms": int(ms)})

        port.subscribe_playback_state_changed(state_changed)  # type: ignore[attr-defined]
        port.subscribe_media_accepted(media_accepted)  # type: ignore[attr-defined]
        port.subscribe_media_rejected(media_rejected)  # type: ignore[attr-defined]
        port.subscribe_end_of_media(end_of_media)  # type: ignore[attr-defined]
        port.subscribe_position_changed(position_changed)  # type: ignore[attr-defined]
        port.subscribe_duration_changed(duration_changed)  # type: ignore[attr-defined]
        failure_callback = getattr(port, "set_runtime_failure_callback", None)
        if failure_callback is not None:

            def runtime_failed(generation: int, reason: str) -> None:
                emit(
                    HostEvent.HOST_FAULT,
                    {"reason": reason, "port_generation": int(generation)},
                )

            failure_callback(runtime_failed)

    def close(self) -> None:
        """Best-effort port teardown before host exit."""
        port = self._port
        self._port = None
        self._opened = False
        if port is None:
            return
        import contextlib

        with contextlib.suppress(Exception):
            port.close()


#: Ops implemented in this phase (Direct staging lands in its own commit).
_HANDLERS: dict[str, Callable[[HostEngineSession, dict], tuple[bool, dict]]] = {
    HostOperation.OPEN.value: HostEngineSession._op_open,
    HostOperation.CLOSE_PIPELINE.value: HostEngineSession._op_close_pipeline,
    HostOperation.LOAD.value: HostEngineSession._op_load,
    HostOperation.PLAY.value: HostEngineSession._op_play,
    HostOperation.PAUSE.value: HostEngineSession._op_pause,
    HostOperation.RESUME.value: HostEngineSession._op_resume,
    HostOperation.STOP.value: HostEngineSession._op_stop,
    HostOperation.SEEK.value: HostEngineSession._op_seek,
    HostOperation.SET_VOLUME.value: HostEngineSession._op_set_volume,
    HostOperation.SET_MUTED.value: HostEngineSession._op_set_muted,
    HostOperation.QUERY_POSITION.value: HostEngineSession._op_query_position,
    HostOperation.QUERY_DURATION.value: HostEngineSession._op_query_duration,
    HostOperation.QUERY_RESYNC_EVIDENCE.value: (
        HostEngineSession._op_query_resync_evidence
    ),
    HostOperation.STAGE_DIRECT.value: HostEngineSession._op_stage_direct,
    HostOperation.DISCARD_DIRECT.value: HostEngineSession._op_discard_direct,
}
