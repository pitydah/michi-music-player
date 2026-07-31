from ui_qml_bridge.capability_bridge import (
    BRIDGE_ALIASES,
    CapabilityBridge,
    CapabilityStatus,
    _resolve_alias,
    _status,
    STATE_AVAILABLE,
    STATE_DEGRADED,
    STATE_UNAVAILABLE,
)


def test_resolve_alias_transforms_known_keys():
    assert _resolve_alias("transmit") == "home_audio"
    assert _resolve_alias("ai") == "michi_ai"
    assert _resolve_alias("library") == "library"
    assert _resolve_alias("unknown_key") == "unknown_key"


def test_state_uses_alias_resolution():
    bridge = CapabilityBridge()
    bridge.refresh()
    result = bridge.state("transmit")
    assert result == "unavailable"

    result = bridge.state("ai")
    assert result == "unavailable"


def test_refresh_returns_structured_dict():
    bridge = CapabilityBridge()
    result = bridge.refresh()

    assert result["ok"] is False
    assert result["error"] == "NO_FACTORY"


def test_refresh_with_factory_wires_capabilities():
    capabilities = {"library": "available", "home_audio": "available"}

    class FakeFactory:
        def __init__(self):
            self.bridges = {}

        def get(self, name):
            return self.bridges.get(name)

    factory = FakeFactory()
    factory.capabilities = dict(capabilities)
    bridge = CapabilityBridge(factory=factory)

    result = bridge.refresh()

    assert result["ok"] is True
    assert bridge.has("library") is True
    assert bridge.has("home_audio") is True
    assert bridge.state("transmit") == "available"


def test_label_preserves_compatibility():
    bridge = CapabilityBridge()

    assert bridge.label("home_audio") == "Home Audio"
    assert bridge.label("unknown") == "unknown"


def test_explicit_factory_capability_is_preserved():
    class FakeFactory:
        def __init__(self):
            self.bridges = {}
            self.capabilities = {"transmit": "deferred_physical"}

        def get(self, name):
            return self.bridges.get(name)

    bridge = CapabilityBridge(factory=FakeFactory())
    bridge.refresh()

    assert bridge.state("transmit") == "deferred_physical"
    assert bridge.has("transmit") is False


def test_bridge_aliases_map_correctly():
    assert "transmit" in BRIDGE_ALIASES
    assert BRIDGE_ALIASES["transmit"] == "home_audio"
    assert "ai" in BRIDGE_ALIASES
    assert BRIDGE_ALIASES["ai"] == "michi_ai"


# ── CapabilityStatus dataclass ───────────────────────────────────────────────


def test_capability_status_flags_derived_from_state():
    s = _status("has_fts5", STATE_AVAILABLE)
    assert s.available is True
    assert s.degraded is False
    assert s.state == "available"

    d = _status("has_radio", STATE_DEGRADED, reason="NO_STATIONS")
    assert d.available is False
    assert d.degraded is True
    assert d.reason == "NO_STATIONS"

    u = _status("has_mpd", STATE_UNAVAILABLE, reason="MPD_BINARY_MISSING")
    assert u.available is False
    assert u.degraded is False


def test_capability_status_direct_construction_defaults_metadata():
    import time

    before = time.time()
    s = CapabilityStatus(
        key="has_fts5",
        state=STATE_AVAILABLE,
        available=True,
        degraded=False,
        reason="",
        last_error="",
        checked_at=before,
    )
    after = time.time()
    # metadata defaults to an empty dict (default_factory), not shared state.
    assert s.metadata == {}
    assert before <= s.checked_at <= after


def test_capability_status_as_dict_roundtrip():
    s = _status("has_snapcast", STATE_AVAILABLE, metadata={"state": "running"})
    payload = s.as_dict()
    assert payload["key"] == "has_snapcast"
    assert payload["state"] == "available"
    assert payload["available"] is True
    assert payload["metadata"] == {"state": "running"}
    assert isinstance(payload, dict)


def test_capability_status_is_frozen():
    s = _status("has_fts5", STATE_AVAILABLE)
    import pytest as _pytest
    with _pytest.raises(Exception):
        s.state = "unavailable"  # type: ignore[misc]


# ── Real probes ──────────────────────────────────────────────────────────────


class FakeContainer:
    """Minimal ServiceContainer stand-in: contains()/get() over a dict."""

    def __init__(self, **services):
        self._services = {k: v for k, v in services.items() if v is not None}

    def contains(self, name: str) -> bool:
        return name in self._services and self._services[name] is not None

    def get(self, name: str):
        return self._services.get(name)


class FakeFactoryWithContainer:
    def __init__(self, container, capabilities=None):
        self._container = container
        self.bridges = {}
        self.capabilities = dict(capabilities or {})

    def get(self, name):
        return self.bridges.get(name)


class FakeSnapserverManager:
    def __init__(self, state: str = "stopped"):
        self.state = state


class FakeRadioService:
    def __init__(self, stations=None):
        self._stations = stations if stations is not None else []

    def get_stations(self):
        return list(self._stations)


def test_fts5_probe_real(tmp_path):
    import sqlite3
    from library.connection_factory import ReadConnectionFactory

    db_path = str(tmp_path / "fts5.db")
    sqlite3.connect(db_path).close()  # create file so read-only URI opens
    reader = ReadConnectionFactory(db_path)
    container = FakeContainer(read_connection_factory=reader)
    bridge = CapabilityBridge(factory=FakeFactoryWithContainer(container))

    bridge.refresh()
    st = bridge.status("has_fts5")
    # Standard CPython ships FTS5 compiled in; the probe must reflect the real
    # scalar call, not a container-presence heuristic.
    assert st["state"] == "available"
    assert st["available"] is True
    assert bridge.state("has_fts5") == "available"


def test_fts5_probe_unavailable_without_container():
    bridge = CapabilityBridge(factory=FakeFactoryWithContainer(None))
    bridge.refresh()
    st = bridge.status("has_fts5")
    assert st["state"] == "unavailable"
    assert st["reason"] == "NO_CONTAINER"


def test_snapcast_probe_real_binary_present():
    container = FakeContainer(snapserver_manager=FakeSnapserverManager("stopped"))
    bridge = CapabilityBridge(factory=FakeFactoryWithContainer(container))
    bridge.refresh()
    st = bridge.status("has_snapcast")
    assert st["state"] == "available"
    assert st["metadata"]["state"] == "stopped"


def test_snapcast_probe_unavailable_when_binary_missing():
    container = FakeContainer(
        snapserver_manager=FakeSnapserverManager("unavailable"))
    bridge = CapabilityBridge(factory=FakeFactoryWithContainer(container))
    bridge.refresh()
    st = bridge.status("has_snapcast")
    assert st["state"] == "unavailable"
    assert st["reason"] == "SNAPSERVER_BINARY_MISSING"


def test_snapcast_probe_unavailable_when_no_service():
    container = FakeContainer()
    bridge = CapabilityBridge(factory=FakeFactoryWithContainer(container))
    bridge.refresh()
    assert bridge.status("has_snapcast")["state"] == "unavailable"


def test_radio_probe_available_with_stations():
    container = FakeContainer(
        radio_service=FakeRadioService(stations=[{"id": "1"}]))
    bridge = CapabilityBridge(factory=FakeFactoryWithContainer(container))
    bridge.refresh()
    st = bridge.status("has_radio")
    assert st["state"] == "available"
    assert st["metadata"]["station_count"] == 1


def test_radio_probe_degraded_without_stations():
    container = FakeContainer(radio_service=FakeRadioService(stations=[]))
    bridge = CapabilityBridge(factory=FakeFactoryWithContainer(container))
    bridge.refresh()
    st = bridge.status("has_radio")
    assert st["state"] == "degraded"
    assert st["reason"] == "NO_STATIONS"


def test_mpd_probe_unavailable_when_binary_missing(monkeypatch):
    from audio.mpd import mpd_service_manager as mod

    monkeypatch.setattr(mod.MpdServiceManager, "is_installed", staticmethod(lambda: False))
    container = FakeContainer()
    bridge = CapabilityBridge(factory=FakeFactoryWithContainer(container))
    bridge.refresh()
    st = bridge.status("has_mpd")
    assert st["state"] == "unavailable"
    assert st["reason"] == "MPD_BINARY_MISSING"


def test_mpd_probe_degraded_when_installed_but_not_running(monkeypatch):
    from audio.mpd import mpd_service_manager as mod

    monkeypatch.setattr(mod.MpdServiceManager, "is_installed", staticmethod(lambda: True))
    container = FakeContainer()
    bridge = CapabilityBridge(factory=FakeFactoryWithContainer(container))
    bridge.refresh()
    st = bridge.status("has_mpd")
    assert st["state"] == "degraded"
    assert st["reason"] == "MPD_NOT_RUNNING"


def test_mpd_probe_available_when_running(monkeypatch):
    from audio.mpd import mpd_service_manager as mod

    monkeypatch.setattr(mod.MpdServiceManager, "is_installed", staticmethod(lambda: True))

    class FakePlayback:
        def get_mpd_status(self):
            return {"running": True}

    container = FakeContainer(playback_service=FakePlayback())
    bridge = CapabilityBridge(factory=FakeFactoryWithContainer(container))
    bridge.refresh()
    st = bridge.status("has_mpd")
    assert st["state"] == "available"
    assert st["metadata"]["running"] is True


def test_statuses_property_exposes_all_probes():
    container = FakeContainer(radio_service=FakeRadioService(stations=[]))
    bridge = CapabilityBridge(factory=FakeFactoryWithContainer(container))
    bridge.refresh()
    all_statuses = bridge.statuses
    assert "has_fts5" in all_statuses
    assert "has_radio" in all_statuses
    assert "has_mpd" in all_statuses
    assert all_statuses["has_radio"]["state"] == "degraded"


def test_status_slot_unknown_for_unprobed_key():
    bridge = CapabilityBridge(factory=FakeFactoryWithContainer(FakeContainer()))
    bridge.refresh()
    st = bridge.status("has_totally_made_up")
    assert st["state"] == "unknown"
    assert st["reason"] == "NOT_PROBED"
