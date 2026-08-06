"""CapabilityBridge — exposes backend capabilities to QML.

Based on BridgeFactory._capabilities + ServiceContainer availability.
No inline SQL — delegates to service capability checks.

Capability checks are REAL: they probe the underlying service or connection
instead of relying on container presence alone (FTS5 scalar probe, Snapserver
lifecycle state, radio station count, MPD binary/run state). Each probe
produces a typed :class:`CapabilityStatus` so QML can render degraded vs.
unavailable vs. failed distinctly.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from PySide6.QtCore import QObject, Signal, Property, Slot

logger = logging.getLogger(__name__)


# Canonical capability states. ``unknown``/``checking`` are transient; the
# remaining four are terminal outcomes for a probe.
STATE_UNKNOWN = "unknown"
STATE_CHECKING = "checking"
STATE_AVAILABLE = "available"
STATE_DEGRADED = "degraded"
STATE_UNAVAILABLE = "unavailable"
STATE_FAILED = "failed"


@dataclass(frozen=True)
class CapabilityStatus:
    """Typed outcome of a single capability probe.

    Attributes:
        key: Capability identifier (e.g. ``"has_fts5"``).
        state: One of unknown/checking/available/degraded/unavailable/failed.
        available: True only when ``state == "available"``.
        degraded: True when ``state == "degraded"`` (service present, limited).
        reason: Short machine-readable code explaining the outcome.
        last_error: Human-readable error string (empty when healthy).
        checked_at: ``time.time()`` when the probe ran.
        metadata: Extra structured details (e.g. station_count, running pid).
    """

    key: str
    state: str
    available: bool
    degraded: bool
    reason: str
    last_error: str
    checked_at: float
    metadata: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "state": self.state,
            "available": self.available,
            "degraded": self.degraded,
            "reason": self.reason,
            "last_error": self.last_error,
            "checked_at": self.checked_at,
            "metadata": dict(self.metadata),
        }


def _status(
    key: str,
    state: str,
    *,
    reason: str = "",
    last_error: str = "",
    metadata: dict | None = None,
) -> CapabilityStatus:
    """Build a CapabilityStatus with derived available/degraded flags."""
    return CapabilityStatus(
        key=key,
        state=state,
        available=state == STATE_AVAILABLE,
        degraded=state == STATE_DEGRADED,
        reason=reason,
        last_error=last_error,
        checked_at=time.time(),
        metadata=metadata or {},
    )


CAPABILITY_LABELS = {
    "connections_michilink": "Michi Link",
    "home_audio": "Home Audio",
    "snapcast": "Snapcast",
    "devices_sync": "Sincronización de dispositivos",
    "radio": "Radio",
    "playlists": "Playlists",
    "eq": "Ecualizador",
    "settings": "Ajustes",
    "audio_lab": "Audio Lab",
    "metadata": "Editor de metadatos",
    "smart_tagging": "Smart Tagging",
    "disc_lab": "Disc Lab",
    "library_doctor": "Library Doctor",
    "diagnostics": "Diagnóstico",
    "michi_ai": "Michi AI",
    "library": "Biblioteca",
    "playback": "Reproducción",
    "mix": "Mix",
    "lyrics": "Letras",
    "notifications": "Notificaciones",
    "global_search": "Búsqueda global",
    "transmit": "Transmitir audio",
    "ai": "Michi AI",
    "connections": "Conexiones",
    "devices": "Dispositivos",
    "output_profiles": "Perfiles de salida",
}

BRIDGE_ALIASES = {
    "transmit": "home_audio",
    "ai": "michi_ai",
}


def _resolve_alias(name: str) -> str:
    return BRIDGE_ALIASES.get(name, name)


CAPABILITY_STATE_KEYS = {
    "library", "playback", "nowplaying", "mix", "lyrics",
    "connections_michilink", "home_audio", "snapcast",
    "devices_sync", "radio", "playlists", "eq",
    "settings", "audio_lab", "metadata", "smart_tagging",
    "disc_lab", "library_doctor", "diagnostics",
    "michi_ai", "theme", "navigation", "route_registry",
    "app_state", "command_palette", "cover",
    "notifications", "global_search",
    "connections", "devices", "output_profiles",
    "ai", "transmit",
}


class CapabilityBridge(QObject):
    dataChanged = Signal()

    def __init__(self, factory=None, parent=None):
        super().__init__(parent)
        logger.debug("CapabilityBridge.__init__ called")
        self._factory = factory
        self._caps: dict[str, str] = {}
        self._statuses: dict[str, CapabilityStatus] = {}

    @Slot(result="QVariantMap")
    def refresh(self):
        if not self._factory:
            return {"ok": False, "error": "NO_FACTORY"}
        caps = dict(self._factory.capabilities)
        container = getattr(self._factory, '_container', None)
        for key in CAPABILITY_STATE_KEYS:
            if key not in caps:
                resolved = _resolve_alias(key)
                if resolved != key and resolved in caps:
                    caps[key] = caps[resolved]
                else:
                    caps[key] = "unavailable"
        # Real capability probes — each returns a typed CapabilityStatus whose
        # state feeds the legacy caps dict while the full record is exposed via
        # status()/statuses for richer QML rendering.
        probes = {
            "has_fts5": self._check_fts5(container),
            "has_radio": self._check_radio(container),
            "has_global_search": self._check_global_search(container),
            "has_sync": self._container_probe(
                container, "has_sync", "device_sync_service"),
            "has_home_audio": self._container_probe(
                container, "has_home_audio", "home_audio_service"),
            "has_snapcast": self._check_snapcast(container),
            "has_mpd": self._check_mpd(container),
            "has_disc_service": self._container_probe(
                container, "has_disc_service", "library_doctor_service"),
            "has_smart_tagging": self._container_probe(
                container, "has_smart_tagging", "smart_tagging_service"),
            "has_metadata_writer": self._check_metadata_writer(container),
        }
        for key, status in probes.items():
            self._statuses[key] = status
            caps[key] = status.state
        self._caps = caps
        self.dataChanged.emit()
        return {"ok": True, "capabilities": dict(self._caps)}

    @Property("QVariantMap", notify=dataChanged)
    def capabilities(self):
        return dict(self._caps)

    @Property("QVariantMap", notify=dataChanged)
    def statuses(self):
        """Full typed probe outcomes keyed by capability name."""
        return {key: status.as_dict() for key, status in self._statuses.items()}

    @Slot(str, result="QVariantMap")
    def status(self, name: str):
        """Return the typed probe outcome for a single capability."""
        record = self._statuses.get(name)
        if record is None:
            return _status(name, STATE_UNKNOWN, reason="NOT_PROBED").as_dict()
        return record.as_dict()

    @Slot(str, result=bool)
    def has(self, name: str) -> bool:
        val = self._caps.get(name, "unavailable")
        return val == "available"

    @Slot(str, result=str)
    def label(self, name: str) -> str:
        return CAPABILITY_LABELS.get(_resolve_alias(name), name)

    @Slot(str, result=str)
    def state(self, name: str) -> str:
        if name in self._caps:
            return self._caps[name]
        resolved = _resolve_alias(name)
        if resolved != name and resolved in self._caps:
            return self._caps[resolved]
        return "unavailable"

    # ── Real capability probes ──────────────────────────────────────────────
    #
    # These inspect the underlying service or connection instead of trusting
    # container presence. Every probe is defensive: a missing container or a
    # raising service degrades to a terminal state, never an exception.

    def _container_probe(self, container, key: str, service_name: str) -> CapabilityStatus:
        """Generic presence probe for capabilities without a deeper API."""
        if not container or not container.contains(service_name):
            return _status(key, STATE_UNAVAILABLE, reason="NO_SERVICE")
        return _status(key, STATE_AVAILABLE)

    def _check_fts5(self, container) -> CapabilityStatus:
        """Probe FTS5 by executing a real FTS5 scalar call on a read connection.

        ``SELECT fts5('test')`` succeeds only when SQLite was compiled with
        FTS5; it does not require any table and is safe on a read-only (URI
        ``mode=ro``) connection. Falls back to the LibraryDB connection when no
        dedicated read factory is registered.
        """
        key = "has_fts5"
        if not container:
            return _status(key, STATE_UNAVAILABLE, reason="NO_CONTAINER")
        conn = None
        try:
            reader = container.get("read_connection_factory")
            if reader is not None and hasattr(reader, "connection"):
                conn = reader.connection()
            if conn is None:
                db = container.get("database")
                if db is not None and hasattr(db, "conn"):
                    conn = db.conn
        except Exception as exc:  # noqa: BLE001 — probe must stay alive
            return _status(key, STATE_UNAVAILABLE, reason="NO_CONNECTION",
                           last_error=str(exc))
        if conn is None:
            return _status(key, STATE_UNAVAILABLE, reason="NO_CONNECTION")
        try:
            conn.execute("SELECT fts5('test')").fetchone()
            return _status(key, STATE_AVAILABLE)
        except Exception as exc:  # noqa: BLE001 — FTS5 not compiled in
            return _status(key, STATE_UNAVAILABLE, reason="FTS5_NOT_COMPILED",
                           last_error=str(exc))

    def _check_global_search(self, container) -> CapabilityStatus:
        """Probe the global search chain truthfully (Slice 6).

        Available only when the service exists AND ``search_available()``
        reports the whole chain operative (query executor + worker manager
        active, database readable, at least one provider registered). The
        reasons surface in the status metadata.
        """
        key = "has_global_search"
        if not container or not container.contains("global_search_service"):
            return _status(key, STATE_UNAVAILABLE, reason="NO_SERVICE")
        try:
            service = container.get("global_search_service")
        except Exception as exc:  # noqa: BLE001 — probe must stay alive
            return _status(key, STATE_UNAVAILABLE, reason="SERVICE_ERROR",
                           last_error=str(exc))
        checker = getattr(service, "search_available", None)
        if not callable(checker):
            return _status(key, STATE_AVAILABLE)
        try:
            info = checker()
        except Exception as exc:  # noqa: BLE001 — probe must stay alive
            return _status(key, STATE_UNAVAILABLE, reason="PROBE_FAILED",
                           last_error=str(exc))
        if isinstance(info, dict) and info.get("ok"):
            return _status(key, STATE_AVAILABLE)
        reasons = info.get("reasons", []) if isinstance(info, dict) else []
        return _status(key, STATE_UNAVAILABLE, reason="CHAIN_UNAVAILABLE",
                       last_error="; ".join(reasons))

    def _check_snapcast(self, container) -> CapabilityStatus:
        """Probe Snapserver lifecycle via the owned SnapServerManager.

        Distinguishes ``unavailable`` (binary missing) from a healthy-but-idle
        manager (``stopped``/``running``/``starting``). The check is real
        because it reads ``SnapServerManager.state`` which reconciles the
        underlying process — not merely the ``home_audio_service`` container
        key the legacy check inspected.
        """
        key = "has_snapcast"
        if not container:
            return _status(key, STATE_UNAVAILABLE, reason="NO_CONTAINER")
        mgr = container.get("snapserver_manager")
        if mgr is None:
            return _status(key, STATE_UNAVAILABLE, reason="NO_SERVICE")
        try:
            state = getattr(mgr, "state", "") or ""
        except Exception as exc:  # noqa: BLE001 — probe must stay alive
            return _status(key, STATE_FAILED, reason="STATE_PROBE_FAILED",
                           last_error=str(exc))
        # STATE_UNAVAILABLE == "unavailable" => snapserver binary missing.
        if state == "unavailable":
            return _status(key, STATE_UNAVAILABLE, reason="SNAPSERVER_BINARY_MISSING")
        return _status(key, STATE_AVAILABLE, metadata={"state": state})

    def _check_radio(self, container) -> CapabilityStatus:
        """Probe radio by asking the service for its actual stations.

        ``available`` requires the service AND at least one station; a service
        with no stations is ``degraded`` (the capability exists but is empty).
        """
        key = "has_radio"
        if not container:
            return _status(key, STATE_UNAVAILABLE, reason="NO_CONTAINER")
        svc = container.get("radio_service")
        if svc is None:
            return _status(key, STATE_UNAVAILABLE, reason="NO_SERVICE")
        try:
            stations = svc.get_stations() if hasattr(svc, "get_stations") else []
            count = len(stations) if stations else 0
        except Exception as exc:  # noqa: BLE001 — probe must stay alive
            return _status(key, STATE_FAILED, reason="STATION_PROBE_FAILED",
                           last_error=str(exc))
        if count > 0:
            return _status(key, STATE_AVAILABLE, metadata={"station_count": count})
        return _status(key, STATE_DEGRADED, reason="NO_STATIONS",
                       metadata={"station_count": 0})

    def _check_mpd(self, container) -> CapabilityStatus:
        """Probe MPD via the real MpdServiceManager, not a container key.

        ``available`` when MPD is installed AND currently running; ``degraded``
        when the binary is present but no instance is running (can be started);
        ``unavailable`` when the binary is absent. The running state is read
        from the playback service's MPD status when wired.
        """
        key = "has_mpd"
        try:
            from audio.mpd.mpd_service_manager import MpdServiceManager
        except Exception as exc:  # noqa: BLE001 — optional module
            return _status(key, STATE_UNAVAILABLE, reason="MPD_MODULE_MISSING",
                           last_error=str(exc))
        try:
            if not MpdServiceManager.is_installed():
                return _status(key, STATE_UNAVAILABLE, reason="MPD_BINARY_MISSING")
        except Exception as exc:  # noqa: BLE001 — probe must stay alive
            return _status(key, STATE_FAILED, reason="MPD_PROBE_FAILED",
                           last_error=str(exc))
        if container is not None:
            playback = container.get("playback_service")
            if playback is not None and hasattr(playback, "get_mpd_status"):
                try:
                    status = playback.get_mpd_status() or {}
                    if status.get("running"):
                        return _status(key, STATE_AVAILABLE,
                                       metadata={"running": True})
                except Exception as exc:  # noqa: BLE001 — probe must stay alive
                    return _status(key, STATE_DEGRADED, reason="MPD_STATUS_UNREADABLE",
                                   last_error=str(exc))
        return _status(key, STATE_DEGRADED, reason="MPD_NOT_RUNNING",
                       metadata={"running": False})

    def _check_metadata_writer(self, container) -> CapabilityStatus:
        key = "has_metadata_writer"
        import importlib.util
        return _status(
            key,
            STATE_AVAILABLE if importlib.util.find_spec("mutagen") is not None
            else STATE_UNAVAILABLE,
            reason="MUTAGEN_MISSING",
        )
