"""Ecosystem composition — connections, home audio, devices, radio, lyrics."""
from __future__ import annotations

from core.service_container import ServiceContainer, ServicePriority


def build(container: ServiceContainer) -> None:
    eb = container.get("event_bus")

    try:
        from core.connection_service import ConnectionService
        from integrations.connections.connection_manager import ConnectionManager
        from integrations.connections.discovery_manager import DiscoveryManager
        from integrations.connections.credentials_store import CredentialsStore
        from integrations.michi_link.client import MichiLinkClient
        disc_mgr = DiscoveryManager()
        conn_mgr = ConnectionManager()
        creds = CredentialsStore()
        michi = MichiLinkClient()
        cs = ConnectionService(connection_manager=conn_mgr,
                              discovery_manager=disc_mgr,
                              credentials_store=creds,
                              michi_link_client=michi,
                              event_bus=eb)
        container.register("connection_service", cs)
    except Exception:
        container.register("connection_service", None)

    try:
        from core.home_audio_service import HomeAudioService
        try:
            from integrations.snapcast.group_manager import GroupManager
            from integrations.snapcast.discovery import SnapClientDiscovery
            from integrations.snapcast.snapserver_manager import SnapServerManager
            disc = SnapClientDiscovery()
            snapserver = SnapServerManager()
            group_mgr = GroupManager()
        except Exception:
            disc = snapserver = group_mgr = None
        ha = HomeAudioService(snapcast_group_manager=group_mgr,
                             snapcast_discovery=disc,
                             snapserver_manager=snapserver,
                             event_bus=eb)
        container.register("home_audio_service", ha)
    except Exception:
        container.register("home_audio_service", None)

    try:
        from core.device_sync_service import DeviceSyncService
        from core.sync.device_registry import DeviceRegistry
        container.register("device_sync_service", DeviceSyncService())
        container.register("device_registry", DeviceRegistry())
    except Exception:
        pass

    try:
        from core.mobile_sync_service import MobileSyncService
        container.register("mobile_sync_service", MobileSyncService(db=container.get("database")))
    except Exception:
        pass

    from core.radio.radio_service import RadioService
    container.register("radio_service", RadioService(event_bus=eb))

    try:
        from lyrics.lrclib_client import LrcLibClient
        from core.lyrics_service import LyricsService
        wm = container.get("worker_manager")
        lrc = LrcLibClient()
        ls = LyricsService(lrclib_client=lrc, worker_manager=wm)
        container.register("lyrics_service", ls)
    except Exception:
        container.register("lyrics_service", None)
