"""DAC-V35-080R1.1 productive cross-generation evidence gates."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from michi.application.audio_output_ports import VolumeAuthority
from michi.domain.audio_evidence import CapabilityEvidence, EvidenceStrength, PcmTuple
from michi.domain.audio_output import AudioOutputSelection, OutputSessionState
from michi.domain.playback import PlaybackStatus
from michi.domain.signal_truth import SignalTruthReason, SignalTruthVerdict
from michi.infrastructure.audio_output.direct_output_executor import DirectExecutorError
from tests.dac._fixtures import AlsaCard, UsbDevice, build_linux_sysfs
from tests.dac.test_v35_080_productive_lifecycle import _disconnect
from tests.dac.test_v35_productive_direct_composition import (
    _accept_current,
    _close_graph,
    _direct_graph,
)

_DEVICE_ID = "usb:2622:0105:DX5ABC123"
_QT_APP = None


@pytest.fixture(autouse=True)
def _qt_runtime():
    global _QT_APP
    from PySide6.QtWidgets import QApplication

    _QT_APP = QApplication.instance() or QApplication([])
    yield _QT_APP


def _candidate_is_absent(graph) -> None:
    with pytest.raises(RuntimeError, match="no Signal Truth candidate"):
        assert graph.signal_truth.candidate_snapshot is not None


def _reconnect_usb_only(graph, tmp_path: Path) -> None:
    sysfs = tmp_path / "linux-topology" / "sys"
    build_linux_sysfs(
        sysfs,
        usb_devices=(
            UsbDevice("2-1", "2622", "0105", serial="DX5ABC123", bcd_device="0100"),
        ),
        cards=(),
    )
    graph.udev_observer.handle_event(action="add", subsystem="usb", sys_name="2-1")


def _reconnect_alsa(graph, tmp_path: Path, *, card_index: int) -> int:
    sysfs = tmp_path / "linux-topology" / "sys"
    build_linux_sysfs(
        sysfs,
        usb_devices=(
            UsbDevice("2-1", "2622", "0105", serial="DX5ABC123", bcd_device="0100"),
        ),
        cards=(AlsaCard(card_index, "DX5", "2-1"),),
    )
    graph.udev_observer.handle_event(
        action="add", subsystem="sound", sys_name=f"card{card_index}"
    )
    generation = graph.audio_device_registry.generation_for(_DEVICE_ID)
    assert generation is not None
    return generation


def _qualify_current(graph, *, evidence_ref: str) -> None:
    graph.dac_qualification.cache_evidence(
        _DEVICE_ID,
        (
            CapabilityEvidence(
                stable_device_id=_DEVICE_ID,
                tuple=PcmTuple(96_000, "S32_LE", 2, 24),
                supported=True,
                strength=EvidenceStrength.OPENED,
                source="michi-alsa-probe",
                observed_at_ns=time.time_ns(),
                environment_fingerprint=(
                    graph.dac_qualification.current_environment_fingerprint(_DEVICE_ID)
                ),
                evidence_refs=(evidence_ref,),
            ),
        ),
    )


def _start_direct(graph, bindings, media: Path):
    graph.playback.load_and_play(media)
    pipeline = bindings.pipelines[-1]
    assert pipeline.volume == 1.0
    _accept_current(graph, bindings)
    assert graph.output_session.state is OutputSessionState.RUNNING
    return pipeline


def test_volume_authority_is_fresh_across_disconnect_rebind_and_shared_return(
    tmp_path: Path,
) -> None:
    """R80R1.1-01: Shared37 -> G1 unity -> LOST -> G2 unity -> Shared37."""
    graph, bindings = _direct_graph(tmp_path)
    try:
        graph.audio_output_profiles.save_selection(AudioOutputSelection(None, None, 2))
        graph.playback.set_volume(37)
        assert graph.playback.snapshot_volume() == (37, False)

        graph.audio_output_profiles.save_selection(
            AudioOutputSelection("p1", _DEVICE_ID, 3)
        )
        _start_direct(graph, bindings, tmp_path / "generation.flac")
        plan_g1 = graph.output_session.active_plan
        handle_g1 = graph.direct_output_executor.handle
        generation_g1 = graph.audio_device_registry.generation_for(_DEVICE_ID)
        assert plan_g1 is not None and handle_g1 is not None
        assert graph.output_session.volume_authority is VolumeAuthority.FIXED
        assert graph.volume_policy.authority is VolumeAuthority.FIXED
        assert graph.playback.state.volume == 100
        assert bindings.pipelines[-1].volume == 1.0

        _disconnect(graph, tmp_path)

        assert graph.output_session.state is OutputSessionState.LOST
        assert graph.playback.state.status is PlaybackStatus.STOPPED
        assert graph.volume_policy.authority is VolumeAuthority.UNKNOWN
        assert graph.playback.snapshot_volume() == (37, False)

        pipeline_count = len(bindings.pipelines)
        _reconnect_usb_only(graph, tmp_path)
        generation_g2 = _reconnect_alsa(graph, tmp_path, card_index=4)
        assert generation_g1 is not None and generation_g2 > generation_g1
        assert graph.output_session.state is OutputSessionState.IDLE
        assert graph.output_session.plan is None
        assert graph.direct_output_executor.handle is None
        assert len(bindings.pipelines) == pipeline_count
        assert graph.playback.snapshot_volume() == (37, False)

        _qualify_current(graph, evidence_ref="probe:R80R1.1-01:g2")
        graph.playback.play()
        pipeline_g2 = bindings.pipelines[-1]
        assert pipeline_g2.volume == 1.0
        _accept_current(graph, bindings)

        plan_g2 = graph.output_session.active_plan
        handle_g2 = graph.direct_output_executor.handle
        assert plan_g2 is not None and handle_g2 is not None
        assert plan_g2.plan_id != plan_g1.plan_id
        assert plan_g2.binding.generation == generation_g2
        assert plan_g2.binding.card_index == 4
        assert handle_g2.generation > handle_g1.generation
        assert handle_g2.plan_id == plan_g2.plan_id
        assert graph.volume_policy._output is graph.output_session
        assert graph.volume_policy.authority is VolumeAuthority.FIXED
        assert graph.playback.state.volume == 100
        assert pipeline_g2.volume == 1.0

        graph.audio_output_profiles.save_selection(AudioOutputSelection(None, None, 4))
        graph.playback.load_and_play(tmp_path / "shared.flac")
        pipeline_shared = bindings.pipelines[-1]
        assert pipeline_shared.volume == pytest.approx(0.37)
        _accept_current(graph, bindings)

        assert graph.volume_policy.authority is VolumeAuthority.MICHI_SOFTWARE
        assert graph.playback.state.volume == 37
        assert graph.playback.snapshot_volume() == (37, False)
        assert pipeline_shared.volume == pytest.approx(0.37)
    finally:
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_signal_truth_is_recreated_not_inherited_across_hardware_generation(
    tmp_path: Path,
) -> None:
    """R80R1.1-02: G2 truth has wholly fresh runtime provenance."""
    graph, bindings = _direct_graph(tmp_path)
    try:
        _start_direct(graph, bindings, tmp_path / "truth.flac")
        snapshot_g1 = graph.signal_truth.active_snapshot
        handle_g1 = graph.direct_output_executor.handle
        plan_g1 = graph.output_session.active_plan
        assert snapshot_g1 is not None and handle_g1 is not None and plan_g1 is not None
        identity_g1 = snapshot_g1.identity

        _disconnect(graph, tmp_path)

        assert graph.signal_truth.active_snapshot is None
        _candidate_is_absent(graph)
        _reconnect_usb_only(graph, tmp_path)
        generation_g2 = _reconnect_alsa(graph, tmp_path, card_index=4)
        assert graph.signal_truth.active_snapshot is None
        _candidate_is_absent(graph)

        _qualify_current(graph, evidence_ref="probe:R80R1.1-02:g2")
        graph.playback.play()
        assert graph.signal_truth.active_snapshot is None
        candidate_g2 = graph.signal_truth.candidate_snapshot
        assert candidate_g2.identity != identity_g1
        _accept_current(graph, bindings)

        snapshot_g2 = graph.signal_truth.active_snapshot
        plan_g2 = graph.output_session.active_plan
        handle_g2 = graph.direct_output_executor.handle
        assert snapshot_g2 is not None and plan_g2 is not None and handle_g2 is not None
        identity_g2 = snapshot_g2.identity
        assert identity_g2 != identity_g1
        assert identity_g2.plan_id != identity_g1.plan_id
        assert identity_g1.plan_id == plan_g1.plan_id
        assert identity_g2.execution_generation > identity_g1.execution_generation
        assert identity_g2.port_generation > identity_g1.port_generation
        assert identity_g2.binding_generation > identity_g1.binding_generation
        assert identity_g2.binding_generation == generation_g2
        assert identity_g2.plan_id == plan_g2.plan_id == handle_g2.plan_id
        assert snapshot_g2.decoded_runtime is not None
        assert snapshot_g2.engine_effective is not None
        # The productive fake keeps procfs hw_params closed, so this fixture
        # must recompute UNKNOWN from fresh G2 evidence rather than fabricate
        # an ALSA observation or inherit G1's result.
        assert snapshot_g2.device_negotiated is None
        assert snapshot_g2.verdict is SignalTruthVerdict.UNKNOWN
        assert SignalTruthReason.ST_MISSING_ALSA in snapshot_g2.reasons
        assert snapshot_g2.decoded_runtime.identity == identity_g2
        assert snapshot_g2.engine_effective.identity == identity_g2

        with pytest.raises(DirectExecutorError, match="DIRECT_STALE_EXECUTION"):
            graph.direct_output_executor.record_runtime_anomaly(
                handle_g1, "late G1 XRUN"
            )
        assert graph.signal_truth.active_snapshot == snapshot_g2
    finally:
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_late_g1_runtime_anomaly_cannot_modify_active_g2_truth(tmp_path: Path) -> None:
    """R80R1.1-03: a stale G1 handle is rejected after G2 becomes active."""
    graph, bindings = _direct_graph(tmp_path)
    try:
        _start_direct(graph, bindings, tmp_path / "late.flac")
        handle_g1 = graph.direct_output_executor.handle
        _disconnect(graph, tmp_path)
        _reconnect_usb_only(graph, tmp_path)
        _reconnect_alsa(graph, tmp_path, card_index=4)
        _qualify_current(graph, evidence_ref="probe:R80R1.1-03:g2")
        graph.playback.play()
        _accept_current(graph, bindings)
        snapshot_g2 = graph.signal_truth.active_snapshot

        with pytest.raises(DirectExecutorError) as raised:
            graph.direct_output_executor.record_runtime_anomaly(handle_g1, "late error")

        assert raised.value.code == "DIRECT_STALE_EXECUTION"
        assert graph.signal_truth.active_snapshot == snapshot_g2
    finally:
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_reconnect_performs_fresh_qualification_before_direct(tmp_path: Path) -> None:
    """R1.2: topology readiness alone is insufficient; fresh exact-open follows."""
    graph, bindings = _direct_graph(tmp_path)
    try:
        _start_direct(graph, bindings, tmp_path / "unqualified.flac")
        _disconnect(graph, tmp_path)
        pipeline_count = len(bindings.pipelines)
        _reconnect_usb_only(graph, tmp_path)
        _reconnect_alsa(graph, tmp_path, card_index=4)

        graph.playback.play()
        from tests.dac.test_v35_productive_direct_composition import (
            _wait_for_pipeline_count,
        )

        _wait_for_pipeline_count(bindings, pipeline_count + 1)

        assert graph.output_session.state is OutputSessionState.READY
        assert graph.output_session.plan is not None
        assert graph.direct_output_executor.handle is not None
        assert graph.signal_truth.active_snapshot is None
        assert graph.volume_policy.authority is VolumeAuthority.FIXED
    finally:
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_usb_only_reconnect_cannot_restore_direct_authority(tmp_path: Path) -> None:
    """R80R1.1-05: USB visibility without current ALSA is not a Direct rebind."""
    graph, bindings = _direct_graph(tmp_path)
    try:
        _start_direct(graph, bindings, tmp_path / "usb-only.flac")
        _disconnect(graph, tmp_path)
        pipeline_count = len(bindings.pipelines)

        _reconnect_usb_only(graph, tmp_path)

        assert graph.output_session.state is OutputSessionState.LOST
        assert graph.output_session.plan is None
        assert graph.direct_output_executor.handle is None
        assert graph.signal_truth.active_snapshot is None
        _candidate_is_absent(graph)
        assert graph.volume_policy.authority is VolumeAuthority.UNKNOWN
        assert len(bindings.pipelines) == pipeline_count
    finally:
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_same_dac_new_card_index_uses_only_g2_binding_and_evidence(
    tmp_path: Path,
) -> None:
    """R80R1.1-06: card renumbering rebuilds volume and truth from G2."""
    graph, bindings = _direct_graph(tmp_path)
    try:
        _start_direct(graph, bindings, tmp_path / "renumber.flac")
        snapshot_g1 = graph.signal_truth.active_snapshot
        plan_g1 = graph.output_session.active_plan
        assert snapshot_g1 is not None and plan_g1 is not None
        identity_g1 = snapshot_g1.identity
        _disconnect(graph, tmp_path)
        _reconnect_usb_only(graph, tmp_path)
        generation_g2 = _reconnect_alsa(graph, tmp_path, card_index=7)
        _qualify_current(graph, evidence_ref="probe:R80R1.1-06:g2-card7")

        graph.playback.play()
        assert bindings.built_recipes[-1].device == "hw:CARD=DX5,DEV=0"
        assert bindings.pipelines[-1].volume == 1.0
        _accept_current(graph, bindings)

        plan_g2 = graph.output_session.active_plan
        snapshot_g2 = graph.signal_truth.active_snapshot
        assert plan_g2 is not None and snapshot_g2 is not None
        assert plan_g2.plan_id != plan_g1.plan_id
        assert plan_g2.binding.card_index == 7
        assert plan_g2.binding.generation == generation_g2
        assert snapshot_g2.identity != identity_g1
        assert snapshot_g2.identity.binding_generation == generation_g2
        assert snapshot_g2.identity.plan_id == plan_g2.plan_id
        assert graph.volume_policy.authority is VolumeAuthority.FIXED
        assert graph.playback.state.volume == 100
    finally:
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)
