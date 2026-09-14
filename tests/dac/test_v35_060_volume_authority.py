"""DAC-V35-060 volume-authority productive gates (V60-01..V60-30)."""

from __future__ import annotations

import inspect
from dataclasses import replace
from pathlib import Path

import pytest

from michi.application.audio_output_ports import OutputVolumeLockedError
from michi.application.playback_service import PlaybackService
from michi.application.ports import AudioLoadError
from michi.domain.audio_output import AudioOutputSelection, VolumePolicy
from michi.infrastructure.audio_output.direct_output_executor import DirectExecutorError
from tests.dac.test_v34_output_planner import _facts
from tests.dac.test_v35_productive_direct_composition import (
    _accept_current,
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


def test_v60_blocker_01_shared_37_never_leaks_into_direct_candidate(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    try:
        graph.audio_output_profiles.save_selection(AudioOutputSelection(None, None, 2))
        graph.playback.set_volume(37)
        graph.playback.load_and_play(tmp_path / "shared-a.flac")
        _accept_current(graph, bindings)
        pipeline_a = bindings.pipelines[-1]
        assert pipeline_a.volume == pytest.approx(0.37)

        volume_calls: list[tuple[object, float]] = []
        original_set_volume = bindings.set_volume

        def record_volume(pipeline, value):
            volume_calls.append((pipeline, value))
            original_set_volume(pipeline, value)

        bindings.set_volume = record_volume
        graph.audio_output_profiles.save_selection(
            AudioOutputSelection("p1", "usb:2622:0105:DX5ABC123", 3)
        )
        graph.playback.load_and_play(tmp_path / "direct-b.flac")
        pipeline_b = bindings.pipelines[-1]

        assert pipeline_a.volume == pytest.approx(0.37)
        assert (pipeline_a, 1.0) not in volume_calls
        assert pipeline_b.volume == pytest.approx(1.0)
        assert (pipeline_b, 0.37) not in volume_calls
    finally:
        _close_graph(graph)


def test_v60_16_fixed_mute_cycle_does_not_destroy_shared_preference(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    try:
        graph.audio_output_profiles.save_selection(AudioOutputSelection(None, None, 2))
        graph.playback.set_volume(37)
        graph.playback.load_and_play(tmp_path / "shared-a.flac")
        _accept_current(graph, bindings)

        graph.audio_output_profiles.save_selection(
            AudioOutputSelection("p1", "usb:2622:0105:DX5ABC123", 3)
        )
        graph.playback.load_and_play(tmp_path / "direct-b.flac")
        _accept_current(graph, bindings)
        graph.playback.set_muted(True)
        graph.playback.set_muted(False)
        assert graph.playback.state.volume == 100
        assert graph.playback.snapshot_volume() == (37, False)

        graph.audio_output_profiles.save_selection(AudioOutputSelection(None, None, 4))
        graph.playback.load_and_play(tmp_path / "shared-c.flac")
        pipeline_c = bindings.pipelines[-1]

        assert pipeline_c.volume == pytest.approx(0.37)
        assert graph.playback.state.volume == 37
    finally:
        _close_graph(graph)


def test_v60_17_fixed_rejection_preserves_pipeline_and_playback_truth(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    try:
        graph.playback.load_and_play(tmp_path / "direct.flac")
        pipeline = bindings.pipelines[-1]
        assert graph.playback.state.volume == 100

        with pytest.raises(OutputVolumeLockedError):
            graph.playback.set_volume(37)

        assert pipeline.volume == pytest.approx(1.0)
        assert graph.playback.state.volume == 100
        assert graph.playback.snapshot_volume() == (100, False)
    finally:
        _close_graph(graph)


def test_v60_25_production_graph_owns_one_mandatory_volume_authority(
    tmp_path: Path,
) -> None:
    graph, _bindings = _direct_graph(tmp_path)
    try:
        assert graph.playback._volume_port is graph.volume_policy
        assert (
            inspect.signature(PlaybackService).parameters["volume_port"].default
            is inspect.Parameter.empty
        )
    finally:
        _close_graph(graph)


@pytest.mark.parametrize("policy", [VolumePolicy.HARDWARE, VolumePolicy.SOFTWARE])
def test_v60_26_direct_executor_accepts_only_fixed_policy(policy) -> None:
    from michi.application.audio_output_planner import OutputPlanner
    from tests.dac.test_v35_productive_direct_composition import _AtomicDirectPort

    port = _AtomicDirectPort()
    from michi.infrastructure.audio_output.direct_output_executor import (
        GStreamerDirectOutputExecutor,
    )

    executor = GStreamerDirectOutputExecutor()
    executor.bind_port_provider(lambda: port)
    plan = OutputPlanner().plan(_facts())

    with pytest.raises(DirectExecutorError) as raised:
        executor.prepare(replace(plan, volume_policy=policy))

    assert raised.value.code == "DIRECT_VOLUME_POLICY_UNAVAILABLE"
    assert port.preparation is None


def test_v60_27_direct_candidate_without_unity_readback_is_rejected(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    bindings.volume = lambda pipeline: 0.5
    try:
        with pytest.raises(AudioLoadError, match="DIRECT_FIXED_UNITY_NOT_ESTABLISHED"):
            graph.playback.load_and_play(tmp_path / "direct.flac")

        assert graph.playback.state.file_path is None
        assert graph.playback.state.volume == 100
    finally:
        _close_graph(graph)


def test_v60_28_fixed_unmute_repairs_current_gain_before_audibility(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    try:
        graph.playback.load_and_play(tmp_path / "direct.flac")
        pipeline = bindings.pipelines[-1]
        graph.playback.set_muted(True)
        pipeline.volume = 0.4

        graph.playback.set_muted(False)

        assert pipeline.volume == pytest.approx(1.0)
        assert pipeline.muted is False
        assert graph.playback.state.volume == 100
    finally:
        _close_graph(graph)


def test_v60_29_direct_projection_never_replaces_persisted_shared_snapshot(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    try:
        graph.audio_output_profiles.save_selection(AudioOutputSelection(None, None, 2))
        graph.playback.set_volume(37)
        graph.audio_output_profiles.save_selection(
            AudioOutputSelection("p1", "usb:2622:0105:DX5ABC123", 3)
        )
        graph.playback.load_and_play(tmp_path / "direct.flac")

        assert bindings.pipelines[-1].volume == pytest.approx(1.0)
        assert graph.playback.state.volume == 100
        assert graph.playback.snapshot_volume() == (37, False)
    finally:
        _close_graph(graph)


def test_v60_30_playback_service_contains_no_generic_volume_bypass() -> None:
    source = inspect.getsource(PlaybackService)

    assert "_audio.set_volume" not in source
    assert "_audio.set_muted" not in source
    assert "_volume_port.apply_volume" in source
    assert "_volume_port.apply_muted" in source
