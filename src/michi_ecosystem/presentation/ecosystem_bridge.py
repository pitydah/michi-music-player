"""Ecosystem dashboard bridge: card projection, routes and high-level intents.

Phase: E1 (fake runtime + dashboard shell, master plan §22). The bridge consumes
a dashboard provider exposing ``dashboard_snapshot()`` (the §21.1 coordinator
shape) and projects QML-friendly card models. No business logic, no network,
no GUI-thread I/O beyond serialization.

Snapshot sections consumed (all optional; each card degrades independently):

    discovery:    {"state", "device_name", "signal", "count"}
    streams:      {"configured", "devices": [{"name", "state"}]}
    spaces:       {"count", "names"}
    servers:      {"micro": {"presence", "services": {...}}, "big": {...} | None}
    link:         {"state", "nodes", "links", "incidents"}
    mobile:       {"trusted", "name", "online", "version"}
    devices:      {"trusted", "total", "items": [...]}
    account:      {"exists", "authenticated", "display_name"}
    health:       {"state", "issues": [{"title", "detail"}]}
    integrations: {"active": [...], "available": [...]}

Card model keys (camelCase for QML): kind, title, subtitle, icon, tone,
highlighted, route, primaryAction, primaryRoute, secondaryAction,
secondaryRoute, items[{label, status, tone}].
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Property, QObject, Qt, Signal, Slot

TONES = frozenset({"neutral", "active", "success", "warning", "error"})

_DISCOVERY_COPY = {
    "idle": ("No hay dispositivos nuevos", "neutral", "Ver detección"),
    "searching": ("Buscando dispositivos Michi…", "active", ""),
    "found_one": ("Nuevo Music Stream encontrado", "success", "Ver dispositivo"),
    "found_multiple": ("Dispositivos encontrados", "success", "Revisar"),
    # Backward-compatible state name from older discovery providers.  The
    # product copy no longer presents Stream onboarding as button pairing.
    "pairing": ("Añadiendo a Michi Home…", "active", ""),
    "needs_attention": ("Un dispositivo necesita atención", "warning", "Revisar"),
    "failed": ("No se pudo añadir el dispositivo", "error", "Ver detección"),
}

_STREAM_STATE = {
    "ready": ("Listo", "success"),
    "pending": ("Vinculación pendiente", "warning"),
    "setup": ("Configuración pendiente", "warning"),
    "offline": ("Sin red", "error"),
}

_HEALTH_COPY = {
    "healthy": ("Todo funcionando", "success"),
    "degraded": ("Hay dispositivos que necesitan atención", "warning"),
    "action_required": ("Acción requerida", "warning"),
    "offline": ("Sin conexión", "error"),
    "unknown": ("Estado desconocido", "neutral"),
}

_SERVICE_LABELS = (
    ("api", "API"),
    ("streaming", "Streaming"),
    ("transcoding", "Transcoding"),
    ("michi_link", "Michi Link"),
)


def _card(
    kind: str,
    title: str,
    subtitle: str,
    icon: str,
    route: str,
    *,
    tone: str = "neutral",
    highlighted: bool = False,
    items: tuple[dict[str, str], ...] | list[dict[str, str]] = (),
    primary_action: str = "",
    primary_route: str = "",
    secondary_action: str = "",
    secondary_route: str = "",
    status: str = "",
    status_tone: str = "neutral",
    eyebrow: str = "",
) -> dict[str, Any]:
    return {
        "kind": kind,
        "title": title,
        "subtitle": subtitle,
        "icon": icon,
        "tone": tone if tone in TONES else "neutral",
        "highlighted": highlighted,
        "route": route,
        "primaryAction": primary_action,
        "primaryRoute": primary_route,
        "secondaryAction": secondary_action,
        "secondaryRoute": secondary_route,
        "status": status,
        "statusTone": status_tone if status_tone in TONES else "neutral",
        "eyebrow": eyebrow,
        "items": [dict(item) for item in items],
    }


def _row(label: str, status: str = "", tone: str = "neutral") -> dict[str, str]:
    return {"label": label, "status": status, "tone": tone}


def _discovery_card(data: dict[str, Any]) -> dict[str, Any]:
    state = str(data.get("state", "idle"))
    subtitle, tone, action_label = _DISCOVERY_COPY.get(state, _DISCOVERY_COPY["idle"])
    if state == "found_multiple":
        count = data.get("count")
        if isinstance(count, int) and count > 0:
            subtitle = f"{count} dispositivos encontrados"

    items: list[dict[str, str]] = []
    device = str(data.get("device_name", "") or "")
    signal = str(data.get("signal", "") or "")
    if device:
        items.append(_row(device, signal, "success" if signal else "neutral"))

    return _card(
        "discovery",
        "Descubrimiento",
        subtitle,
        "search",
        "ecosystem/discovery",
        tone=tone,
        highlighted=state == "found_one",
        items=items,
        primary_action=action_label,
        primary_route="ecosystem/discovery",
        status="Buscando" if state == "searching" else "",
        status_tone="active" if state == "searching" else tone,
        eyebrow="RED LOCAL",
    )


def _music_stream_card(data: dict[str, Any]) -> dict[str, Any]:
    configured = int(data.get("configured", 0) or 0)
    devices = data.get("devices") or []

    items: list[dict[str, str]] = []
    for device in devices:
        if not isinstance(device, dict):
            continue
        name = str(device.get("name", "") or "")
        status, tone = _STREAM_STATE.get(
            str(device.get("state", "")), ("Desconocido", "neutral")
        )
        if name:
            items.append(_row(name, status, tone))

    if configured == 0:
        subtitle = "No encontramos ningún Music Stream."
    elif configured == 1:
        subtitle = "1 configurado"
    else:
        subtitle = f"{configured} configurados"
    return _card(
        "music_stream",
        "Music Stream",
        subtitle,
        "audio-output",
        "ecosystem/devices",
        items=items,
        primary_action="Administrar",
        primary_route="ecosystem/devices",
        secondary_action="+ Crear Stream",
        secondary_route="ecosystem/music-stream/create",
        status="En línea"
        if any(item.get("tone") == "success" for item in items)
        else "",
        status_tone="success",
        eyebrow="AUDIO",
    )


def _spaces_card(data: dict[str, Any]) -> dict[str, Any]:
    count = int(data.get("count", 0) or 0)
    names = [str(name) for name in (data.get("names") or []) if str(name)]

    items = [_row(name) for name in names]
    subtitle = f"{count} espacios" if count != 1 else "1 espacio"
    return _card(
        "spaces",
        "Espacios",
        subtitle,
        "pin",
        "ecosystem/spaces",
        items=items,
        primary_action="Administrar",
        primary_route="ecosystem/spaces",
        eyebrow="MULTIROOM",
    )


def _micro_server_card(data: dict[str, Any]) -> dict[str, Any]:
    micro = data.get("micro") or {}
    if micro:
        online = str(micro.get("presence", "")) == "online"
        subtitle = "En línea" if online else "Sin conexión"
        tone = "success" if online else "error"
        services = micro.get("services") or {}
        items = [
            _row(
                label,
                "OK" if bool(services.get(key, False)) else "Pendiente",
                "success" if bool(services.get(key, False)) else "warning",
            )
            for key, label in _SERVICE_LABELS
        ]
    else:
        subtitle = "Michi Micro Server no está disponible."
        tone = "neutral"
        items = []

    return _card(
        "micro_server",
        "Michi Micro Server",
        subtitle,
        "audio-engine",
        "ecosystem/micro-server",
        tone=tone,
        items=items,
        primary_action="Administrar",
        primary_route="ecosystem/micro-server",
        status=subtitle if micro else "",
        status_tone=tone,
        eyebrow="SERVIDOR",
    )


def _michi_link_card(data: dict[str, Any]) -> dict[str, Any]:
    state = str(data.get("state", "unknown"))
    subtitle, tone = {
        "operational": ("Operativo", "success"),
        "degraded": ("Con incidencias", "warning"),
        "offline": ("Sin conexión", "error"),
    }.get(state, ("Sin datos", "neutral"))

    nodes = int(data.get("nodes", 0) or 0)
    links = int(data.get("links", 0) or 0)
    incidents = int(data.get("incidents", 0) or 0)
    items = [
        _row("Nodos", str(nodes)),
        _row("Enlaces", str(links)),
        _row(
            "Incidencias",
            str(incidents),
            "success" if incidents == 0 else "warning",
        ),
    ]
    return _card(
        "michi_link",
        "Michi Link",
        subtitle,
        "view-timeline",
        "ecosystem/michi-link",
        tone=tone,
        items=items,
        primary_action="Configurar",
        primary_route="ecosystem/michi-link",
        status=subtitle,
        status_tone=tone,
        eyebrow="IDENTIDAD Y CONTROL",
    )


def _mobile_card(data: dict[str, Any]) -> dict[str, Any]:
    trusted = int(data.get("trusted", data.get("paired", 0)) or 0)
    name = str(data.get("name", "") or "")
    online = bool(data.get("online", trusted > 0))
    version = str(data.get("version", "") or "")

    if trusted == 0:
        subtitle = "Sin dispositivos confiables"
    elif trusted == 1:
        subtitle = "1 dispositivo confiable"
    else:
        subtitle = f"{trusted} dispositivos confiables"

    items: list[dict[str, str]] = []
    if name:
        items.append(
            _row(
                name,
                "En línea" if online else "Sin conexión",
                "success" if online else "error",
            )
        )
    if version:
        items.append(_row("Versión", version))
    return _card(
        "mobile",
        "Michi Music Mobile",
        subtitle,
        "device",
        "ecosystem/mobile",
        tone="success" if online and trusted else "neutral",
        items=items,
        primary_action="Administrar" if trusted else "",
        primary_route="ecosystem/mobile",
        secondary_action="Abrir en Michi Devices" if trusted else "",
        secondary_route="devices/mobile",
        status="Conectado" if online and trusted else "",
        status_tone="success",
        eyebrow="CONTROLADOR",
    )


def _devices_card(data: dict[str, Any]) -> dict[str, Any]:
    trusted = int(data.get("trusted", 0) or 0)
    total = int(data.get("total", 0) or 0)
    subtitle = (
        f"{trusted} de {total} confiables"
        if total
        else "Todavía no hay dispositivos en tu Michi Home."
    )
    items: list[dict[str, str]] = []
    for item in data.get("items") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "") or "")
        if not name:
            continue
        state = str(item.get("state", "unknown"))
        label, tone = {
            "ready": ("Listo", "success"),
            "online": ("En línea", "success"),
            "pending": ("Pendiente", "warning"),
            "revoked": ("Revocado", "error"),
            "offline": ("Sin conexión", "error"),
        }.get(state, ("Desconocido", "neutral"))
        items.append(_row(name, label, tone))
    return _card(
        "devices",
        "Tus dispositivos",
        subtitle,
        "view-grid",
        "ecosystem/devices",
        items=items[:4],
        primary_action="Ver dispositivos" if total else "",
        primary_route="ecosystem/devices",
        eyebrow="MICHI HOME",
    )


def _health_card(data: dict[str, Any]) -> dict[str, Any]:
    state = str(data.get("state", "unknown"))
    headline, tone = _HEALTH_COPY.get(state, _HEALTH_COPY["unknown"])
    issues = data.get("issues") or []

    items = [
        _row(
            str(issue.get("title", "") or ""),
            str(issue.get("detail", "") or ""),
            "warning",
        )
        for issue in issues
        if isinstance(issue, dict)
    ]
    return _card(
        "health",
        "Estado del sistema",
        headline,
        "heart",
        "ecosystem/diagnostics",
        tone=tone,
        highlighted=state in {"degraded", "action_required"},
        items=items,
        primary_action="Revisar" if items else "",
        primary_route="ecosystem/diagnostics",
        status=headline,
        status_tone=tone,
        eyebrow="SALUD",
    )


def _integrations_card(data: dict[str, Any]) -> dict[str, Any]:
    active = [str(name) for name in (data.get("active") or []) if str(name)]
    available = [str(name) for name in (data.get("available") or []) if str(name)]

    items = [_row(name, "Activa", "success") for name in active]
    items += [_row(name, "Disponible") for name in available]

    subtitle = f"{len(active)} activas" if active else "Sin integraciones activas"
    return _card(
        "integrations",
        "Integraciones",
        subtitle,
        "sparkles",
        "ecosystem/integrations",
        items=items,
        primary_action="Administrar",
        primary_route="ecosystem/integrations",
        eyebrow="AUTOMATIZACIÓN",
    )


def _account_card(data: dict[str, Any]) -> dict[str, Any]:
    exists = bool(data.get("exists", False))
    authenticated = bool(data.get("authenticated", False))
    display_name = str(data.get("display_name", "") or "")
    if not exists:
        subtitle = "Configura al propietario local de Michi Home"
        action = "Crear cuenta"
        tone = "warning"
    elif authenticated:
        subtitle = display_name or "Propietario local"
        action = "Administrar"
        tone = "success"
    else:
        subtitle = display_name or "Cuenta local bloqueada"
        action = "Desbloquear"
        tone = "neutral"
    return _card(
        "account",
        "Cuenta local",
        subtitle,
        "artist",
        "ecosystem/account",
        tone=tone,
        primary_action=action,
        primary_route="ecosystem/account",
        status="Desbloqueada" if authenticated else "",
        status_tone="success",
        eyebrow="PROPIETARIO",
    )


def _create_stream_card() -> dict[str, Any]:
    route = "ecosystem/music-stream/create"
    return _card(
        "create_stream",
        "Crear Music Stream",
        "Convierte una ESP32-S3 en un receptor Michi.",
        "plus",
        route,
        primary_action="Conectar por USB-C",
        primary_route=route,
        eyebrow="FÁBRICA",
    )


class EcosystemBridge(QObject):
    """QML projection of the Ecosystem dashboard (E1)."""

    cards_changed = Signal()
    navigation_requested = Signal(str)
    _registry_refresh_requested = Signal()

    def __init__(self, provider: object, parent: QObject | None = None) -> None:
        super().__init__(parent)
        if provider is None or not callable(
            getattr(provider, "dashboard_snapshot", None)
        ):
            raise TypeError("provider must expose dashboard_snapshot()")
        self._provider = provider
        self._registry_refresh_requested.connect(
            self.refresh, Qt.ConnectionType.QueuedConnection
        )

    @Property("QVariantList", notify=cards_changed)
    def dashboardCards(self) -> list[dict[str, Any]]:
        return self._build_cards()

    @Property(str, notify=cards_changed)
    def healthStatus(self) -> str:
        state = str((self._snapshot().get("health") or {}).get("state", "unknown"))
        return _HEALTH_COPY.get(state, _HEALTH_COPY["unknown"])[0]

    @Property(str, notify=cards_changed)
    def healthTone(self) -> str:
        state = str((self._snapshot().get("health") or {}).get("state", "unknown"))
        return _HEALTH_COPY.get(state, _HEALTH_COPY["unknown"])[1]

    @Property(int, notify=cards_changed)
    def attentionCount(self) -> int:
        return len((self._snapshot().get("health") or {}).get("issues") or [])

    @Property(str, notify=cards_changed)
    def deviceSummary(self) -> str:
        data = self._snapshot().get("devices") or {}
        total = int(data.get("total", 0) or 0)
        trusted = int(data.get("trusted", 0) or 0)
        if total == 0:
            return "Sin dispositivos"
        return f"{trusted}/{total} confiables"

    @Property(bool, notify=cards_changed)
    def isEmpty(self) -> bool:
        snapshot = self._snapshot()
        devices = snapshot.get("devices") or {}
        streams = snapshot.get("streams") or {}
        servers = snapshot.get("servers") or {}
        mobile = snapshot.get("mobile") or {}
        return (
            int(devices.get("total", 0) or 0) == 0
            and int(streams.get("configured", 0) or 0) == 0
            and not (servers.get("micro") or {})
            and int(mobile.get("trusted", mobile.get("paired", 0)) or 0) == 0
        )

    @Slot()
    def refresh(self) -> None:
        self.cards_changed.emit()

    def on_registry_changed(self, _devices) -> None:
        """Queue refresh onto the QObject-owning GUI thread."""
        self._registry_refresh_requested.emit()

    @Slot(str)
    def activate(self, route: str) -> None:
        if route:
            self.navigation_requested.emit(route)

    def _snapshot(self) -> dict[str, Any]:
        snapshot = self._provider.dashboard_snapshot()
        return snapshot if isinstance(snapshot, dict) else {}

    def _build_cards(self) -> list[dict[str, Any]]:
        snapshot = self._snapshot()
        return [
            _discovery_card(snapshot.get("discovery") or {}),
            _music_stream_card(snapshot.get("streams") or {}),
            _spaces_card(snapshot.get("spaces") or {}),
            _micro_server_card(snapshot.get("servers") or {}),
            _michi_link_card(snapshot.get("link") or {}),
            _mobile_card(snapshot.get("mobile") or {}),
            _devices_card(snapshot.get("devices") or {}),
            _health_card(snapshot.get("health") or {}),
            _integrations_card(snapshot.get("integrations") or {}),
            _account_card(snapshot.get("account") or {}),
            _create_stream_card(),
        ]
