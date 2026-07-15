from __future__ import annotations

import contextlib
import logging
import sys
import time
from typing import Any, Callable

from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication, QKeySequence
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtTest import QTest
from PySide6.QtQuick import QQuickItem

logger = logging.getLogger("michi.qml_harness")

_APP: QGuiApplication | None = None


class MockContractBridge(QObject):
    stateChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._handlers: dict[str, Callable] = {}

    def register_handler(self, name: str, handler: Callable):
        self._handlers[name] = handler

    @Slot(result=dict)
    def refresh(self):
        return {"ok": True}

    @Slot(str, result=dict)
    def genericAction(self, action: str):
        handler = self._handlers.get(action)
        if handler:
            return handler()
        return {"ok": False, "error": f"UNKNOWN_ACTION:{action}"}


def create_app() -> QGuiApplication:
    global _APP
    if _APP is None:
        _APP = QGuiApplication(sys.argv if sys.argv else [])
    return _APP


def create_engine(parent=None) -> QQmlEngine:
    engine = QQmlEngine(parent)
    return engine


def register_mock_bridge(engine: QQmlEngine, name: str, bridge: QObject):
    engine.rootContext().setContextProperty(name, bridge)


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
        QTest.mouseClick(window, control.pos().toPoint(), Qt.LeftButton)
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


def destroy_page(page: QQuickItem):
    if page is None:
        return
    with contextlib.suppress(RuntimeError):
        page.setParent(None)
    with contextlib.suppress(RuntimeError):
        page.deleteLater()


def check_cleanup(engine: QQmlEngine) -> bool:
    try:
        engine.clearComponentCache()
        engine.collectGarbage()
    except RuntimeError:
        return False
    return True


class HarnessEventLoop:
    def __init__(self, timeout_ms: int = 5000):
        self._timeout_ms = timeout_ms
        self._finished = False
        self._result: Any = None

    def run(self, callback: Callable[[], Any]) -> Any:
        self._result = None
        self._finished = False
        QTimer.singleShot(0, self._do_run, callback)
        deadline = time.monotonic() + self._timeout_ms / 1000.0
        while not self._finished and time.monotonic() < deadline:
            QGuiApplication.processEvents()
        return self._result

    def _do_run(self, callback: Callable[[], Any]):
        try:
            self._result = callback()
        except Exception as e:
            self._result = e
        finally:
            self._finished = True
