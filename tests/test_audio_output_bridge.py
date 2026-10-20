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
    def __init__(self, mode: str, active_execution: str | None = None) -> None:
        self.mode = mode
        self.active_execution_id = active_execution
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


def _event(execution_id, state, *, plan_id="dsp:plan", policy=("dsp",)):
    from michi.domain.signal_truth import OutputFamilyEvent

    return OutputFamilyEvent(
        family="managed",
        state=state,
        device_id="dev:dac",
        execution_id=execution_id,
        processing_plan_id=plan_id,
        transform_policy=policy,
        runtime_identity={
            "negotiated": {"format": "S16LE", "rate_hz": 48000, "channels": 2}
        },
        bit_perfect=False,
    )


def _bridge(mode="managed", active="exec:1", events=None):
    from michi.domain.signal_truth import (
        OutputFamilyState,
        SignalTruthRecorder,
    )

    recorder = SignalTruthRecorder()
    for event in events or [_event("exec:1", OutputFamilyState.RUNNING)]:
        recorder.record_output_family_event(event)
    return AudioOutputBridge(
        VolumeTruth(),
        ObservablePlayback(),
        recorder,
        output_session=_Session(mode, active),
    )


def test_managed_signal_path_says_processed_never_direct() -> None:
    bridge = _bridge()
    assert bridge.signalPathKind == "processed"
    assert bridge.processed is True
    assert bridge.processedActive is True
    # Processing never proves bit-perfect.
    assert bridge.processingBitPerfect is False
    stages = bridge._projection["signalPath"]
    kinds = [stage.get("kind") for stage in stages]
    assert "processed" in kinds
    assert "managed_device" in kinds
    assert all(kind != "direct" for kind in kinds if kind)
    processing = next(stage for stage in stages if stage.get("kind") == "processed")
    assert processing["summary"] == "dsp"
    assert processing["rateHz"] == 48000
    assert processing["format"] == "S16LE"
    assert processing["detail"] == "dsp:plan"


def test_ready_managed_execution_is_prepared_not_confirmed_playback() -> None:
    from michi.domain.signal_truth import OutputFamilyState

    bridge = _bridge(events=[_event("exec:1", OutputFamilyState.READY)])
    assert bridge.signalPathKind == "processed_ready"
    assert bridge.processed is True
    assert bridge.processedActive is False
    assert bridge.processingBitPerfect is None


def test_terminal_event_retires_the_execution_even_with_older_running() -> None:
    from michi.domain.signal_truth import OutputFamilyState

    bridge = _bridge(
        events=[
            _event("exec:1", OutputFamilyState.RUNNING),
            _event("exec:1", OutputFamilyState.RELEASED),
        ]
    )
    # The session still reports the (now stale) identity: the terminal event
    # must win. Never PROCESSED.
    assert bridge.signalPathKind != "processed"
    assert bridge.processed is False
    assert bridge.processedActive is False
    assert bridge.processingBitPerfect is None


def test_new_execution_supersedes_and_late_events_cannot_resurrect_a() -> None:
    from michi.domain.signal_truth import OutputFamilyState

    bridge = _bridge(
        active="exec:B",
        events=[
            _event("exec:A", OutputFamilyState.RUNNING, plan_id="dsp:A"),
            _event("exec:B", OutputFamilyState.RUNNING, plan_id="dsp:B"),
            # A late RUNNING for A arrives AFTER B started.
            _event("exec:A", OutputFamilyState.RUNNING, plan_id="dsp:A"),
        ],
    )
    processing = next(
        stage
        for stage in bridge._projection["signalPath"]
        if stage.get("kind") == "processed"
    )
    assert processing["detail"] == "dsp:B"
    assert bridge.signalPathKind == "processed"


def test_managed_mode_without_an_active_execution_is_not_processed() -> None:
    from michi.domain.signal_truth import OutputFamilyState

    bridge = _bridge(
        active=None,
        events=[_event("exec:1", OutputFamilyState.RUNNING)],
    )
    assert bridge.signalPathKind != "processed"
    assert bridge.processed is False
    assert bridge.processingBitPerfect is None


def test_historical_managed_event_during_direct_playback_is_direct() -> None:
    from michi.domain.signal_truth import OutputFamilyState

    bridge = _bridge(
        mode="direct",
        active=None,
        events=[_event("exec:1", OutputFamilyState.RUNNING)],
    )
    assert bridge.signalPathKind == "direct"
    assert bridge.processed is False
    assert bridge.processingBitPerfect is None


def test_direct_route_is_not_classified_processed() -> None:
    bridge = _bridge(
        mode="direct",
        active=None,
        events=[],
    )
    assert bridge.signalPathKind == "direct"
    assert bridge.processed is False
    assert bridge.processingBitPerfect is None
    assert all(
        stage.get("kind") != "processed" for stage in bridge._projection["signalPath"]
    )
