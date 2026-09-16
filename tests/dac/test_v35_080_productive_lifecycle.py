"""DAC-V35-080 productive disconnect/reconnect lifecycle gates."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from michi.application.audio_device_registry import AudioDeviceTopologyChange
from michi.application.output_session_service import OutputSessionError
from michi.domain.audio_evidence import CapabilityEvidence, EvidenceStrength, PcmTuple
from michi.domain.audio_output import OutputSessionState
from michi.domain.playback import PlaybackStatus
from tests.dac._fixtures import (
    AlsaCard,
    UsbDevice,
    build_linux_sysfs,
    remove_alsa_card,
    remove_usb_device,
)
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


def _play_direct(graph, bindings, tmp_path: Path, *, status: PlaybackStatus) -> None:
    from test_gstreamer_audio_port import _deliver, _FakeState, msg_state

    graph.playback.load_and_play(tmp_path / "active.flac")
    _accept_current(graph, bindings)
    if status is not PlaybackStatus.STOPPED:
        port = graph.gstreamer_engine_provider.current_port
        message, generation = msg_state(
            port, bindings.pipelines[-1], _FakeState.PLAYING
        )
        _deliver(port, message, generation)
        if status is PlaybackStatus.PAUSED:
            graph.playback.pause()
            message, generation = msg_state(
                port, bindings.pipelines[-1], _FakeState.PAUSED
            )
            _deliver(port, message, generation)
    assert graph.playback.state.status is status
    assert graph.output_session.state is OutputSessionState.RUNNING


def _disconnect(graph, tmp_path: Path) -> None:
    sysfs = tmp_path / "linux-topology" / "sys"
    remove_usb_device(sysfs, "2-1")
    remove_alsa_card(sysfs, 1)
    graph.udev_observer.handle_event(
        action="remove", subsystem="sound", sys_name="card1"
    )


@pytest.mark.parametrize(
    ("status", "gate"),
    [
        (PlaybackStatus.PLAYING, "R80-01"),
        (PlaybackStatus.PAUSED, "R80-02"),
        (PlaybackStatus.STOPPED, "R80-03"),
    ],
)
def test_r80_01_03_disconnect_converges_through_productive_path(
    tmp_path: Path, status: PlaybackStatus, gate: str
) -> None:
    del gate
    graph, bindings = _direct_graph(tmp_path)
    try:
        _play_direct(graph, bindings, tmp_path, status=status)
        stable_id = graph.output_session.active_device_id
        selected = graph.audio_output_profiles.load_selection()
        pipeline = bindings.pipelines[-1]

        _disconnect(graph, tmp_path)

        assert graph.playback.state.status is PlaybackStatus.STOPPED
        assert graph.playback.state.error_message == "OUTPUT_DEVICE_LOST"
        assert graph.output_session.state is OutputSessionState.LOST
        assert graph.output_session.active_device_id is None
        assert graph.output_session.active_plan is None
        assert graph.direct_output_executor.handle is None
        assert pipeline.closed is True
        assert graph.audio_output_profiles.load_selection() == selected
        assert selected.selected_device_id == stable_id
    finally:
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_r80_04_09_disconnect_is_idempotent_and_never_falls_back(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    try:
        _play_direct(graph, bindings, tmp_path, status=PlaybackStatus.PLAYING)
        pipeline_count = len(bindings.pipelines)
        release_reasons = []
        original_release = graph.direct_output_executor.release

        def counting_release(reason):
            release_reasons.append(reason)
            original_release(reason)

        graph.direct_output_executor.release = counting_release
        eom_events = []
        graph.playback.subscribe_end_of_media(lambda: eom_events.append("eom"))
        queue_before = tuple(graph.queue.state.tracks)

        _disconnect(graph, tmp_path)
        graph.udev_observer.handle_event(
            action="remove", subsystem="usb", sys_name="2-1"
        )

        assert graph.output_session.state is OutputSessionState.LOST
        assert graph.playback.state.status is PlaybackStatus.STOPPED
        assert graph.audio_router.bound_engine_id.value == "gstreamer"
        assert len(bindings.pipelines) == pipeline_count
        assert release_reasons == ["device_lost"]
        assert eom_events == []
        assert tuple(graph.queue.state.tracks) == queue_before
    finally:
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_r80_13_19_reconnect_same_identity_is_inactive_until_fresh_play(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    try:
        _play_direct(graph, bindings, tmp_path, status=PlaybackStatus.PLAYING)
        stable_id = graph.output_session.active_device_id
        assert stable_id is not None
        first_plan_id = graph.output_session.active_plan.plan_id
        old_bindings = graph.audio_device_registry.bindings_for(stable_id)
        old_generation = graph.audio_device_registry.generation_for(stable_id)
        _disconnect(graph, tmp_path)
        pipeline_count = len(bindings.pipelines)

        sysfs = tmp_path / "linux-topology" / "sys"
        build_linux_sysfs(
            sysfs,
            usb_devices=(
                UsbDevice("2-1", "2622", "0105", serial="DX5ABC123", bcd_device="0100"),
            ),
            cards=(),
        )
        graph.udev_observer.handle_event(action="add", subsystem="usb", sys_name="2-1")
        assert graph.output_session.state is OutputSessionState.LOST
        assert graph.direct_output_executor.handle is None

        build_linux_sysfs(
            sysfs,
            usb_devices=(
                UsbDevice("2-1", "2622", "0105", serial="DX5ABC123", bcd_device="0100"),
            ),
            cards=(AlsaCard(4, "DX5", "2-1"),),
        )
        graph.udev_observer.handle_event(
            action="add", subsystem="sound", sys_name="card4"
        )

        assert graph.output_session.state is OutputSessionState.IDLE
        assert graph.output_session.active_device_id is None
        assert graph.direct_output_executor.handle is None
        assert graph.playback.state.status is PlaybackStatus.STOPPED
        assert len(bindings.pipelines) == pipeline_count
        new_generation = graph.audio_device_registry.generation_for(stable_id)
        assert new_generation > old_generation
        assert graph.dac_qualification.cached_evidence_current(stable_id) == ()
        with pytest.raises(OutputSessionError):
            graph.playback.play()
        assert graph.output_session.active_plan is None
        assert len(bindings.pipelines) == pipeline_count

        graph.dac_qualification.cache_evidence(
            stable_id,
            (
                CapabilityEvidence(
                    stable_device_id=stable_id,
                    tuple=PcmTuple(96_000, "S32_LE", 2, 24),
                    supported=True,
                    strength=EvidenceStrength.OPENED,
                    source="michi-alsa-probe",
                    observed_at_ns=time.time_ns(),
                    environment_fingerprint=(
                        graph.dac_qualification.current_environment_fingerprint(
                            stable_id
                        )
                    ),
                    evidence_refs=("probe:reconnected",),
                ),
            ),
        )
        graph.playback.play()

        assert graph.output_session.active_device_id == stable_id
        assert graph.output_session.active_plan is not None
        assert graph.output_session.active_plan.binding.generation == new_generation
        assert graph.output_session.active_plan.binding.card_index == 4
        assert graph.output_session.active_plan.plan_id != first_plan_id
        assert graph.output_session.active_plan.binding not in old_bindings
        assert len(bindings.pipelines) == pipeline_count + 1

        graph.direct_output_lifecycle.handle_topology_changed(
            AudioDeviceTopologyChange(
                stable_device_id=stable_id,
                previous_available=True,
                current_available=False,
                previous_generation=old_generation,
                current_generation=new_generation - 1,
                previous_bindings=old_bindings,
                current_bindings=(),
            )
        )
        assert graph.output_session.active_device_id == stable_id
    finally:
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_r80_23_25_no_eom_queue_or_engine_fallback_side_effects(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    try:
        _play_direct(graph, bindings, tmp_path, status=PlaybackStatus.PLAYING)
        session_before = graph.playback_session.state
        engine_before = graph.audio_engine_service.state
        eom = []
        graph.playback.subscribe_end_of_media(lambda: eom.append(True))

        _disconnect(graph, tmp_path)

        assert eom == []
        assert graph.playback_session.state == session_before
        assert graph.audio_engine_service.state == engine_before
        assert graph.output_session.allows_automatic_engine_fallback() is False
    finally:
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)
