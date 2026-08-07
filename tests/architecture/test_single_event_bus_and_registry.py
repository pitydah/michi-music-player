"""P0 FASE 10 — single event bus + single device registry + lazy network.

Mandatory architecture guarantees:
1. Exactly ONE ``EventBus()`` is created in composition; lyrics events flow
   through it (LyricEventBus is a typed wrapper with no handler state of its
   own; no second standalone pub/sub).
2. Exactly ONE ``DeviceRegistry`` in composition; device_sync, mobile_sync
   and the devices bridge receive the same injected instance.
3. The Home Assistant client composed in ecosystem.py never connects at
   construction — network starts only on explicit enable.
4. FileManagerService is registered once as an explicit port; no ad-hoc
   construction outside composition.
5. RecognitionService receives the canonical advanced detection stack
   (provider_manager + detection_service + capture).
6. No service construction in lazy getters/fallbacks (``if self._x is None``).
7. No cross-service private ``._db``/``._conn`` access in productive code.
8. Job handlers close over ports only (F2 re-assert).
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest

from core.application_bootstrap import ApplicationBootstrap
from core.service_manifest import SERVICE_MANIFEST

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

COMPOSITION_DIR = PROJECT_ROOT / "core" / "composition"
CORE_DIR = PROJECT_ROOT / "core"
BRIDGE_DIR = PROJECT_ROOT / "ui_qml_bridge"
LYRICS_EVENTS = CORE_DIR / "lyrics" / "events.py"
RADIO_EVENTS = CORE_DIR / "radio" / "events.py"


@pytest.fixture(scope="module")
def app():
    from PySide6.QtGui import QGuiApplication

    instance = QGuiApplication.instance()
    if not instance:
        instance = QGuiApplication(sys.argv)
    return instance


@pytest.fixture(scope="module")
def container(app):
    bootstrap = ApplicationBootstrap()
    bootstrap.build()
    return bootstrap.container


# ── 1. Single EventBus ────────────────────────────────────────────────────


def test_exactly_one_eventbus_instance_in_composition() -> None:
    count = 0
    for path in COMPOSITION_DIR.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        count += len(re.findall(r"(?<![A-Za-z])EventBus\(", source))
    assert count == 1, (
        f"Expected exactly 1 'EventBus(' in composition, found {count} — "
        "typed wrappers must be aliased (RadioEventBus/LyricEventBus)"
    )


def test_lyric_event_bus_is_typed_wrapper_without_own_state() -> None:
    source = LYRICS_EVENTS.read_text(encoding="utf-8")
    assert "_handlers" not in source, (
        "LyricEventBus must NOT keep its own handler dict (no second pub/sub)"
    )
    assert "self._bus.on(" in source or "self._bus.subscribe(" in source, (
        "LyricEventBus must delegate subscribe to the wrapped canonical bus"
    )
    assert "from core.event_bus import" in source, (
        "LyricEventBus must wrap the canonical core.event_bus.EventBus"
    )


def test_radio_event_bus_is_typed_wrapper_without_own_state() -> None:
    source = RADIO_EVENTS.read_text(encoding="utf-8")
    assert "_handlers" not in source, (
        "radio EventBus must NOT keep its own handler dict (no second pub/sub)"
    )
    assert "from core.event_bus import" in source


def test_composition_shares_one_canonical_bus(app) -> None:
    from core.event_bus import EventBus

    bootstrap = ApplicationBootstrap()
    bootstrap.build()
    container = bootstrap.container
    canonical = container.get("event_bus")
    assert isinstance(canonical, EventBus)

    lyrics = container.get("lyrics_service")
    assert lyrics is not None
    assert lyrics.event_bus is not None
    assert lyrics.event_bus._bus is canonical, (
        "lyrics event bus must wrap the canonical event_bus instance"
    )

    radio = container.get("radio_service")
    assert radio is not None
    assert radio.event_bus is not None
    assert radio.event_bus._bus is canonical, (
        "radio event bus must wrap the canonical event_bus instance"
    )

    assert container.get("notification_service")._event_bus is canonical
    assert container.get("favorite_service")._eb is canonical


# ── 2. Single DeviceRegistry ──────────────────────────────────────────────


def test_exactly_one_device_registry_in_composition() -> None:
    count = 0
    for path in COMPOSITION_DIR.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        count += len(re.findall(r"DeviceRegistry\(", source))
    assert count == 1, (
        f"Expected exactly 1 'DeviceRegistry(' in composition, found {count}"
    )


def test_single_device_registry_shared_by_consumers(container) -> None:
    registry = container.get("device_registry")
    assert registry is not None

    device_sync = container.get("device_sync_service")
    assert device_sync is not None
    assert device_sync.device_registry is registry, (
        "device_sync_service must hold the composed registry instance"
    )

    mobile_sync = container.get("mobile_sync_service")
    assert mobile_sync is not None
    assert mobile_sync.device_registry is registry, (
        "mobile_sync_service must hold the composed registry instance"
    )


def test_devices_bridge_receives_injected_device_sync(container) -> None:
    from ui_qml_bridge.devices_bridge import DevicesBridge

    bridge = DevicesBridge(device_sync_service=container.get("device_sync_service"))
    assert bridge._dev_svc is container.get("device_sync_service")
    assert "DeviceRegistry(" not in (
        PROJECT_ROOT / "ui_qml_bridge" / "devices_bridge.py"
    ).read_text(encoding="utf-8")


# ── 3. Home Assistant lazy network ────────────────────────────────────────


def test_composition_never_subscribes_home_assistant(app) -> None:
    source = (COMPOSITION_DIR / "ecosystem.py").read_text(encoding="utf-8")
    assert "ha_client.subscribe_events()" not in source, (
        "composition must NOT start HA network (subscribe_events) at build"
    )
    assert "ha_client.connect_to_host" not in source
    assert "configure(" not in source or "ha_client.configure" not in source


def test_home_assistant_constructor_does_not_connect(app) -> None:
    """Constructing the HA client performs no network I/O until enable."""
    from PySide6.QtCore import QObject, Signal

    class FakeWebsocket(QObject):
        state_changed = Signal(dict)
        connection_changed = Signal(bool)

        def __init__(self):
            super().__init__()
            self.calls = []
            self.connected = False

        def connect_to_host(self):
            self.calls.append("connect")

        def stop(self):
            self.calls.append("stop")

        def configure(self, host, token, port=8123):
            self.calls.append("configure")

    from integrations.home_audio_service import HomeAssistantService

    fake = FakeWebsocket()
    client = HomeAssistantService(
        "http://localhost:8123", "tok", websocket_client=fake)
    assert "connect" not in fake.calls, (
        f"constructor must not connect ({fake.calls})"
    )
    # Explicit enable (subscribe_events) is the ONLY thing that connects.
    client.subscribe_events(interval_ms=100000)
    assert "connect" in fake.calls, (
        "subscribe_events must connect (explicit enable)"
    )


# ── 4. FileManagerService single registration ─────────────────────────────


def test_file_manager_service_registered_in_composition() -> None:
    assert "file_manager_service" in SERVICE_MANIFEST
    source = (COMPOSITION_DIR / "library.py").read_text(encoding="utf-8")
    assert 'register("file_manager_service"' in source


def test_no_ad_hoc_file_manager_construction() -> None:
    forbidden = []
    for root in (CORE_DIR, BRIDGE_DIR):
        for path in root.rglob("*.py"):
            if "/tests/" in str(path) or "/composition/" in str(path):
                continue
            source = path.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"FileManagerService\(", source):
                forbidden.append(str(path))
    assert forbidden == [], (
        f"FileManagerService( must never be constructed outside composition: "
        f"{forbidden}"
    )


# ── 5. Recognition advanced stack ─────────────────────────────────────────


def test_recognition_receives_advanced_detection_stack(container) -> None:
    recognition = container.get("recognition_service")
    assert recognition is not None
    assert recognition.provider_manager is not None, (
        "recognition must receive the shared ProviderManager"
    )
    assert recognition.detection_service is not None, (
        "recognition must receive the DetectionService"
    )
    assert recognition.capture is not None, (
        "recognition must receive the AudioCaptureService"
    )
    assert container.get("provider_manager") is recognition.provider_manager, (
        "composition must register the SAME provider_manager instance"
    )
    assert recognition.detection_service._provider_mgr is recognition.provider_manager


# ── 6. No service construction in getters/fallbacks ───────────────────────

_SERVICE_CLASS_RE = re.compile(
    r"^\s*self\._\w+\s*=\s*[A-Za-z_]\w*(?:Service|Manager|Registry|"
    r"Repository|Client|Bridge|Engine|Bus)\(",
    re.M,
)


def test_no_service_construction_in_lazy_getters() -> None:
    findings = []
    for root in (CORE_DIR, BRIDGE_DIR):
        for path in root.rglob("*.py"):
            if "/tests/" in str(path):
                continue
            source = path.read_text(encoding="utf-8", errors="ignore")
            lines = source.splitlines()
            for i, line in enumerate(lines):
                if "if self._" in line and " is None" in line:
                    for j in range(i + 1, min(i + 4, len(lines))):
                        if _SERVICE_CLASS_RE.match(lines[j]):
                            findings.append(f"{path}:{j + 1}: {lines[j].strip()}")
                            break
    # job_manager is LEGACY (S2 retired) — exempt.
    findings = [f for f in findings if "jobs/job_manager.py" not in f]
    assert findings == [], (
        f"lazy getters must not construct services (compose instead): "
        f"{findings}"
    )


# ── 7. No cross-service private access ────────────────────────────────────

_PRIVATE_TARGETS = frozenset({"_db", "_conn", "_mutation", "_repo"})


def _base_is_self(value: ast.AST) -> bool:
    while isinstance(value, ast.Attribute):
        value = value.value
    return isinstance(value, ast.Name) and value.id in ("self", "cls")


def test_no_cross_service_private_attribute_access() -> None:
    findings = []
    for root in (CORE_DIR, BRIDGE_DIR):
        for path in root.rglob("*.py"):
            if "/tests/" in str(path):
                continue
            source = path.read_text(encoding="utf-8", errors="ignore")
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Attribute):
                    continue
                if node.attr not in _PRIVATE_TARGETS:
                    continue
                if _base_is_self(node.value):
                    continue  # same-class direct usage (self._db)
                findings.append(
                    f"{path}:{node.lineno}: {ast.unparse(node)[:80]}")
    findings = [f for f in findings if "jobs/job_manager.py" not in f]
    assert findings == [], (
        f"cross-service private attribute access must go through public "
        f"methods/ports: {findings}"
    )


# ── 8. Handlers use ports only ────────────────────────────────────────────


def test_job_handlers_use_ports_only() -> None:
    source = (CORE_DIR / "jobs" / "handlers.py").read_text(encoding="utf-8")
    module = ast.parse(source)
    docstring = ast.get_docstring(module)
    if docstring:
        source = source.replace(docstring, "")
    assert "container.get" not in source
    assert "ServiceClass(" not in source
    assert "import ServiceContainer" not in source
    assert "SERVICE_MANIFEST" not in source


def test_manifest_describes_new_ports() -> None:
    assert "file_manager_service" in SERVICE_MANIFEST
    assert SERVICE_MANIFEST["provider_manager"].service_class.value == "registry"
    assert "event_bus" in SERVICE_MANIFEST["lyrics_service"].dependencies
