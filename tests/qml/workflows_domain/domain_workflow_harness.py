from __future__ import annotations

import contextlib
import logging
import sys
import time
from typing import Any

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QGuiApplication, QKeySequence
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtTest import QTest
from PySide6.QtQuick import QQuickItem

logger = logging.getLogger("michi.domain_harness")

_APP: QGuiApplication | None = None


def create_app() -> QGuiApplication:
    global _APP
    if _APP is None:
        _APP = QGuiApplication(sys.argv if sys.argv else [])
    return _APP


def create_engine(parent=None) -> QQmlEngine:
    return QQmlEngine(parent)


def register_mock_bridge(engine: QQmlEngine, name: str, bridge: QObject):
    engine.rootContext().setContextProperty(name, bridge)


def register_contract_doubles(engine: QQmlEngine, doubles: dict[str, QObject]):
    for name, obj in doubles.items():
        register_mock_bridge(engine, name, obj)


def load_page(engine: QQmlEngine, qml_path: str,
              context_properties: dict[str, QObject] | None = None) -> QQmlComponent:
    for name, obj in (context_properties or {}).items():
        register_mock_bridge(engine, name, obj)
    component = QQmlComponent(engine)
    component.loadUrl(qml_path)
    if component.isError():
        errors = component.errors()
        raise RuntimeError(f"QML load errors for {qml_path}: {errors}")
    return component


def create_page(engine: QQmlEngine, qml_path: str,
                context_properties: dict[str, QObject] | None = None) -> QQuickItem:
    component = load_page(engine, qml_path, context_properties)
    obj = component.create()
    if obj is None:
        raise RuntimeError(f"Failed to create object from {qml_path}: {component.errors()}")
    return obj


def find_control(root: QQuickItem, object_name: str) -> QQuickItem | None:
    if not root:
        return None
    if root.objectName() == object_name:
        return root
    for child in root.childItems():
        result = find_control(child, object_name)
        if result is not None:
            return result
    return None


def click_control(control: QQuickItem):
    if control is None:
        return
    window = control.window()
    if window:
        QTest.mouseClick(window, Qt.LeftButton, pos=control.pos().toPoint())
    else:
        logger.warning("click_control: no window for %s", control.objectName())


def key_click(control: QQuickItem, key: str | int):
    if control is None:
        return
    window = control.window()
    if not window:
        logger.warning("key_click: no window for %s", control.objectName())
        return
    if isinstance(key, str):
        seq = QKeySequence(key)
        if seq.count() > 0:
            QTest.keyClick(window, seq[0].key())
        else:
            logger.warning("key_click: invalid key string %r", key)
    else:
        QTest.keyClick(window, key)


def wait_for_signal(signal: Signal, timeout_ms: int = 5000) -> bool:
    result = [False]

    def handler(*_args):
        result[0] = True

    signal.connect(handler)
    deadline = time.monotonic() + timeout_ms / 1000.0
    while not result[0] and time.monotonic() < deadline:
        QGuiApplication.processEvents()
    with contextlib.suppress(RuntimeError, TypeError):
        signal.disconnect(handler)
    return result[0]


def verify_state(control: QQuickItem, prop: str, expected: Any) -> bool:
    if control is None:
        logger.error("verify_state: control is None for property %s", prop)
        return False
    actual = control.property(prop)
    if actual != expected:
        logger.error(
            "verify_state: %s.%s expected=%r actual=%r",
            control.objectName(), prop, expected, actual,
        )
        return False
    return True


def verify_double_state(double: QObject, prop: str, expected: Any) -> bool:
    actual = getattr(double, prop, None)
    if callable(actual):
        actual = actual()
    if actual != expected:
        logger.error(
            "verify_double_state: %s expected=%r actual=%r",
            prop, expected, actual,
        )
        return False
    return True


def destroy_page(page: QQuickItem):
    if page is None:
        return
    with contextlib.suppress(RuntimeError):
        page.setParent(None)
    with contextlib.suppress(RuntimeError):
        page.deleteLater()


def verify_cleanup(engine: QQmlEngine) -> bool:
    try:
        engine.clearComponentCache()
        engine.collectGarbage()
    except RuntimeError:
        return False
    return True


class DomainHarness:
    def __init__(self, qml_dir, qml_path):
        self.qml_dir = qml_dir
        self.qml_path = qml_path
        self.app = create_app()
        self.engine = create_engine()
        self.page = None
        self.doubles = {}

    def register_double(self, name: str, double: QObject):
        self.doubles[name] = double
        register_mock_bridge(self.engine, name, double)

    def register_doubles(self, doubles: dict[str, QObject]):
        for name, obj in doubles.items():
            self.register_double(name, obj)

    def load(self):
        self.engine.addImportPath(str(self.qml_dir))
        self.page = create_page(self.engine, self.qml_path, self.doubles)
        return self.page

    def find(self, object_name: str) -> QQuickItem | None:
        return find_control(self.page, object_name)

    def verify(self, control_name: str, prop: str, expected: Any) -> bool:
        control = self.find(control_name)
        return verify_state(control, prop, expected)

    def verify_double(self, name: str, prop: str, expected: Any) -> bool:
        double = self.doubles.get(name)
        if not double:
            return False
        return verify_double_state(double, prop, expected)

    def click(self, control_name: str):
        control = self.find(control_name)
        click_control(control)

    def key(self, control_name: str, key: str | int):
        control = self.find(control_name)
        key_click(control, key)

    def teardown(self):
        if self.page:
            destroy_page(self.page)
            self.page = None
        verify_cleanup(self.engine)
