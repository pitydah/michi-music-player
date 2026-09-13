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


def _direct_graph(tmp_path: Path):
    from test_gstreamer_audio_port import FakeBindings

    from michi.application.dac_qualification_service import (
        default_environment_fingerprint,
    )
    from michi.bootstrap import _build_services
    from michi.domain.audio_device import (
        AudioDeviceBinding,
        BindingKind,
        DeviceObservation,
    )
    from michi.domain.audio_engine import AudioEngineId
    from michi.domain.audio_evidence import (
        CapabilityEvidence,
        EvidenceStrength,
        PcmTuple,
    )
    from michi.domain.audio_output import AudioOutputSelection, stable_direct_preset
    from michi.domain.library import TrackMetadata

    class _Metadata:
        def extract(self, path):
            return TrackMetadata(
                title=Path(path).stem,
                sample_rate_hz=96_000,
                bit_depth=24,
                channels=2,
            )

    bindings = FakeBindings()
    graph = _build_services(
        tmp_path / "michi.db",
        startup_selected_engine=AudioEngineId.GSTREAMER,
        metadata_extractor=_Metadata(),
        artwork_provider=None,
        artwork_cache=None,
        gstreamer_bindings=bindings,
    )
    device_id = "usb:2622:0105:DX5ABC123"
    physical_path = "2-1"
    graph.audio_device_registry.ingest(
        (
            DeviceObservation(
                source="sysfs",
                observed_at_ns=1,
                vendor_id="2622",
                product_id="0105",
                serial="DX5ABC123",
                manufacturer="MichiAudio",
                product="DAC Test",
                physical_path=physical_path,
                bcd_device="0100",
                binding=None,
            ),
            DeviceObservation(
                source="alsa",
                observed_at_ns=1,
                vendor_id=None,
                product_id=None,
                serial=None,
                manufacturer=None,
                product="DX5",
                physical_path=physical_path,
                bcd_device=None,
                binding=AudioDeviceBinding(
                    kind=BindingKind.ALSA_PCM,
                    locator="hw:CARD=DX5,DEV=0",
                    generation=0,
                    currently_available=True,
                    card_index=1,
                    pcm_device=0,
                ),
            ),
        )
    )
    profile = stable_direct_preset("p1", device_id)
    graph.audio_output_profiles.save_profile(profile)
    graph.audio_output_profiles.save_selection(
        AudioOutputSelection("p1", device_id, time.time_ns() // 1_000_000)
    )
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
                environment_fingerprint=default_environment_fingerprint(),
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


class _AtomicDirectPort:
    def __init__(self) -> None:
        self.executor = None
        self.preparation = None

    def stage_direct_load(self, preparation, *, executor) -> None:
        self.executor = executor
        self.preparation = preparation


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
        with pytest.raises(Exception) as exc_info:
            graph.playback.load_and_play(tmp_path / "missing.flac")

        assert "DEVICE_UNAVAILABLE" in str(exc_info.value)
        assert bindings.pipelines == []
        assert graph.audio_router.bound_engine_id.value == "gstreamer"
        assert graph.direct_output_executor.handle is None
    finally:
        _close_graph(graph)
