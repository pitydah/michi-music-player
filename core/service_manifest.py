"""Declarative service manifest — single source of truth for container lifecycle.

Every stateful runtime component (including *Manager/*Registry/*Executor/*Store
classes that do not end in "Service") is declared here with its lifecycle kind,
priority, dependencies and consumers. ServiceContainer derives start/shutdown
behaviour from SERVICE_MANIFEST instead of static name lists (ADR-001).

Rule: the manifest is the source of truth; composition builders only construct.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ServiceClass(Enum):
    """Taxonomy of runtime components (audit RUNTIME_SERVICE_AUDIT_CURRENT §5)."""

    MANAGED_SERVICE = "managed_service"
    DOMAIN_SERVICE = "domain_service"
    APPLICATION_SERVICE = "application_service"
    PASSIVE_REPOSITORY = "passive_repository"
    STATE_STORE = "state_store"
    EXECUTOR = "executor"
    PROCESS_MANAGER = "process_manager"
    UI_ADAPTER = "ui_adapter"
    REGISTRY = "registry"
    FACTORY = "factory"
    EXTERNAL_RESOURCE = "external_resource"
    LEGACY_COMPONENT = "legacy_component"


class ServicePriority(Enum):
    """Availability requirements for a registered service."""

    REQUIRED = "required"
    OPTIONAL = "optional"
    CAPABILITY_GATED = "capability_gated"
    DEFERRED_PHYSICAL = "deferred_physical"
    DEFERRED = "deferred"


class LifecycleKind(Enum):
    """How the container treats a component's lifecycle."""

    MANAGED = "managed"
    PASSIVE = "passive"
    EXTERNAL = "external"


@dataclass(frozen=True)
class ServiceDescriptor:
    """Declarative description of a runtime component.

    Attributes:
        name: Canonical key (registered container key, or component name for
            standalone components that live outside the container).
        service_class: Taxonomy bucket from ServiceClass.
        lifecycle: MANAGED (start/shutdown called), PASSIVE (no lifecycle
            calls), EXTERNAL (only shutdown/cancel, never start).
        priority: Availability requirement (ServicePriority).
        dependencies: Container keys that must exist before this one.
        consumers: Bridges/modules that consume this component (best effort;
            empty tuple is acceptable for shared infrastructure).
        capabilities: Real capability keys used by the capability bridge.
        start_method/shutdown_method/stop_method/cancel_method: Method names
            to invoke; missing methods are skipped, not errors.
        optional: True when registration may be None or absent.
        description: Why this component exists / how it is used.
    """

    name: str
    service_class: ServiceClass
    lifecycle: LifecycleKind
    priority: ServicePriority
    dependencies: tuple[str, ...] = ()
    consumers: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    start_method: str = "start"
    shutdown_method: str = "shutdown"
    stop_method: str = "stop"
    cancel_method: str = "cancel"
    optional: bool = False
    description: str = ""


def _d(name, service_class, lifecycle, priority, **kwargs) -> ServiceDescriptor:
    """Compact descriptor factory for the manifest table."""
    return ServiceDescriptor(
        name=name,
        service_class=service_class,
        lifecycle=lifecycle,
        priority=priority,
        **kwargs,
    )


SERVICE_MANIFEST: dict[str, ServiceDescriptor] = {
    # ── Infrastructure (18 registered keys) ──────────────────────────────
    "settings_manager": _d(
        "settings_manager", ServiceClass.PASSIVE_REPOSITORY,
        LifecycleKind.PASSIVE, ServicePriority.OPTIONAL,
        capabilities=("settings",),
        description="QSettings wrapper; passive by design.",
    ),
    "paths": _d(
        "paths", ServiceClass.PASSIVE_REPOSITORY,
        LifecycleKind.PASSIVE, ServicePriority.OPTIONAL,
        description="XDG path resolver (function); passive by design.",
    ),
    "database": _d(
        "database", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.REQUIRED,
        capabilities=("library",),
        description="LibraryDB — SQLite WAL database handle.",
    ),
    "connection_factory": _d(
        "connection_factory", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.REQUIRED,
        dependencies=("database",),
        description="Alias of database object for legacy consumers.",
    ),
    "read_connection_factory": _d(
        "read_connection_factory", ServiceClass.PASSIVE_REPOSITORY,
        LifecycleKind.PASSIVE, ServicePriority.OPTIONAL,
        dependencies=("database",),
        consumers=("capability_bridge",),
        description="Read-only SQLite connection factory.",
    ),
    "writer_coordinator": _d(
        "writer_coordinator", ServiceClass.STATE_STORE,
        LifecycleKind.MANAGED, ServicePriority.OPTIONAL,
        dependencies=("database",),
        description="Coordinated SQLite write queue; no lifecycle methods yet.",
    ),
    "track_repository": _d(
        "track_repository", ServiceClass.PASSIVE_REPOSITORY,
        LifecycleKind.PASSIVE, ServicePriority.OPTIONAL,
        dependencies=("database",),
        consumers=("library_query_service",),
        description="Track CRUD repository.",
    ),
    "album_repository": _d(
        "album_repository", ServiceClass.PASSIVE_REPOSITORY,
        LifecycleKind.PASSIVE, ServicePriority.OPTIONAL,
        dependencies=("database",),
        consumers=("library_query_service",),
        description="Album CRUD repository.",
    ),
    "artist_repository": _d(
        "artist_repository", ServiceClass.PASSIVE_REPOSITORY,
        LifecycleKind.PASSIVE, ServicePriority.OPTIONAL,
        dependencies=("database",),
        consumers=("library_query_service",),
        description="Artist CRUD repository.",
    ),
    "runtime_persistence": _d(
        "runtime_persistence", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.REQUIRED,
        description="Persists runtime session state.",
    ),
    "process_controller": _d(
        "process_controller", ServiceClass.PROCESS_MANAGER,
        LifecycleKind.MANAGED, ServicePriority.REQUIRED,
        description="Controls owned subprocesses.",
    ),
    "event_bus": _d(
        "event_bus", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.REQUIRED,
        description="In-process pub/sub event bus.",
    ),
    "worker_manager": _d(
        "worker_manager", ServiceClass.EXECUTOR,
        LifecycleKind.MANAGED, ServicePriority.REQUIRED,
        consumers=("job_bridge", "query_executor", "library_service",
                   "folder_service", "smart_tagging_service", "metadata_service"),
        description="ThreadPool executor; single productive instance.",
    ),
    "query_executor": _d(
        "query_executor", ServiceClass.EXECUTOR,
        LifecycleKind.MANAGED, ServicePriority.REQUIRED,
        dependencies=("worker_manager",),
        description="Async SQLite queries with sync fallback.",
    ),
    "job_service": _d(
        "job_service", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.REQUIRED,
        consumers=("notification_service",),
        capabilities=("app_state",),
        description="Durable job service (S2 migrates JobBridge onto it).",
    ),
    "confirmation_service": _d(
        "confirmation_service", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.REQUIRED,
        dependencies=("action_registry",),
        description="Destructive-action confirmation flow.",
    ),
    "settings_coordinator": _d(
        "settings_coordinator", ServiceClass.DOMAIN_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.REQUIRED,
        dependencies=("settings_service",),
        capabilities=("settings",),
        consumers=("settings_service", "settings_bridge"),
        description="SettingsRuntimeCoordinator — applies runtime settings.",
    ),
    "settings_service": _d(
        "settings_service", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.REQUIRED,
        dependencies=("settings_coordinator",),
        capabilities=("settings",),
        consumers=("settings_bridge",),
        description="Settings get/set/reset service.",
    ),
    # ── Playback (4 registered keys) ─────────────────────────────────────
    "queue_service": _d(
        "queue_service", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.REQUIRED,
        dependencies=("playback_service",),
        capabilities=("playback", "nowplaying"),
        consumers=("nowplaying_bridge", "playback_bridge", "track_action_service"),
        description="Canonical play queue synced to the active backend.",
    ),
    "playback_service": _d(
        "playback_service", ServiceClass.APPLICATION_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.REQUIRED,
        dependencies=("worker_manager", "event_bus", "database"),
        capabilities=("playback", "eq", "output_profiles", "transmit"),
        consumers=("queue_service", "mpris_adapter", "home_audio_service",
                   "playback_bridge", "home_dashboard"),
        description="PlayerService facade over GStreamer/MPD engines.",
    ),
    "notification_service": _d(
        "notification_service", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.REQUIRED,
        dependencies=("event_bus",),
        capabilities=("notifications",),
        consumers=("notification_bridge",),
        description="User-facing notifications.",
    ),
    "mpris_adapter": _d(
        "mpris_adapter", ServiceClass.UI_ADAPTER,
        LifecycleKind.EXTERNAL, ServicePriority.OPTIONAL,
        dependencies=("playback_service", "queue_service"),
        optional=True,
        description="MPRIS D-Bus adapter; may be None when D-Bus is absent.",
    ),
    # ── Library (20 registered keys) ─────────────────────────────────────
    "library_sources_service": _d(
        "library_sources_service", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.REQUIRED,
        capabilities=("library",),
        consumers=("library_bridge", "folder_tree_model"),
        description="Library root paths and sources.",
    ),
    "library_query_service": _d(
        "library_query_service", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.REQUIRED,
        dependencies=("connection_factory", "library_sources_service"),
        capabilities=("library",),
        consumers=("library_bridge", "track_action_service", "playlist_service",
                   "global_search_service", "mix_service", "collection_service",
                   "library_service", "smart_tagging_service", "audio_lab_service"),
        description="Canonical library queries (FTS5).",
    ),
    "library_filtered_query_service": _d(
        "library_filtered_query_service", ServiceClass.DOMAIN_SERVICE,
        LifecycleKind.PASSIVE, ServicePriority.OPTIONAL,
        dependencies=("library_query_service",),
        description="Alias of library_query_service (same object).",
    ),
    "collection_service": _d(
        "collection_service", ServiceClass.DOMAIN_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.OPTIONAL,
        dependencies=("database", "library_query_service"),
        consumers=("library_bridge",),
        capabilities=("library",),
        description="User collections over the library.",
    ),
    "folder_tree_model": _d(
        "folder_tree_model", ServiceClass.STATE_STORE,
        LifecycleKind.PASSIVE, ServicePriority.OPTIONAL,
        dependencies=("library_sources_service",),
        consumers=("folder_bridge",),
        description="Qt model of the folder tree.",
    ),
    "library_mutation_service": _d(
        "library_mutation_service", ServiceClass.DOMAIN_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.REQUIRED,
        dependencies=("database", "event_bus", "favorite_service"),
        capabilities=("library", "metadata"),
        consumers=("metadata_service", "library_doctor_service",
                   "library_bridge", "track_action_service"),
        description="Canonical library mutation authority (S3): favorites via "
                    "FavoriteService, track removal, metadata field edits.",
    ),
    "favorite_service": _d(
        "favorite_service", ServiceClass.DOMAIN_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.OPTIONAL,
        dependencies=("database", "event_bus"),
        capabilities=("library",),
        consumers=("library_bridge", "track_action_service", "songs_service",
                   "library_mutation_service"),
        description="Canonical favorites with entity identity "
                    "(entity_type/entity_id/public_ref); always registered by "
                    "composition, optional priority so the frozen required "
                    "set stays the start gate.",
    ),
    "metadata_editor_service": _d(
        "metadata_editor_service", ServiceClass.DOMAIN_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.OPTIONAL,
        dependencies=("database",),
        capabilities=("metadata",),
        consumers=("metadata_service", "metadata_bridge"),
        description="MetadataEditorService — field-level metadata editing with "
                    "preview/rollback (legacy library_mutation_service binding).",
    ),
    "library_service": _d(
        "library_service", ServiceClass.APPLICATION_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.OPTIONAL,
        dependencies=("database", "worker_manager", "library_query_service"),
        consumers=("library_bridge",),
        capabilities=("library",),
        description="Scan/index orchestration; shutdown-only (no start method).",
    ),
    "playlist_service": _d(
        "playlist_service", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.REQUIRED,
        dependencies=("library_query_service", "connection_factory"),
        capabilities=("playlists",),
        consumers=("playlists_bridge", "track_action_service", "mix_service"),
        description="Playlist CRUD.",
    ),
    "track_action_service": _d(
        "track_action_service", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.REQUIRED,
        dependencies=("queue_service", "library_query_service", "playlist_service"),
        capabilities=("library",),
        description="Track-level actions (queue, playlists, files).",
    ),
    "history_query_service": _d(
        "history_query_service", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.REQUIRED,
        dependencies=("connection_factory",),
        consumers=("history_bridge",),
        description="Playback history queries.",
    ),
    "global_search_service": _d(
        "global_search_service", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.REQUIRED,
        dependencies=("connection_factory", "library_query_service"),
        capabilities=("global_search",),
        consumers=("global_search_bridge",),
        description="Global FTS5 search.",
    ),
    "metadata_service": _d(
        "metadata_service", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.REQUIRED,
        dependencies=("worker_manager", "library_mutation_service"),
        capabilities=("metadata",),
        consumers=("metadata_bridge", "audio_lab_service"),
        description="Metadata read/edit operations.",
    ),
    "library_doctor_service": _d(
        "library_doctor_service", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.OPTIONAL,
        dependencies=("database", "library_mutation_service", "worker_manager"),
        optional=True,
        capabilities=("library_doctor",),
        consumers=("library_doctor_bridge",),
        description="Library health diagnosis; may be None.",
    ),
    "library_doctor_scan_repository": _d(
        "library_doctor_scan_repository", ServiceClass.PASSIVE_REPOSITORY,
        LifecycleKind.PASSIVE, ServicePriority.OPTIONAL,
        dependencies=("database",),
        optional=True,
        consumers=("library_doctor_bridge",),
        description="Scan/repair repository for the library doctor; injected "
                    "into LibraryDoctorBridge (no bridge construction).",
    ),
    "recognition_service": _d(
        "recognition_service", ServiceClass.APPLICATION_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.OPTIONAL,
        dependencies=(),
        consumers=("smart_tagging_service", "identifier_controller"),
        description="Music identification via providers (ProviderManager injected by constructor); start() is a no-op and safe at bootstrap.",
    ),
    "smart_tagging_service": _d(
        "smart_tagging_service", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.OPTIONAL,
        dependencies=("worker_manager", "library_query_service", "recognition_service"),
        optional=True,
        capabilities=("smart_tagging",),
        description="Smart tagging suggestions; may be None.",
    ),
    "artwork_service": _d(
        "artwork_service", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.OPTIONAL,
        dependencies=("database",),
        optional=True,
        capabilities=("cover",),
        consumers=("library_bridge", "cover_bridge"),
        description="CoverArtService; shutdown-only (no start method).",
    ),
    "songs_service": _d(
        "songs_service", ServiceClass.DOMAIN_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.OPTIONAL,
        dependencies=("database", "library_query_service"),
        optional=True,
        capabilities=("library",),
        consumers=("library_bridge",),
        description="Songs view service; shutdown-only.",
    ),
    "track_service": _d(
        "track_service", ServiceClass.DOMAIN_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.OPTIONAL,
        dependencies=("database",),
        optional=True,
        capabilities=("library",),
        consumers=("library_bridge",),
        description="Track detail service; shutdown-only.",
    ),
    "genres_service": _d(
        "genres_service", ServiceClass.DOMAIN_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.OPTIONAL,
        dependencies=("database",),
        optional=True,
        capabilities=("library",),
        consumers=("library_bridge",),
        description="Genres service; shutdown-only.",
    ),
    "folder_service": _d(
        "folder_service", ServiceClass.DOMAIN_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.OPTIONAL,
        dependencies=("database", "worker_manager"),
        optional=True,
        capabilities=("library",),
        consumers=("folder_bridge",),
        description="Folder browsing service; shutdown-only.",
    ),
    # ── Audio Lab (3 registered keys) ────────────────────────────────────
    "audio_lab_service": _d(
        "audio_lab_service", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.OPTIONAL,
        dependencies=("worker_manager", "library_query_service", "metadata_service"),
        optional=True,
        capabilities=("audio_lab", "disc_lab"),
        consumers=("audio_lab_bridge",),
        description="Audio Lab orchestrator; start() is idempotent.",
    ),
    "diagnostics_service": _d(
        "diagnostics_service", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.REQUIRED,
        dependencies=("worker_manager", "library_query_service", "settings_service"),
        optional=True,
        capabilities=("diagnostics",),
        consumers=("diagnostics_bridge",),
        description="Audio/backend diagnostics.",
    ),
    "cd_ripper_service": _d(
        "cd_ripper_service", ServiceClass.DOMAIN_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.OPTIONAL,
        dependencies=(),
        optional=True,
        capabilities=("disc_lab",),
        consumers=("audio_lab_bridge",),
        description="CD ripping; cancel/shutdown only, no start.",
    ),
    # ── Ecosystem (9 registered keys) ────────────────────────────────────
    "connection_service": _d(
        "connection_service", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.OPTIONAL,
        dependencies=("worker_manager",),
        optional=True,
        capabilities=("connections", "connections_michilink"),
        consumers=("connections_bridge",),
        description="Michi Link / connection management.",
    ),
    "snapcast_control": _d(
        "snapcast_control", ServiceClass.EXTERNAL_RESOURCE,
        LifecycleKind.EXTERNAL, ServicePriority.OPTIONAL,
        optional=True,
        capabilities=("snapcast",),
        consumers=("home_audio_service",),
        description="Snapcast JSON-RPC client; external resource, never started.",
    ),
    "snapserver_manager": _d(
        "snapserver_manager", ServiceClass.PROCESS_MANAGER,
        LifecycleKind.MANAGED, ServicePriority.OPTIONAL,
        dependencies=(),
        optional=True,
        capabilities=("snapcast",),
        consumers=("home_audio_service", "capability_bridge"),
        description="Owned snapserver daemon lifecycle; start degrades gracefully when the binary is missing.",
    ),
    "home_audio_service": _d(
        "home_audio_service", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.OPTIONAL,
        dependencies=("worker_manager", "playback_service",
                      "snapserver_manager", "snapcast_control"),
        optional=True,
        capabilities=("home_audio", "snapcast", "transmit"),
        consumers=("home_audio_bridge",),
        description="Home Audio orchestration (Snapcast + Home Assistant).",
    ),
    "device_sync_service": _d(
        "device_sync_service", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.OPTIONAL,
        dependencies=("worker_manager", "library_query_service"),
        optional=True,
        capabilities=("devices_sync",),
        consumers=("sync_bridge",),
        description="Mobile device sync orchestration.",
    ),
    "device_registry": _d(
        "device_registry", ServiceClass.REGISTRY,
        LifecycleKind.PASSIVE, ServicePriority.OPTIONAL,
        dependencies=(),
        optional=True,
        capabilities=("devices_sync",),
        consumers=("device_sync_service",),
        description="Paired device registry.",
    ),
    "mobile_sync_service": _d(
        "mobile_sync_service", ServiceClass.DOMAIN_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.OPTIONAL,
        dependencies=("database",),
        optional=True,
        capabilities=("devices_sync",),
        consumers=("mobile_sync_bridge",),
        description="Mobile sync session state; no listener today (S7).",
    ),
    "radio_service": _d(
        "radio_service", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.OPTIONAL,
        dependencies=("event_bus",),
        optional=True,
        capabilities=("radio",),
        consumers=("radio_bridge",),
        description="Radio stations + persisted history.",
    ),
    "lyrics_service": _d(
        "lyrics_service", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.OPTIONAL,
        dependencies=("worker_manager",),
        optional=True,
        capabilities=("lyrics",),
        consumers=("lyrics_bridge",),
        description="Lyrics via LRCLIB.",
    ),
    # ── Settings / presentation (2 registered keys) ──────────────────────
    "theme_service": _d(
        "theme_service", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.REQUIRED,
        optional=True,
        capabilities=("theme",),
        description="Background theme service.",
    ),
    "accessibility_service": _d(
        "accessibility_service", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.REQUIRED,
        optional=True,
        capabilities=(),
        description="Accessibility runtime settings.",
    ),
    # ── Intelligence (4 registered keys) ─────────────────────────────────
    "action_registry": _d(
        "action_registry", ServiceClass.REGISTRY,
        LifecycleKind.MANAGED, ServicePriority.REQUIRED,
        consumers=("action_registry_binder", "notification_service",
                   "confirmation_service"),
        description="Registry of user actions.",
    ),
    "mix_query_service": _d(
        "mix_query_service", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.REQUIRED,
        dependencies=("database",),
        optional=True,
        capabilities=("mix",),
        consumers=("mix_bridge", "mix_service"),
        description="Smart-mix/recommendation queries.",
    ),
    "mix_service": _d(
        "mix_service", ServiceClass.MANAGED_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.REQUIRED,
        dependencies=("database", "library_query_service", "playlist_service",
                      "mix_query_service"),
        optional=True,
        capabilities=("mix",),
        consumers=("mix_bridge",),
        description="Mix creation/editing.",
    ),
    "michi_ai_service": _d(
        "michi_ai_service", ServiceClass.DOMAIN_SERVICE,
        LifecycleKind.MANAGED, ServicePriority.CAPABILITY_GATED,
        dependencies=("global_search_service", "playback_service", "queue_service",
                      "playlist_service", "diagnostics_service", "settings_service",
                      "action_registry"),
        optional=True,
        capabilities=("michi_ai", "ai"),
        consumers=("michi_ai_bridge",),
        description="Michi AI engine (capability-gated; S4 fixes gateways).",
    ),
    # ── Application (1 registered key) ───────────────────────────────────
    "navigation_service": _d(
        "navigation_service", ServiceClass.APPLICATION_SERVICE,
        LifecycleKind.PASSIVE, ServicePriority.OPTIONAL,
        capabilities=("navigation",),
        consumers=("navigation_bridge", "assistant_context_providers"),
        description="View navigation state; passive (used directly by shell).",
    ),
    # ── Standalone components (not registered in the container) ──────────
    "job_bridge": _d(
        "job_bridge", ServiceClass.UI_ADAPTER,
        LifecycleKind.PASSIVE, ServicePriority.OPTIONAL,
        dependencies=("worker_manager", "job_service"),
        description="QML scan jobs (de facto productive); S2 migrates onto job_service.",
    ),
    "job_manager": _d(
        "job_manager", ServiceClass.LEGACY_COMPONENT,
        LifecycleKind.PASSIVE, ServicePriority.OPTIONAL,
        description="Legacy job repository (job_queue.db); retired in S2.",
    ),
    "audio_lab_job_adapter": _d(
        "audio_lab_job_adapter", ServiceClass.LEGACY_COMPONENT,
        LifecycleKind.PASSIVE, ServicePriority.OPTIONAL,
        dependencies=("worker_manager",),
        description="Legacy audio-lab job adapter without callers; retired in S2.",
    ),
    "action_registry_binder": _d(
        "action_registry_binder", ServiceClass.FACTORY,
        LifecycleKind.PASSIVE, ServicePriority.OPTIONAL,
        dependencies=("action_registry",),
        description="Binds registry actions to widgets/bridges.",
    ),
    "selection_context_bridge": _d(
        "selection_context_bridge", ServiceClass.STATE_STORE,
        LifecycleKind.PASSIVE, ServicePriority.OPTIONAL,
        description="Shared QML selection context.",
    ),
    "bridge_factory": _d(
        "bridge_factory", ServiceClass.FACTORY,
        LifecycleKind.PASSIVE, ServicePriority.OPTIONAL,
        dependencies=("worker_manager", "job_service"),
        description="Builds QML bridges from the container.",
    ),
    "page_state_store": _d(
        "page_state_store", ServiceClass.STATE_STORE,
        LifecycleKind.PASSIVE, ServicePriority.OPTIONAL,
        description="QML page state store.",
    ),
    "hybrid_audio_manager": _d(
        "hybrid_audio_manager", ServiceClass.APPLICATION_SERVICE,
        LifecycleKind.PASSIVE, ServicePriority.OPTIONAL,
        dependencies=("playback_service",),
        description="GStreamer/MPD backend orchestrator owned by PlayerService.",
    ),
    "provider_manager": _d(
        "provider_manager", ServiceClass.REGISTRY,
        LifecycleKind.PASSIVE, ServicePriority.OPTIONAL,
        consumers=("recognition_service",),
        description="Recognition provider registry (Shazam/AudD/AcoustID).",
    ),
    "knowledge_broker": _d(
        "knowledge_broker", ServiceClass.DOMAIN_SERVICE,
        LifecycleKind.PASSIVE, ServicePriority.OPTIONAL,
        description="AI knowledge broker; production wiring unverified (S4).",
    ),
    "mpd_service_manager": _d(
        "mpd_service_manager", ServiceClass.PROCESS_MANAGER,
        LifecycleKind.PASSIVE, ServicePriority.OPTIONAL,
        description="MPD daemon management owned by MpdBackend.",
    ),
}


def descriptor_for(name: str) -> ServiceDescriptor | None:
    """Return the manifest descriptor for *name*, or None when absent."""
    return SERVICE_MANIFEST.get(name)


def priority_for(name: str) -> ServicePriority | None:
    """Return the manifest priority for *name*, or None when absent."""
    desc = SERVICE_MANIFEST.get(name)
    return desc.priority if desc else None


def managed_names() -> list[str]:
    """Return manifest keys with MANAGED lifecycle, in declaration order."""
    return [name for name, desc in SERVICE_MANIFEST.items()
            if desc.lifecycle == LifecycleKind.MANAGED]
