"""GStreamerBackend — wraps GStreamerEngine behind the common AudioBackend API.

Re-emits engine Qt signals so PlayerService can delegate all operations
to the HybridAudioManager without bifurcating between engine/backend.
"""

from PySide6.QtCore import QObject, Signal

from audio.backends.types import (
    BackendCapabilities,
    PlaybackSnapshot,
    AudioDiagnostics,
)


class GStreamerBackend(QObject):
    """Adapter that translates AudioBackend API calls to GStreamerEngine.

    Re-emits position_changed, state_changed, duration_changed from the engine
    so PlayerService can listen to the active backend uniformly.
    """

    position_changed = Signal(float)
    state_changed = Signal(str)
    duration_changed = Signal(float)

    backend_id = "gstreamer"
    display_name = "GStreamer"

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine

        engine.position_changed.connect(self.position_changed)
        engine.state_changed.connect(self._forward_state)
        engine.duration_changed.connect(self.duration_changed)

    def _forward_state(self, state):
        from audio.player import PlaybackState
        s_map = {PlaybackState.PLAYING: "playing",
                 PlaybackState.PAUSED: "paused",
                 PlaybackState.STOPPED: "stopped"}
        self.state_changed.emit(s_map.get(state, "stopped"))

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            backend_id=self.backend_id,
            display_name=self.display_name,
            supports_eq=True,
            supports_replaygain=True,
            supports_spectrum=True,
            supports_radio=True,
            supports_streams=True,
            supports_digital_volume=True,
        )

    @property
    def engine(self):
        return self._engine

    def play(self, path_or_uri: str):
        self._engine.play(path_or_uri)

    def pause(self):
        self._engine.pause()

    def resume(self):
        self._engine.resume()

    def toggle(self):
        self._engine.toggle()

    def stop(self):
        self._engine.stop()

    def seek(self, seconds: float):
        self._engine.seek(seconds)

    def set_volume(self, volume: int):
        self._engine.set_volume(volume)

    def set_queue(self, paths: list[str], start_index: int = 0):
        self._engine.set_queue(paths, start_index)

    def enqueue(self, paths: list[str], play_now: bool = True):
        self._engine.enqueue(paths, play_now)

    def enqueue_next(self, paths: list[str]):
        self._engine.enqueue_next(paths)

    def clear_queue(self):
        self._engine.clear_queue()

    def play_next(self) -> bool:
        return self._engine.play_next()

    def play_prev(self) -> bool:
        return self._engine.play_prev()

    def get_queue(self) -> list[dict]:
        return self._engine.get_queue()

    def get_queue_index(self) -> int:
        return self._engine.get_queue_index()

    def get_snapshot(self) -> PlaybackSnapshot:
        from audio.player import PlaybackState
        state = self._engine.state
        state_map = {
            PlaybackState.PLAYING: "playing",
            PlaybackState.PAUSED: "paused",
            PlaybackState.STOPPED: "stopped",
        }
        return PlaybackSnapshot(
            backend_id=self.backend_id,
            state=state_map.get(state, "stopped"),
            current_path=self._engine.current or "",
            current_uri=self._engine.current or "",
            volume=int(getattr(self._engine, '_volume', 0.7) * 100),
            queue_index=self._engine.get_queue_index(),
            queue_length=len(self._engine.get_queue()),
        )

    def get_diagnostics(self) -> AudioDiagnostics:
        diag = self._engine.get_audio_diagnostics()
        return AudioDiagnostics(
            backend_id=self.backend_id,
            profile=getattr(diag, 'profile', 'standard'),
            device_name=getattr(diag, 'device_name', ''),
            device_string=getattr(diag, 'device_string', ''),
            input_codec=getattr(diag, 'input_codec', ''),
            input_sample_rate=getattr(diag, 'input_sample_rate', 0),
            input_bit_depth=getattr(diag, 'input_bit_depth', 0),
            input_channels=getattr(diag, 'input_channels', 0),
            output_sample_rate=getattr(diag, 'output_sample_rate', 0),
            output_format=getattr(diag, 'output_format', ''),
            output_channels=getattr(diag, 'output_channels', 0),
            bitperfect_status=getattr(diag, 'bitperfect_status', 'unknown'),
            eq_active=getattr(diag, 'eq_active', False),
            replaygain_active=getattr(diag, 'replaygain_active', False),
            spectrum_active=getattr(diag, 'spectrum_active', False),
            resampling_active=getattr(diag, 'resampling_active', False),
            dsp_active=(
                getattr(diag, 'eq_active', False)
                or getattr(diag, 'replaygain_active', False)
                or getattr(diag, 'spectrum_active', False)
            ),
            digital_volume_active=True,
            warnings=getattr(diag, 'warnings', []),
        )

    def shutdown(self):
        self._engine.stop()
