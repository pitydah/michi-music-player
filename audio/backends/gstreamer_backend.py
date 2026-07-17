"""GStreamerAudioBackend — production audio backend using GStreamer pipeline."""

from __future__ import annotations

import logging
import contextlib

logger = logging.getLogger("michi.audio.gstreamer")


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

    def play(self, uri: str) -> bool:
        try:
            import gi
            gi.require_version("Gst", "1.0")
            from gi.repository import Gst
            Gst.init(None)
            self._pipeline = Gst.ElementFactory.make("playbin", "player")
            self._pipeline.set_property("uri", uri)
            self._pipeline.set_state(Gst.State.PLAYING)
            self._playing = True
            return True
        except Exception as e:
            logger.error("GStreamer play failed: %s", e)
            return False

    def pause(self):
        if self._pipeline:
            try:
                import gi
                gi.require_version("Gst", "1.0")
                from gi.repository import Gst
                self._pipeline.set_state(Gst.State.PAUSED)
            except Exception:
                pass

    def resume(self):
        if self._pipeline:
            try:
                import gi
                gi.require_version("Gst", "1.0")
                from gi.repository import Gst
                self._pipeline.set_state(Gst.State.PLAYING)
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

    def set_volume(self, volume: float):
        self._volume = max(0.0, min(1.0, volume))
        if self._pipeline:
            with contextlib.suppress(Exception):
                self._pipeline.set_property("volume", self._volume)

    def get_position(self) -> float:
        if self._pipeline:
            try:
                import gi
                gi.require_version("Gst", "1.0")
                from gi.repository import Gst
                ok, pos = self._pipeline.query_position(Gst.Format.TIME)
                if ok:
                    self._position = pos / float(Gst.SECOND)
            except Exception:
                pass
        return self._position

    def get_duration(self) -> float:
        if self._pipeline:
            try:
                import gi
                gi.require_version("Gst", "1.0")
                from gi.repository import Gst
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

    def enqueue(self, paths: list[str], play_now: bool = True):
        self._queue.extend(paths)
        if play_now and self._queue_index < 0 and self._queue:
            self._queue_index = 0

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
            return True
        return False

    def play_prev(self) -> bool:
        if self._queue_index > 0:
            self._queue_index -= 1
            return True
        return False

    def get_queue(self) -> list[dict]:
        return [{"filepath": p} for p in self._queue]

    def get_queue_index(self) -> int:
        return self._queue_index
