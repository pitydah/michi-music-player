from __future__ import annotations

from enum import Enum


class RiskLevel(str, Enum):
    SAFE = "safe"
    LOW = "low"
    MODERATE = "moderate"
    CRITICAL = "critical"


_ACTION_RISK_MAP: dict[str, RiskLevel] = {
    "delete_from_disk": RiskLevel.CRITICAL,
    "format_drive": RiskLevel.CRITICAL,
    "unpair_all": RiskLevel.CRITICAL,
    "factory_reset": RiskLevel.CRITICAL,
    "delete_from_library": RiskLevel.MODERATE,
    "batch_metadata_edit": RiskLevel.MODERATE,
    "convert_files": RiskLevel.MODERATE,
    "unpair_device": RiskLevel.MODERATE,
    "pair_device": RiskLevel.MODERATE,
    "transfer_files": RiskLevel.MODERATE,
    "sync_playlists": RiskLevel.MODERATE,
    "skip_track": RiskLevel.LOW,
    "change_volume": RiskLevel.LOW,
    "add_to_queue": RiskLevel.LOW,
    "remove_from_queue": RiskLevel.LOW,
    "create_playlist": RiskLevel.LOW,
    "rename_playlist": RiskLevel.LOW,
    "delete_playlist": RiskLevel.MODERATE,
    "toggle_favorite": RiskLevel.LOW,
    "search_library": RiskLevel.SAFE,
    "get_playback_status": RiskLevel.SAFE,
    "list_albums": RiskLevel.SAFE,
    "list_artists": RiskLevel.SAFE,
    "get_diagnostics": RiskLevel.SAFE,
    "get_suggestions": RiskLevel.SAFE,
    "get_track_info": RiskLevel.SAFE,
    "get_album_info": RiskLevel.SAFE,
    "get_artist_info": RiskLevel.SAFE,
    "navigate": RiskLevel.SAFE,
    "unknown": RiskLevel.MODERATE,
}

_REQUIRE_CONFIRMATION_LEVELS: set[RiskLevel] = {RiskLevel.MODERATE, RiskLevel.CRITICAL}


class RiskPolicy:
    def assess(self, action_type: str, resources: list[str] | None = None, source: str = "ai") -> RiskLevel:
        return _ACTION_RISK_MAP.get(action_type, RiskLevel.MODERATE)

    def require_confirmation(self, risk: RiskLevel) -> bool:
        return risk in _REQUIRE_CONFIRMATION_LEVELS

    def get_risk(self, action_type: str) -> RiskLevel:
        return _ACTION_RISK_MAP.get(action_type, RiskLevel.MODERATE)
