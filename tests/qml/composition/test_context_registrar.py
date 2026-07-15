"""Tests for ContextRegistrar — contract validation, duplicates, audit."""
from unittest.mock import Mock

from PySide6.QtCore import QObject
from PySide6.QtQml import QQmlApplicationEngine

from ui_qml_bridge.context_registrar import ContextRegistrar
import pytest
pytestmark = [pytest.mark.qml_module("worker_manager")]


class TestContextRegistrar:
    def test_initial_count_zero(self):
        engine = Mock(spec=QQmlApplicationEngine)
        cr = ContextRegistrar(engine)
        assert cr.count == 0

    def test_register_qobject(self):
        engine = Mock(spec=QQmlApplicationEngine)
        root_ctx = Mock()
        engine.rootContext.return_value = root_ctx
        cr = ContextRegistrar(engine)
        obj = QObject()
        cr.register("testObj", obj)
        assert cr.count == 1
        root_ctx.setContextProperty.assert_called_once_with("testObj", obj)

    def test_register_none_skips(self):
        engine = Mock(spec=QQmlApplicationEngine)
        root_ctx = Mock()
        engine.rootContext.return_value = root_ctx
        cr = ContextRegistrar(engine)
        cr.register("testObj", None)
        assert cr.count == 0

    def test_register_twice_same_type(self):
        engine = Mock(spec=QQmlApplicationEngine)
        root_ctx = Mock()
        engine.rootContext.return_value = root_ctx
        cr = ContextRegistrar(engine)
        cr.register("testObj", QObject())
        cr.register("testObj", QObject())
        assert cr.count == 1
        assert len(cr.duplicates) == 0

    def test_register_duplicate_different_type(self):
        engine = Mock(spec=QQmlApplicationEngine)
        root_ctx = Mock()
        engine.rootContext.return_value = root_ctx
        cr = ContextRegistrar(engine)

        class TypeA(QObject):
            pass

        class TypeB(QObject):
            pass

        cr.register("testObj", TypeA())
        cr.register("testObj", TypeB())
        assert len(cr.duplicates) == 1

    def test_register_dict(self):
        engine = Mock(spec=QQmlApplicationEngine)
        root_ctx = Mock()
        engine.rootContext.return_value = root_ctx
        cr = ContextRegistrar(engine)
        cr.register_dict({"a": QObject(), "b": QObject()})
        assert cr.count == 2

    def test_names_returns_sorted(self):
        engine = Mock(spec=QQmlApplicationEngine)
        root_ctx = Mock()
        engine.rootContext.return_value = root_ctx
        cr = ContextRegistrar(engine)
        cr.register("z", QObject())
        cr.register("a", QObject())
        assert cr.names == ["a", "z"]

    def test_audit_returns_dict(self):
        engine = Mock(spec=QQmlApplicationEngine)
        root_ctx = Mock()
        engine.rootContext.return_value = root_ctx
        cr = ContextRegistrar(engine)
        audit = cr.audit()
        assert "total" in audit
        assert "names" in audit
        assert "duplicates" in audit

    def test_violations_returns_empty_initially(self):
        engine = Mock(spec=QQmlApplicationEngine)
        cr = ContextRegistrar(engine)
        assert cr.violations == []
