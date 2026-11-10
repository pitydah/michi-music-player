"""Playback control endpoint port (E9, master plan §156).

Substrate for the future Michi Control: selection, snapshots and commands
against a remote target. Stale responses (selection epoch changed mid-flight)
fail closed; duplicate in-flight commands are never double-issued.
"""

from __future__ import annotations

from typing import Protocol

from michi_ecosystem.domain.playback import CommandOutcome, PlaybackSnapshot


class PlaybackControlError(RuntimeError):
    def __init__(self, code: str, message: str, status: int = 0) -> None:
        self.code = code
        self.message = message
        self.status = status
        super().__init__(f"{code}: {message}")


class StaleResponseError(PlaybackControlError):
    def __init__(self, message: str = "selection changed while in flight") -> None:
        super().__init__("STALE_RESPONSE", message)


class PlaybackControlEndpoint(Protocol):
    def select_target(self, target_id: str) -> None: ...

    def clear_target(self) -> None: ...

    def selection_epoch(self) -> int: ...

    def capabilities(self) -> frozenset[str]: ...

    def snapshot(self) -> PlaybackSnapshot: ...

    def send(
        self,
        command: str,
        *,
        position_ms: int | None = None,
        volume: int | None = None,
        value: object | None = None,
    ) -> CommandOutcome: ...
