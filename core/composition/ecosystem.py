"""Ecosystem composition — connections, home audio, devices and radio."""

from __future__ import annotations

import logging

from core.service_container import ServiceContainer

logger = logging.getLogger(__name__)


def build(container: ServiceContainer) -> None:
    """Register ecosystem integrations in the application service container.

    Each integration is composed independently so an unavailable optional
    dependency does not prevent the remaining ecosystem services from loading.

    Args:
        container: Application container that provides shared dependencies and
            receives the composed services.
    """
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
        search_registry = container.get("search_provider_registry")
        if search_registry is not None:
            from core.search.models import SearchDomain
            from core.search.providers import ConnectionSearchProvider

            search_registry.register(
                SearchDomain.CONNECTION,
                ConnectionSearchProvider(connection_service),
            )
    except Exception as exc:
        logger.error("Failed to create connection_service: %s", exc)
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
        from integrations.snapcast.group_manager import GroupManager
        group_manager = GroupManager()
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
        ha_ws_port = get_int("home_audio/ha_ws_port") or 8123
        ha_client = HomeAssistantService(
            ha_url,
            ha_token,
            websocket_port=ha_ws_port,
        )
        if ha_url and ha_token:
            ha_client.subscribe_events()
        home_audio = HomeAudioService(
            snapcast_group_manager=group_manager,
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
        logger.error("Failed to create home_audio_service: %s", exc)
        container.register("home_audio_service", None)

    try:
        from core.device_sync_service import DeviceSyncService
        from core.sync.device_registry import DeviceRegistry

        container.register("device_sync_service", DeviceSyncService())
        device_registry = DeviceRegistry()
        container.register("device_registry", device_registry)
        search_registry = container.get("search_provider_registry")
        if search_registry is not None:
            from core.search.models import SearchDomain
            from core.search.providers import DeviceSearchProvider

            search_registry.register(
                SearchDomain.DEVICE, DeviceSearchProvider(device_registry)
            )
    except Exception as exc:
        logger.error("Failed to create device_sync_service: %s", exc)
        container.register("device_sync_service", None)
        container.register("device_registry", None)

    try:
        from core.mobile_sync_service import MobileSyncService

        container.register(
            "mobile_sync_service",
            MobileSyncService(db=container.get("database")),
        )
    except Exception as exc:
        logger.error("Failed to create mobile_sync_service: %s", exc)
        container.register("mobile_sync_service", None)

    from core.radio.radio_service import RadioService

    container.register("radio_service", RadioService(event_bus=event_bus))

    try:
        from core.lyrics.service import LyricsService
        from core.lyrics.resolver import LyricsResolver
        from core.lyrics.registry import LyricsProviderRegistry
        from core.lyrics.storage import LyricsStorageService
        from core.lyrics.editor import LyricsEditorService
        from core.lyrics.events import LyricEventBus
        from core.paths import lyrics_cache_path
        from infrastructure.lyrics.cache_repository import SqliteLyricsCacheRepository
        from infrastructure.lyrics.sidecar_provider import FileSidecarProvider
        from infrastructure.lyrics.embedded_writer import MutagenEmbeddedLyricsWriter
        from infrastructure.lyrics.providers.lrclib_provider import LrcLibProvider

        cache_repo = SqliteLyricsCacheRepository(lyrics_cache_path())
        cache_repo.initialize()
        registry = LyricsProviderRegistry()
        registry.register(LrcLibProvider(cache=cache_repo))
        sidecar_provider = FileSidecarProvider()
        storage_service = LyricsStorageService(
            sidecar_provider=sidecar_provider,
            embedded_writer=MutagenEmbeddedLyricsWriter(),
        )
        resolver = LyricsResolver(
            provider_registry=registry,
            cache_repo=cache_repo,
            sidecar_provider=sidecar_provider,
            event_bus=LyricEventBus(),
        )
        lyrics_service = LyricsService(
            resolver=resolver,
            provider_registry=registry,
            cache_repo=cache_repo,
            storage_service=storage_service,
            editor_service=LyricsEditorService(),
            event_bus=LyricEventBus(),
        )
        container.register("lyrics_service", lyrics_service)
    except Exception as exc:
        logger.error("Failed to create lyrics_service: %s", exc)
        container.register("lyrics_service", None)
