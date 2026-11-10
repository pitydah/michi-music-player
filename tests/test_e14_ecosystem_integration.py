"""E14 Player/Ecosystem integration contracts.

These are software integration checks: route ownership, the copied QML
surface, the host seam and manual-only discovery. They do not prove a live
KWin session, real USB hardware or physical DAC behavior.
"""

from __future__ import annotations

import os
import re
import tomllib
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from michi.application.navigation_service import ECOSYSTEM_ROUTE_IDS, NavigationService
from michi.domain.navigation import AppRoute, NavigationState
from michi.integration.ecosystem_host import (
    EcosystemIntegrationError,
    EcosystemPlayerHost,
)
from michi.presentation.navigation_bridge import NavigationBridge
from michi_ecosystem.application.device_registry_service import DeviceSource
from michi_ecosystem.application.discovery_runner import DiscoveryRunner
from michi_ecosystem.composition import FactoryEnvironment
from michi_ecosystem.domain.device_registry import (
    DeviceDescriptor,
    DeviceType,
    HomeMembershipState,
    canonical_id_for,
)
from michi_ecosystem.infrastructure.michi_link.contracts import load_bundle
from michi_ecosystem.integration.player_host import (
    CONTEXT_PROPERTIES,
    PAGE_ROUTES,
    route_errors,
    route_manifest,
)
from michi_ecosystem.integration.player_navigation_contract import (
    player_navigation_errors,
)
from michi_ecosystem.ports.installation_detector import (
    InstallationEvidence,
    InstallationReport,
)

ROOT = Path(__file__).resolve().parents[1]
PLAYER_QML = ROOT / "src/michi/presentation/qml"


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])
    yield app


ECOSYSTEM_QML = PLAYER_QML / "ecosystem"


class _Dashboard:
    def dashboard_snapshot(self) -> dict:
        return {"discovery": {"state": "idle"}}


class _DetailDashboard:
    def dashboard_snapshot(self) -> dict:
        return {
            "servers": {
                "micro": {
                    "name": "Sala",
                    "presence": "online",
                    "services": {"api": True, "streaming": True, "michi_link": False},
                }
            },
            "link": {"state": "degraded", "nodes": 3, "links": 2, "incidents": 1},
            "mobile": {"name": "Teléfono", "online": True, "version": "2.0"},
        }


class _Scanner:
    def scan(self):
        return ()

    def port_still_present(self, port: str) -> bool:
        return False


class _Catalog:
    def load(self, reference: str):
        raise KeyError(reference)


class _Backend:
    def probe_chip(self, port: str):
        return None

    def read_device_identity(self, port: str):
        return None

    def erase_flash(self, port: str) -> None:
        raise AssertionError("not used")

    def write_segment(self, port: str, offset: int, payload: bytes) -> None:
        raise AssertionError("not used")

    def verify_segment(
        self, port: str, offset: int, size: int, expected_sha256: str
    ) -> bool:
        return False

    def hard_reset(self, port: str) -> None:
        raise AssertionError("not used")


class _Detector:
    def inspect(self, port: str) -> InstallationReport:
        return InstallationReport(InstallationEvidence.BLANK, "fake")


class _Discovery:
    def __init__(self) -> None:
        self.started = False
        self.closed = False

    def start(self) -> None:
        self.started = True

    def poll(self):
        return ()

    def close(self) -> None:
        self.closed = True


class _Context:
    def __init__(self) -> None:
        self.values: dict[str, object] = {}

    def setContextProperty(self, name: str, value: object) -> None:  # noqa: N802
        self.values[name] = value


def _factory() -> FactoryEnvironment:
    return FactoryEnvironment(
        serial=_Scanner(),
        catalog=_Catalog(),
        backend=_Backend(),
        installation_detector=_Detector(),
    )


def _host(
    tmp_path: Path, discovery: _Discovery, dashboard: object | None = None
) -> EcosystemPlayerHost:
    return EcosystemPlayerHost(
        dashboard_service=dashboard or _Dashboard(),
        player_qml_root=PLAYER_QML,
        state_root=tmp_path / "ecosystem",
        factory=_factory(),
        discovery_source=discovery,
    )


def test_navigation_state_owns_the_ecosystem_subroute():
    state = NavigationState()
    assert state.ecosystem_route == "ecosystem"

    service = NavigationService()
    seen: list[str] = []
    service.subscribe_changed(lambda: seen.append(service.state.ecosystem_route))

    for route_id in sorted(ECOSYSTEM_ROUTE_IDS):
        service.navigate(route_id)
        assert service.state.current_route is AppRoute.ECOSYSTEM
        assert service.state.ecosystem_route == route_id
        assert service.state.playlist_id is None

    assert seen == sorted(ECOSYSTEM_ROUTE_IDS)
    assert len(PAGE_ROUTES) == len(ECOSYSTEM_ROUTE_IDS) == 14


def test_leaving_ecosystem_resets_the_stale_subroute():
    service = NavigationService()
    service.navigate("ecosystem/discovery")
    service.navigate("library")
    assert service.state.ecosystem_route == "ecosystem"

    service.navigate("ecosystem")
    assert service.state.current_route is AppRoute.ECOSYSTEM
    assert service.state.ecosystem_route == "ecosystem"


def test_bridge_publishes_pages_and_detail_models():
    service = NavigationService()
    bridge = NavigationBridge(service)
    bridge.register_ecosystem_route(
        "ecosystem/discovery", "discovery/DiscoveryPage.qml"
    )
    bridge.register_ecosystem_route(
        "ecosystem/micro-server", "micro/MicroServerPage.qml"
    )

    service.navigate("ecosystem/discovery")
    assert bridge.ecosystemRoute == "ecosystem/discovery"
    assert bridge.ecosystemPageSource == "discovery/DiscoveryPage.qml"

    service.navigate("ecosystem/micro-server")
    bridge.set_ecosystem_model("ecosystem/micro-server", {"name": "local"})
    assert bridge.ecosystemServer == {"name": "local"}
    assert bridge.ecosystemPageSource == "micro/MicroServerPage.qml"

    service.navigate("library")
    assert bridge.ecosystemRoute == "ecosystem"


def test_player_navigation_contract_and_route_assets_are_complete():
    assert player_navigation_errors(ROOT) == ()
    assert route_errors(ECOSYSTEM_QML, PLAYER_QML) == ()
    manifest = route_manifest()
    assert len(manifest) == 14
    assert {entry["routeId"] for entry in manifest} == set(ECOSYSTEM_ROUTE_IDS)


def test_host_registers_routes_binds_seven_properties_and_starts_stopped(
    qapp, tmp_path: Path
):
    discovery = _Discovery()
    host = _host(tmp_path, discovery)
    try:
        context = _Context()
        host.bind(context)
        assert set(context.values) == set(CONTEXT_PROPERTIES)
        assert len(context.values) == 7

        registered: dict[str, str] = {}

        def record(route_id: str, source: str) -> None:
            registered[route_id] = source

        host.register_routes(record)
        assert set(registered) == set(ECOSYSTEM_ROUTE_IDS)
        assert all(source.startswith("file://") for source in registered.values())

        assert host.discovery.available is True
        assert host.discovery.running is False
        assert discovery.started is False
        assert discovery.closed is False

        assert host.discovery.start() is True
        assert host.discovery.running is True
        assert discovery.started is True

        assert host.discovery.stop() is True
        assert host.discovery.running is False
    finally:
        host.close(force=True)

    assert discovery.closed is True


def _ingest_device(
    host: EcosystemPlayerHost, device_type: DeviceType, michi_id: str, name: str
) -> str:
    canonical_id = canonical_id_for(michi_id=michi_id)
    host.runtime.device_registry.ingest(
        DeviceSource.HOME_ROSTER,
        DeviceDescriptor(
            canonical_id=canonical_id,
            michi_id=michi_id,
            michi_home_id="home-1",
            home_membership=HomeMembershipState.ACTIVE,
            name=name,
            type=device_type,
            online=True,
        ),
    )
    return canonical_id


def test_host_publishes_only_the_selected_canonical_devices(qapp, tmp_path: Path):
    host = _host(tmp_path, _Discovery(), _DetailDashboard())
    published: dict[str, dict] = {}
    try:
        first_mobile = _ingest_device(
            host, DeviceType.MOBILE, "michi-mobile-1", "Teléfono 1"
        )
        second_mobile = _ingest_device(
            host, DeviceType.MOBILE, "michi-mobile-2", "Teléfono 2"
        )
        first_server = _ingest_device(
            host, DeviceType.MICRO_SERVER, "michi-server-1", "Servidor 1"
        )
        second_server = _ingest_device(
            host, DeviceType.MICRO_SERVER, "michi-server-2", "Servidor 2"
        )
        host.connect_models(
            lambda route_id, model: published.__setitem__(route_id, model)
        )
        operations = host.runtime.operations_bridge

        operations.openDevice(second_mobile)
        assert published["ecosystem/mobile"]["canonicalId"] == second_mobile
        assert published["ecosystem/mobile"]["name"] == "Teléfono 2"

        operations.openDevice(first_mobile)
        assert published["ecosystem/mobile"]["canonicalId"] == first_mobile
        assert published["ecosystem/mobile"]["name"] == "Teléfono 1"

        operations.openDevice(second_server)
        assert published["ecosystem/micro-server"]["canonicalId"] == second_server
        assert published["ecosystem/micro-server"]["name"] == "Servidor 2"
        assert published["ecosystem/micro-server"]["online"] is True

        operations.openDevice(first_server)
        assert published["ecosystem/micro-server"]["canonicalId"] == first_server
        assert published["ecosystem/micro-server"]["name"] == "Servidor 1"
        assert published["ecosystem/michi-link"]["status"] == "Con incidencias"
        assert published["ecosystem/michi-link"]["tone"] == "warning"

        host.runtime.device_registry.remove_evidence(
            DeviceSource.HOME_ROSTER, first_mobile
        )
        operations.openDevice(first_mobile)
        assert published["ecosystem/mobile"] == {}
    finally:
        host.close(force=True)


def test_host_rejects_a_missing_qml_surface(qapp, tmp_path: Path):
    with pytest.raises(EcosystemIntegrationError):
        EcosystemPlayerHost(
            dashboard_service=_Dashboard(),
            player_qml_root=tmp_path / "missing",
            state_root=tmp_path / "state",
            factory=_factory(),
            discovery_source=_Discovery(),
        )


def test_mobile_revoke_is_consumed_by_the_home_authority() -> None:
    content = (ROOT / "src/michi/presentation/qml/shell/ContentHost.qml").read_text()
    mobile = (
        ROOT / "src/michi/presentation/qml/ecosystem/mobile/MobileDetailPage.qml"
    ).read_text()
    micro = (
        ROOT / "src/michi/presentation/qml/ecosystem/micro/MicroServerDetailPage.qml"
    ).read_text()
    assert "item.revokeRequested.connect" in content
    assert "home.revokeDevice(canonicalId" in content
    assert "primaryEnabled: false" in mobile
    assert "secondaryEnabled: false" in mobile
    assert "dangerEnabled: homeCanAdminister" in mobile
    assert "AirCat conservan sus propias reglas" in mobile
    assert "primaryEnabled: false" in micro
    assert "Michi Control todavía no está disponible" in micro


def test_micro_client_receives_the_packaged_contract_bundle():
    bundle = load_bundle()
    assert bundle.schema_count >= 60
    client, status = EcosystemPlayerHost._build_micro_client("http://micro.local:8080")
    assert client._contracts is not None
    assert client._contracts.root == bundle.root
    assert client._contracts.version == bundle.version
    assert client._contracts.schema_count == bundle.schema_count
    assert status == {
        "state": "validated",
        "version": bundle.version,
        "upstream_commit": bundle.upstream_commit,
        "schema_count": bundle.schema_count,
    }


def test_invalid_micro_bundle_degrades_without_claiming_conformance(
    qapp, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("MICHI_MICRO_SERVER_URL", "http://micro.local:8080")

    def reject(_url: str):
        raise RuntimeError("bundle mismatch")

    monkeypatch.setattr(
        EcosystemPlayerHost, "_build_micro_client", staticmethod(reject)
    )
    host = _host(tmp_path, _Discovery())
    try:
        assert host.micro_contract_status == {
            "state": "invalid_bundle",
            "reason": "RuntimeError",
        }

    finally:
        host.close(force=True)


def test_integration_has_no_timer_polling_or_second_playback_authority():
    host_source = (ROOT / "src/michi/integration/ecosystem_host.py").read_text()
    assert "QTimer" not in host_source
    assert "AudioEngine" not in host_source
    assert "PlaybackService" not in host_source

    discovery_page = (ECOSYSTEM_QML / "discovery/DiscoveryPage.qml").read_text()
    assert "Buscar ahora" in discovery_page
    assert "Detener búsqueda" in discovery_page
    assert "startDiscovery" in discovery_page
    assert "stopDiscovery" in discovery_page
    assert "QTimer" not in discovery_page


def test_package_data_includes_ecosystem_runtime_and_qml():
    with (ROOT / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    package_data = data["tool"]["setuptools"]["package-data"]
    michi_globs = package_data["michi"]
    assert "presentation/qml/ecosystem/*.qml" in michi_globs
    assert "presentation/qml/ecosystem/*/*.qml" in michi_globs

    ecosystem_globs = package_data["michi_ecosystem"]
    assert "ECOSYSTEM_HOST_COMPATIBILITY.json" in ecosystem_globs
    assert "qml/ecosystem/*.qml" in ecosystem_globs
    assert "qml/ecosystem/*/*.qml" in ecosystem_globs


def test_manual_discovery_runner_is_the_lifecycle_owner():
    runner = DiscoveryRunner
    assert hasattr(runner, "start")
    assert hasattr(runner, "stop")
    host_source = (ROOT / "src/michi/integration/ecosystem_host.py").read_text()
    assert "discovery_runner" in host_source
    assert 'getattr(runner, "stop", None)' in host_source
    assert "stop()" in host_source


def test_content_host_keeps_the_loader_index_and_sidebar_route_aligned():
    content_host = (PLAYER_QML / "shell/ContentHost.qml").read_text()
    assert 'objectName: "ecosystemContentLoader"' in content_host
    assert re.search(r'case "ecosystem":\s+return 4', content_host)
    assert re.search(r'case "playlists":\s+return 5', content_host)
    assert "navigation.ecosystemPageSource" in content_host

    sidebar = (PLAYER_QML / "shell/Sidebar.qml").read_text()
    assert 'id: "ecosystem"' in sidebar

    app_shell = (PLAYER_QML / "shell/AppShell.qml").read_text()
    assert 'objectName: "contentHost"' in app_shell
