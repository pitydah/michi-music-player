"""Player-owned lifetime for the Michi Ecosystem control plane (E14).

The Ecosystem package owns Home, Registry, Discovery, Stream, Micro, Link,
Mobile, Spaces, diagnostics and Home Assistant.  This host only exposes those
surfaces through the single Player navigation authority and never creates a
second playback, queue, DAC, DSP or Signal Truth authority.
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from michi_ecosystem.infrastructure.michi_link.transport import (
    CompositeDiscoverySource,
    UdpDiscoverySource,
)
from michi_ecosystem.infrastructure.micro_server.client import MicroServerClient
from michi_ecosystem.integration.coupling import (
    HOST_API_VERSION,
    EcosystemCouplingKit,
)
from michi_ecosystem.integration.player_host import (
    CONTEXT_PROPERTIES,
    apply_page_model,
    connect_page_navigation,
    register_player_routes,
    route_errors,
)


class EcosystemIntegrationError(RuntimeError):
    """The host cannot safely expose an Ecosystem surface."""


class PlayerEcosystemDashboard:
    """Minimal host dashboard; canonical registry data is overlaid by Ecosystem."""

    def dashboard_snapshot(self) -> dict[str, Any]:
        return {"health": {"state": "unknown"}, "discovery": {"state": "stopped"}}


class DiscoveryControl:
    """Objects used by the QML operations bridge; manual lifecycle only."""

    def __init__(self, runtime: object) -> None:
        self._runtime = runtime

    def _availability(self) -> Mapping[str, Any]:
        value = getattr(self._runtime, "availability", None)
        if not callable(value):
            return {}
        try:
            result = value()
        except Exception:
            return {}
        return result if isinstance(result, Mapping) else {}

    @property
    def available(self) -> bool:
        discovery = self._availability().get("discovery", {})
        if not isinstance(discovery, Mapping):
            return False
        return bool(discovery.get("available", False))

    @property
    def running(self) -> bool:
        discovery = self._availability().get("discovery", {})
        if not isinstance(discovery, Mapping):
            return False
        return bool(discovery.get("running", False))

    @property
    def state(self) -> str:
        if not self.available:
            return "unavailable"
        return "running" if self.running else "stopped"

    @property
    def health(self) -> dict[str, Any]:
        discovery = self._availability().get("discovery", {})
        health = discovery.get("health") if isinstance(discovery, Mapping) else None
        return dict(health) if isinstance(health, Mapping) else {}

    def start(self) -> bool:
        start = getattr(self._runtime, "start", None)
        return bool(start()) if callable(start) else False

    def stop(self) -> bool:
        runner = getattr(self._runtime, "discovery_runner", None)
        stop = getattr(runner, "stop", None)
        if not callable(stop):
            return True
        stop()
        return not self.running


def _default_factory() -> object:
    """Build the real firmware/SDK adapters; no fake product adapters."""
    from michi_ecosystem.composition import FactoryEnvironment
    from michi_ecosystem.infrastructure.flashing.esptool_backend import (
        EsptoolBackend,
    )
    from michi_ecosystem.infrastructure.flashing.firmware_catalog import (
        LocalFirmwareCatalog,
    )
    from michi_ecosystem.infrastructure.flashing.installation_detector import (
        EspInstallationDetector,
    )
    from michi_ecosystem.infrastructure.flashing.serial_port_scanner import (
        PyserialScanner,
    )

    firmware_root = os.environ.get("MICHI_FIRMWARE_DIR", "").strip()
    backend = EsptoolBackend()
    return FactoryEnvironment(
        serial=PyserialScanner(),
        catalog=LocalFirmwareCatalog(Path(firmware_root) if firmware_root else None),
        backend=backend,
        installation_detector=EspInstallationDetector(backend),
    )


class EcosystemPlayerHost:
    """One owner for Ecosystem construction, routes, QML context and close."""

    def __init__(
        self,
        *,
        dashboard_service: object | None = None,
        player_qml_root: Path,
        state_root: Path,
        factory: object | None = None,
        discovery_source: object | None = None,
        micro_client: object | None = None,
        home_automation: object | None = None,
        home_automation_settings: object | None = None,
    ) -> None:
        from PySide6.QtGui import QGuiApplication

        if QGuiApplication.instance() is None:
            raise EcosystemIntegrationError(
                "Build Ecosystem only after QGuiApplication has been created"
            )
        if HOST_API_VERSION != 1:
            raise EcosystemIntegrationError(
                f"Unsupported Ecosystem host API version: {HOST_API_VERSION}"
            )

        self.player_qml_root = Path(player_qml_root).resolve()
        self._ecosystem_pages = self.player_qml_root / "ecosystem"
        errors = route_errors(self._ecosystem_pages, self.player_qml_root)
        if errors:
            raise EcosystemIntegrationError("QML preflight: " + "; ".join(errors))

        self._state_root = Path(state_root).resolve()
        self._state_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if os.name == "posix":
            self._state_root.chmod(0o700)

        configured_micro = micro_client
        if configured_micro is None:
            micro_url = os.environ.get("MICHI_MICRO_SERVER_URL", "").strip()
            if micro_url:
                configured_micro = MicroServerClient(micro_url)

        self._dashboard_service = (
            dashboard_service
            if dashboard_service is not None
            else PlayerEcosystemDashboard()
        )
        self._kit = EcosystemCouplingKit(
            dashboard_service=self._dashboard_service,
            factory=factory if factory is not None else _default_factory(),
            home_state_dir=self._state_root / "home",
            account_state_dir=self._state_root / "account",
            discovery_source=(
                discovery_source
                if discovery_source is not None
                else CompositeDiscoverySource(udp=UdpDiscoverySource())
            ),
            micro_client=configured_micro,
            home_automation=home_automation,
            home_automation_settings=home_automation_settings,
        )
        self._discovery = DiscoveryControl(self._kit.runtime)
        self._closed = False
        self._registered_routes: tuple[str, ...] = ()
        self._apply_model: Callable[[str, dict[str, Any]], None] | None = None
        self._cards_changed: object | None = None

    @property
    def runtime(self) -> object:
        return self._kit.runtime

    @property
    def registered_routes(self) -> tuple[str, ...]:
        return self._registered_routes

    @property
    def discovery(self) -> DiscoveryControl:
        return self._discovery

    def bind(self, root_context: object) -> tuple[str, ...]:
        """Publish exactly the seven QML properties required by Ecosystem."""
        if self._closed:
            raise EcosystemIntegrationError("Ecosystem runtime already closed")
        self._kit.bind(root_context)
        return CONTEXT_PROPERTIES

    def register_routes(self, register: Callable[[str, str], None]) -> tuple[str, ...]:
        """Register the 14 validated routes into the Player navigation bridge."""
        if self._closed:
            raise EcosystemIntegrationError("Ecosystem runtime already closed")

        def register_url(route_id: str, source: Path) -> None:
            # QML Loader consumes a URL; NavigationBridge owns the string map.
            register(route_id, Path(source).resolve().as_uri())

        routes = register_player_routes(
            register_url, self._ecosystem_pages, player_qml=self.player_qml_root
        )
        self._registered_routes = routes
        return routes

    def connect_navigation(self, navigate: Callable[[str], None]) -> None:
        if self._closed:
            raise EcosystemIntegrationError("Ecosystem runtime already closed")
        self._kit.connect_navigation(navigate)
        operations = getattr(self._kit.runtime, "operations_bridge", None)
        attach = getattr(operations, "attach_discovery", None)
        if callable(attach):
            attach(self._discovery)

    def connect_models(
        self, apply_model: Callable[[str, dict[str, Any]], None]
    ) -> None:
        """Publish the three detail-page models through the Player bridge."""
        if self._closed:
            raise EcosystemIntegrationError("Ecosystem runtime already closed")
        self._apply_model = apply_model
        cards_changed = getattr(
            self._kit.runtime.ecosystem_bridge, "cards_changed", None
        )
        if cards_changed is not None:
            cards_changed.connect(self.refresh_models)
        self.refresh_models()

    def refresh_models(self) -> None:
        """Project canonical dashboard state into the detail-page models."""
        if self._closed or self._apply_model is None:
            return
        try:
            snapshot = self._dashboard_service.dashboard_snapshot()
            if not isinstance(snapshot, Mapping):
                snapshot = {}
            models = self._detail_models(snapshot)
        except Exception:
            return
        for route_id, model in models.items():
            try:
                self._apply_model(route_id, model)
            except Exception:
                continue

    def _detail_models(self, snapshot: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        from michi_ecosystem.domain.device_registry import DeviceType

        registry = self._kit.runtime.device_registry
        micro = self._runtime_model(registry, DeviceType.MICRO_SERVER)
        servers = snapshot.get("servers")
        micro_snapshot = servers.get("micro") if isinstance(servers, Mapping) else None
        if isinstance(micro_snapshot, Mapping):
            services = micro_snapshot.get("services")
            services = services if isinstance(services, Mapping) else {}
            micro.update(
                {
                    "name": micro_snapshot.get("name", micro.get("name", "")),
                    "platform": micro_snapshot.get(
                        "platform", micro.get("platform", "")
                    ),
                    "online": micro_snapshot.get("presence", "") == "online",
                    "apiReady": bool(services.get("api", False)),
                    "streamingReady": bool(services.get("streaming", False)),
                    "linkReady": bool(services.get("michi_link", False)),
                }
            )
        micro.setdefault("name", "Michi Micro Server")
        micro.setdefault("platform", "")
        micro.setdefault("online", False)
        micro.setdefault("apiReady", False)
        micro.setdefault("streamingReady", False)
        micro.setdefault("linkReady", False)

        link = snapshot.get("link")
        link_model = dict(link) if isinstance(link, Mapping) else {}
        state = str(link_model.get("state", "unknown"))
        link_model["status"] = {
            "operational": "Operativo",
            "degraded": "Con incidencias",
            "offline": "Sin conexión",
        }.get(state, "Sin datos")
        link_model["tone"] = {
            "operational": "success",
            "degraded": "warning",
            "offline": "error",
        }.get(state, "neutral")

        mobile = self._runtime_model(registry, DeviceType.MOBILE)
        mobile_snapshot = snapshot.get("mobile")
        if not mobile and isinstance(mobile_snapshot, Mapping):
            mobile = dict(mobile_snapshot)
        return {
            "ecosystem/micro-server": micro,
            "ecosystem/michi-link": link_model,
            "ecosystem/mobile": mobile,
        }

    @staticmethod
    def _runtime_model(registry: object, device_type: object) -> dict[str, Any]:
        by_type = getattr(registry, "by_type", None)
        projection = getattr(registry, "ecosystem_projection", None)
        if not callable(by_type) or not callable(projection):
            return {}
        for device in by_type(device_type):
            model = projection(device.canonical_id)
            if isinstance(model, Mapping):
                return dict(model)
        return {}

    def connect_page(self, page: object, navigate: Callable[[str], None]) -> bool:
        return connect_page_navigation(page, navigate)

    def apply_page_model(
        self, page: object, route_id: str, model: dict[str, Any]
    ) -> tuple[str, ...]:
        return apply_page_model(page, route_id, model)

    def availability(self) -> dict[str, object]:
        return self._kit.availability()

    def close(self, *, force: bool = False, timeout: float = 5.0) -> None:
        """Stop manual discovery first, then close every owned adapter."""
        if self._closed:
            return
        if self._cards_changed is not None:
            with contextlib.suppress(RuntimeError, TypeError):
                self._cards_changed.disconnect(self.refresh_models)
            self._cards_changed = None
        if self._discovery.running:
            self._discovery.stop()
        if force:
            self._kit.runtime.close(force=True, timeout=timeout)
        else:
            self._kit.close(timeout=timeout)
        self._closed = True
