"""BridgeFactory creates bridges from ServiceContainer, no caching.

Does not open databases, construct backends, or start services.
Does not cache or create core services internally.
API: BridgeFactory(container).create_all() -> BridgeRegistry.
"""
from __future__ import annotations

import logging
from PySide6.QtCore import Property, QObject, Signal

from core.service_container import ServiceContainer
from ui_qml_bridge.context_bindings import (
    CONTEXT_BINDINGS,
    ContextBinding,
    QML_CONTEXT_BINDINGS,
)

logger = logging.getLogger("michi.bridge_factory")

# Cross-bridge references that must be non-None after the two-phase wiring
# (Corrección 3). Each entry maps a bridge key to the instance attribute that
# holds a dependency created *after* the bridge itself, so the constructor
# legitimately receives ``None`` and the dependency is injected later by
# :meth:`BridgeFactory._wire_bridges`.
_REQUIRED_BRIDGE_REFS: dict[str, tuple[str, ...]] = {
    "confirmation": ("_action_registry",),
    "library": ("_cover_provider",),
    "playlists": ("_notifications",),
    "history": ("_notifications",),
    "global_search": ("_notifications",),
}


class BridgeFactory(QObject):
    """Creates each bridge with injected dependencies from ServiceContainer."""

    bridgeReportChanged = Signal()

    def __init__(
        self, container: ServiceContainer, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._container = container
        self._bridges: dict[str, QObject] = {}
        self._capabilities: dict[str, bool] = {}
        self._degraded: list[tuple[str, str]] = []
        self._binding_by_key: dict[str, ContextBinding] = {}
        self._bridge_report: dict = {}
        for _binding in CONTEXT_BINDINGS:
            _bridge_key = QML_CONTEXT_BINDINGS.get(_binding.context_name)
            if _bridge_key is not None:
                self._binding_by_key[_bridge_key] = _binding

    @property
    def bridges(self) -> dict[str, QObject]:
        return dict(self._bridges)

    @property
    def capabilities(self) -> dict[str, bool]:
        return dict(self._capabilities)

    def get(self, name: str) -> QObject | None:
        return self._bridges.get(name)

    def has(self, name: str) -> bool:
        return name in self._bridges

    @property
    def degraded_bridges(self) -> list[tuple[str, str]]:
        """Bridges skipped due to missing dependencies.

        Each entry is a ``(bridge_key, reason)`` tuple.
        """
        return list(self._degraded)

    def validate_binding(self, binding: ContextBinding) -> tuple[bool, str | None]:
        """Check that all required_services for a binding exist in container or bridges.

        Returns ``(True, None)`` when all required services are available, or
        ``(False, reason)`` when a required service is missing.
        """
        for svc in binding.required_services:
            if not self._container.contains(svc) and svc not in self._bridges:
                return False, f"Missing {svc} for {binding.context_name}"
        return True, None

    def _missing_required_services(self, binding: ContextBinding) -> list[str]:
        """Return required_services for *binding* that are absent (None or unregistered)."""
        return [
            svc
            for svc in binding.required_services
            if not self._container.contains(svc) and svc not in self._bridges
        ]

    def _missing_required_refs(self, bridge: QObject, key: str) -> list[str]:
        """Return cross-bridge refs for *bridge* that are still None (Corrección 3).

        ``_REQUIRED_BRIDGE_REFS`` lists the instance attributes that hold a
        dependency injected by :meth:`_wire_bridges`. A None value here means the
        two-phase wiring did not run or the dependency itself was not created.
        """
        refs = _REQUIRED_BRIDGE_REFS.get(key, ())
        return [
            f"{key}.{ref}"
            for ref in refs
            if getattr(bridge, ref, None) is None
        ]

    def validate_all_bridges(self) -> dict:
        """Validate every bridge against its ContextBinding and return a report.

        Each known bridge key is classified as:

        - ``ok``: created, all ``required_services`` present (non-None) and all
          required cross-bridge references wired (non-None).
        - ``missing_required``: created but a required service is None/missing,
          a required cross-bridge reference is still None, or expected by a
          binding but not created at all.
        - ``degraded``: creation skipped (recorded in :attr:`degraded_bridges`).
        - ``created``: created but has no ContextBinding to validate against
          (e.g. internal helpers like ``query_executor``).

        The report is stored on the factory (see :attr:`bridgeReport`) and
        emitted via :attr:`bridgeReportChanged` for QML diagnostics.
        """
        per_bridge: dict[str, dict] = {}
        degraded_map = dict(self._degraded)
        all_keys = set(self._bridges) | set(degraded_map) | set(self._binding_by_key)
        ok_count = missing_count = degraded_count = created_count = 0
        for key in sorted(all_keys):
            if key in degraded_map:
                entry = {"status": "degraded", "reason": degraded_map[key]}
                degraded_count += 1
            else:
                bridge = self._bridges.get(key)
                binding = self._binding_by_key.get(key)
                if bridge is None:
                    missing = self._missing_required_services(binding) if binding else []
                    entry = {
                        "status": "missing_required",
                        "missing": missing,
                        "reason": "not created",
                    }
                    missing_count += 1
                    logger.warning(
                        "BridgeFactory: '%s' not created — missing %s", key, missing
                    )
                else:
                    missing = self._missing_required_services(binding) if binding else []
                    # Cross-bridge references injected by _wire_bridges() must
                    # also be non-None (Corrección 3).
                    missing_refs = self._missing_required_refs(bridge, key)
                    if missing or missing_refs:
                        combined = list(missing) + list(missing_refs)
                        entry = {"status": "missing_required", "missing": combined}
                        missing_count += 1
                        logger.warning(
                            "BridgeFactory: '%s' missing required deps %s", key, combined
                        )
                    elif binding is None:
                        entry = {"status": "created"}
                        created_count += 1
                    else:
                        entry = {"status": "ok"}
                        ok_count += 1
            logger.debug("BridgeFactory: %s -> %s", key, entry["status"])
            per_bridge[key] = entry
        report = {
            "bridges": per_bridge,
            "summary": {
                "total": len(per_bridge),
                "ok": ok_count,
                "missing_required": missing_count,
                "degraded": degraded_count,
                "created": created_count,
            },
        }
        self._bridge_report = report
        self.bridgeReportChanged.emit()
        logger.info(
            "BridgeFactory: bridge graph validated — %d ok, %d missing_required, "
            "%d degraded, %d created",
            ok_count,
            missing_count,
            degraded_count,
            created_count,
        )
        return report

    @Property("QVariantMap", notify=bridgeReportChanged)
    def bridgeReport(self) -> dict:
        """Last bridge-graph validation report, exposed to QML for diagnostics."""
        return self._bridge_report

    def _try_create(self, bridge_key: str, create_fn) -> None:
        """Validate the binding for *bridge_key*, then create or skip.

        If the binding's required services are missing, the bridge is skipped
        and recorded in :attr:`degraded_bridges`. If no binding exists for the
        key (e.g. internal helpers like ``query_executor``), the create function
        is called directly.
        """
        if bridge_key in self._bridges:
            return
        binding = self._binding_by_key.get(bridge_key)
        if binding is not None:
            ok, reason = self.validate_binding(binding)
            if not ok:
                self._degraded.append((bridge_key, reason or ""))
                logger.warning("BridgeFactory: skipping %s — %s", bridge_key, reason)
                return
        try:
            create_fn()
        except Exception as exc:  # noqa: BLE001 — graceful degradation
            self._degraded.append((bridge_key, f"Creation failed: {exc}"))
            logger.warning("BridgeFactory: failed to create %s — %s", bridge_key, exc)

    def _get(self, name: str):
        return self._container.get(name)

    def create_page_state_store(self):
        if "page_state" not in self._bridges:
            from ui_qml_bridge.page_state_store import PageStateStore
            self._bridges["page_state"] = PageStateStore()

    def create_route_registry_bridge(self):
        if "route_registry" not in self._bridges:
            from ui_qml_bridge.route_registry_bridge import RouteRegistryBridge
            self._bridges["route_registry"] = RouteRegistryBridge()

    def create_navigation_bridge(self):
        if "navigation" not in self._bridges:
            from ui_qml_bridge.navigation_bridge import NavigationBridge
            navigation = NavigationBridge(
                navigation_service=self._get("navigation_service"),
            )
            self._bridges["navigation"] = navigation
            settings = self._bridges.get("settings")
            if settings is not None:
                navigation.registerLeaveGuard("settings", settings)

    def create_job_bridge(self):
        if "job_bridge" not in self._bridges:
            from ui_qml_bridge.job_bridge import JobBridge
            self._bridges["job_bridge"] = JobBridge(
                job_service=self._get("job_service"),
                worker_manager=self._get("worker_manager"),
                db=self._get("database"),
            )

    def create_confirmation_bridge(self):
        if "confirmation" not in self._bridges:
            from ui_qml_bridge.confirmation_bridge import ConfirmationBridge
            self._bridges["confirmation"] = ConfirmationBridge(
                confirmation_service=self._get("confirmation_service"),
                action_registry=self._bridges.get("action_registry"),
            )

    def create_accessibility_bridge(self):
        if "accessibility" not in self._bridges:
            from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
            self._bridges["accessibility"] = AccessibilityBridge(
                service=self._get("settings_coordinator"),
                settings_service=self._get("settings_coordinator"),
                playback_service=self._get("playback_service"),
            )

    def create_theme_bridge(self):
        if "theme" not in self._bridges:
            from ui_qml_bridge.theme_bridge import ThemeBridge
            self._bridges["theme"] = ThemeBridge(
                coordinator=self._get("settings_coordinator"),
            )

    def create_capability_bridge(self):
        if "capability" not in self._bridges:
            from ui_qml_bridge.capability_bridge import CapabilityBridge
            cb = CapabilityBridge(factory=self)
            self._bridges["capability"] = cb

    def create_library_bridge(self):
        if "library" not in self._bridges:
            from ui_qml_bridge.library_bridge import LibraryBridge
            self._bridges["library"] = LibraryBridge(
                db=self._get("database"),
                search_engine=self._get("global_search_service"),
                player_service=self._get("playback_service"),
                query_service=self._get("library_query_service"),
                query_executor=self._get("query_executor"),
                worker_manager=self._get("worker_manager"),
                job_bridge=self._bridges.get("job_bridge"),
                track_action_service=self._get("track_action_service"),
                queue_service=self._get("queue_service"),
                library_sources_service=self._get("library_sources_service"),
                library_service=self._get("library_service"),
                songs_service=self._get("songs_service"),
                track_service=self._get("track_service"),
                genres_service=self._get("genres_service"),
                collection_service=self._get("collection_service"),
                folder_tree_model=self._get("folder_tree_model"),
                playlists_bridge=self._bridges.get("playlists"),
                container=self._container,
                artwork_svc=self._get("artwork_service"),
                cover_provider=self._bridges.get("cover_provider"),
            )

    def create_library_sources_bridge(self):
        if "library_sources" not in self._bridges:
            from ui_qml_bridge.library_sources_bridge import LibrarySourcesBridge
            self._bridges["library_sources"] = LibrarySourcesBridge(
                service=self._get("library_sources_service"),
                job_bridge=self._bridges.get("job_bridge"),
                folder_service=self._get("folder_service"),
            )

    def create_nowplaying_bridge(self):
        if "nowplaying" not in self._bridges:
            from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
            from ui_qml_bridge.audio_quality_adapter import AudioQualityAdapter
            quality_adapter = AudioQualityAdapter(
                worker_manager=self._get("worker_manager"),
            )
            self._bridges["nowplaying"] = NowPlayingBridge(
                player_service=self._get("playback_service"),
                queue_service=self._get("queue_service"),
                audio_quality_adapter=quality_adapter,
                cover_provider=self._bridges.get("cover_provider"),
            )

    def create_queue_bridge(self):
        if "queue" not in self._bridges:
            from ui_qml_bridge.queue_bridge import QueueBridge
            self._bridges["queue"] = QueueBridge(
                player_service=self._get("playback_service"),
                playlists_bridge=self.get("playlists"),
                queue_service=self._get("queue_service"),
            )

    def create_playlists_bridge(self):
        if "playlists" not in self._bridges:
            from ui_qml_bridge.playlists_bridge import PlaylistsBridge
            from ui_qml_bridge.selection_context_bridge import SelectionContextBridge
            sel = SelectionContextBridge()
            self._bridges["selection_context"] = sel
            self._bridges["playlists"] = PlaylistsBridge(
                db=self._get("database"),
                selection_context=sel,
                player_service=self._get("playback_service"),
                playlist_service=self._get("playlist_service"),
                queue_service=self._get("queue_service"),
                action_registry=self._bridges.get("action_registry"),
                confirmation_bridge=self._bridges.get("confirmation"),
                navigation_bridge=self._bridges.get("navigation"),
                page_state_store=self._bridges.get("page_state"),
                capability_bridge=self._bridges.get("capability"),
                accessibility_bridge=self._bridges.get("accessibility"),
                notification_bridge=self._bridges.get("notification"),
                job_bridge=self._bridges.get("job_bridge"),
            )

    def create_history_bridge(self):
        if "history" not in self._bridges:
            from ui_qml_bridge.history_bridge import HistoryBridge
            self._bridges["history"] = HistoryBridge(
                db=self._get("database"),
                history_query_service=self._get("history_query_service"),
                query_executor=self._get("query_executor"),
                playback_service=self._get("playback_service"),
                action_registry=self._bridges.get("action_registry"),
                navigation_bridge=self._bridges.get("navigation"),
                page_state_store=self._bridges.get("page_state"),
                capability_bridge=self._bridges.get("capability"),
                accessibility_bridge=self._bridges.get("accessibility"),
                notification_bridge=self._bridges.get("notification"),
                job_bridge=self._bridges.get("job_bridge"),
            )

    def create_search_bridge(self):
        if "global_search" not in self._bridges:
            from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
            self._bridges["global_search"] = GlobalSearchBridge(
                search_service=self._get("global_search_service"),
                query_executor=self._get("query_executor"),
                action_registry=self._bridges.get("action_registry"),
                navigation_bridge=self._bridges.get("navigation"),
                page_state_store=self._bridges.get("page_state"),
                capability_bridge=self._bridges.get("capability"),
                accessibility_bridge=self._bridges.get("accessibility"),
                notification_bridge=self._bridges.get("notification"),
            )

    def create_mix_bridge(self):
        if "mix" not in self._bridges:
            from ui_qml_bridge.mix_bridge import MixBridge
            self._bridges["mix"] = MixBridge(
                mix_service=self._get("mix_service"),
                job_service=self._get("job_service"),
                action_registry=self._bridges.get("action_registry"),
                navigation_bridge=self._bridges.get("navigation"),
                page_state_store=self._bridges.get("page_state"),
                capability_bridge=self._bridges.get("capability"),
                accessibility_bridge=self._bridges.get("accessibility"),
                playlist_service=self._get("playlist_service"),
                playback_service=self._get("playback_service"),
                queue_service=self._get("queue_service"),
                query_executor=self._get("query_executor"),
            )

    def create_lyrics_bridge(self):
        if "lyrics" not in self._bridges:
            from ui_qml_bridge.lyrics_bridge import LyricsBridge
            self._bridges["lyrics"] = LyricsBridge(
                worker_manager=self._get("worker_manager"),
                nowplaying_bridge=self.get("nowplaying"),
            )

    def create_settings_bridge(self):
        if "settings" not in self._bridges:
            from ui_qml_bridge.settings_bridge import SettingsBridgeV2
            bridge = SettingsBridgeV2(service=self._get("settings_service"))
            self._bridges["settings"] = bridge
            navigation = self._bridges.get("navigation")
            if navigation is not None:
                navigation.registerLeaveGuard("settings", bridge)

    def create_output_profiles_bridge(self):
        if "output_profiles" not in self._bridges:
            from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge
            self._bridges["output_profiles"] = OutputProfilesBridge(
                player_service=self._get("playback_service"),
            )

    def create_eq_bridge(self):
        if "eq" not in self._bridges:
            from ui_qml_bridge.eq_bridge import EqBridge
            self._bridges["eq"] = EqBridge(
                player_service=self._get("playback_service"),
            )

    def create_connections_bridge(self):
        if "connections" not in self._bridges:
            nav = self._bridges.get("navigation")
            if nav is None:
                self.create_navigation_bridge()
                nav = self._bridges["navigation"]
            from ui_qml_bridge.connections_bridge import ConnectionsBridge
            self._bridges["connections"] = ConnectionsBridge(
                connection_service=self._get("connection_service"),
                navigation_bridge=nav,
            )

    def create_home_audio_bridge(self):
        if "home_audio" not in self._bridges:
            nav = self._bridges.get("navigation")
            if nav is None:
                self.create_navigation_bridge()
                nav = self._bridges["navigation"]
            pss = self._bridges.get("page_state")
            if pss is None:
                self.create_page_state_store()
                pss = self._bridges["page_state"]
            cap = self._bridges.get("capability")
            if cap is None:
                self.create_capability_bridge()
                cap = self._bridges["capability"]
            acc = self._bridges.get("accessibility")
            if acc is None:
                self.create_accessibility_bridge()
                acc = self._bridges["accessibility"]
            notif = self._bridges.get("notification")
            if notif is None:
                self.create_notification_bridge()
                notif = self._bridges["notification"]
            from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
            self._bridges["home_audio"] = HomeAudioBridge(
                home_audio_service=self._get("home_audio_service"),
                job_service=self._get("job_service"),
                action_registry=self._bridges.get("action_registry"),
                navigation_bridge=nav,
                page_state_store=pss,
                capability_bridge=cap,
                accessibility_bridge=acc,
                notification_bridge=notif,
                worker_manager=self._get("worker_manager"),
            )

    def create_devices_bridge(self):
        if "devices" not in self._bridges:
            from ui_qml_bridge.devices_bridge import DevicesBridge
            self._bridges["devices"] = DevicesBridge(
                device_sync_service=self._get("device_sync_service"),
                job_service=self._get("job_service"),
                action_registry=self._bridges.get("action_registry"),
                confirmation_service=self._bridges.get("confirmation"),
                navigation_bridge=self._bridges.get("navigation"),
                capability_bridge=self._bridges.get("capability"),
                page_state_store=self._bridges.get("page_state"),
                accessibility_bridge=self._bridges.get("accessibility"),
            )

    def create_mobile_sync_bridge(self):
        if "mobile_sync" not in self._bridges:
            from ui_qml_bridge.mobile_sync_bridge import MobileSyncBridge
            self._bridges["mobile_sync"] = MobileSyncBridge(
                mobile_sync_service=self._get("mobile_sync_service"),
            )

    def create_radio_bridge(self):
        if "radio" not in self._bridges:
            from ui_qml_bridge.radio_bridge import RadioBridge
            self._bridges["radio"] = RadioBridge(
                radio_manager=self._get("radio_service"),
                player_service=self._get("playback_service"),
            )

    def create_audio_lab_bridge(self):
        if "audio_lab" not in self._bridges:
            from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
            self._bridges["audio_lab"] = AudioLabBridge(
                audio_lab_service=self._get("audio_lab_service"),
                job_service=self._get("job_service"),
                process_controller=self._get("process_controller"),
                confirmation_service=self._bridges.get("confirmation"),
                navigation_bridge=self._bridges.get("navigation"),
                capability_bridge=self._bridges.get("capability"),
                notification_bridge=self._bridges.get("notification"),
            )

    def create_metadata_bridge(self):
        if "metadata" not in self._bridges:
            from ui_qml_bridge.metadata_bridge import MetadataBridge
            self._bridges["metadata"] = MetadataBridge(
                metadata_service=self._get("metadata_service"),
                job_service=self._get("job_service"),
            )

    def create_smart_tagging_bridge(self):
        if "smart_tagging" not in self._bridges:
            from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
            self._bridges["smart_tagging"] = SmartTaggingBridge(
                service=self._get("smart_tagging_service"),
                worker_manager=self._get("worker_manager"),
                query_service=self._get("library_query_service"),
            )

    def create_disc_lab_bridge(self):
        if "disc_lab" not in self._bridges:
            from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
            self._bridges["disc_lab"] = DiscLabBridge(
                disc_detection_service=self._get("cd_ripper_service"),
                worker_manager=self._get("worker_manager"),
                process_controller=self._get("process_controller"),
            )

    def create_library_doctor_bridge(self):
        if "library_doctor" not in self._bridges:
            from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
            self._bridges["library_doctor"] = LibraryDoctorBridge(
                db=self._get("database"),
                worker_manager=self._get("worker_manager"),
            )

    def create_diagnostics_bridge(self):
        if "diagnostics" not in self._bridges:
            from ui_qml_bridge.diagnostics_bridge import DiagnosticsBridge
            self._bridges["diagnostics"] = DiagnosticsBridge(
                diagnostics_service=self._get("diagnostics_service"),
                player_service=self._get("playback_service"),
                worker_manager=self._get("worker_manager"),
                query_executor=self._get("query_executor"),
                library_bridge=self._bridges.get("library"),
            )

    def create_michi_ai_bridge(self):
        if "michi_ai" not in self._bridges:
            from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
            self._bridges["michi_ai"] = MichiAIBridge(
                michi_ai_service=self._get("michi_ai_service"),
                device_sync_service=self._get("device_sync_service"),
                job_service=self._get("job_service"),
                action_registry=self._bridges.get("action_registry"),
                confirmation_service=self._bridges.get("confirmation"),
                navigation_bridge=self._bridges.get("navigation"),
                capability_bridge=self._bridges.get("capability"),
                page_state_store=self._bridges.get("page_state"),
                accessibility_bridge=self._bridges.get("accessibility"),
            )

    def create_tagging_bridge(self):
        self.create_smart_tagging_bridge()

    def create_doctor_bridge(self):
        self.create_library_doctor_bridge()

    def create_action_registry_bridge(self):
        if "action_registry" not in self._bridges:
            from ui_qml_bridge.action_registry import ActionRegistry
            reg = self._get("action_registry")
            self._bridges["action_registry"] = reg if reg is not None else ActionRegistry()

    def create_notification_bridge(self):
        if "notification" not in self._bridges:
            from ui_qml_bridge.notification_bridge import NotificationBridge
            self._bridges["notification"] = NotificationBridge(
                action_registry=self._bridges.get("action_registry"),
                job_bridge=self._bridges.get("job_bridge"),
                notification_service=self._get("notification_service"),
                navigation_bridge=self._bridges.get("navigation"),
                diagnostics_service=self._get("diagnostics_service"),
            )

    def create_command_palette_bridge(self):
        if "command_palette" not in self._bridges:
            from ui_qml_bridge.command_palette_bridge import CommandPaletteBridge
            self._bridges["command_palette"] = CommandPaletteBridge(
                action_registry=self._bridges.get("action_registry"),
                navigation_bridge=self._bridges.get("navigation"),
                nowplaying_bridge=self.get("nowplaying"),
                capability_bridge=self._bridges.get("capability"),
                confirmation_bridge=self._bridges.get("confirmation"),
                page_state_store=self._bridges.get("page_state"),
            )

    def create_home_bridge(self):
        if "home" not in self._bridges:
            from ui_qml_bridge.home_bridge import HomeBridge
            self._bridges["home"] = HomeBridge(
                db=self._get("database"),
                player_service=self._get("playback_service"),
                library_bridge=self._bridges.get("library"),
                library_sources_service=self._get("library_sources_service"),
                job_bridge=self._bridges.get("job_bridge"),
                connections_bridge=self._bridges.get("connections"),
            )

    def create_app_bridge(self):
        if "app" not in self._bridges:
            from ui_qml_bridge.app_bridge import AppBridge
            self._bridges["app"] = AppBridge(
                worker_manager=self._get("worker_manager"),
                query_executor=self._get("query_executor"),
                player_service=self._get("playback_service"),
                queue_bridge=self._bridges.get("queue"),
                sync_manager=self._get("device_sync_service"),
                home_audio_controller=self._get("home_audio_service"),
                radio_manager=self._get("radio_service"),
                discovery=None,
                db=self._get("database"),
            )

    def create_desktop_bridge(self):
        if "desktop" not in self._bridges:
            from ui_qml_bridge.desktop_bridge import DesktopBridge
            self._bridges["desktop"] = DesktopBridge()

    def create_runtime_quality_bridge(self):
        if "runtime_quality" not in self._bridges:
            from ui_qml_bridge.runtime_quality_bridge import RuntimeQualityBridge
            self._bridges["runtime_quality"] = RuntimeQualityBridge()

    def create_physical_audio_bridge(self):
        if "physical_audio" not in self._bridges:
            from ui_qml_bridge.physical_audio_bridge import PhysicalAudioBridge
            self._bridges["physical_audio"] = PhysicalAudioBridge()

    def create_selection_context_bridge(self):
        if "selection_context" not in self._bridges:
            from ui_qml_bridge.selection_context_bridge import SelectionContextBridge
            self._bridges["selection_context"] = SelectionContextBridge()

    def create_cover_provider_bridge(self):
        if "cover_provider" not in self._bridges:
            from ui_qml_bridge.cover_provider_bridge import CoverProviderBridge
            self._bridges["cover_provider"] = CoverProviderBridge(
                artwork_service=self._get("artwork_service"),
            )

    def create_query_executor(self):
        if "query_executor" not in self._bridges:
            self._bridges["query_executor"] = self._container.require("query_executor")

    def create_app_state_bridge(self):
        if "app_state" not in self._bridges:
            from ui_qml_bridge.app_state_bridge import AppStateBridge
            self._bridges["app_state"] = AppStateBridge()

    def create_all(self) -> dict[str, QObject]:
        self._degraded.clear()

        # 1. Infraestructura
        self._try_create("page_state", self.create_page_state_store)
        self._try_create("route_registry", self.create_route_registry_bridge)
        self._try_create("navigation", self.create_navigation_bridge)
        self._try_create("job_bridge", self.create_job_bridge)
        self._try_create("confirmation", self.create_confirmation_bridge)
        self._try_create("accessibility", self.create_accessibility_bridge)
        self._try_create("theme", self.create_theme_bridge)
        self._try_create("capability", self.create_capability_bridge)
        self._try_create("action_registry", self.create_action_registry_bridge)

        # 2. Dominio
        self._try_create("playlists", self.create_playlists_bridge)
        self._try_create("library", self.create_library_bridge)
        self._try_create("library_sources", self.create_library_sources_bridge)
        self._try_create("cover_provider", self.create_cover_provider_bridge)
        self._try_create("nowplaying", self.create_nowplaying_bridge)
        self._try_create("queue", self.create_queue_bridge)
        self._try_create("history", self.create_history_bridge)
        self._try_create("global_search", self.create_search_bridge)
        self._try_create("mix", self.create_mix_bridge)
        self._try_create("lyrics", self.create_lyrics_bridge)
        self._try_create("settings", self.create_settings_bridge)
        self._try_create("output_profiles", self.create_output_profiles_bridge)
        self._try_create("eq", self.create_eq_bridge)
        self._try_create("connections", self.create_connections_bridge)
        self._try_create("home_audio", self.create_home_audio_bridge)
        self._try_create("devices", self.create_devices_bridge)
        self._try_create("mobile_sync", self.create_mobile_sync_bridge)
        self._try_create("radio", self.create_radio_bridge)
        self._try_create("audio_lab", self.create_audio_lab_bridge)
        self._try_create("metadata", self.create_metadata_bridge)
        self._try_create("disc_lab", self.create_disc_lab_bridge)
        self._try_create("smart_tagging", self.create_smart_tagging_bridge)
        self._try_create("library_doctor", self.create_library_doctor_bridge)
        self._try_create("diagnostics", self.create_diagnostics_bridge)
        self._try_create("michi_ai", self.create_michi_ai_bridge)

        # 3. Agregadores
        self._try_create("command_palette", self.create_command_palette_bridge)
        self._try_create("home", self.create_home_bridge)
        self._try_create("app", self.create_app_bridge)
        self._try_create("desktop", self.create_desktop_bridge)

        self._try_create("runtime_quality", self.create_runtime_quality_bridge)
        self._try_create("physical_audio", self.create_physical_audio_bridge)
        self._try_create("app_state", self.create_app_state_bridge)
        self._try_create("selection_context", self.create_selection_context_bridge)
        self._try_create("query_executor", self.create_query_executor)

        # All bridges created — inject cross-bridge dependencies that were None
        # at construction time (Corrección 3, two-phase wiring).
        self._wire_bridges()

        capability = self._bridges.get("capability")
        if capability and hasattr(capability, 'refresh'):
            capability.refresh()

        self.bind_action_handlers()

        self._validate_bridge_identities()
        self._assert_wiring()
        self.validate_all_bridges()
        return self._bridges

    def _wire_bridges(self) -> None:
        """Second-phase wiring for cross-bridge dependencies (Corrección 3).

        Bridges reference each other through ``self._bridges.get("x")`` at
        construction time, but creation order means some of those references are
        legitimately ``None`` when the bridge is built (e.g. ``action_registry``
        and ``cover_provider`` are created after the bridges that need them, and
        ``notification`` is created lazily). This pass runs once *all* bridges
        exist and injects the real dependency through a public setter, so no
        bridge advertises a missing required reference at runtime.
        """
        # ConfirmationBridge needs ActionRegistry (created after confirmation).
        conf = self._bridges.get("confirmation")
        ar = self._bridges.get("action_registry")
        if conf is not None and ar is not None and hasattr(conf, "set_action_registry"):
            conf.set_action_registry(ar)

        # LibraryBridge needs CoverProvider (created after library).
        lib = self._bridges.get("library")
        cp = self._bridges.get("cover_provider")
        if lib is not None and cp is not None and hasattr(lib, "set_cover_provider"):
            lib.set_cover_provider(cp)

        # Playlists/History/GlobalSearch need NotificationBridge (created lazily
        # by home_audio, i.e. after these three).
        nb = self._bridges.get("notification")
        for name in ("playlists", "history", "global_search"):
            br = self._bridges.get(name)
            if br is not None and nb is not None and hasattr(br, "set_notification_bridge"):
                br.set_notification_bridge(nb)

        # JobBridge needs LibraryBridge (created after job_bridge) to refresh
        # the library view when a scan job completes.
        jb = self._bridges.get("job_bridge")
        lib = self._bridges.get("library")
        if jb is not None and lib is not None and hasattr(jb, "set_library_bridge"):
            jb.set_library_bridge(lib)

    def _validate_bridge_identities(self):
        keys = set(self._bridges.keys())
        missing = [k for k in QML_CONTEXT_BINDINGS.values() if k not in keys]
        if missing:
            logger.warning("BridgeFactory: missing context bindings: %s", missing)

    def _assert_wiring(self):
        container = self._container
        factory = self

        reg = factory._bridges.get("action_registry")
        if reg is not None and container.contains("action_registry"):
            container_reg = container.require("action_registry")
            if reg is not container_reg:
                raise RuntimeError("action_registry identity mismatch")

        qb = factory._bridges.get("queue")
        if (
            qb is not None
            and qb._queue_service is not container.require("queue_service")
        ):
            raise RuntimeError("queue_bridge.queue_service identity mismatch")

        sb = factory._bridges.get("settings")
        if sb is not None and sb._svc is not container.require("settings_service"):
            raise RuntimeError("settings_bridge.service identity mismatch")

        plb = factory._bridges.get("playlists")
        if plb is not None:
            container_svc = container.require("playlist_service")
            if plb._svc is not container_svc:
                raise RuntimeError("playlists_bridge.playlist_service identity mismatch")

        search = factory._bridges.get("global_search")
        if (
            search is not None
            and search._svc is not container.require("global_search_service")
        ):
            raise RuntimeError("search_bridge.search_service identity mismatch")

        mix = factory._bridges.get("mix")
        if mix is not None and mix._mix_svc is not container.require("mix_service"):
            raise RuntimeError("mix_bridge.mix_service identity mismatch")

        ai = factory._bridges.get("michi_ai")
        if (
            ai is not None
            and container.contains("action_registry")
            and ai._registry is not container.require("action_registry")
        ):
            raise RuntimeError("ai_bridge.action_registry identity mismatch")

        np = factory._bridges.get("nowplaying")
        cp = factory._bridges.get("cover_provider")
        if np and cp and hasattr(np, "_cover_provider"):
            assert np._cover_provider is cp, "NowPlayingBridge.cover_provider wiring mismatch"

    def bind_action_handlers(self):
        registry = self._bridges.get("action_registry")
        if not registry:
            return
        from ui_qml_bridge.action_registry_binder import ActionRegistryBinder
        binder = ActionRegistryBinder(registry, self._bridges)
        binder.bind_all()

    def __repr__(self) -> str:
        return f"BridgeFactory(bridges={len(self._bridges)})"


def create_all_bridges(container: ServiceContainer) -> dict[str, QObject]:
    factory = BridgeFactory(container)
    return factory.create_all()
