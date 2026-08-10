"""Application ports — persistence interfaces."""

from abc import ABC, abstractmethod

from michi.domain.settings import SettingsState


class SettingsRepository(ABC):
    """Abstract persistence for application settings."""

    @abstractmethod
    def load(self) -> SettingsState: ...

    @abstractmethod
    def save(self, state: SettingsState) -> None: ...
