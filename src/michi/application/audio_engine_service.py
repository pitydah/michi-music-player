"""AudioEngineService — sole owner of AudioEngineState (M11.3A foundation).

State ownership + observation only. Framework-free: no PySide6, no gi, no
subprocess, no socket, no SQLite. Runtime switching belongs to M11.3F."""

from collections.abc import Callable

from michi.application.audio_engine_registry import AudioEngineRegistry
from michi.domain.audio_engine import (
    AudioEngineId,
    AudioEngineLifecycle,
    AudioEngineState,
)


class AudioEngineService:
    """Sole authority over AudioEngineState (engine selection/lifecycle).

    SELECTED != ACTIVE: the service establishes the initial state (selected
    QT_MULTIMEDIA, active None until an engine is initialized/bound)."""

    def __init__(self, registry: AudioEngineRegistry | None = None) -> None:
        self._registry = registry
        self._state = AudioEngineState(
            selected_engine_id=AudioEngineId.QT_MULTIMEDIA,
            active_engine_id=None,
            lifecycle=AudioEngineLifecycle.UNINITIALIZED,
        )
        self._subscribers: list[Callable[[], None]] = []

    @property
    def state(self) -> AudioEngineState:
        return self._state

    @property
    def registry(self) -> AudioEngineRegistry | None:
        return self._registry

    def subscribe_changed(self, callback: Callable[[], None]) -> None:
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe_changed(self, callback: Callable[[], None]) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)
