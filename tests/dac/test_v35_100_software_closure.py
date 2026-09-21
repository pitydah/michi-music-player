"""DAC-V35-100 automated software closure gates (E2E-100-01..10)."""

from __future__ import annotations

import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from michi.application.audio_output_ports import VolumeAuthority
from michi.application.audio_output_selection_coordinator import (
    AudioOutputSelectionCoordinator,
)
from michi.domain.audio_engine import AudioEngineId
from michi.domain.audio_evidence import (
    CapabilityEvidence,
    EvidenceStrength,
    ExactProbeResult,
    PcmTuple,
)
from michi.domain.audio_output import (
    AudioOutputSelection,
    OutputSessionState,
    stable_direct_preset,
)
from michi.domain.playback import PlaybackStatus
from michi.infrastructure.audio_output.direct_output_executor import DirectExecutorError
from michi.presentation.audio_output_bridge import AudioOutputBridge, failure_copy
from tests.dac._fixtures import AlsaCard, UsbDevice, build_linux_sysfs
from tests.dac.test_v35_080_productive_lifecycle import _disconnect
from tests.dac.test_v35_productive_direct_composition import (
    _accept_current,
    _close_graph,
    _direct_graph,
)

_DEVICE_ID = "usb:2622:0105:DX5ABC123"
_QT_APP = None

AUTHORITY_MANIFEST = {
    "sequence_navigation": "PlaybackSessionService",
    "playback_state": "PlaybackService",
    "engine_state": "AudioEngineService",
    "device_topology": "AudioDeviceRegistry",
    "profile_selection": "AudioOutputProfileService",
    "output_transaction": "OutputSessionService",
    "volume_execution": "VolumePolicyService",
    "runtime_evidence": "SignalTruthRecorder",
    "presentation_projection": "AudioOutputBridge (non-authority)",
}

VERIFICATION_MANIFEST = {
    "automated": tuple(f"DAC-V35-{number:03d}" for number in range(0, 101, 10)),
    "physical": ("DAC-V35-110",),
    "conditional": ("DAC-V35-120",),
    "post_stable": ("DAC-V35-130",),
    "separate_promotion": ("DAC-V35-140",),
}


@pytest.fixture(autouse=True)
def _qt_runtime():
    global _QT_APP
    from PySide6.QtWidgets import QApplication

    _QT_APP = QApplication.instance() or QApplication([])
    yield _QT_APP


def _bridge_for(graph) -> AudioOutputBridge:
    selection = AudioOutputSelectionCoordinator(
        profiles=graph.audio_output_profiles,
        devices=graph.audio_device_registry,
        output_session=graph.output_session,
        engines=graph.audio_engine_service,
    )
    return AudioOutputBridge(
        graph.volume_policy,
        graph.playback,
        graph.signal_truth,
        devices=graph.audio_device_registry,
        profiles=graph.audio_output_profiles,
        output_session=graph.output_session,
        engines=graph.audio_engine_service,
        selection_coordinator=selection,
        qualification=graph.dac_qualification,
        refresh_devices=graph.udev_observer.rescan,
    )


def assert_audio_output_consistent(graph) -> None:
    """Cross-authority invariant used at every lifecycle boundary."""
    assert graph.playback._output_tx is graph.output_session
    assert graph.playback._volume_port is graph.volume_policy
    assert graph.volume_policy._audio is graph.audio_router
    assert graph.volume_policy._output is graph.output_session
    assert (
        graph.gstreamer_engine_provider.direct_executor is graph.direct_output_executor
    )
    assert graph.output_session._executors["gstreamer"] is graph.direct_output_executor
    assert graph.direct_output_lifecycle._registry is graph.audio_device_registry
    assert graph.direct_output_lifecycle._playback is graph.playback
    assert graph.direct_output_lifecycle._output_session is graph.output_session
    assert (
        graph.audio_engine_service.state.active_engine_id
        == graph.audio_router.bound_engine_id
    )

    plan = graph.output_session.active_plan
    handle = graph.direct_output_executor.handle
    truth = graph.signal_truth.active_snapshot
    if graph.output_session.state in {
        OutputSessionState.READY,
        OutputSessionState.RUNNING,
        OutputSessionState.PAUSED,
    }:
        assert plan is not None and handle is not None
        assert plan.plan_id == handle.plan_id
        if graph.output_session.state is OutputSessionState.RUNNING:
            assert truth is not None
            assert truth.identity.plan_id == plan.plan_id
            assert truth.identity.stable_device_id == plan.stable_device_id
            assert graph.volume_policy.authority is VolumeAuthority.FIXED
    else:
        assert plan is None
        assert handle is None
        assert truth is None


def _reconnect_and_qualify(graph, tmp_path: Path, *, card_index: int) -> int:
    sysfs = tmp_path / "linux-topology" / "sys"
    build_linux_sysfs(
        sysfs,
        usb_devices=(
            UsbDevice("2-1", "2622", "0105", serial="DX5ABC123", bcd_device="0100"),
        ),
        cards=(),
    )
    graph.udev_observer.handle_event(action="add", subsystem="usb", sys_name="2-1")
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
                evidence_refs=("probe:E2E-100",),
            ),
        ),
    )
    return generation


def test_e2e_100_01_authority_and_package_manifests_are_complete() -> None:
    assert set(AUTHORITY_MANIFEST) == {
        "sequence_navigation",
        "playback_state",
        "engine_state",
        "device_topology",
        "profile_selection",
        "output_transaction",
        "volume_execution",
        "runtime_evidence",
        "presentation_projection",
    }
    assert VERIFICATION_MANIFEST["automated"] == (
        "DAC-V35-000",
        "DAC-V35-010",
        "DAC-V35-020",
        "DAC-V35-030",
        "DAC-V35-040",
        "DAC-V35-050",
        "DAC-V35-060",
        "DAC-V35-070",
        "DAC-V35-080",
        "DAC-V35-090",
        "DAC-V35-100",
    )
    assert "DAC-V35-110" not in VERIFICATION_MANIFEST["automated"]
    assert VERIFICATION_MANIFEST["conditional"] == ("DAC-V35-120",)
    assert VERIFICATION_MANIFEST["post_stable"] == ("DAC-V35-130",)
    assert VERIFICATION_MANIFEST["separate_promotion"] == ("DAC-V35-140",)


def test_e2e_100_02_productive_graph_has_one_authority_per_concern(
    tmp_path: Path,
) -> None:
    graph, _bindings = _direct_graph(tmp_path)
    try:
        assert_audio_output_consistent(graph)
        assert graph.output_session.state is OutputSessionState.IDLE
    finally:
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_e2e_100_03_direct_prepare_commit_converges_every_authority(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    bridge = _bridge_for(graph)
    try:
        graph.playback.load_and_play(tmp_path / "closure.flac")
        assert graph.output_session.state is OutputSessionState.READY
        assert graph.playback.state.file_path is None
        assert_audio_output_consistent(graph)

        _accept_current(graph, bindings)
        assert graph.playback.state.file_path == tmp_path / "closure.flac"
        assert bridge.selectedDeviceId == _DEVICE_ID
        assert bridge.activeDeviceId == _DEVICE_ID
        assert bridge.isDirect is True
        assert_audio_output_consistent(graph)
    finally:
        bridge.dispose()
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_e2e_100_04_direct_replacement_has_one_committed_identity(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    try:
        graph.playback.load_and_play(tmp_path / "a.flac")
        _accept_current(graph, bindings)
        first = graph.output_session.active_plan
        first_handle = graph.direct_output_executor.handle
        graph.playback.load_and_play(tmp_path / "b.flac")
        _accept_current(graph, bindings)
        second = graph.output_session.active_plan
        second_handle = graph.direct_output_executor.handle

        assert first is not None and second is not None
        assert first_handle is not None and second_handle is not None
        assert second_handle.generation > first_handle.generation
        assert second_handle.plan_id == second.plan_id
        assert graph.playback.state.file_path == tmp_path / "b.flac"
        assert_audio_output_consistent(graph)
    finally:
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_e2e_100_05_disconnect_stops_without_fallback_or_intent_loss(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    selection = graph.audio_output_profiles.load_selection()
    try:
        graph.playback.load_and_play(tmp_path / "loss.flac")
        _accept_current(graph, bindings)
        pipeline_count = len(bindings.pipelines)
        _disconnect(graph, tmp_path)

        assert graph.playback.state.status is PlaybackStatus.STOPPED
        assert graph.output_session.state is OutputSessionState.LOST
        assert graph.audio_output_profiles.load_selection() == selection
        assert graph.audio_router.bound_engine_id.value == "gstreamer"
        assert len(bindings.pipelines) == pipeline_count
        assert graph.output_session.allows_automatic_engine_fallback() is False
        assert_audio_output_consistent(graph)
    finally:
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_e2e_100_06_reconnect_requires_fresh_generation_and_explicit_play(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    try:
        graph.playback.load_and_play(tmp_path / "generation.flac")
        _accept_current(graph, bindings)
        old_generation = graph.output_session.active_plan.binding.generation
        _disconnect(graph, tmp_path)
        pipeline_count = len(bindings.pipelines)
        new_generation = _reconnect_and_qualify(graph, tmp_path, card_index=7)

        assert new_generation > old_generation
        assert graph.output_session.state is OutputSessionState.IDLE
        assert len(bindings.pipelines) == pipeline_count
        assert_audio_output_consistent(graph)

        graph.playback.play()
        _accept_current(graph, bindings)
        assert graph.output_session.active_plan.binding.generation == new_generation
        assert graph.output_session.active_plan.binding.card_index == 7
        assert_audio_output_consistent(graph)
    finally:
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_e2e_100_07_shared_volume_survives_fixed_direct_round_trip(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    try:
        graph.audio_output_profiles.save_selection(AudioOutputSelection(None, None, 2))
        graph.playback.set_volume(37)
        graph.audio_output_profiles.save_selection(
            AudioOutputSelection("p1", _DEVICE_ID, 3)
        )
        graph.playback.load_and_play(tmp_path / "direct.flac")
        _accept_current(graph, bindings)
        assert graph.volume_policy.authority is VolumeAuthority.FIXED
        assert graph.playback.state.volume == 100

        graph.audio_output_profiles.save_selection(AudioOutputSelection(None, None, 4))
        graph.playback.load_and_play(tmp_path / "shared.flac")
        _accept_current(graph, bindings)
        assert graph.volume_policy.authority is VolumeAuthority.MICHI_SOFTWARE
        assert graph.playback.state.volume == 37
        assert bindings.pipelines[-1].volume == pytest.approx(0.37)
    finally:
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_e2e_100_08_signal_truth_is_fresh_and_stale_writes_are_rejected(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    try:
        graph.playback.load_and_play(tmp_path / "truth.flac")
        _accept_current(graph, bindings)
        g1_handle = graph.direct_output_executor.handle
        g1_identity = graph.signal_truth.active_snapshot.identity
        _disconnect(graph, tmp_path)
        _reconnect_and_qualify(graph, tmp_path, card_index=4)
        graph.playback.play()
        _accept_current(graph, bindings)
        g2_snapshot = graph.signal_truth.active_snapshot

        assert g2_snapshot.identity != g1_identity
        with pytest.raises(DirectExecutorError, match="DIRECT_STALE_EXECUTION"):
            graph.direct_output_executor.record_runtime_anomaly(
                g1_handle, "late generation"
            )
        assert graph.signal_truth.active_snapshot == g2_snapshot
        assert_audio_output_consistent(graph)
    finally:
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_e2e_100_09_normal_projection_never_uses_backend_identity(
    tmp_path: Path,
) -> None:
    graph, _bindings = _direct_graph(tmp_path)
    bridge = _bridge_for(graph)
    try:
        row = next(item for item in bridge.devices if not item["isShared"])
        assert row["stableDeviceId"] == _DEVICE_ID
        assert "hw:" not in row["displayName"].casefold()
        assert _DEVICE_ID not in row["displayName"]
        assert row["alsaLocator"].startswith("hw:")  # diagnostics only
    finally:
        bridge.dispose()
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_e2e_100_10_shutdown_follows_sealed_callback_and_authority_order() -> None:
    from michi.bootstrap import ApplicationContainer

    calls: list[str] = []
    container = ApplicationContainer()

    container._persistence = SimpleNamespace(shutdown=lambda: calls.append("persist"))
    container._playback_session = SimpleNamespace(stop=lambda: calls.append("session"))
    container._aob = SimpleNamespace(dispose=lambda: calls.append("bridge"))
    container._direct_output_lifecycle = SimpleNamespace(
        shutdown=lambda: calls.append("lifecycle")
    )
    container._udev_observer = SimpleNamespace(stop=lambda: calls.append("udev"))
    container._audio_engine_convergence = SimpleNamespace(
        shutdown=lambda: calls.append("convergence")
    )
    container._playback = SimpleNamespace(stop=lambda: calls.append("playback-stop"))
    container._output_session = SimpleNamespace(
        state=SimpleNamespace(value="running"),
        release_active=lambda _reason: calls.append("output-release"),
    )
    container._audio_engine_registry = None
    container._audio_engine_service = None
    container._audio_router = SimpleNamespace(
        unbind=lambda: calls.append("engine-unbind")
    )

    ApplicationContainer.shutdown(container)

    expected = (
        "persist",
        "session",
        "bridge",
        "lifecycle",
        "udev",
        "convergence",
        "playback-stop",
        "output-release",
        "engine-unbind",
    )
    assert tuple(item for item in calls if item in expected) == expected


def test_e2e_100r1_01_qt_engine_refuses_direct_without_switch_or_fallback(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(
        tmp_path, startup_selected_engine=AudioEngineId.QT_MULTIMEDIA
    )
    try:
        graph.playback.load_and_play(tmp_path / "engine.flac")
        assert graph.playback.state.error_message.startswith(
            "Direct requires GStreamer:"
        )
        assert (
            graph.audio_engine_service.state.active_engine_id
            is AudioEngineId.QT_MULTIMEDIA
        )
        assert graph.audio_output_profiles.load_selection().selected_profile_id == "p1"
        assert graph.output_session.active_plan is None
        assert graph.direct_output_executor.handle is None
        assert bindings.pipelines == []
        assert failure_copy("ENGINE_UNSUPPORTED_FOR_DIRECT")[0] == (
            "Direct requires GStreamer"
        )
    finally:
        graph.direct_output_lifecycle.shutdown()
        graph.audio_engine_convergence.shutdown()
        if graph.audio_router.bound_engine_id is not None:
            graph.audio_router.unbind()
        graph.qt_engine_provider.close()


def test_e2e_100r1_02_busy_is_ambiguous_not_negative_capability(
    tmp_path: Path,
) -> None:
    graph, _bindings = _direct_graph(tmp_path)
    requested = PcmTuple(96_000, "S32_LE", 2, 24)

    class _BusyProbe:
        def probe_exact(self, **_kwargs):
            return ExactProbeResult(
                requested=requested,
                negotiated=None,
                disposition="device_busy",
                alsa_error_code=16,
                detail="busy",
                evidence_ref="probe:busy",
            )

    try:
        before = graph.dac_qualification.cached_evidence(_DEVICE_ID)
        graph.dac_qualification._adapter = _BusyProbe()
        result = graph.dac_qualification.qualify_and_cache(
            stable_device_id=_DEVICE_ID,
            locator="hw:CARD=DX5,DEV=0",
            rate_hz=96_000,
            transport_format="S32_LE",
            channels=2,
        )
        assert result.supported is None
        assert result.evidence_refs == ("probe:busy",)
        assert graph.dac_qualification.cached_evidence(_DEVICE_ID) == before
        assert graph.output_session.active_plan is None
        assert graph.audio_output_profiles.load_selection().selected_profile_id == "p1"
        assert failure_copy("ALSA_DEVICE_BUSY")[0] == "Device busy"
    finally:
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_e2e_100r12_03_unknown_exact_tuple_is_qualified_before_executor(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    try:
        graph.dac_qualification.cache_evidence(_DEVICE_ID, ())
        graph.playback.load_and_play(tmp_path / "unknown.flac")
        from tests.dac.test_v35_productive_direct_composition import (
            _wait_for_pipeline_count,
        )

        _wait_for_pipeline_count(bindings, 1)
        assert graph.output_session.active_plan is not None
        assert graph.direct_output_executor.handle is not None
        assert graph.audio_output_profiles.load_selection().selected_profile_id == "p1"
        assert failure_copy("EXACT_TUPLE_UNKNOWN")[0] == "Format not verified"
    finally:
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_e2e_100r1_04_identical_dacs_keep_distinct_identity_and_profiles(
    tmp_path: Path,
) -> None:
    graph, _bindings = _direct_graph(tmp_path)
    bridge = _bridge_for(graph)
    second_id = "usb:2622:0105:DX5XYZ999"
    sysfs = tmp_path / "linux-topology" / "sys"
    try:
        build_linux_sysfs(
            sysfs,
            usb_devices=(
                UsbDevice("2-1", "2622", "0105", serial="DX5ABC123"),
                UsbDevice("2-2", "2622", "0105", serial="DX5XYZ999"),
            ),
            cards=(
                AlsaCard(1, "DX5", "2-1"),
                AlsaCard(2, "DX5B", "2-2"),
            ),
        )
        graph.udev_observer.rescan()
        graph.audio_output_profiles.save_profile(stable_direct_preset("p2", second_id))

        ids = {item.stable_device_id for item in graph.audio_device_registry.snapshot()}
        assert {_DEVICE_ID, second_id} <= ids
        assert graph.audio_device_registry.bindings_for(_DEVICE_ID)[0].card_index == 1
        assert graph.audio_device_registry.bindings_for(second_id)[0].card_index == 2
        profiles = {
            item.profile_id: item.stable_device_id
            for item in graph.audio_output_profiles.load_profiles()
        }
        assert profiles["p1"] == _DEVICE_ID
        assert profiles["p2"] == second_id
        rows = [item for item in bridge.devices if not item["isShared"]]
        names = {item["stableDeviceId"]: item["displayName"] for item in rows}
        assert names[_DEVICE_ID] != names[second_id]
    finally:
        bridge.dispose()
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)


def test_e2e_100r1_05_same_dac_reselection_preserves_selected_profile(
    tmp_path: Path,
) -> None:
    graph, _bindings = _direct_graph(tmp_path)
    coordinator = AudioOutputSelectionCoordinator(
        profiles=graph.audio_output_profiles,
        devices=graph.audio_device_registry,
        output_session=graph.output_session,
        engines=graph.audio_engine_service,
    )
    try:
        graph.audio_output_profiles.save_profile(stable_direct_preset("p2", _DEVICE_ID))
        graph.audio_output_profiles.save_selection(
            AudioOutputSelection("p2", _DEVICE_ID, 2)
        )
        coordinator.select_device(_DEVICE_ID)
        selection = graph.audio_output_profiles.load_selection()
        assert selection.selected_device_id == _DEVICE_ID
        assert selection.selected_profile_id == "p2"
    finally:
        graph.direct_output_lifecycle.shutdown()
        _close_graph(graph)
