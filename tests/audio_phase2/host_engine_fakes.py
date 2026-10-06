"""Scripted engine ports for hosted-port tests (child-side doubles).

Not production code. Each behavior deterministically exercises one boundary:
normal command flow, event emission, rejections with typed dispositions,
wedges, crashes and pump-death telemetry.
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path

from michi.application.ports import AudioLoadError
from michi.domain.playback import PlaybackStatus
from michi.infrastructure.audio_output.runtime_inspector import (
    DirectRuntimeSnapshot,
)


class FakeEnginePort:
    def __init__(self, behavior: str = "normal", coordinator=None) -> None:
        self.behavior = behavior
        self.coordinator = coordinator
        self.direct_stage = None
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
        if self.behavior == "crash_on_close":
            os._exit(9)
        if self.coordinator is not None and self.direct_stage is not None:
            self.direct_stage = None
            self.coordinator.release("fake_close")

    # ── Direct staging (fake port exercises the real coordinator) ─────
    def stage_direct_load(self, preparation, *, executor) -> None:
        if executor is not self.coordinator:
            raise RuntimeError("DIRECT_EXECUTOR_IDENTITY_MISMATCH")
        self.direct_stage = preparation

    def discard_direct_load(self, handle, *, executor) -> bool:
        if executor is not self.coordinator:
            raise RuntimeError("DIRECT_EXECUTOR_IDENTITY_MISMATCH")
        if self.direct_stage is None or self.direct_stage.handle != handle:
            return False
        self.direct_stage = None
        return True

    def _snapshot_for(self, preparation) -> DirectRuntimeSnapshot:
        recipe = preparation.recipe
        snapshot = DirectRuntimeSnapshot(
            execution_generation=preparation.handle.generation,
            port_generation=7,
            plan_id=preparation.handle.plan_id,
            sink_factory=recipe.sink_factory,
            sink_device=recipe.device,
            negotiated_format=recipe.gst_format,
            negotiated_rate_hz=recipe.rate_hz,
            negotiated_channels=recipe.channels,
            graph_factories=("capsfilter", recipe.sink_factory),
        )
        if self.behavior == "direct_stale":
            return DirectRuntimeSnapshot(
                execution_generation=preparation.handle.generation + 50,
                port_generation=snapshot.port_generation,
                plan_id=snapshot.plan_id,
                sink_factory=snapshot.sink_factory,
                sink_device=snapshot.sink_device,
                negotiated_format=snapshot.negotiated_format,
                negotiated_rate_hz=snapshot.negotiated_rate_hz,
                negotiated_channels=snapshot.negotiated_channels,
                graph_factories=snapshot.graph_factories,
            )
        return snapshot

    def _emit_direct_callbacks(self) -> None:
        preparation = self.direct_stage
        coordinator = self.coordinator
        if preparation is None or coordinator is None:
            return
        coordinator.mark_previous_source_released()
        coordinator.begin_runtime(preparation.handle, port_generation=7)
        snapshot = self._snapshot_for(preparation)
        coordinator.verify_preroll(preparation.handle, snapshot)
        coordinator.observe_runtime(preparation.handle, snapshot)

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
        if self.behavior == "delayed_event":
            # Spontaneous late event: arrives while the parent owner is IDLE,
            # so only the real Qt dispatch path can deliver it.
            def late() -> None:
                time.sleep(0.3)
                self._emit_state(PlaybackStatus.PLAYING)

            threading.Thread(target=late, daemon=True).start()
            return
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
        self._emit_direct_callbacks()
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
        if self.behavior == "crash_on_stop":
            os._exit(9)
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

    def processing_capabilities(self) -> dict:
        if self.behavior == "capabilities_hang":
            time.sleep(60)
        if self.behavior == "capabilities_crash":
            os._exit(9)
        factories = {
            name: {"available": True, "properties": {}, "missing_properties": []}
            for name in (
                "equalizer-nbands",
                "audioiirfilter",
                "audiofirfilter",
                "audioconvert",
                "audioresample",
                "volume",
            )
        }
        if self.behavior == "capabilities_missing_eq":
            factories["equalizer-nbands"] = {
                "available": False,
                "properties": {},
                "missing_properties": ["num-bands"],
            }
        if self.behavior == "capabilities_incompatible_prop":
            factories["audioiirfilter"] = {
                "available": False,
                "properties": {"a": True},
                "missing_properties": ["b"],
            }
        return {
            "schema_version": 1,
            "gstreamer_version": "GStreamer fake-1.0",
            "runtime_failure": None,
            "factories": factories,
        }

    def resync_evidence(self) -> dict:
        return {
            "resync_delay_ms": 250,
            "resync_actual_hold_ms": 248,
            "port_generation": 7,
            "execution_generation": 1,
            "plan_id": "plan:direct",
        }

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
