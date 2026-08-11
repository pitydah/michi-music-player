"""Settings use case — owns persisted preference lifecycle.

Depends on SettingsRepository port. No SQLite/infrastructure dependency.
Does NOT own runtime Playback/Queue/Library state.
"""

from michi.application.persistence import SettingsRepository
from michi.domain.settings import SettingsState


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
        if self._state is not None:
            self._repo.save(self._state)

    def set_last_directory(self, path: str) -> None:
        self.state.last_directory = path

    def set_recent_files(self, files: list[str]) -> None:
        self.state.recent_files = list(files)
