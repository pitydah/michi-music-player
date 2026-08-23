"""Settings use case — owns persisted preference lifecycle.

Depends on SettingsRepository port. No SQLite/infrastructure dependency.
Does NOT own runtime Playback/Queue/Library state.
"""

from michi.application.persistence import SettingsRepository
from michi.domain.audio_engine import AudioEngineId
from michi.domain.settings import SettingsState, WindowGeometry


class SettingsService:
    """Authority over persisted SettingsState. Coordinates load/save lifecycle."""

    def __init__(self, repository: SettingsRepository) -> None:
        self._repo = repository
        self._state: SettingsState | None = None

    @property
    def state(self) -> SettingsState:
        if self._state is None:
            self._state = self._repo.load()
        return self._state

    def load(self) -> SettingsState:
        self._state = self._repo.load()
        return self._state

    def save(self) -> None:
        self._repo.save(self.state)

    def set_playback_preferences(self, volume: int, muted: bool) -> None:
        s = self.state
        s.volume = max(0, min(100, volume))
        s.muted = muted

    def set_last_directory(self, path: str) -> None:
        self.state.last_directory = path

    def set_recent_files(self, files: list[str]) -> None:
        self.state.recent_files = list(files)

    def set_theme(self, theme: str) -> None:
        self.state.theme = theme
        self.save()

    def set_window_geometry(self, geometry: WindowGeometry) -> None:
        self.state.window_geometry = geometry
        self.save()

    def set_audio_engine(self, engine_id: AudioEngineId) -> None:
        """Persist the SELECTED engine preference (M11.3F).

        Durable save BEFORE any destructive engine-switch boundary: if the
        persistence write fails, the in-memory preference is restored to its
        previous value and the ORIGINAL persistence error re-raised — no
        half-mutated preference survives a failed save.
        """
        previous = self.state.audio_engine_id
        if previous == engine_id:
            return
        self.state.audio_engine_id = engine_id
        try:
            self.save()
        except Exception:
            self.state.audio_engine_id = previous
            raise
