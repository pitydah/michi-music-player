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
