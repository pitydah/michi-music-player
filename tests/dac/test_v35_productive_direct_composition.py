"""DAC-V35-050 productive Direct vertical gates (P050-01..P050-14)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from michi.application.audio_output_planner import OutputPlanner
from michi.application.output_session_service import (
    OutputRequest,
    OutputSessionService,
)
from michi.application.ports import PlaybackOutputTransactionPort
from michi.domain.audio_device import AudioDeviceBinding, BindingKind, DeviceObservation
from michi.domain.audio_output import OutputSessionState
from michi.infrastructure.audio_output.direct_output_executor import (
    DirectExecutorError,
    GStreamerDirectOutputExecutor,
)
from tests.dac.test_v34_output_planner import _facts

_QT_APP = None


@pytest.fixture(autouse=True)
def _qt_runtime():
    """Install a GUI-capable Qt app without requiring pytest-qt in CI."""
    global _QT_APP
    from PySide6.QtWidgets import QApplication

    _QT_APP = QApplication.instance() or QApplication([])
    yield _QT_APP


def _direct_graph(
    tmp_path: Path,
    *,
    playback_pcms: tuple[int, ...] = (0,),
    alsa_hw_params_reader=None,
    source_metadata=None,
    startup_selected_engine=None,
    preseed_qualification: bool = True,
    qualification_adapter=None,
):
    from test_gstreamer_audio_port import FakeBindings

    from michi.bootstrap import _build_services
    from michi.domain.audio_engine import AudioEngineId
    from michi.domain.audio_evidence import (
        CapabilityEvidence,
        EvidenceStrength,
        ExactProbeResult,
        PcmTuple,
    )
    from michi.domain.audio_output import AudioOutputSelection, stable_direct_preset
    from michi.domain.library import TrackMetadata
    from tests.dac._fixtures import (
        AlsaCard,
        UsbDevice,
        build_linux_sysfs,
        make_roots,
    )

    class _Metadata:
        def extract(self, path):
            return source_metadata or TrackMetadata(
                title=Path(path).stem,
                sample_rate_hz=96_000,
                bit_depth=24,
                channels=2,
            )

    topology_root = tmp_path / "linux-topology"
    topology_root.mkdir()
    sysfs_root = make_roots(topology_root)
    build_linux_sysfs(
        sysfs_root,
        usb_devices=(
            UsbDevice(
                "2-1",
                "2622",
                "0105",
                serial="DX5ABC123",
                bcd_device="0100",
            ),
        ),
        cards=(
            AlsaCard(
                card_index=1,
                card_id="DX5",
                usb_devpath="2-1",
                playback_pcms=playback_pcms,
            ),
        ),
    )
    proc_root = topology_root / "proc" / "asound"
    card_root = proc_root / "card1"
    card_root.mkdir(parents=True)
    (card_root / "id").write_text("DX5\n", encoding="utf-8")
    for pcm_device in playback_pcms:
        sub_root = card_root / f"pcm{pcm_device}p" / "sub0"
        sub_root.mkdir(parents=True)
        (sub_root / "hw_params").write_text("closed\n", encoding="utf-8")

    bindings = FakeBindings()

    if qualification_adapter is None:

        class _ExactOpeningProbe:
            def probe_exact(self, **kwargs):
                significant_bits = 24 if kwargs["transport_format"] == "S32_LE" else 16
                requested = PcmTuple(
                    kwargs["rate_hz"],
                    kwargs["transport_format"],
                    kwargs["channels"],
                    significant_bits,
                )
                return ExactProbeResult(
                    requested,
                    requested,
                    "OPENED",
                    None,
                    None,
                    "probe:test-exact-open",
                )

        qualification_adapter = _ExactOpeningProbe()
    selected_engine = startup_selected_engine or AudioEngineId.GSTREAMER
    graph = _build_services(
        tmp_path / "michi.db",
        startup_selected_engine=selected_engine,
        metadata_extractor=_Metadata(),
        artwork_provider=None,
        artwork_cache=None,
        gstreamer_bindings=bindings,
        alsa_hw_params_reader=alsa_hw_params_reader,
        audio_sysfs_root=sysfs_root,
        alsa_proc_root=proc_root,
        qualification_adapter=qualification_adapter,
    )
    device_id = "usb:2622:0105:DX5ABC123"
    profile = stable_direct_preset("p1", device_id)
    graph.audio_output_profiles.save_profile(profile)
    graph.audio_output_profiles.save_selection(
        AudioOutputSelection("p1", device_id, time.time_ns() // 1_000_000)
    )
    if preseed_qualification:
        graph.dac_qualification.cache_evidence(
            device_id,
            (
                CapabilityEvidence(
                    stable_device_id=device_id,
                    tuple=PcmTuple(96_000, "S32_LE", 2, 24),
                    supported=True,
                    strength=EvidenceStrength.OPENED,
                    source="michi-alsa-probe",
                    observed_at_ns=1,
                    environment_fingerprint=(
                        graph.dac_qualification.current_environment_fingerprint(
                            device_id
                        )
                    ),
                    evidence_refs=("probe:productive",),
                ),
            ),
        )
    return graph, bindings


def _close_graph(graph) -> None:
    graph.audio_engine_convergence.shutdown()
    if graph.audio_router.bound_engine_id is not None:
        graph.audio_router.unbind()
    provider = graph.gstreamer_engine_provider
    if provider.current_port is not None:
        provider.close()


def _accept_current(graph, bindings) -> None:
    from test_gstreamer_audio_port import _deliver, _FakeMsgType, _msg

    port = graph.gstreamer_engine_provider.current_port
    message, generation = _msg(port, _FakeMsgType.ASYNC_DONE, bindings.pipelines[-1])
    _deliver(port, message, generation)


def _wait_for_pipeline_count(bindings, count: int, timeout_s: float = 2.0) -> None:
    from PySide6.QtCore import QCoreApplication

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline and len(bindings.pipelines) < count:
        QCoreApplication.processEvents()
        time.sleep(0.01)
    assert len(bindings.pipelines) >= count


class _AtomicDirectPort:
    def __init__(self) -> None:
        self.executor = None
        self.preparation = None

    def stage_direct_load(self, preparation, *, executor) -> None:
        self.executor = executor
        self.preparation = preparation

    def discard_direct_load(self, handle, *, executor) -> bool:
        if executor is not self.executor:
            return False
        if self.preparation is None or self.preparation.handle != handle:
            return False
        self.preparation = None
        return True


def _direct_service(port: _AtomicDirectPort):
    executor = GStreamerDirectOutputExecutor()
    executor.bind_port_provider(lambda: port)
    service = OutputSessionService(
        OutputPlanner(),
        request_provider=lambda path: OutputRequest.direct(_facts()),
        executors={"gstreamer": executor},
    )
    return service, executor


def test_p050_01_production_bootstrap_owns_one_direct_executor(tmp_path: Path) -> None:
    from conftest import FakeAudioPort

    from michi.bootstrap import _build_services
    from michi.domain.audio_engine import AudioEngineId

    graph = _build_services(tmp_path / "michi.db", backend=FakeAudioPort())
    try:
        provider = graph.audio_engine_registry.provider(AudioEngineId.GSTREAMER)
        assert graph.direct_output_executor is provider.direct_executor
    finally:
        graph.audio_router.unbind()


def test_p050_02_output_session_is_productively_installed(tmp_path: Path) -> None:
    from conftest import FakeAudioPort

    from michi.bootstrap import _build_services

    graph = _build_services(tmp_path / "michi.db", backend=FakeAudioPort())
    try:
        assert graph.playback._output_tx is graph.output_session
        assert isinstance(graph.output_session, PlaybackOutputTransactionPort)
    finally:
        graph.audio_router.unbind()


def test_p050_03_default_selection_remains_explicit_shared(tmp_path: Path) -> None:
    from conftest import FakeAudioPort

    from michi.bootstrap import _build_services

    audio = FakeAudioPort()
    graph = _build_services(tmp_path / "michi.db", backend=audio)
    try:
        graph.playback.load_and_play(tmp_path / "shared.flac")
        assert graph.output_session.mode == "shared"
        assert graph.direct_output_executor.handle is None
    finally:
        graph.audio_router.unbind()


def test_p050_04_plan_handle_recipe_are_staged_as_one_identity() -> None:
    port = _AtomicDirectPort()
    service, executor = _direct_service(port)

    token = service.prepare_for_media(Path("a.flac"))

    assert token.startswith("output-tx:")
    assert port.executor is executor
    assert port.preparation.handle == executor.handle
    assert port.preparation.handle.plan_id == port.preparation.recipe.plan_id


def test_p050_07_unverified_execution_cannot_commit_session() -> None:
    port = _AtomicDirectPort()
    service, _executor = _direct_service(port)
    media = Path("a.flac")
    token = service.prepare_for_media(media)

    with pytest.raises(DirectExecutorError) as exc_info:
        service.commit_media(token, media)

    assert exc_info.value.code == "DIRECT_PREROLL_NOT_VERIFIED"
    assert service.state is OutputSessionState.READY


def test_p050_05_runtime_is_verified_before_playback_commit(tmp_path: Path) -> None:
    graph, bindings = _direct_graph(tmp_path)
    media = tmp_path / "direct.flac"
    try:
        graph.playback.load_and_play(media)
        assert graph.output_session.state is OutputSessionState.READY
        assert graph.playback.state.file_path is None

        _accept_current(graph, bindings)

        assert graph.output_session.state is OutputSessionState.RUNNING
        assert graph.playback.state.file_path == media

        from test_gstreamer_audio_port import _deliver, _FakeMsgType, _msg

        port = graph.gstreamer_engine_provider.current_port
        message, generation = _msg(
            port,
            _FakeMsgType.ERROR,
            bindings.pipelines[-1],
            error_text="device lost",
        )
        _deliver(port, message, generation)
        assert graph.output_session.state is OutputSessionState.IDLE
        assert graph.direct_output_executor.handle is None
    finally:
        _close_graph(graph)


def test_p050_06_runtime_mismatch_aborts_transaction_once(tmp_path: Path) -> None:
    graph, bindings = _direct_graph(tmp_path)
    calls: list[str] = []
    original_abort = graph.output_session.abort_media

    def _abort(token, reason):
        calls.append(reason)
        original_abort(token, reason)

    graph.output_session.abort_media = _abort
    try:
        graph.playback.load_and_play(tmp_path / "bad.flac")
        bindings.direct_snapshot_overrides = {"rate": 48_000}
        _accept_current(graph, bindings)

        assert calls == ["media_rejected"]
        assert graph.output_session.state is OutputSessionState.IDLE
        assert graph.playback.state.file_path is None
    finally:
        _close_graph(graph)


def test_p050_08_failed_direct_candidate_leaves_next_shared_load_clean(
    tmp_path: Path,
) -> None:
    from michi.domain.audio_output import AudioOutputSelection

    graph, bindings = _direct_graph(tmp_path)
    try:
        graph.playback.load_and_play(tmp_path / "bad.flac")
        bindings.direct_snapshot_overrides = {"format": "S16LE"}
        _accept_current(graph, bindings)
        graph.audio_output_profiles.save_selection(AudioOutputSelection(None, None, 2))
        bindings.direct_snapshot_overrides = None

        shared = tmp_path / "shared.flac"
        graph.playback.load_and_play(shared)
        assert bindings.pipelines[-1].audio_sink is None
        _accept_current(graph, bindings)

        assert graph.output_session.mode == "shared"
        assert graph.playback.state.file_path == shared
    finally:
        _close_graph(graph)


def test_p050_09_direct_to_shared_releases_direct_state(tmp_path: Path) -> None:
    from michi.domain.audio_output import AudioOutputSelection

    graph, bindings = _direct_graph(tmp_path)
    try:
        graph.playback.load_and_play(tmp_path / "direct.flac")
        _accept_current(graph, bindings)
        graph.audio_output_profiles.save_selection(AudioOutputSelection(None, None, 2))

        graph.playback.load_and_play(tmp_path / "shared.flac")
        _accept_current(graph, bindings)

        assert graph.direct_output_executor.handle is None
        assert bindings.pipelines[-1].audio_sink is None
    finally:
        _close_graph(graph)


def test_r1_provisional_direct_then_shared_cannot_leak_strict_recipe(
    tmp_path: Path,
) -> None:
    from michi.domain.audio_output import AudioOutputSelection

    graph, bindings = _direct_graph(tmp_path)
    try:
        graph.output_session.prepare_for_media(tmp_path / "direct.flac")
        port = graph.gstreamer_engine_provider.current_port
        assert port is not None and port._pending_direct_load is not None

        graph.audio_output_profiles.save_selection(AudioOutputSelection(None, None, 2))
        graph.output_session.prepare_for_media(tmp_path / "shared.flac")

        assert graph.direct_output_executor.handle is None
        assert port._pending_direct_load is None
        port.load(tmp_path / "shared.flac")
        assert bindings.pipelines[-1].audio_sink is None
    finally:
        _close_graph(graph)


def test_p050_10_shared_to_direct_stages_exact_new_plan(tmp_path: Path) -> None:
    from michi.domain.audio_output import AudioOutputSelection

    graph, bindings = _direct_graph(tmp_path)
    try:
        graph.audio_output_profiles.save_selection(AudioOutputSelection(None, None, 2))
        graph.playback.load_and_play(tmp_path / "shared.flac")
        _accept_current(graph, bindings)
        graph.audio_output_profiles.save_selection(
            AudioOutputSelection("p1", "usb:2622:0105:DX5ABC123", 3)
        )

        graph.playback.load_and_play(tmp_path / "direct.flac")

        plan = graph.output_session.plan
        handle = graph.direct_output_executor.handle
        assert plan is not None and handle is not None
        assert handle.plan_id == plan.plan_id
        assert bindings.pipelines[-1].audio_sink is not None
    finally:
        _close_graph(graph)


def test_p050_11_stop_releases_active_direct_once(tmp_path: Path) -> None:
    graph, bindings = _direct_graph(tmp_path)
    calls: list[str] = []
    original_release = graph.direct_output_executor.release

    def _release(reason):
        calls.append(reason)
        original_release(reason)

    graph.direct_output_executor.release = _release
    try:
        graph.playback.load_and_play(tmp_path / "direct.flac")
        _accept_current(graph, bindings)
        graph.playback.stop()

        assert calls == ["stop"]
        assert graph.output_session.state is OutputSessionState.IDLE
        assert graph.playback._accepted is False
    finally:
        _close_graph(graph)


def test_p050_12_engine_loss_releases_direct_without_automatic_fallback(
    tmp_path: Path,
) -> None:
    from michi.application.audio_engine_runtime_failure import (
        AudioEngineRuntimeFailureEvent,
    )
    from michi.domain.audio_engine import AudioEngineId

    graph, bindings = _direct_graph(tmp_path)
    calls: list[str] = []
    original_release = graph.direct_output_executor.release

    def _release(reason):
        calls.append(reason)
        original_release(reason)

    graph.direct_output_executor.release = _release
    try:
        graph.playback.load_and_play(tmp_path / "direct.flac")
        _accept_current(graph, bindings)
        provider = graph.gstreamer_engine_provider
        graph.audio_engine_convergence.handle_runtime_failure(
            AudioEngineRuntimeFailureEvent(
                AudioEngineId.GSTREAMER,
                provider.current_runtime_generation,
                "device lost",
            )
        )

        assert calls.count("engine_loss") == 1
        assert graph.audio_router.bound_engine_id is None
        assert graph.audio_engine_service.state.active_engine_id is None
    finally:
        _close_graph(graph)


def test_p050_13_engine_switch_stop_leaves_no_orphan_session(tmp_path: Path) -> None:
    graph, bindings = _direct_graph(tmp_path)
    try:
        graph.playback.load_and_play(tmp_path / "direct.flac")
        _accept_current(graph, bindings)
        from test_gstreamer_audio_port import _deliver, msg_state

        port = graph.gstreamer_engine_provider.current_port
        message, generation = msg_state(
            port, bindings.pipelines[-1], bindings.STATE.PLAYING
        )
        _deliver(port, message, generation)
        lease = graph.playback.begin_engine_switch()
        lease.controlled_stop()

        assert graph.output_session.state is OutputSessionState.IDLE
        assert graph.direct_output_executor.handle is None
        lease.invalidate_backend_acceptance()
        lease.release()
    finally:
        _close_graph(graph)


def test_p050_14_direct_prepare_failure_never_loads_or_falls_back(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path)
    graph.audio_device_registry.handle_removed("2-1")
    try:
        graph.playback.load_and_play(tmp_path / "missing.flac")

        assert graph.playback.state.error_message.startswith("Device disconnected:")
        assert bindings.pipelines == []
        assert graph.audio_router.bound_engine_id.value == "gstreamer"
        assert graph.direct_output_executor.handle is None
    finally:
        _close_graph(graph)


def test_dr_04_productive_pre_destructive_failure_restores_direct_a(
    tmp_path: Path,
) -> None:
    """R1: if GStreamer preserves A, every canonical layer restores A."""
    from michi.application.ports import AudioLoadError

    graph, bindings = _direct_graph(tmp_path)
    media_a = tmp_path / "a.flac"
    media_b = tmp_path / "b.flac"
    try:
        graph.playback.load_and_play(media_a)
        _accept_current(graph, bindings)
        plan_a = graph.output_session.plan
        handle_a = graph.direct_output_executor.handle
        pipeline_a = bindings.pipelines[-1]

        bindings.failed_states.add(bindings.STATE.NULL)
        with pytest.raises((AudioLoadError, RuntimeError)):
            graph.playback.load_and_play(media_b)

        assert graph.playback.state.file_path == media_a
        assert graph.playback._accepted is True
        assert graph.output_session.state is OutputSessionState.RUNNING
        assert graph.output_session.plan == plan_a
        assert graph.direct_output_executor.handle == handle_a
        assert graph.gstreamer_engine_provider.current_port._pipeline is pipeline_a
    finally:
        bindings.failed_states.clear()
        _close_graph(graph)


def test_dr_05_post_destructive_arm_failure_never_resurrects_a(
    tmp_path: Path,
) -> None:
    from michi.application.ports import AudioLoadError
    from michi.domain.playback import PlaybackStatus

    graph, bindings = _direct_graph(tmp_path)
    media_a = tmp_path / "a.flac"
    try:
        graph.playback.load_and_play(media_a)
        _accept_current(graph, bindings)
        bindings.arm_exception_stage = "set_uri"
        bindings.arm_exception = ValueError("synthetic post-destructive failure")

        with pytest.raises(AudioLoadError) as caught:
            graph.playback.load_and_play(tmp_path / "b.flac")

        assert caught.value.previous_source_preserved is False
        assert graph.playback.state.file_path == media_a  # logical history only
        assert graph.playback.state.status is PlaybackStatus.STOPPED
        assert graph.playback._accepted is False
        assert graph.output_session.state is OutputSessionState.IDLE
        assert graph.output_session.plan is None
        assert graph.direct_output_executor.handle is None
        assert graph.signal_truth.active_snapshot is None
        port = graph.gstreamer_engine_provider.current_port
        assert port._current_path is None and port._pending_path is None
    finally:
        bindings.arm_exception_stage = None
        _close_graph(graph)


def test_dr_06_successful_b_commit_has_one_direct_authority(tmp_path: Path) -> None:
    from michi.infrastructure.audio_output.direct_output_executor import (
        DirectExecutionState,
    )

    graph, bindings = _direct_graph(tmp_path)
    try:
        graph.playback.load_and_play(tmp_path / "a.flac")
        _accept_current(graph, bindings)
        handle_a = graph.direct_output_executor.handle

        media_b = tmp_path / "b.flac"
        graph.playback.load_and_play(media_b)
        pipeline_b = bindings.pipelines[-1]
        assert bindings.null_request_count == 1, "A is released exactly once"
        _accept_current(graph, bindings)

        handle_b = graph.direct_output_executor.handle
        assert handle_b is not None and handle_b != handle_a
        assert graph.direct_output_executor.state is DirectExecutionState.COMMITTED
        assert graph.output_session.state is OutputSessionState.RUNNING
        assert graph.output_session.plan.plan_id == handle_b.plan_id
        assert graph.playback.state.file_path == media_b
        assert graph.gstreamer_engine_provider.current_port._pipeline is pipeline_b
    finally:
        _close_graph(graph)


def test_dr_07_play_failure_after_b_load_clears_a_and_b(tmp_path: Path) -> None:
    from michi.domain.playback import PlaybackStatus

    graph, bindings = _direct_graph(tmp_path)
    media_a = tmp_path / "a.flac"
    try:
        graph.playback.load_and_play(media_a)
        _accept_current(graph, bindings)
        bindings.arm_exception_stage = "set_state_playing"
        bindings.arm_exception = RuntimeError("synthetic B play failure")

        with pytest.raises(RuntimeError, match="B play failure"):
            graph.playback.load_and_play(tmp_path / "b.flac")

        assert graph.playback.state.file_path == media_a
        assert graph.playback.state.status is PlaybackStatus.STOPPED
        assert graph.playback._accepted is False
        assert graph.output_session.state is OutputSessionState.IDLE
        assert graph.direct_output_executor.handle is None
    finally:
        bindings.arm_exception_stage = None
        _close_graph(graph)


def test_dr_08_stale_b_acceptance_cannot_reclaim_after_failure(tmp_path: Path) -> None:
    from michi.application.ports import AudioLoadError

    graph, bindings = _direct_graph(tmp_path)
    media_a = tmp_path / "a.flac"
    media_b = tmp_path / "b.flac"
    try:
        graph.playback.load_and_play(media_a)
        _accept_current(graph, bindings)
        bindings.arm_exception_stage = "set_uri"
        bindings.arm_exception = ValueError("B arm failed")
        with pytest.raises(AudioLoadError):
            graph.playback.load_and_play(media_b)
        failed_b = bindings.pipelines[-1]
        failed_generation = graph.gstreamer_engine_provider.current_port._generation - 1
        bindings.arm_exception_stage = None

        from test_gstreamer_audio_port import _deliver, _FakeMsgType, _msg

        port = graph.gstreamer_engine_provider.current_port
        message, _generation = _msg(port, _FakeMsgType.ASYNC_DONE, failed_b)
        _deliver(port, message, failed_generation)

        assert graph.playback.state.file_path == media_a
        assert graph.playback._accepted is False
        assert graph.output_session.state is OutputSessionState.IDLE
        assert graph.direct_output_executor.handle is None
    finally:
        _close_graph(graph)


def test_me_01_zero_playback_endpoints_refuses_direct(tmp_path: Path) -> None:
    graph, bindings = _direct_graph(tmp_path, playback_pcms=())
    try:
        graph.playback.load_and_play(tmp_path / "zero.flac")
        # UNIVERSAL-DISCOVERY-R1: brand-new hardware with no proven playback
        # endpoint is not admitted into AudioDeviceRegistry. A stale/preseeded
        # Direct selection therefore fails closed as an unavailable device;
        # Michi must never synthesize a PCM binding to preserve old semantics.
        assert graph.playback.state.error_code == "DEVICE_UNAVAILABLE"
        assert graph.playback.state.error_message.startswith("Device disconnected:")
        assert bindings.pipelines == []
    finally:
        _close_graph(graph)


def test_me_02_one_playback_endpoint_uses_the_exact_binding(tmp_path: Path) -> None:
    graph, bindings = _direct_graph(tmp_path, playback_pcms=(7,))
    try:
        graph.playback.load_and_play(tmp_path / "one.flac")
        assert graph.output_session.plan is not None
        assert graph.output_session.plan.binding.locator == "hw:CARD=DX5,DEV=7"
        assert bindings.built_recipes[-1].device == "hw:CARD=DX5,DEV=7"
    finally:
        _close_graph(graph)


def test_me_03_multiple_playback_endpoints_fail_closed(tmp_path: Path) -> None:
    graph, bindings = _direct_graph(tmp_path, playback_pcms=(0, 1))
    try:
        graph.playback.load_and_play(tmp_path / "ambiguous.flac")
        assert graph.playback.state.error_message.startswith(
            "Choose a Direct endpoint:"
        )
        assert graph.output_session.plan is None
        assert graph.direct_output_executor.handle is None
        assert bindings.pipelines == []
    finally:
        _close_graph(graph)


def test_me_04_ambiguity_refusal_is_independent_of_endpoint_order(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path, playback_pcms=(9, 2))
    try:
        graph.playback.load_and_play(tmp_path / "unordered.flac")
        error = graph.playback.state.error_message
        assert error.startswith("Choose a Direct endpoint:")
        assert "DEV=2" not in error and "DEV=9" not in error
        assert bindings.built_recipes == []
    finally:
        _close_graph(graph)


def test_me_05_productive_resolver_never_uses_compatibility_binding_for(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path, playback_pcms=(3,))
    graph.audio_device_registry.binding_for = lambda *args: (_ for _ in ()).throw(
        AssertionError("binding_for must not select a Direct endpoint")
    )
    try:
        graph.playback.load_and_play(tmp_path / "canonical.flac")
        assert graph.output_session.plan.binding.pcm_device == 3
    finally:
        _close_graph(graph)


def test_me_06_ambiguous_direct_does_not_touch_backend_or_shared_fallback(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path, playback_pcms=(0, 1))
    try:
        graph.playback.load_and_play(tmp_path / "no-fallback.flac")
        assert graph.playback.state.error_message.startswith(
            "Choose a Direct endpoint:"
        )
        assert bindings.pipelines == []
        assert graph.audio_router.bound_engine_id.value == "gstreamer"
        assert graph.output_session.mode == "shared"
    finally:
        _close_graph(graph)


def test_me_07_endpoint_set_change_advances_generation_but_never_guesses(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path, playback_pcms=(0,))
    device_id = "usb:2622:0105:DX5ABC123"
    first_generation = graph.audio_device_registry.generation_for(device_id)
    usb = DeviceObservation(
        source="sysfs",
        observed_at_ns=2,
        vendor_id="2622",
        product_id="0105",
        serial="DX5ABC123",
        manufacturer="MichiAudio",
        product="DAC Test",
        physical_path="2-1",
        bcd_device="0100",
        binding=None,
        descriptor_sha256="a" * 64,
    )

    def endpoint(pcm_device: int) -> DeviceObservation:
        return DeviceObservation(
            source="alsa",
            observed_at_ns=2,
            vendor_id=None,
            product_id=None,
            serial=None,
            manufacturer=None,
            product="DX5",
            physical_path="2-1",
            bcd_device=None,
            binding=AudioDeviceBinding(
                kind=BindingKind.ALSA_PCM,
                locator=f"hw:CARD=DX5,DEV={pcm_device}",
                generation=0,
                currently_available=True,
                card_index=1,
                pcm_device=pcm_device,
            ),
        )

    graph.audio_device_registry.ingest((usb, endpoint(0), endpoint(1)))
    try:
        assert graph.audio_device_registry.generation_for(device_id) != first_generation
        graph.playback.load_and_play(tmp_path / "changed.flac")
        assert graph.playback.state.error_message.startswith(
            "Choose a Direct endpoint:"
        )
        assert bindings.pipelines == []
    finally:
        _close_graph(graph)
