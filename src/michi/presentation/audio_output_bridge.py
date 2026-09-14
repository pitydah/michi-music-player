"""Read-only QML projection of current output volume policy."""

from PySide6.QtCore import Property, QObject, Signal

from michi.application.playback_service import PlaybackService
from michi.application.volume_policy_service import VolumePolicyService


class AudioOutputBridge(QObject):
    """Expose volume presentation facts without owning output state."""

    state_changed = Signal()

    def __init__(
        self,
        volume_policy: VolumePolicyService,
        playback: PlaybackService,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._volume_policy = volume_policy
        self._playback = playback
        playback.subscribe_changed(self._on_playback_changed)

    def _on_playback_changed(self) -> None:
        self.state_changed.emit()

    def dispose(self) -> None:
        self._playback.unsubscribe_changed(self._on_playback_changed)

    def _get_volume_mode(self) -> str:
        return self._volume_policy.authority.value

    def _get_volume_adjustable(self) -> bool:
        return self._volume_policy.volume_adjustable

    def _get_volume_label(self) -> str:
        return self._volume_policy.volume_label

    volumeMode = Property(str, _get_volume_mode, notify=state_changed)
    volumeAdjustable = Property(bool, _get_volume_adjustable, notify=state_changed)
    volumeLabel = Property(str, _get_volume_label, notify=state_changed)
