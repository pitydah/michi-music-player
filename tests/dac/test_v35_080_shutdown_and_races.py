"""DAC-V35-080 shutdown and adversarial race gates."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from michi.application.audio_device_registry import AudioDeviceTopologyChange
from michi.application.audio_engine_runtime_failure import (
    AudioEngineRuntimeFailureEvent,
)
from michi.domain.audio_engine import AudioEngineId
from michi.domain.audio_output import OutputSessionState
from michi.domain.playback import PlaybackStatus
from tests.dac.test_v35_080_productive_lifecycle import _disconnect, _play_direct
from tests.dac.test_v35_productive_direct_composition import (
    _close_graph,
    _direct_graph,
)

_QT_APP = None


@pytest.fixture(autouse=True)
def _qt_runtime():
    global _QT_APP
    from PySide6.QtWidgets import QApplication

    _QT_APP = QApplication.instance() or QApplication([])
    yield _QT_APP


def test_r80_05_disconnect_while_load_pending_terminalizes_once(tmp_path: Path) -> None:
    graph, bindings = _direct_graph(tmp_path)
    rejected = []
    try:
        graph.playback.load_and_play(
            tmp_path / "pending.flac",
            on_rejected=lambda path, reason: rejected.append((path, reason)),
        )
        assert graph.output_session.state is OutputSessionState.READY

        _disconnect(graph, tmp_path)
        _disconnect(graph, tmp_path)

        assert graph.playback.state.status is PlaybackStatus.STOPPED
        assert graph.playback.state.error_message == "OUTPUT_DEVICE_LOST"
        assert graph.output_session.state is OutputSessionState.LOST
        assert graph.direct_output_executor.handle is None
        assert len(rejected) == 1
        assert rejected[0][1] == "OUTPUT_DEVICE_LOST"
        assert len(bindings.pipelines) == 1
        assert bindings.pipelines[0].closed is True
    finally:
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_r80_26_unplug_during_prepare_rejects_stale_binding(tmp_path: Path) -> None:
    graph, _bindings = _direct_graph(tmp_path)
    original_prepare = graph.direct_output_executor.prepare

    def racing_prepare(plan):
        receipt = original_prepare(plan)
        _disconnect(graph, tmp_path)
        return receipt

    graph.direct_output_executor.prepare = racing_prepare
    try:
        graph.playback.load_and_play(tmp_path / "racing.flac")

        assert graph.output_session.active_plan is None
        assert graph.direct_output_executor.handle is None
        assert graph.playback.state.status is PlaybackStatus.STOPPED
        # R1.3: the stale-binding refusal now names the real cause (endpoint change)
        assert graph.playback.state.error_message.startswith(
            ("DAC connection changed:", "Output unavailable:")
        )
    finally:
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_r80_24_simultaneous_engine_failure_cannot_fallback_from_direct_stop(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    try:
        _play_direct(graph, bindings, tmp_path, status=PlaybackStatus.PLAYING)
        _disconnect(graph, tmp_path)
        provider = graph.gstreamer_engine_provider

        graph.audio_engine_convergence.handle_runtime_failure(
            AudioEngineRuntimeFailureEvent(
                engine_id=AudioEngineId.GSTREAMER,
                runtime_generation=provider.current_runtime_generation,
                reason="simultaneous fatal",
            )
        )

        assert graph.audio_router.bound_engine_id is None
        assert graph.audio_engine_service.state.active_engine_id is None
        assert graph.playback.state.status is PlaybackStatus.STOPPED
    finally:
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_r80_27_shutdown_order_disables_callbacks_before_release() -> None:
    from michi.bootstrap import ApplicationContainer

    calls = []
    container = ApplicationContainer()

    class _Lifecycle:
        def shutdown(self):
            calls.append("lifecycle-off")

    class _Observer:
        def stop(self):
            calls.append("udev-off")

    class _Convergence:
        def shutdown(self):
            calls.append("engine-callbacks-off")

    class _Playback:
        def stop(self):
            calls.append("safety-stop")

    class _Output:
        state = SimpleNamespace(value="running")

        def release_active(self, reason):
            calls.append(f"release:{reason}")

    container._direct_output_lifecycle = _Lifecycle()
    container._udev_observer = _Observer()
    container._audio_engine_convergence = _Convergence()
    container._playback = _Playback()
    container._output_session = _Output()

    ApplicationContainer.shutdown(container)

    assert calls.index("lifecycle-off") < calls.index("udev-off")
    assert calls.index("udev-off") < calls.index("engine-callbacks-off")
    assert calls.index("engine-callbacks-off") < calls.index("safety-stop")
    assert calls.index("safety-stop") < calls.index("release:shutdown")


def test_r80_28_late_topology_callback_after_lifecycle_shutdown_is_inert(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    try:
        _play_direct(graph, bindings, tmp_path, status=PlaybackStatus.PLAYING)
        stable_id = graph.output_session.active_device_id
        generation = graph.audio_device_registry.generation_for(stable_id)
        graph.direct_output_lifecycle.shutdown()

        graph.direct_output_lifecycle.handle_topology_changed(
            AudioDeviceTopologyChange(
                stable_device_id=stable_id,
                previous_available=True,
                current_available=False,
                previous_generation=generation,
                current_generation=generation + 1,
                previous_bindings=graph.audio_device_registry.bindings_for(stable_id),
                current_bindings=(),
            )
        )

        assert graph.output_session.state is OutputSessionState.RUNNING
        assert graph.direct_output_executor.handle is not None
    finally:
        _close_graph(graph)
