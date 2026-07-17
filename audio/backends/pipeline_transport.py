"""GStreamerPipelineTransport — low-level GStreamer pipeline controller.

This is the internal transport used by GStreamerEngine.
It is NOT an AudioBackend — that role belongs to EngineBackendAdapter.

Responsibilities:
- adopt_pipeline() / get_pipeline()
- pause / resume / stop / seek / set_volume
- GStreamer bus message handling
- Position and duration queries
"""
from __future__ import annotations

import logging
import contextlib

import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib  # noqa: E402

logger = logging.getLogger("michi.audio.transport")


class GStreamerPipelineTransport:
    def __init__(self):
        self._pipeline = None
        self._playing = False
        self._volume = 1.0
        self._position: float = 0.0
        self._duration: float = 0.0

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

    def pause(self):
        if self._pipeline:
            with contextlib.suppress(Exception):
                self._pipeline.set_state(Gst.State.PAUSED)
                self._playing = False

    def resume(self):
        if self._pipeline:
            with contextlib.suppress(Exception):
                self._pipeline.set_state(Gst.State.PLAYING)
                self._playing = True

    def stop(self):
        if self._pipeline:
            with contextlib.suppress(Exception):
                self._pipeline.set_state(Gst.State.NULL)
                self._pipeline.get_state(Gst.CLOCK_TIME_NONE)
        self._playing = False
        self._position = 0.0

    def seek(self, seconds: float):
        if self._pipeline:
            with contextlib.suppress(Exception):
                self._pipeline.seek_simple(
                    Gst.Format.TIME, Gst.SeekFlags.FLUSH,
                    int(seconds * Gst.SECOND))

    def set_volume(self, volume: float):
        clamped = max(0.0, min(1.0, float(volume)))
        self._volume = clamped
        if self._pipeline:
            with contextlib.suppress(Exception):
                self._pipeline.set_property("volume", clamped)

    def get_position(self) -> float:
        if self._pipeline:
            with contextlib.suppress(Exception):
                ok, pos = self._pipeline.query_position(Gst.Format.TIME)
                if ok:
                    self._position = pos / float(Gst.SECOND)
        return self._position

    def get_duration(self) -> float:
        if self._pipeline:
            with contextlib.suppress(Exception):
                ok, dur = self._pipeline.query_duration(Gst.Format.TIME)
                if ok:
                    self._duration = dur / float(Gst.SECOND)
        return self._duration

    def setup_bus(self, pipeline, on_message):
        bus = pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", on_message)

    def shutdown(self):
        self.stop()
        self._on_state_changed = None
        self._on_track_ended = None
        self._on_position_updated = None
        self._on_error = None
