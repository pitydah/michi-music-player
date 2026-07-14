"""ServiceBundle — single source of references to all backend services for QML.

Contains existing service references only. No service creation.
No database opening. No backend construction.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from audio.player_service import PlayerService
    from library.search_engine import SearchEngine
    from streaming.radio_manager import RadioManager
    from sync.sync_manager import SyncManager
    from core.worker_manager import WorkerManager
    from metadata.services import MetadataService
    from integrations.michi_link.services.service_manager import ServiceManager as MichiLinkManager
    from streaming.disc_service import DiscService


@dataclass
class ServiceBundle:
    player_service: PlayerService | None = None
    db: Any | None = None
    db_connection: Any | None = None
    search_engine: SearchEngine | None = None
    radio_manager: RadioManager | None = None
    sync_manager: SyncManager | None = None
    michi_link_controller: MichiLinkManager | None = None
    home_audio_controller: Any | None = None
    snapcast_controller: Any | None = None
    disc_service: DiscService | None = None
    worker_manager: WorkerManager | None = None
    metadata_service: MetadataService | None = None
    smart_tagging_service: Any | None = None
    settings_coordinator: Any | None = None
    queue_service: Any | None = None
    audio_lab_service: Any | None = None
    device_sync_service: Any | None = None
    notification_service: Any | None = None
    action_registry: Any | None = None
    history_query_service: Any | None = None
    global_search_service: Any | None = None
    diagnostics_service: Any | None = None
    job_service: Any | None = None

    def has(self, name: str) -> bool:
        return getattr(self, name, None) is not None

    def require(self, name: str) -> Any:
        val = getattr(self, name, None)
        if val is None:
            raise ValueError(f"Service '{name}' is not available")
        return val

    @property
    def available_services(self) -> list[str]:
        return [k for k, v in self.__dict__.items() if v is not None]

    def to_dict(self) -> dict:
        return {k: v is not None for k, v in self.__dict__.items()}
