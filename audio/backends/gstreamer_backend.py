"""GStreamerAudioBackend — production audio backend using GStreamer pipeline."""

from __future__ import annotations

import logging
import contextlib
import os

from audio.backends.types import PlaybackSnapshot, AudioDiagnostics, BackendCapabilities
from audio.pipeline_factory import PipelineFactory, AudioFormatInfo, AudioRoutePlan, DspState

logger = logging.getLogger("michi.audio.gstreamer")


def _path_to_file_uri(path: str) -> str:
    """Convert a local file path to a file:// URI."""
    if path.startswith('file://') or path.startswith('http://') or path.startswith('https://'):
        return path
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    return 'file://' + path


class GStreamerAudioBackend:
    backend_id = "gstreamer"
    name = "GStreamer"

    def __init__(self):
        self._pipeline = None
        self._playing = False
        self._volume = 1.0
        self._position = 0.0
        self._duration = 0.0
        self._queue: list[str] = []
        self._queue_index = -1

        self._on_state_changed = None
        self._on_track_ended = None
        self._on_position_updated = None
        self._on_error = None

    def set_callbacks(self, *, on_state_changed=None, on_track_ended=None,
                      on_position_updated=None, on_error=None):
        self._on_state_changed = on_state_changed
        self._on_track_ended = on_track_ended
        self._on_position_updated = on_position_updated
        self._on_error = on_error

    def adopt_pipeline(self, pipeline):
        self._pipeline = pipeline
        self._playing = False

    def get_pipeline(self):
        return self._pipeline

    @staticmethod
    def _ensure_gst():
        try:
            import gi
            gi.require_version("Gst", "1.0")
            from gi.repository import Gst
            Gst.init(None)
            return Gst
        except ImportError:
            return None

    def play(self, uri: str) -> bool:
        Gst = self._ensure_gst()
        if Gst is None:
            return False
        try:
            file_uri = _path_to_file_uri(uri)
            playbin = Gst.ElementFactory.make("playbin", "player")
            playbin.set_property("uri", file_uri)

            # Attach advanced audio sink (EQ, volume, spectrum) if available
            try:
                route = AudioRoutePlan()
                dsp = DspState()
                factory = PipelineFactory()
                sink = factory.build_playbin_audio_sink(route, dsp)
                if sink:
                    playbin.set_property("audio-sink", sink)
            except Exception:
                pass  # Fall back to playbin default sink

            self._pipeline = playbin
            self._pipeline.set_state(Gst.State.PLAYING)
            self._playing = True
            return True
        except Exception as e:
            logger.error("GStreamer play failed: %s", e)
            return False

    def pause(self):
        Gst = self._ensure_gst()
        if self._pipeline and Gst:
            try:
                self._pipeline.set_state(Gst.State.PAUSED)
                self._playing = False
            except Exception:
                pass

    def resume(self):
        Gst = self._ensure_gst()
        if self._pipeline and Gst:
            try:
                self._pipeline.set_state(Gst.State.PLAYING)
                self._playing = True
            except Exception:
                pass

    def stop(self):
        if self._pipeline:
            try:
                import gi
                gi.require_version("Gst", "1.0")
                from gi.repository import Gst
                self._pipeline.set_state(Gst.State.NULL)
            except Exception:
                pass
        self._playing = False
        self._position = 0.0

    def seek(self, position: float):
        if self._pipeline:
            try:
                import gi
                gi.require_version("Gst", "1.0")
                from gi.repository import Gst
                self._pipeline.seek_simple(
                    Gst.Format.TIME, Gst.SeekFlags.FLUSH,
                    int(position * Gst.SECOND))
            except Exception:
                pass

    def set_volume(self, volume: int):
        clamped = max(0, min(100, int(volume)))
        self._volume = clamped / 100.0
        if self._pipeline:
            with contextlib.suppress(Exception):
                self._pipeline.set_property("volume", self._volume)

    def toggle(self):
        if self._playing:
            self.pause()
        else:
            self.resume()

    def get_snapshot(self) -> PlaybackSnapshot:
        state = "playing" if self._playing else ("paused" if self._pipeline and hasattr(self._pipeline, 'set_state') else "stopped")
        return PlaybackSnapshot(
            backend_id="gstreamer",
            state=state,
            position_seconds=self.get_position(),
            duration_seconds=self.get_duration(),
            volume=int(self._volume * 100),
            queue_index=self._queue_index,
            queue_length=len(self._queue),
        )

    def get_diagnostics(self) -> AudioDiagnostics:
        return AudioDiagnostics(
            backend_id="gstreamer",
            profile="default",
            device_name="default",
            dsp_active=False,
            eq_active=False,
            replaygain_active=False,
            spectrum_active=False,
            digital_volume_active=True,
        )

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            backend_id="gstreamer",
            display_name="GStreamer",
            supports_seek=True,
            supports_queue=True,
            supports_digital_volume=True,
        )

    def get_position(self) -> float:
        Gst = self._ensure_gst()
        if self._pipeline and Gst:
            try:
                ok, pos = self._pipeline.query_position(Gst.Format.TIME)
                if ok:
                    self._position = pos / float(Gst.SECOND)
            except Exception:
                pass
        return self._position

    def get_duration(self) -> float:
        Gst = self._ensure_gst()
        if self._pipeline and Gst:
            try:
                ok, dur = self._pipeline.query_duration(Gst.Format.TIME)
                if ok:
                    self._duration = dur / float(Gst.SECOND)
            except Exception:
                pass
        return self._duration

    @property
    def is_playing(self) -> bool:
        return self._playing

    def health(self) -> dict:
        return {"available": True, "playing": self._playing,
                "volume": self._volume, "pipeline": self._pipeline is not None}

    def shutdown(self):
        self.stop()

    def set_queue(self, paths: list[str], start_index: int = 0):
        self._queue = list(paths)
        self._queue_index = start_index
        if start_index >= 0 and start_index < len(self._queue):
            self.play(self._queue[start_index])

    def enqueue(self, paths: list[str], play_now: bool = True):
        self._queue.extend(paths)
        if play_now and self._queue_index < 0 and self._queue:
            self._queue_index = 0
            self.play(self._queue[0])

    def enqueue_next(self, paths: list[str]):
        pos = self._queue_index + 1 if self._queue_index >= 0 else len(self._queue)
        for i, p in enumerate(paths):
            self._queue.insert(pos + i, p)

    def clear_queue(self):
        self._queue.clear()
        self._queue_index = -1

    def play_next(self) -> bool:
        if self._queue_index < len(self._queue) - 1:
            self._queue_index += 1
            self.play(self._queue[self._queue_index])
            return True
        return False

    def play_prev(self) -> bool:
        if self._queue_index > 0:
            self._queue_index -= 1
            self.play(self._queue[self._queue_index])
            return True
        return False

    def get_queue(self) -> list[dict]:
        return [{"filepath": p} for p in self._queue]

    def get_queue_index(self) -> int:
        return self._queue_index
