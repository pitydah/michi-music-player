from michi.application.audio_output_ports import VolumeAuthority
from michi.presentation.audio_output_bridge import AudioOutputBridge


class VolumeTruth:
    authority = VolumeAuthority.FIXED
    volume_adjustable = False
    volume_label = "Fixed / Unity"


class ObservablePlayback:
    def __init__(self) -> None:
        self.subscribers = []

    def subscribe_changed(self, callback) -> None:
        self.subscribers.append(callback)

    def unsubscribe_changed(self, callback) -> None:
        self.subscribers.remove(callback)


def test_v60_19_audio_output_bridge_projects_read_only_volume_policy() -> None:
    playback = ObservablePlayback()
    bridge = AudioOutputBridge(VolumeTruth(), playback)

    assert bridge.volumeMode == "fixed"
    assert bridge.volumeAdjustable is False
    assert bridge.volumeLabel == "Fixed / Unity"


def test_v60_20_audio_output_bridge_tracks_playback_output_transitions() -> None:
    playback = ObservablePlayback()
    bridge = AudioOutputBridge(VolumeTruth(), playback)
    emissions = []
    bridge.state_changed.connect(lambda: emissions.append(True))

    playback.subscribers[0]()

    assert emissions == [True]
    bridge.dispose()
    assert playback.subscribers == []


class _Session:
    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.subscribers: list = []

    def subscribe_changed(self, callback) -> None:
        self.subscribers.append(callback)

    def unsubscribe_changed(self, callback) -> None:
        self.subscribers.remove(callback)

    def selection_state(self):
        from types import SimpleNamespace

        return SimpleNamespace(
            selected_device_id=None,
            selected_profile_id=None,
            active_device_id=None,
            active_plan_id=None,
            session_state=SimpleNamespace(value="idle"),
            error_code=None,
        )


def _managed_bridge(mode: str = "managed"):
    from michi.domain.signal_truth import (
        OutputFamilyEvent,
        OutputFamilyState,
        SignalTruthRecorder,
    )

    recorder = SignalTruthRecorder()
    recorder.record_output_family_event(
        OutputFamilyEvent(
            family="managed",
            state=OutputFamilyState.RUNNING,
            device_id="dev:dac",
            execution_id="exec:1",
            processing_plan_id="dsp:plan",
            transform_policy=("dsp", "rate_change"),
            runtime_identity={
                "negotiated": {"format": "S16LE", "rate_hz": 48000, "channels": 2}
            },
            bit_perfect=False,
        )
    )
    return AudioOutputBridge(
        VolumeTruth(),
        ObservablePlayback(),
        recorder,
        output_session=_Session(mode),
    )


def test_managed_signal_path_says_processed_never_direct() -> None:
    bridge = _managed_bridge("managed")
    assert bridge.signalPathKind == "processed"
    assert bridge.processed is True
    # Processing never proves bit-perfect.
    assert bridge.processingBitPerfect is False
    stages = bridge._projection["signalPath"]
    kinds = [stage.get("kind") for stage in stages]
    assert "processed" in kinds
    assert "managed_device" in kinds
    assert all(kind != "direct" for kind in kinds if kind)
    processing = next(stage for stage in stages if stage.get("kind") == "processed")
    assert processing["summary"] == "dsp + rate_change"
    assert processing["rateHz"] == 48000
    assert processing["format"] == "S16LE"
    assert processing["detail"] == "dsp:plan"


def test_direct_route_is_not_classified_processed() -> None:
    bridge = _managed_bridge("direct")
    assert bridge.signalPathKind == "direct"
    assert bridge.processed is False
    assert bridge.processingBitPerfect is None
    assert all(
        stage.get("kind") != "processed" for stage in bridge._projection["signalPath"]
    )
