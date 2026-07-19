"""Ecosystem composition — connections, home audio, devices and radio."""

from __future__ import annotations

from core.service_container import ServiceContainer


def build(container: ServiceContainer) -> None:
    event_bus = container.get("event_bus")

    try:
        from core.connection_service import ConnectionService
        from integrations.connections.connection_manager import ConnectionManager
        from integrations.connections.credentials_store import CredentialsStore
        from integrations.connections.discovery_manager import DiscoveryManager
        from integrations.michi_link.client import MichiLinkClient

        connection_service = ConnectionService(
            connection_manager=ConnectionManager(),
            discovery_manager=DiscoveryManager(),
            credentials_store=CredentialsStore(),
            michi_link_client=MichiLinkClient(),
            event_bus=event_bus,
        )
        container.register("connection_service", connection_service)
    except Exception:
        container.register("connection_service", None)

    try:
        from core.home_audio_service import HomeAudioService
        from integrations.home_audio_service import SnapcastService
        from integrations.snapcast.discovery import SnapClientDiscovery
        from integrations.snapcast.group_manager import GroupManager
        from integrations.snapcast.snapserver_manager import SnapServerManager

        discovery = SnapClientDiscovery()
        snapserver = SnapServerManager()
        group_manager = GroupManager()
        snapcast_control = SnapcastService(
            host="127.0.0.1",
            port=snapserver.control_port,
        )
        home_audio = HomeAudioService(
            snapcast_group_manager=group_manager,
            snapcast_discovery=discovery,
            snapserver_manager=snapserver,
            snapcast_control=snapcast_control,
            playback_service=container.get("playback_service"),
            event_bus=event_bus,
        )
        container.register("home_audio_service", home_audio)
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

        container.register(
            "mobile_sync_service",
            MobileSyncService(db=container.get("database")),
        )
    except Exception:
        pass

    from core.radio.radio_service import RadioService

    container.register("radio_service", RadioService(event_bus=event_bus))

    try:
        from core.lyrics_service import LyricsService
        from lyrics.lrclib_client import LrcLibClient

        lyrics_service = LyricsService(
            lrclib_client=LrcLibClient(),
            worker_manager=container.get("worker_manager"),
        )
        container.register("lyrics_service", lyrics_service)
    except Exception:
        container.register("lyrics_service", None)
