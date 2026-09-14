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
