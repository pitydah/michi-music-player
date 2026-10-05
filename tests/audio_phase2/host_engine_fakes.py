"""Scripted engine ports for hosted-port tests (child-side doubles).

Not production code. Each behavior deterministically exercises one boundary:
normal command flow, event emission, rejections with typed dispositions,
wedges, crashes and pump-death telemetry.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from michi.application.ports import AudioLoadError
from michi.domain.playback import PlaybackStatus


class FakeEnginePort:
    def __init__(self, behavior: str = "normal") -> None:
        self.behavior = behavior
        self.calls: list[tuple[str, object]] = []
        self._eom: list = []
        self._pos: list = []
        self._dur: list = []
        self._acc: list = []
        self._rej: list = []
        self._pst: list = []
        self._failure_cb = None
        self.position_value = 1234
        self.duration_value = 2345

    # ── ciclo de vida ─────────────────────────────────────────────────
    def activate(self) -> None:
        self.calls.append(("activate", None))
        if self.behavior == "fail_open":
            raise RuntimeError("engine refused to activate")

    def close(self) -> None:
        self.calls.append(("close", None))
        if self.behavior == "hang_on_close":
            time.sleep(60)

    # ── comandos ──────────────────────────────────────────────────────
    def load(self, file_path: Path) -> None:
        self.calls.append(("load", str(file_path)))
        if self.behavior == "hang_on_load":
            time.sleep(60)
        if self.behavior == "crash_on_load":
            os._exit(9)
        if self.behavior == "reject_load":
            raise AudioLoadError(
                Path(file_path), "candidate rejected", previous_source_preserved=False
            )
        if self.behavior == "reject_load_preserved":
            raise AudioLoadError(
                Path(file_path), "candidate rejected", previous_source_preserved=True
            )
        if self.behavior == "slow":
            time.sleep(0.2)
        self._emit_accepted(Path(file_path))

    def play(self) -> None:
        self.calls.append(("play", None))
        if self.behavior == "hang_on_play":
            time.sleep(60)
        if self.behavior == "crash_on_play":
            os._exit(9)
        if self.behavior == "reject_play":
            raise RuntimeError("play refused")
        if self.behavior == "pump_death":
            if self._failure_cb is not None:
                self._failure_cb(7, "GStreamer pump died inside the host")
            return
        self._emit_state(PlaybackStatus.PLAYING)

    def pause(self) -> None:
        self.calls.append(("pause", None))
        self._emit_state(PlaybackStatus.PAUSED)

    def resume(self) -> None:
        self.calls.append(("resume", None))
        self._emit_state(PlaybackStatus.PLAYING)

    def stop(self) -> None:
        self.calls.append(("stop", None))
        if self.behavior == "hang_on_stop":
            time.sleep(60)
        if self.behavior == "reject_stop":
            raise RuntimeError("stop refused")
        self._emit_state(PlaybackStatus.STOPPED)

    def seek(self, position_ms: int) -> None:
        self.calls.append(("seek", position_ms))

    def set_volume(self, value: int) -> None:
        self.calls.append(("set_volume", value))

    def set_muted(self, muted: bool) -> None:
        self.calls.append(("set_muted", muted))

    def position(self) -> int:
        return self.position_value

    def duration(self) -> int:
        return self.duration_value

    # ── subscriptions ─────────────────────────────────────────────────
    def subscribe_end_of_media(self, callback) -> None:
        self._eom.append(callback)

    def subscribe_position_changed(self, callback) -> None:
        self._pos.append(callback)

    def subscribe_duration_changed(self, callback) -> None:
        self._dur.append(callback)

    def subscribe_media_accepted(self, callback) -> None:
        self._acc.append(callback)

    def subscribe_media_rejected(self, callback) -> None:
        self._rej.append(callback)

    def subscribe_playback_state_changed(self, callback) -> None:
        self._pst.append(callback)

    def set_runtime_failure_callback(self, callback) -> None:
        self._failure_cb = callback

    # ── emisión ───────────────────────────────────────────────────────
    def _emit_state(self, status: PlaybackStatus) -> None:
        for callback in list(self._pst):
            callback(status)

    def _emit_accepted(self, path: Path) -> None:
        for callback in list(self._acc):
            callback(path)

    def emit_eos(self) -> None:
        for callback in list(self._eom):
            callback()

    def emit_position(self, ms: int) -> None:
        for callback in list(self._pos):
            callback(ms)

    def emit_duration(self, ms: int) -> None:
        for callback in list(self._dur):
            callback(ms)
