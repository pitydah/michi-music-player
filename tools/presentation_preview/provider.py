"""PresentationPreviewProvider — read-only demo data adapters.

Active ONLY when --presentation-preview flag is present.
Never imported or instantiated in normal runtime.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


class PresentationPreviewProvider:
    """Provides demo data for presentation mode via read-only adapters."""

    def __init__(self, fixtures: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self._fixtures = deepcopy(fixtures) if fixtures else {}

    @property
    def albums(self) -> list[dict[str, Any]]:
        """Demo album snapshot (read-only)."""
        return deepcopy(self._fixtures.get("albums", []))

    @property
    def artists(self) -> list[dict[str, Any]]:
        """Demo artist snapshot (read-only)."""
        return deepcopy(self._fixtures.get("artists", []))

    @property
    def tracks(self) -> list[dict[str, Any]]:
        """Demo track snapshot (read-only)."""
        return deepcopy(self._fixtures.get("tracks", []))

    @property
    def playlists(self) -> list[dict[str, Any]]:
        """Demo playlist snapshot (read-only)."""
        return deepcopy(self._fixtures.get("playlists", []))

    def is_active(self) -> bool:
        """The provider only exists when the preview flag is active."""
        return True
