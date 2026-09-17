"""DAC-V35-090 UI90-01..21 — truthful audio-output presentation gates."""

from __future__ import annotations

from types import SimpleNamespace

from michi.application.audio_device_registry import AudioDeviceRegistry
from michi.application.audio_output_ports import VolumeAuthority
from michi.application.audio_output_profile_service import AudioOutputProfileService
from michi.application.audio_output_selection_coordinator import (
    AudioOutputSelectionCoordinator,
)
from michi.domain.audio_device import (
    AudioDeviceBinding,
    BindingKind,
    DeviceObservation,
)
from michi.domain.audio_engine import AudioEngineId
from michi.domain.audio_evidence import PcmTuple
from michi.domain.audio_output import (
    AudioOutputProfile,
    AudioOutputSelection,
    FallbackKind,
    OutputPathPreference,
    OutputSelectionState,
    OutputSessionState,
    RatePolicy,
    VolumePolicy,
)
from michi.domain.playback import PlaybackState
from michi.domain.signal_truth import (
    AlsaRuntimeEvidence,
    DecodedRuntimeEvidence,
    EngineRuntimeEvidence,
    OutputPlanEvidence,
    SignalTruthIdentity,
    SignalTruthRecorder,
)
from michi.presentation.audio_output_bridge import AudioOutputBridge, failure_copy


class _Repo:
    def __init__(self) -> None:
        self.profiles = []
        self.selection = AudioOutputSelection(None, None, 0)

    def load_profiles(self):
        return tuple(self.profiles)

    def save_profile(self, profile) -> None:
        self.profiles = [
            item for item in self.profiles if item.profile_id != profile.profile_id
        ]
        self.profiles.append(profile)

    def load_selection(self):
        return self.selection

    def save_selection(self, selection) -> None:
        self.selection = selection


class _Observable:
    def __init__(self) -> None:
        self.subscribers = []

    def subscribe_changed(self, callback) -> None:
        if callback not in self.subscribers:
            self.subscribers.append(callback)

    def unsubscribe_changed(self, callback) -> None:
        if callback in self.subscribers:
            self.subscribers.remove(callback)

    def publish(self) -> None:
        for callback in tuple(self.subscribers):
            callback()


class _Playback(_Observable):
    def __init__(self) -> None:
        super().__init__()
        self.state = PlaybackState()


class _Engine(_Observable):
    def __init__(self) -> None:
        super().__init__()
        self.state = SimpleNamespace(active_engine_id=AudioEngineId.GSTREAMER)


class _Session(_Observable):
    def __init__(self) -> None:
        super().__init__()
        self.selected_device_id = None
        self.selected_profile_id = None
        self.active_device_id = None
        self.active_plan_id = None
        self.state = OutputSessionState.IDLE
        self.error_code = None
        self.mode = "shared"
        self.last_cleanup_diagnostic = None

    def select(self, *, device_id, profile_id) -> None:
        self.selected_device_id = device_id
        self.selected_profile_id = profile_id
        self.publish()

    def selection_state(self):
        return OutputSelectionState(
            self.selected_device_id,
            self.selected_profile_id,
            self.active_device_id,
            self.active_plan_id,
            self.state,
            self.error_code,
        )

    def activate(self, stable_id: str, *, generation: int) -> None:
        self.active_device_id = stable_id
        self.active_plan_id = f"plan:{generation}"
        self.state = OutputSessionState.RUNNING
        self.mode = "direct"
        self.publish()

    def lose(self) -> None:
        self.active_device_id = None
        self.active_plan_id = None
        self.state = OutputSessionState.LOST
        self.mode = "lost"
        self.error_code = "device_lost"
        self.publish()


class _Volume:
    def __init__(self) -> None:
        self.authority = VolumeAuthority.MICHI_SOFTWARE
        self.volume_adjustable = True
        self.volume_label = "Software volume"


def _observations(path: str, *, card: int = 1, product: str = "DX5"):
    binding = AudioDeviceBinding(
        kind=BindingKind.ALSA_PCM,
        locator="hw:CARD=DX5,DEV=0",
        generation=0,
        currently_available=True,
        card_index=card,
        pcm_device=0,
        stable_endpoint_signature=f"usb:{path}:pcm0",
    )
    usb = DeviceObservation(
        source="usb",
        observed_at_ns=1,
        vendor_id="2622",
        product_id="0105",
        serial=None,
        manufacturer="Topping",
        product=product,
        physical_path=path,
        bcd_device="0100",
        binding=None,
    )
    alsa = DeviceObservation(
        source="alsa",
        observed_at_ns=1,
        vendor_id=None,
        product_id=None,
        serial=None,
        manufacturer=None,
        product=None,
        physical_path=path,
        bcd_device=None,
        binding=binding,
    )
    return usb, alsa


def _direct_truth(recorder: SignalTruthRecorder, stable_id: str, generation: int):
    pcm = PcmTuple(96_000, "S32_LE", 2, 32)
    identity = SignalTruthIdentity(
        plan_id=f"plan:{generation}",
        execution_generation=generation,
        port_generation=generation,
        binding_generation=generation,
        stable_device_id=stable_id,
        stable_endpoint_signature="usb:pcm0",
    )
    recorder.begin_candidate(
        OutputPlanEvidence(identity, pcm, "alsasink", "hw:CARD=DX5,DEV=0", True)
    )
    recorder.observe(DecodedRuntimeEvidence(identity, pcm))
    recorder.observe(
        EngineRuntimeEvidence(
            identity=identity,
            effective_pcm=pcm,
            sink_factory="alsasink",
            sink_device="hw:CARD=DX5,DEV=0",
            graph_factories=("flacdec", "capsfilter", "alsasink"),
            graph_inspection_complete=True,
            software_gain=1.0,
            muted=False,
            sink_provides_clock=True,
            sink_clock_is_pipeline_clock=True,
            slave_method="none",
        )
    )
    recorder.observe(
        AlsaRuntimeEvidence(
            identity=identity,
            negotiated_pcm=pcm,
            access="RW_INTERLEAVED",
            subformat="STD",
            period_size=1024,
            buffer_size=4096,
            proc_path="/proc/asound/card1/pcm0p/sub0/hw_params",
            locator="hw:CARD=DX5,DEV=0",
        )
    )
    assert recorder.commit_candidate(identity)
    return identity


def _graph():
    devices = AudioDeviceRegistry()
    devices.ingest(_observations("/devices/usb1/1-2"))
    stable_id = devices.available_ids()[0]
    repository = _Repo()
    profiles = AudioOutputProfileService(repository)
    session = _Session()
    engines = _Engine()
    coordinator = AudioOutputSelectionCoordinator(
        profiles=profiles,
        devices=devices,
        output_session=session,
        engines=engines,
        clock_ms=lambda: 90,
    )
    playback = _Playback()
    volume = _Volume()
    truth = SignalTruthRecorder()
    bridge = AudioOutputBridge(
        volume,
        playback,
        truth,
        devices=devices,
        profiles=profiles,
        output_session=session,
        engines=engines,
        selection_coordinator=coordinator,
    )
    return SimpleNamespace(
        devices=devices,
        stable_id=stable_id,
        profiles=profiles,
        repository=repository,
        session=session,
        engines=engines,
        coordinator=coordinator,
        playback=playback,
        volume=volume,
        truth=truth,
        bridge=bridge,
    )


def _device(bridge, stable_id):
    return next(row for row in bridge.devices if row["stableDeviceId"] == stable_id)


def test_ui90_01_shared_projection_without_physical_dac_is_truthful() -> None:
    graph = _graph()
    shared = graph.bridge.devices[0]
    assert shared["displayName"] == "System Output"
    assert shared["transportMode"] == "shared"
    assert shared["isShared"] is True


def test_ui90_02_available_selected_dac_differs_from_active_dac() -> None:
    graph = _graph()
    graph.coordinator.select_device(graph.stable_id)
    row = _device(graph.bridge, graph.stable_id)
    assert row["selected"] is True and row["active"] is False
    assert row["statusLabel"] == "Selected · inactive"


def test_ui90_03_selected_active_direct_is_projected_correctly() -> None:
    graph = _graph()
    graph.coordinator.select_device(graph.stable_id)
    graph.session.activate(graph.stable_id, generation=1)
    row = _device(graph.bridge, graph.stable_id)
    assert row["statusLabel"] == "Selected · Active"
    assert row["transportLabel"] == "Direct"


def test_ui90_04_selected_disconnected_is_projected_correctly() -> None:
    graph = _graph()
    graph.coordinator.select_device(graph.stable_id)
    graph.devices.ingest(())
    row = _device(graph.bridge, graph.stable_id)
    assert row["selected"] is True and row["available"] is False
    assert row["statusLabel"] == "Selected · unavailable"
    assert row["alsaLocator"] == ""
    assert row["bindingAvailable"] is False


def test_ui90_05_reconnect_does_not_project_active_state() -> None:
    graph = _graph()
    graph.coordinator.select_device(graph.stable_id)
    graph.session.lose()
    graph.devices.ingest(())
    graph.devices.ingest(_observations("/devices/usb1/1-2", card=7))
    row = _device(graph.bridge, graph.stable_id)
    assert row["available"] is True and row["active"] is False


def test_ui90_06_fresh_g2_activation_projects_active() -> None:
    graph = _graph()
    graph.coordinator.select_device(graph.stable_id)
    graph.session.lose()
    graph.devices.ingest(())
    graph.devices.ingest(_observations("/devices/usb1/1-2", card=7))
    generation = graph.devices.generation_for(graph.stable_id)
    graph.session.activate(graph.stable_id, generation=generation)
    assert _device(graph.bridge, graph.stable_id)["active"] is True


def test_ui90_07_fixed_volume_projects_locked_unity() -> None:
    graph = _graph()
    graph.volume.authority = VolumeAuthority.FIXED
    graph.volume.volume_adjustable = False
    graph.volume.volume_label = "Fixed / Unity"
    graph.playback.publish()
    assert graph.bridge.volumeMode == "fixed"
    assert graph.bridge.volumeAdjustable is False
    assert graph.bridge.volumeLabel == "Fixed / Unity"


def test_ui90_08_shared_volume_projects_adjustable_software() -> None:
    graph = _graph()
    assert graph.bridge.volumeMode == "michi_software"
    assert graph.bridge.volumeAdjustable is True
    assert graph.bridge.volumeLabel == "Software volume"


def test_ui90_09_unknown_authority_projects_disabled_unavailable() -> None:
    graph = _graph()
    graph.volume.authority = VolumeAuthority.UNKNOWN
    graph.volume.volume_adjustable = False
    graph.volume.volume_label = "Volume unavailable"
    graph.playback.publish()
    assert graph.bridge.volumeAdjustable is False
    assert graph.bridge.volumeLabel == "Volume unavailable"


def test_ui90_10_signal_truth_verdict_updates_live() -> None:
    graph = _graph()
    graph.coordinator.select_device(graph.stable_id)
    graph.session.activate(graph.stable_id, generation=1)
    _direct_truth(graph.truth, graph.stable_id, 1)
    assert graph.bridge.signalTruthVerdict == "direct"
    assert graph.bridge.signalTruthLabel == "Direct path"
    assert graph.bridge.currentDeviceRate == 96_000


def test_ui90_11_signal_truth_retirement_removes_stale_g1_verdict() -> None:
    graph = _graph()
    identity = _direct_truth(graph.truth, graph.stable_id, 1)
    assert graph.truth.retire_active(identity)
    assert graph.bridge.signalTruthVerdict == "unknown"
    assert graph.bridge.currentDeviceRate == 0


def test_ui90_12_late_stale_g1_does_not_alter_bridge_projection() -> None:
    graph = _graph()
    g1 = _direct_truth(graph.truth, graph.stable_id, 1)
    assert graph.truth.retire_active(g1)
    graph.session.activate(graph.stable_id, generation=2)
    _direct_truth(graph.truth, graph.stable_id, 2)
    before = (graph.bridge.signalTruthVerdict, graph.bridge.currentDeviceRate)
    assert before == ("direct", 96_000)
    assert (
        graph.truth.observe(
            DecodedRuntimeEvidence(g1, PcmTuple(44_100, "S16_LE", 2, 16))
        )
        is False
    )
    assert (graph.bridge.signalTruthVerdict, graph.bridge.currentDeviceRate) == before


def test_ui90_13_card_index_churn_preserves_stable_card_identity() -> None:
    graph = _graph()
    before = _device(graph.bridge, graph.stable_id)
    graph.devices.ingest(_observations("/devices/usb1/1-2", card=7))
    after = _device(graph.bridge, graph.stable_id)
    assert before["stableDeviceId"] == after["stableDeviceId"]
    assert after["generation"] > before["generation"]


def test_ui90_14_identical_models_remain_distinct_by_stable_id() -> None:
    graph = _graph()
    graph.devices.ingest(
        (*_observations("/devices/usb1/1-2"), *_observations("/devices/usb2/2-1"))
    )
    rows = [row for row in graph.bridge.devices if not row["isShared"]]
    assert len(rows) == 2
    assert rows[0]["displayName"] == rows[1]["displayName"] == "Topping DX5"
    assert rows[0]["stableDeviceId"] != rows[1]["stableDeviceId"]


def test_ui90_15_alsa_locator_is_diagnostic_not_selected_identity() -> None:
    graph = _graph()
    graph.coordinator.select_device(graph.stable_id)
    row = _device(graph.bridge, graph.stable_id)
    assert graph.bridge.selectedDeviceId == graph.stable_id
    assert row["alsaLocator"] == "hw:CARD=DX5,DEV=0"
    assert row["displayName"] == "Topping DX5"


def test_ui90_16_busy_maps_to_device_busy() -> None:
    assert failure_copy("ALSA_DEVICE_BUSY")[0] == "Device busy"


def test_ui90_17_disconnected_maps_to_device_disconnected() -> None:
    assert failure_copy("OUTPUT_DEVICE_LOST")[0] == "Device disconnected"


def test_ui90_18_engine_unsupported_maps_to_direct_requires_gstreamer() -> None:
    graph = _graph()
    graph.engines.state.active_engine_id = AudioEngineId.QT_MULTIMEDIA
    failures = []
    graph.bridge.action_failed.connect(
        lambda code, title, detail: failures.append((code, title, detail))
    )
    selection_before = graph.repository.selection
    graph.bridge.select_device(graph.stable_id)
    assert graph.engines.state.active_engine_id is AudioEngineId.QT_MULTIMEDIA
    assert graph.repository.selection == selection_before
    assert graph.session.selected_device_id is None
    assert failures[0][0] == "ENGINE_UNSUPPORTED_FOR_DIRECT"
    assert (
        failure_copy("ENGINE_UNSUPPORTED_FOR_DIRECT")[0] == "Direct requires GStreamer"
    )


def test_ui90_19_exact_tuple_unknown_maps_to_format_not_verified() -> None:
    assert failure_copy("EXACT_TUPLE_UNKNOWN")[0] == "Format not verified"


def test_ui90_20_fixed_volume_failure_has_explicit_locked_copy() -> None:
    assert failure_copy("OUTPUT_VOLUME_LOCKED")[0] == "Output locked at fixed level"


def test_ui90_21_contradiction_and_dispose_are_symmetric() -> None:
    graph = _graph()
    assert failure_copy("SIGNAL_TRUTH_CONTRADICTED")[0] == "Output mismatch"
    graph.bridge.dispose()
    assert graph.playback.subscribers == []
    assert graph.profiles._subscribers == []
    assert graph.session.subscribers == []
    assert graph.engines.subscribers == []


def test_selection_notifications_never_publish_mixed_authorities() -> None:
    graph = _graph()
    snapshots = []
    graph.bridge.state_changed.connect(
        lambda: snapshots.append(
            (graph.bridge.selectedDeviceId, graph.session.selected_device_id)
        )
    )
    graph.coordinator.select_device(graph.stable_id)
    assert snapshots
    assert all(item == (graph.stable_id, graph.stable_id) for item in snapshots)


def test_physical_device_selection_never_chooses_shared_profile() -> None:
    graph = _graph()
    graph.profiles.save_profile(
        AudioOutputProfile(
            profile_id="aaa-shared",
            stable_device_id=graph.stable_id,
            path=OutputPathPreference.DESKTOP,
            rate_policy=RatePolicy.SYSTEM,
            volume_policy=VolumePolicy.SOFTWARE,
            allow_resample=True,
            allow_remix=True,
            allow_processing=False,
            fallback=FallbackKind.DESKTOP_DEFAULT,
        )
    )
    graph.coordinator.select_device(graph.stable_id)
    selected = graph.repository.selection
    assert selected.selected_profile_id != "aaa-shared"
    profile = next(
        item
        for item in graph.repository.profiles
        if item.profile_id == selected.selected_profile_id
    )
    assert profile.path is OutputPathPreference.HARDWARE_DIRECT


def test_canonical_bridge_fields_and_intents_are_present() -> None:
    graph = _graph()
    for field in (
        "pathMode",
        "availability",
        "availabilityReason",
        "currentRateHz",
        "significantBits",
        "isDirect",
        "isExclusiveObserved",
        "isBusy",
        "isReconnecting",
    ):
        assert hasattr(graph.bridge, field)
    for intent in (
        "refresh_devices",
        "select_device",
        "select_path_mode",
        "select_volume_mode",
        "set_resync_delay_ms",
        "open_diagnostics",
    ):
        assert callable(getattr(graph.bridge, intent))
