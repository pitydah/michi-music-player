"""Read-only QML projection of current output volume policy."""

from PySide6.QtCore import Property, QObject, Signal

from michi.application.playback_service import PlaybackService
from michi.application.volume_policy_service import VolumePolicyService
from michi.domain.signal_truth import SignalTruthRecorder


class AudioOutputBridge(QObject):
    """Expose volume presentation facts without owning output state."""

    state_changed = Signal()

    def __init__(
        self,
        volume_policy: VolumePolicyService,
        playback: PlaybackService,
        signal_truth: SignalTruthRecorder | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._volume_policy = volume_policy
        self._playback = playback
        self._signal_truth = signal_truth
        playback.subscribe_changed(self._on_playback_changed)
        if signal_truth is not None:
            signal_truth.subscribe(self._on_signal_truth_changed)

    def _on_playback_changed(self) -> None:
        self.state_changed.emit()

    def _on_signal_truth_changed(self) -> None:
        self.state_changed.emit()

    def dispose(self) -> None:
        self._playback.unsubscribe_changed(self._on_playback_changed)
        if self._signal_truth is not None:
            self._signal_truth.unsubscribe(self._on_signal_truth_changed)

    def _get_volume_mode(self) -> str:
        return self._volume_policy.authority.value

    def _get_volume_adjustable(self) -> bool:
        return self._volume_policy.volume_adjustable

    def _get_volume_label(self) -> str:
        return self._volume_policy.volume_label

    def _get_signal_truth_verdict(self) -> str:
        snapshot = self._signal_truth.active_snapshot if self._signal_truth else None
        return snapshot.verdict.value if snapshot is not None else "unknown"

    def _get_signal_truth_summary(self) -> str:
        snapshot = self._signal_truth.active_snapshot if self._signal_truth else None
        if snapshot is None:
            return "ST_MISSING_RUNTIME"
        if snapshot.reasons:
            return snapshot.reasons[0].value
        return snapshot.verdict.value

    volumeMode = Property(str, _get_volume_mode, notify=state_changed)
    volumeAdjustable = Property(bool, _get_volume_adjustable, notify=state_changed)
    volumeLabel = Property(str, _get_volume_label, notify=state_changed)
    signalTruthVerdict = Property(str, _get_signal_truth_verdict, notify=state_changed)
    signalTruthSummary = Property(str, _get_signal_truth_summary, notify=state_changed)
