"""PlayerBarService — thin honest facade over PlaybackSnapshotService.

PlayerBarService never invents playback values. All readback derives from the
canonical :class:`core.playback_snapshot_service.PlaybackSnapshotService`;
when the player is unavailable the explicit contract is
``available=False`` / ``status=SERVICE_UNAVAILABLE`` (ADR-005, criterion 49).
"""
from __future__ import annotations

import logging

from core.playback_snapshot_service import PlaybackSnapshotService

logger = logging.getLogger("michi.player_bar")


class PlayerBarService:
    """Player bar playback state — honest readback only, no fabricated defaults."""

    def __init__(self, player_service=None, snapshot_service=None):
        if snapshot_service is not None:
            self._snapshot = snapshot_service
        else:
            self._snapshot = PlaybackSnapshotService(player_service=player_service)

    @property
    def available(self) -> bool:
        return self._snapshot.available

    def get_state(self) -> str:
        """Playback state; ``unavailable`` (never ``stopped``) without a player."""
        return self._snapshot.get_state()

    def get_position(self):
        """Position in seconds, or None when the player is missing."""
        return self._snapshot.get_position()

    def get_volume(self):
        """Volume, or None when the player is missing."""
        return self._snapshot.get_volume()

    def get_snapshot(self) -> dict:
        """Full canonical snapshot (see PlaybackSnapshotService.snapshot)."""
        return self._snapshot.snapshot()

    def health(self) -> dict:
        """Honest health: available + status + reasons."""
        snap = self._snapshot.snapshot()
        return {
            "available": snap["available"],
            "status": snap["status"],
            "reasons": [] if snap["available"] else ["player_missing"],
        }

    def start(self):
        pass

    def shutdown(self):
        pass
