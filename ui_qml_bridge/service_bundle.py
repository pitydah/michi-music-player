from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ServiceBundle:
    player_service: Any = None
    db: Any = None
    db_connection: Any = None
    search_engine: Any = None
    radio_manager: Any = None
    sync_manager: Any = None
    michi_link_controller: Any = None
    home_audio_controller: Any = None
    snapcast_controller: Any = None
    disc_service: Any = None
    worker_manager: Any = None
    metadata_service: Any = None
    playlist_controller: Any = None
    smart_tagging_service: Any = None
    assistant_core_service: Any = None
    job_service: Any = None
    confirmation_service: Any = None
    event_bus: Any = None
    lyrics_service: Any = None
    radio_service: Any = None
    registry: Any = None

    def has(self, name: str) -> bool:
        return getattr(self, name, None) is not None

    def require(self, name: str) -> Any:
        val = getattr(self, name, None)
        if val is None:
            raise RuntimeError(f"Required service '{name}' not available in ServiceBundle")
        return val

    @property
    def available_services(self) -> list[str]:
        return [k for k in self.__dataclass_fields__ if getattr(self, k, None) is not None]

    def to_dict(self) -> dict[str, Any]:
        return {
            k: getattr(self, k)
            for k in self.__dataclass_fields__
            if getattr(self, k, None) is not None
        }
