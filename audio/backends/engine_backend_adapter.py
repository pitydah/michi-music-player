"""EngineBackendAdapter — wraps GStreamerEngine as an AudioBackend for HybridAudioManager.

This is the EXTERNAL adapter. It wraps GStreamerEngine for use by HybridAudioManager
and PlayerService. GStreamerEngine internally uses GStreamerPipelineTransport.
There is exactly ONE EngineBackendAdapter instance per engine.
"""
from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QObject, Signal

from audio.backends.types import PlaybackSnapshot, AudioDiagnostics, BackendCapabilities
from audio.player import GStreamerEngine, PlaybackState

logger = logging.getLogger("michi.audio.engine_adapter")


class EngineBackendAdapter(QObject):
    """Adapt one GStreamerEngine instance to the AudioBackend contract."""

    backend_id = "gstreamer"
    name = "GStreamer (Engine)"

    position_changed = Signal(float)
    state_changed = Signal(str)
    duration_changed = Signal(float)
    queue_progressed = Signal(int, str, str, object)

    def __init__(self, engine: GStreamerEngine, parent=None):
        super().__init__(parent)
        self._engine = engine

        self._engine.position_changed.connect(self.position_changed)
        self._engine.duration_changed.connect(self.duration_changed)
        self._engine.state_changed.connect(lambda s: self.state_changed.emit(
            {PlaybackState.PLAYING: "playing", PlaybackState.PAUSED: "paused",
             PlaybackState.STOPPED: "stopped"}.get(s, "stopped")))
        self._engine.queue_progressed.connect(self.queue_progressed)

    def set_callbacks(self, **kwargs: Any) -> None:
        on_state = kwargs.get("on_state_changed")
        on_track_ended = kwargs.get("on_track_ended")
        on_position = kwargs.get("on_position_updated")
        on_error = kwargs.get("on_error")
        if on_state:
            self._engine.state_changed.connect(on_state)
        if on_track_ended:
            self._engine.finished.connect(on_track_ended)
        if on_position:
            self._engine.position_changed.connect(on_position)
        if on_error:
            self._engine.error_occurred.connect(on_error)

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            backend_id="gstreamer", display_name="GStreamer (Engine)",
            supports_digital_volume=True, supports_eq=True,
            supports_replaygain=True, supports_spectrum=True,
            supports_radio=True, supports_streams=True,
            supports_bitperfect=True, supports_dsd=True,
            supports_dop=True,
        )

    def play(self, path_or_uri: str) -> None:
        self._engine.play(path_or_uri)

    def pause(self) -> None:
        self._engine.pause()

    def resume(self) -> None:
        self._engine.resume()

    def stop(self) -> None:
        self._engine.stop()

    def seek(self, seconds: float) -> None:
        self._engine.seek(seconds)

    def toggle(self) -> None:
        self._engine.toggle()

    def set_volume(self, volume: int) -> None:
        clamped = max(0, min(100, int(volume)))
        self._engine.set_volume(clamped)

    def set_repeat(self, mode: str) -> str:
        return self._engine.set_repeat(mode)

    def set_shuffle(self, enabled: bool) -> bool:
        # QueueService supplies the effective order; the engine must not reshuffle it.
        return self._engine.set_shuffle(enabled)

    def get_snapshot(self) -> PlaybackSnapshot:
        s = self._engine.state
        state_map = {
            PlaybackState.PLAYING: "playing",
            PlaybackState.PAUSED: "paused",
            PlaybackState.STOPPED: "stopped",
        }
        return PlaybackSnapshot(
            backend_id="gstreamer",
            state=state_map.get(s, "stopped"),
            current_path=self._engine.current or "",
            position_seconds=self._engine.get_position_ns() / 1e9 if hasattr(self._engine, 'get_position_ns') else 0.0,
            duration_seconds=float(getattr(self._engine, "_duration", 0.0)),
            volume=self._normalized_volume(),
            queue_index=getattr(self._engine, '_queue_index', -1),
            queue_length=len(getattr(self._engine, '_queue', [])),
        )

    def get_diagnostics(self) -> AudioDiagnostics:
        return AudioDiagnostics(
            backend_id="gstreamer",
            profile=getattr(self._engine, '_audio_profile', 'default') or 'default',
            device_name="",
            dsp_active=getattr(self._engine, '_eq', None) is not None,
            eq_active=getattr(self._engine, '_eq', None) is not None,
            replaygain_active=getattr(self._engine, '_replaygain', False),
            spectrum_active=getattr(self._engine, '_spectrum_enabled', False),
            digital_volume_active=True,
        )

    def _normalized_volume(self) -> int:
        volume = float(getattr(self._engine, "_volume", 70))
        return int(volume * 100) if 0.0 <= volume <= 1.0 else int(volume)

    def set_queue(self, paths: list[str], start_index: int = 0,
                  revision: int | None = None) -> None:
        self._engine.set_queue(paths, start_index, revision=revision)

    def enqueue(self, paths: list[str], play_now: bool = True) -> None:
        self._engine._queue.extend(paths)
        if play_now and paths:
            self._engine.play(paths[0])

    def enqueue_next(self, paths: list[str]) -> None:
        idx = self._engine._queue_index
        for p in reversed(paths):
            self._engine._queue.insert(idx + 1, p)

    def clear_queue(self) -> None:
        self._engine._queue.clear()
        self._engine._queue_index = -1

    def play_next(self) -> bool:
        return self._engine.play_next()

    def play_prev(self) -> bool:
        return self._engine.play_prev()

    def play_queue_index(self, index: int) -> bool:
        if index < 0 or index >= len(self._engine._queue):
            return False
        self._engine._queue_index = index
        self._engine.play(self._engine._queue[index])
        return True

    def get_queue(self) -> list[dict]:
        return [{"filepath": p} for p in getattr(self._engine, '_queue', [])]

    def get_queue_index(self) -> int:
        return getattr(self._engine, '_queue_index', -1)

    def shutdown(self) -> None:
        self._engine.stop()
