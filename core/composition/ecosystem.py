"""Ecosystem composition — connections, home audio, devices and radio."""

from __future__ import annotations

import logging

from core.service_container import ServiceContainer

logger = logging.getLogger(__name__)


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
    except Exception as exc:
        logger.warning("Connection service unavailable: %s", exc)
        container.register("connection_service", None)

    try:
        from core.home_audio_service import HomeAudioService
        from core.settings_manager import get_int, get_str
        from integrations.home_audio_service import HomeAssistantService
        from integrations.snapcast.json_rpc_client import SnapcastJsonRpcClient
        from integrations.snapcast.discovery import SnapClientDiscovery
        from integrations.snapcast.snapserver_manager import SnapServerManager

        discovery = SnapClientDiscovery()
        snapserver = SnapServerManager()
        snapserver.configure(
            get_int("home_audio/snapserver_tcp_port") or 1704,
            get_int("home_audio/snapserver_control_port") or 1705,
            get_int("home_audio/snapserver_http_port") or 1780,
        )
        snapcast_control = SnapcastJsonRpcClient(
            host=get_str("home_audio/snapcast_host") or "127.0.0.1",
            port=get_int("home_audio/snapcast_port")
            or get_int("home_audio/snapserver_control_port")
            or 1705,
        )
        ha_url = get_str("home_audio/ha_base_url")
        if not ha_url:
            ha_host = get_str("home_audio/ha_host")
            ha_port = get_int("home_audio/ha_port")
            if ha_host:
                ha_url = f"{ha_host.rstrip('/')}:{ha_port}" if ha_port else ha_host
        ha_token = get_str("home_audio/ha_token")
        ha_client = HomeAssistantService(ha_url, ha_token) if ha_url and ha_token else None
        home_audio = HomeAudioService(
            snapcast_discovery=discovery,
            snapserver_manager=snapserver,
            snapcast_control=snapcast_control,
            ha_client=ha_client,
            playback_service=container.get("playback_service"),
            event_bus=event_bus,
        )
        container.register("snapcast_control", snapcast_control)
        container.register("snapserver_manager", snapserver)
        container.register("home_audio_service", home_audio)
    except Exception as exc:
        logger.warning("Home Audio degraded during composition: %s", exc)
        container.register("home_audio_service", None)

    try:
        from core.device_sync_service import DeviceSyncService
        from core.sync.device_registry import DeviceRegistry

        container.register("device_sync_service", DeviceSyncService())
        container.register("device_registry", DeviceRegistry())
    except Exception as exc:
        logger.warning("Device sync unavailable: %s", exc)

    try:
        from core.mobile_sync_service import MobileSyncService

        container.register(
            "mobile_sync_service",
            MobileSyncService(db=container.get("database")),
        )
    except Exception as exc:
        logger.warning("Mobile sync unavailable: %s", exc)

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
    except Exception as exc:
        logger.warning("Lyrics service unavailable: %s", exc)
        container.register("lyrics_service", None)
