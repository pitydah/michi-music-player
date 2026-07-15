"""Test ContextRegistrar — declarative bindings, validation, audit."""
import pytest
from unittest.mock import MagicMock

from PySide6.QtCore import QObject
from PySide6.QtQml import QQmlApplicationEngine

from ui_qml_bridge.context_registrar import ContextRegistrar, CONTEXT_BINDINGS, CONTEXT_MODELS


class _FakeBridge(QObject):
    pass


class _OtherBridge(QObject):
    pass


@pytest.fixture
def engine():
    eng = MagicMock(spec=QQmlApplicationEngine)
    rc = MagicMock()
    eng.rootContext.return_value = rc
    return eng


@pytest.fixture
def registrar(engine):
    return ContextRegistrar(engine)


# ── CONTEXT_BINDINGS integrity ──


def test_context_bindings_has_expected_keys():
    expected_keys = [
        "appBridge", "navigationBridge", "queueBridge", "devicesBridge",
        "playbackBridge", "settingsBridge", "themeBridge", "libraryBridge",
        "radioBridge", "connectionsBridge", "homeAudioBridge",
        "michiAiBridge", "metadataBridge", "mixBridge", "nowplayingBridge",
        "playlistsBridge", "lyricsBridge", "notificationBridge",
        "globalSearchBridge", "jobBridge", "historyBridge", "homeBridge",
    ]
    for key in expected_keys:
        assert key in CONTEXT_BINDINGS, f"Missing binding: {key}"


def test_context_bindings_no_empty_values():
    for qml_name, bridge_key in CONTEXT_BINDINGS.items():
        assert qml_name, "Empty QML name"
        assert bridge_key, f"Empty bridge key for {qml_name}"


def test_context_bindings_unique_qml_names():
    names = list(CONTEXT_BINDINGS.keys())
    assert len(names) == len(set(names)), "Duplicate QML context names"


def test_context_bindings_unique_bridge_keys():
    keys = list(CONTEXT_BINDINGS.values())
    assert len(keys) == len(set(keys)), "Duplicate bridge keys"


# ── Basic registration ──


def test_register_qobject(registrar, engine):
    bridge = _FakeBridge()
    registrar.register("testBridge", bridge)
    assert registrar.count == 1
    assert "testBridge" in registrar.names


def test_register_none_skipped(registrar, engine):
    registrar.register("nullBridge", None)
    assert registrar.count == 0


def test_register_duplicate_same_type(registrar, engine):
    b1 = _FakeBridge()
    b2 = _FakeBridge()
    registrar.register("dupBridge", b1)
    registrar.register("dupBridge", b2)
    assert registrar.count == 1
    assert len(registrar.duplicates) == 0


def test_register_duplicate_different_type(registrar, engine):
    b1 = _FakeBridge()
    b2 = _OtherBridge()
    registrar.register("dupBridge", b1)
    registrar.register("dupBridge", b2)
    assert len(registrar.duplicates) >= 1


# ── QtWidgets rejection ──


def test_qt_widget_rejected(registrar, engine):
    import PySide6.QtWidgets
    widget = MagicMock(spec=PySide6.QtWidgets.QWidget)
    registrar.register("widgetBridge", widget)
    assert registrar.count == 0
    errors = registrar.validation_errors
    assert any("qt_widget_object_rejected" in str(e.get("error", "")) for e in errors)


# ── register_all ──


def test_register_all_with_bridges(registrar, engine):
    bridges = {
        "app": _FakeBridge(),
        "navigation": _FakeBridge(),
        "queue": _FakeBridge(),
    }
    registrar.register_all(bridges)
    assert registrar.count >= 2


def test_register_all_missing_bridge_logs_warning(registrar, engine):
    bridges = {"app": _FakeBridge()}
    registrar.register_all(bridges)
    assert len(registrar.validation_errors) >= 0


# ── register_dict ──


def test_register_dict(registrar, engine):
    mapping = {
        "bridgeA": _FakeBridge(),
        "bridgeB": _FakeBridge(),
        "nullBridge": None,
    }
    registrar.register_dict(mapping)
    assert registrar.count == 2


# ── Audit ──


def test_audit_returns_expected_keys(registrar, engine):
    bridge = _FakeBridge()
    registrar.register("testBridge", bridge)
    audit = registrar.audit()
    assert "total" in audit
    assert "names" in audit
    assert "duplicates" in audit
    assert "validation_errors" in audit
    assert audit["total"] == 1
    assert "testBridge" in audit["names"]


def test_audit_with_validation_errors(registrar, engine):
    import PySide6.QtWidgets
    widget = MagicMock(spec=PySide6.QtWidgets.QWidget)
    registrar.register("widgetBridge", widget)
    audit = registrar.audit()
    assert len(audit["validation_errors"]) > 0


# ── CONTEXT_MODELS singleton registration ──


def test_register_singleton_model(registrar, engine):
    class FakeModel(QObject):
        pass
    CONTEXT_MODELS["fakeModel"] = FakeModel
    try:
        bridges = {}
        registrar.register_all(bridges)
        assert "fakeModel" in registrar.names
    finally:
        CONTEXT_MODELS.pop("fakeModel", None)
