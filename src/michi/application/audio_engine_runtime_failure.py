"""M11.3G — engine runtime failure telemetry (application layer).

Typed ENGINE-LIFECYCLE failure seam. This is NOT AudioPort media telemetry:
media rejection, corrupt tracks, EOS and device/output loss are explicitly
NOT engine runtime failures (see M11.3G contract). Only a proven fatal
engine runtime loss (e.g. managed process exit, fatal transport loss) may
produce AudioEngineRuntimeFailureEvent.

Framework-free: no PySide6, no gi, no MPD protocol, no SQLite.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass

from michi.domain.audio_engine import AudioEngineId


@dataclass(frozen=True)
class AudioEngineRuntimeFailureEvent:
    """Fatal engine runtime loss — engine lifecycle telemetry.

    engine_id: the engine whose runtime died.
    runtime_generation: the provider's runtime generation at failure time;
        a delayed event from generation N must never kill generation N+1.
    reason: deterministic human-readable reason (never raw repr).
    """

    engine_id: AudioEngineId
    runtime_generation: int
    reason: str


RuntimeFailureCallback = Callable[[AudioEngineRuntimeFailureEvent], None]


class AudioEngineRuntimeFailureSourcePort(ABC):
    """Provider-level runtime-failure observation.

    Lives BESIDE provider lifecycle — AudioPort stays transport-only."""

    @abstractmethod
    def subscribe_runtime_failed(self, callback: RuntimeFailureCallback) -> None: ...

    @abstractmethod
    def unsubscribe_runtime_failed(self, callback: RuntimeFailureCallback) -> None: ...
