"""E12 Player host seam: deterministic QML routes and context properties.

This module contains no navigation authority.  The Player supplies the page
registrar and navigator; Michi Ecosystem supplies only validated route assets
and runtime-owned QObject bridges.  Nothing here starts playback, Factory,
OTA, AirCat or network discovery.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class PageRoute:
    route_id: str
    relative_qml: str
    #: Context properties the page reads directly (must be non-null).
    required_bridges: tuple[str, ...] = ()
    #: Context properties the page tolerates as null.
    optional_bridges: tuple[str, ...] = ()
    #: Host-injected model property (selected device/server projection).
    model_property: str = ""
    #: Route for the back affordance; empty means "root page".
    return_route: str = "ecosystem"


# Explicit route manifest: do not assume a page exists because a card emits
# a navigation signal.  The separate Michi Devices navigation is host-owned.
PAGE_ROUTES: tuple[PageRoute, ...] = (
    PageRoute("ecosystem", "EcosystemPage.qml", ("ecosystem",), return_route=""),
    PageRoute("ecosystem/home", "home/HomePage.qml", ("home",)),
    PageRoute(
        "ecosystem/diagnostics",
        "diagnostics/DiagnosticsPage.qml",
        ("ecosystemOperations",),
    ),
    PageRoute("ecosystem/spaces", "spaces/SpacesPage.qml", ("ecosystemOperations",)),
    PageRoute(
        "ecosystem/devices",
        "devices/DeviceLifecyclePage.qml",
        ("ecosystemOperations",),
    ),
    PageRoute(
        "ecosystem/discovery",
        "discovery/DiscoveryPage.qml",
        ("ecosystemOperations",),
    ),
    PageRoute("ecosystem/streams", "stream/StreamDetailPage.qml", ("streamDevice",)),
    PageRoute(
        "ecosystem/micro-server",
        "micro/MicroServerDetailPage.qml",
        model_property="server",
    ),
    PageRoute(
        "ecosystem/michi-link",
        "link/MichiLinkDetailPage.qml",
        model_property="linkState",
    ),
    PageRoute(
        "ecosystem/mobile",
        "mobile/MobileDetailPage.qml",
        model_property="mobile",
    ),
    PageRoute(
        "ecosystem/account",
        "account/LocalAccountPage.qml",
        ("localAccount",),
        ("home",),
    ),
    PageRoute(
        "ecosystem/integrations",
        "integrations/IntegrationsPage.qml",
        ("ecosystem",),
    ),
    PageRoute(
        "ecosystem/integrations/home-assistant",
        "integrations/HomeAssistantPage.qml",
        ("homeAssistant",),
        ("home",),
    ),
    PageRoute(
        "ecosystem/music-stream/create",
        "factory/StreamFactoryWizard.qml",
        ("streamFactory",),
    ),
)

# These route IDs are not supplied by the Ecosystem incubator.
EXTERNAL_ROUTES: tuple[str, ...] = ("devices", "devices/mobile")

# Detail pages take a model property from the host (never a bridge singleton):
# the Player selects the device and injects its runtime projection. Derived
# from the canonical route manifest so both can never drift.
PAGE_MODEL_PROPERTIES: Mapping[str, str] = {
    route.route_id: route.model_property
    for route in PAGE_ROUTES
    if route.model_property
}


def route_manifest() -> tuple[dict[str, object], ...]:
    """Canonical route manifest consumed by hosts, docs and tests."""
    return tuple(
        {
            "routeId": route.route_id,
            "qml": route.relative_qml,
            "requiredBridges": list(route.required_bridges),
            "optionalBridges": list(route.optional_bridges),
            "modelProperty": route.model_property,
            "returnRoute": route.return_route,
        }
        for route in PAGE_ROUTES
    )


def routes_requiring(bridge: str) -> tuple[str, ...]:
    """Route IDs that need a given context property (nullability contract)."""
    return tuple(
        route.route_id for route in PAGE_ROUTES if bridge in route.required_bridges
    )


CONTEXT_PROPERTIES: tuple[str, ...] = (
    "ecosystem",
    "streamFactory",
    "home",
    "localAccount",
    "streamDevice",
    "homeAssistant",
    "ecosystemOperations",
)

_CONTEXT_ATTRIBUTES = (
    ("ecosystem", "ecosystem_bridge"),
    ("streamFactory", "factory.bridge"),
    ("home", "home_bridge"),
    ("localAccount", "account_bridge"),
    ("streamDevice", "stream_bridge"),
    ("homeAssistant", "home_assistant_bridge"),
    ("ecosystemOperations", "operations_bridge"),
)


class QmlContextPort(Protocol):
    def setContextProperty(self, name: str, value: object) -> None: ...  # noqa: N802 (Qt API name)


def _attribute(obj: object, path: str) -> object | None:
    for segment in path.split("."):
        obj = getattr(obj, segment, None)
        if obj is None:
            return None
    return obj


def bind_player_context(context: QmlContextPort, runtime: object) -> None:
    """Bind the E11.5/E11.6 context names without owning host navigation.

    E11.6 requires an operations bridge. Other bridges may be nullable for a
    minimal host, and their pages must remain disabled or absent accordingly.
    """
    if _attribute(runtime, "ecosystem_bridge") is None:
        raise ValueError("Missing runtime.ecosystem_bridge")
    if _attribute(runtime, "operations_bridge") is None:
        raise ValueError("Missing runtime.operations_bridge (E11.6)")
    if _attribute(runtime, "factory.bridge") is None:
        raise ValueError("Missing runtime.factory.bridge")
    for name, path in _CONTEXT_ATTRIBUTES:
        context.setContextProperty(name, _attribute(runtime, path))


def route_errors(
    ecosystem_qml: Path, player_qml: Path | None = None
) -> tuple[str, ...]:
    """Check staged assets without Qt or a running Player process."""
    ecosystem_qml = Path(ecosystem_qml)
    errors: list[str] = []
    seen: set[str] = set()
    for route in PAGE_ROUTES:
        if route.route_id in seen:
            errors.append(f"Duplicate route ID: {route.route_id}")
        seen.add(route.route_id)
        if not (ecosystem_qml / route.relative_qml).is_file():
            errors.append(f"Missing QML for {route.route_id}: {route.relative_qml}")
    if player_qml is not None:
        player_qml = Path(player_qml)
        for directory in ("controls", "primitives", "theme"):
            if not (player_qml / directory).is_dir():
                errors.append(f"Missing Player design system: {directory}")
        for qml in (
            "controls/MichiButton.qml",
            "controls/MichiTextField.qml",
            "primitives/MichiGlassSurface.qml",
            "theme/MichiBreakpoints.qml",
        ):
            if not (player_qml / qml).is_file():
                errors.append(f"Missing Player component: {qml}")
    return tuple(errors)


def register_player_routes(
    register: Callable[[str, Path], None],
    ecosystem_qml: Path,
    *,
    player_qml: Path | None = None,
) -> tuple[str, ...]:
    """Register only verified pages; reject the *whole* batch on missing files.

    The Player owns `register` and should handle route changes itself. Routes
    into Michi Devices remain external and must be registered by that module.
    """
    errors = route_errors(ecosystem_qml, player_qml)
    if errors:
        raise ValueError("E12 QML preflight failed: " + "; ".join(errors))
    root = Path(ecosystem_qml)
    for page in PAGE_ROUTES:
        register(page.route_id, root / page.relative_qml)
    return tuple(page.route_id for page in PAGE_ROUTES)


def connect_player_navigation(
    runtime: object, open_route: Callable[[str], None]
) -> None:
    """Forward EcosystemBridge navigation to the Player once per session."""
    bridge = _attribute(runtime, "ecosystem_bridge")
    signal = getattr(bridge, "navigation_requested", None)
    if signal is None or not callable(getattr(signal, "connect", None)):
        raise ValueError(
            "Player navigation requires ecosystem_bridge.navigation_requested"
        )
    signal.connect(open_route)


def connect_page_navigation(page: object, open_route: Callable[[str], None]) -> bool:
    """Connect an instantiated detail page's navigationRequested signal.

    `EcosystemBridge` events and QML page signals are distinct: a Player must
    forward both. Some lower-level pages have no navigationRequested signal;
    this returns False so the host can rely on its own back affordance.
    """
    signal = getattr(page, "navigationRequested", None)
    if signal is None:
        return False
    connect = getattr(signal, "connect", None)
    if not callable(connect):
        raise ValueError("Invalid QML page navigationRequested signal")
    connect(open_route)
    return True


def apply_page_model(
    page: object, route_id: str, model: Mapping[str, object]
) -> tuple[str, ...]:
    """Inject the selected device/server projection into a loaded detail page.

    Only routes with an explicit model contract accept a model; the selected
    identity always comes from the runtime projection, never from QML state.
    Returns the property names applied (empty for self-contained pages) and
    fails closed when the page cannot accept the documented property.
    """
    property_name = PAGE_MODEL_PROPERTIES.get(route_id)
    if property_name is None:
        return ()
    if not isinstance(model, Mapping):
        raise ValueError("page model must be a mapping")
    setter = getattr(page, "setProperty", None)
    if not callable(setter):
        raise ValueError("loaded QML page does not expose setProperty")
    if setter(property_name, dict(model)) is False:
        raise ValueError(f"QML page for {route_id} has no {property_name!r} model")
    return (property_name,)
