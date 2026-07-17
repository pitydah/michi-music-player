"""Adapters for the unified GStreamer engine.

``EngineBackendAdapter`` exposes :class:`GStreamerEngine` through the public
``AudioBackend`` contract used by ``HybridAudioManager``.

The current engine constructor also instantiates this class as its private
transport. That compatibility path is isolated in ``GStreamerPipelineTransport``
so low-level Gst calls never recurse back through the public engine API.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402
from PySide6.QtCore import QObject, Signal  # noqa: E402

from audio.backends.types import AudioDiagnostics, BackendCapabilities, PlaybackSnapshot
from audio.player import GStreamerEngine, PlaybackState

logger = logging.getLogger("michi.audio.engine_adapter")


class GStreamerPipelineTransport:
    """Private pipeline and queue transport used by ``GStreamerEngine``."""

    def __init__(self, engine: GStreamerEngine):
        self._engine = engine
        self._pipeline = None
        self._callbacks: dict[str, Callable[..., Any]] = {}

    def set_callbacks(self, **callbacks: Callable[..., Any]) -> None:
        self._callbacks = {
            name: callback for name, callback in callbacks.items() if callable(callback)
        }

    def adopt_pipeline(self, pipeline) -> None:
        self._pipeline = pipeline

    def get_pipeline(self):
        return self._pipeline

    def pause(self) -> bool:
        if not self._pipeline:
            return False
        return self._pipeline.set_state(Gst.State.PAUSED) != Gst.StateChangeReturn.FAILURE

    def resume(self) -> bool:
        if not self._pipeline:
            return False
        return self._pipeline.set_state(Gst.State.PLAYING) != Gst.StateChangeReturn.FAILURE

    def stop(self) -> bool:
        if not self._pipeline:
            return True
        result = self._pipeline.set_state(Gst.State.NULL)
        return result != Gst.StateChangeReturn.FAILURE

    def seek(self, seconds: float) -> bool:
        if not self._pipeline:
            return False
        target = max(0, int(float(seconds) * Gst.SECOND))
        return bool(
            self._pipeline.seek_simple(
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                target,
            )
        )

    def set_volume(self, volume: int) -> bool:
        clamped = max(0, min(100, int(volume)))
        normalized = clamped / 100.0
        if not self._pipeline:
            return False

        candidates = (
            "software-volume",
            "replaygain-volume",
            "rg-volume",
            "volume",
            "playbin",
            "player",
        )
        for name in candidates:
            element = self._pipeline.get_by_name(name)
            if element is not None and element.find_property("volume") is not None:
                element.set_property("volume", normalized)
                return True

        if self._pipeline.find_property("volume") is not None:
            self._pipeline.set_property("volume", normalized)
            return True

        logger.debug("Active pipeline has no writable volume element")
        return False

    def set_queue(self, paths: list[str], start_index: int = 0) -> None:
        clean = [path for path in paths if isinstance(path, str) and path]
        self._engine._queue = clean
        self._engine._queue_index = (
            max(0, min(int(start_index), len(clean) - 1)) if clean else -1
        )

    def enqueue(self, paths: list[str], play_now: bool = True) -> None:
        clean = [path for path in paths if isinstance(path, str) and path]
        if not clean:
            return
        first_new_index = len(self._engine._queue)
        self._engine._queue.extend(clean)
        if play_now:
            self._engine._queue_index = first_new_index
            self._engine.play(clean[0])

    def enqueue_next(self, paths: list[str]) -> None:
        clean = [path for path in paths if isinstance(path, str) and path]
        if not clean:
            return
        insert_at = max(0, self._engine._queue_index + 1)
        self._engine._queue[insert_at:insert_at] = clean

    def clear_queue(self) -> None:
        self._engine._queue.clear()
        self._engine._queue_index = -1

    def play_next(self) -> bool:
        queue = self._engine._queue
        if not queue:
            return False

        current = self._engine._queue_index
        repeat_mode = getattr(self._engine, "_repeat", "none")
        if repeat_mode == "one" and 0 <= current < len(queue):
            target = current
        elif current + 1 < len(queue):
            target = current + 1
        elif repeat_mode == "all":
            target = 0
        else:
            return False

        self._engine._queue_index = target
        self._engine.play(queue[target])
        return True

    def play_prev(self) -> bool:
        queue = self._engine._queue
        if not queue:
            return False

        current = self._engine._queue_index
        repeat_mode = getattr(self._engine, "_repeat", "none")
        if repeat_mode == "one" and 0 <= current < len(queue):
            target = current
        elif current > 0:
            target = current - 1
        elif repeat_mode == "all":
            target = len(queue) - 1
        else:
            return False

        self._engine._queue_index = target
        self._engine.play(queue[target])
        return True

    def get_queue(self) -> list[dict[str, str]]:
        return [{"filepath": path} for path in self._engine._queue]

    def get_queue_index(self) -> int:
        return self._engine._queue_index

    def shutdown(self) -> None:
        self.stop()
        self._pipeline = None


class EngineBackendAdapter(QObject):
    """Expose ``GStreamerEngine`` through the public AudioBackend contract.

    ``GStreamerEngine`` currently creates the first adapter instance while it
    is constructing itself. That instance automatically enters transport mode.
    The adapter created later by ``PlayerService`` remains the public wrapper.
    """

    backend_id = "gstreamer"
    name = "GStreamer (Engine)"

    position_changed = Signal(float)
    state_changed = Signal(str)
    duration_changed = Signal(float)

    def __init__(
        self,
        engine: GStreamerEngine,
        parent=None,
        *,
        internal_transport: bool | None = None,
    ):
        super().__init__(parent)
        self._engine = engine
        self._callbacks: dict[str, Callable[..., Any]] = {}

        if internal_transport is None:
            internal_transport = (
                type(engine).__name__ == "GStreamerEngine"
                and not hasattr(engine, "_backend")
            )
        self._transport = (
            GStreamerPipelineTransport(engine) if internal_transport else None
        )

        self._engine.position_changed.connect(self.position_changed)
        self._engine.duration_changed.connect(self.duration_changed)
        self._engine.state_changed.connect(
            lambda state: self.state_changed.emit(
                {
                    PlaybackState.PLAYING: "playing",
                    PlaybackState.PAUSED: "paused",
                    PlaybackState.STOPPED: "stopped",
                }.get(state, "stopped")
            )
        )

    @property
    def is_internal_transport(self) -> bool:
        return self._transport is not None

    def set_callbacks(self, **callbacks: Callable[..., Any]) -> None:
        self._callbacks = {
            name: callback for name, callback in callbacks.items() if callable(callback)
        }
        if self._transport is not None:
            self._transport.set_callbacks(**self._callbacks)

    def adopt_pipeline(self, pipeline) -> None:
        if self._transport is None:
            raise RuntimeError("Public EngineBackendAdapter cannot own a Gst pipeline")
        self._transport.adopt_pipeline(pipeline)

    def get_pipeline(self):
        if self._transport is None:
            return None
        return self._transport.get_pipeline()

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            backend_id="gstreamer",
            display_name="GStreamer (Engine)",
            supports_digital_volume=True,
            supports_eq=True,
            supports_replaygain=True,
            supports_spectrum=True,
            supports_radio=True,
            supports_streams=True,
            supports_bitperfect=True,
            supports_dsd=True,
            supports_dop=True,
        )

    def play(self, path_or_uri: str) -> None:
        self._engine.play(path_or_uri)

    def pause(self):
        if self._transport is not None:
            return self._transport.pause()
        return self._engine.pause()

    def resume(self):
        if self._transport is not None:
            return self._transport.resume()
        return self._engine.resume()

    def stop(self):
        if self._transport is not None:
            return self._transport.stop()
        return self._engine.stop()

    def seek(self, seconds: float):
        if self._transport is not None:
            return self._transport.seek(seconds)
        return self._engine.seek(seconds)

    def toggle(self) -> None:
        self._engine.toggle()

    def set_volume(self, volume: int):
        clamped = max(0, min(100, int(volume)))
        if self._transport is not None:
            return self._transport.set_volume(clamped)
        return self._engine.set_volume(clamped)

    def get_snapshot(self) -> PlaybackSnapshot:
        state_map = {
            PlaybackState.PLAYING: "playing",
            PlaybackState.PAUSED: "paused",
            PlaybackState.STOPPED: "stopped",
        }
        return PlaybackSnapshot(
            backend_id="gstreamer",
            state=state_map.get(self._engine.state, "stopped"),
            current_path=self._engine.current or "",
            position_seconds=(
                self._engine.get_position_ns() / 1e9
                if hasattr(self._engine, "get_position_ns")
                else 0.0
            ),
            volume=int(getattr(self._engine, "_volume", 0.7) * 100),
            queue_index=getattr(self._engine, "_queue_index", -1),
            queue_length=len(getattr(self._engine, "_queue", [])),
        )

    def get_diagnostics(self) -> AudioDiagnostics:
        eq = getattr(self._engine, "_eq", None)
        eq_active = bool(eq and getattr(eq, "mode", "bypass") != "bypass")
        return AudioDiagnostics(
            backend_id="gstreamer",
            profile=getattr(self._engine, "_audio_profile", "default") or "default",
            device_name=getattr(getattr(self._engine, "_dac", None), "device", "") or "",
            dsp_active=(
                eq_active
                or bool(getattr(self._engine, "_replaygain", False))
                or bool(getattr(self._engine, "_spectrum_enabled", False))
            ),
            eq_active=eq_active,
            replaygain_active=bool(getattr(self._engine, "_replaygain", False)),
            spectrum_active=bool(getattr(self._engine, "_spectrum_enabled", False)),
            digital_volume_active=True,
        )

    def set_queue(self, paths: list[str], start_index: int = 0) -> None:
        if self._transport is not None:
            self._transport.set_queue(paths, start_index)
        else:
            self._engine.set_queue(paths, start_index)

    def enqueue(self, paths: list[str], play_now: bool = True) -> None:
        if self._transport is not None:
            self._transport.enqueue(paths, play_now)
        else:
            self._engine.enqueue(paths, play_now)

    def enqueue_next(self, paths: list[str]) -> None:
        if self._transport is not None:
            self._transport.enqueue_next(paths)
        else:
            self._engine.enqueue_next(paths)

    def clear_queue(self) -> None:
        if self._transport is not None:
            self._transport.clear_queue()
        else:
            self._engine.clear_queue()

    def play_next(self) -> bool:
        if self._transport is not None:
            return self._transport.play_next()
        return self._engine.play_next()

    def play_prev(self) -> bool:
        if self._transport is not None:
            return self._transport.play_prev()
        return self._engine.play_prev()

    def get_queue(self) -> list[dict]:
        if self._transport is not None:
            return self._transport.get_queue()
        return self._engine.get_queue()

    def get_queue_index(self) -> int:
        if self._transport is not None:
            return self._transport.get_queue_index()
        return self._engine.get_queue_index()

    def shutdown(self) -> None:
        if self._transport is not None:
            self._transport.shutdown()
        else:
            self._engine.stop()
