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
        # ── Device sync (Fase Sync, single authority) ────────────────────
        # The facade owns NO parallel system: registry, discovery adapters,
        # resolvers, planners, job service, transfer adapter, verification
        # and history repository are all composed HERE and injected.
        from core.device_sync.discovery import (
            DiscoveryComposite,
            MscDiscoveryAdapter,
            MtpDiscoveryAdapter,
            NetworkDiscoveryAdapter,
        )
        from core.device_sync.history import SyncHistoryRepository
        from core.device_sync.planning import DeviceSyncPlanner
        from core.device_sync.profile_resolver import DeviceProfileResolver
        from core.device_sync.transcode_planning import TranscodePlanner
        from core.device_sync.transfer import TransferAdapter
        from core.device_sync.verification import VerificationService
        from core.device_sync_service import DeviceSyncService
        from core.sync.device_registry import DeviceRegistry

        device_registry = DeviceRegistry()
        container.register("device_registry", device_registry)

        process_controller = container.get("process_controller")
        discovery_adapters = DiscoveryComposite([
            MscDiscoveryAdapter(),
            MtpDiscoveryAdapter(process_controller=process_controller),
            NetworkDiscoveryAdapter(),
        ])
        profile_resolver = DeviceProfileResolver()
        transcode_planner = TranscodePlanner()
        sync_planner = DeviceSyncPlanner(transcode_planner=transcode_planner)
        transfer_adapter = TransferAdapter(process_controller=process_controller)
        verification_service = VerificationService()

        app_db = container.get("database")
        history_repository = SyncHistoryRepository(app_db)
        history_repository.initialize()

        device_sync = DeviceSyncService(
            device_registry=device_registry,
            discovery_adapters=discovery_adapters,
            profile_resolver=profile_resolver,
            sync_planner=sync_planner,
            transcode_planner=transcode_planner,
            job_service=container.get("job_service"),
            transfer_adapter=transfer_adapter,
            verification_service=verification_service,
            history_repository=history_repository,
            event_bus=event_bus,
            process_controller=process_controller,
        )
        container.register("device_sync_service", device_sync)
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
        from core.settings_manager import get_bool, get_list, get_str

        container.register(
            "mobile_sync_service",
            MobileSyncService(
                db=container.get("database"),
                device_registry=container.get("device_registry"),
                bind_host=get_str("mobile_sync/bind_host") or "127.0.0.1",
                allow_lan_pairing=get_bool("mobile_sync/allow_lan_pairing"),
                tls_mode=get_str("mobile_sync/tls_mode") or "none",
                allowed_networks=list(
                    get_list("mobile_sync/allowed_networks") or []),
                legacy_code_pairing_enabled=get_bool(
                    "mobile_sync/legacy_code_pairing_enabled"),
                signature_pairing_enabled=get_bool(
                    "mobile_sync/signature_pairing_enabled"),
            ),
        )
    except Exception as exc:
        logger.error("Failed to create mobile_sync_service: %s", exc)
        container.register("mobile_sync_service", None)

    try:
        # ── Michi Link advanced services (ADR-002 single domain authority) ──
        # Canonical stack: integrations/michi_link/services/. The legacy
        # variants (core/micro_server_service.py, integrations/
        # micro_server_service.py, integrations/michi_link/*stubs) are marked
        # LEGACY and are never registered here.
        from integrations.michi_link.client import MichiLinkClient
        from integrations.michi_link.services.micro_server_service import (
            MicroServerService,
        )
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        from integrations.michi_link.services.continue_on_server_service import (
            ContinueOnServerService,
        )
        from integrations.michi_link.services.remote_library_service import (
            RemoteLibraryService,
        )
        from integrations.michi_link.services.track_identity_service import (
            TrackIdentityService,
        )
        from integrations.michi_link.services.diagnostics_service import (
            LinkDiagnosticsService,
        )

        michi_link_client = MichiLinkClient()
        container.register("michi_link_client", michi_link_client)

        track_identity_svc = TrackIdentityService()
        import_svc = ImportToServerService(identity_service=track_identity_svc)
        server_svc = MicroServerService(client=michi_link_client)
        container.register("michi_link_server_service", server_svc)
        container.register("michi_link_import_service", import_svc)
        container.register("michi_link_track_identity_service", track_identity_svc)

        queue_service = container.get("queue_service")
        playback_service = container.get("playback_service")

        def _queue_provider():
            if queue_service is None:
                return [], -1, 0.0
            try:
                state = queue_service.get_state()
                items = state.get("items") or []
                ids = [
                    i.get("track_id") or i.get("filepath") or ""
                    for i in items
                ]
                return ids, int(state.get("current_index", -1) or -1), \
                    float(state.get("position_ms", 0.0) or 0.0)
            except Exception:
                return [], -1, 0.0

        def _pause_local():
            if playback_service is not None:
                try:
                    playback_service.pause()
                except Exception as exc:
                    logger.warning("Failed to pause local playback: %s", exc)

        continue_svc = ContinueOnServerService(
            queue_provider=_queue_provider,
            pause_local=_pause_local,
            identity_service=track_identity_svc,
            import_service=import_svc,
        )
        container.register("michi_link_continue_service", continue_svc)
        container.register(
            "michi_link_remote_library_service",
            RemoteLibraryService(micro=server_svc),
        )
        container.register("michi_link_diagnostics_service", LinkDiagnosticsService())
    except Exception as exc:
        logger.error("Failed to create michi_link services: %s", exc)
        for key in ("michi_link_client", "michi_link_server_service",
                    "michi_link_import_service", "michi_link_continue_service",
                    "michi_link_remote_library_service",
                    "michi_link_track_identity_service",
                    "michi_link_diagnostics_service"):
            container.register(key, None)

    try:
        # ── Radio (ADR-002 single domain authority) ──────────────────────
        # Composition registers the canonical stack directly — no facade
        # constructs the canonical service internally:
        #   SqliteStationRepository + SqliteRadioHistoryRepository (PASSIVE)
        #   + RadioPlaybackAdapter (over PlayerService) + CanonicalRadioService
        from core.paths import radio_database_path
        from core.radio.playback_adapter import RadioPlaybackAdapter
        from core.radio.service import RadioService as CanonicalRadioService
        from infrastructure.radio.history_repository import SqliteRadioHistoryRepository
        from infrastructure.radio.station_repository import SqliteStationRepository

        radio_db = radio_database_path()
        station_repo = SqliteStationRepository(radio_db)
        station_repo.initialize()
        history_repo = SqliteRadioHistoryRepository(radio_db)
        history_repo.initialize()
        playback_adapter = RadioPlaybackAdapter(
            player_service=container.get("playback_service"),
        )
        radio_service = CanonicalRadioService(
            station_repo=station_repo,
            history_repo=history_repo,
            playback_adapter=playback_adapter,
            event_bus=event_bus,
        )
        container.register("radio_station_repository", station_repo)
        container.register("radio_history_repository", history_repo)
        container.register("radio_playback_adapter", playback_adapter)
        container.register("radio_service", radio_service)
    except Exception as exc:
        logger.error("Failed to create radio_service: %s", exc)
        container.register("radio_station_repository", None)
        container.register("radio_history_repository", None)
        container.register("radio_playback_adapter", None)
        container.register("radio_service", None)

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
