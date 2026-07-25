"""Offscreen behavioral rendering tests for the canonical queue page."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QObject, QSize, QUrl, qInstallMessageHandler
from PySide6.QtQuick import QQuickItem, QQuickView

pytestmark = [pytest.mark.qml_module("queue")]
from PySide6.QtTest import QTest

from core.queue_service import QueueService
from ui_qml_bridge.queue_bridge import QueueBridge


QML_DIR = Path(__file__).resolve().parents[3] / "ui_qml"
CRITICAL_MARKERS = (
    "ReferenceError",
    "TypeError",
    "Binding loop",
    "Cannot assign",
    "failed to load",
)


@pytest.fixture
def qml_messages() -> Iterator[list[str]]:
    messages: list[str] = []
    previous = qInstallMessageHandler(
        lambda _message_type, _context, message: messages.append(message)
    )
    try:
        yield messages
    finally:
        qInstallMessageHandler(previous)


def _process(qapp) -> None:
    qapp.processEvents()
    QTest.qWait(30)
    qapp.processEvents()


def _queue_page(qapp, items: list[dict], current_index: int = -1):
    service = QueueService()
    if items:
        result = service.replace(items, start_index=current_index)
        assert result["ok"] is True
    bridge = QueueBridge(queue_service=service)
    view = QQuickView()
    view.engine().addImportPath(str(QML_DIR))
    view.rootContext().setContextProperty("queueBridge", bridge)
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(QSize(1000, 700))
    view.setSource(QUrl.fromLocalFile(str(QML_DIR / "pages/queue/QueuePage.qml")))
    assert view.status() == QQuickView.Ready, [error.toString() for error in view.errors()]
    view.show()
    _process(qapp)
    page = view.rootObject()
    assert page is not None
    return view, page, bridge, service


def _delegates(page: QObject) -> list[QObject]:
    pending = [page]
    delegates = []
    while pending:
        child = pending.pop()
        if child.objectName() == "queueItem_control":
            delegates.append(child)
        if isinstance(child, QQuickItem):
            pending.extend(child.childItems())
    return sorted(delegates, key=lambda child: child.property("itemIndex"))


def _assert_no_critical_messages(messages: list[str]) -> None:
    critical = [
        message
        for message in messages
        if any(marker.lower() in message.lower() for marker in CRITICAL_MARKERS)
    ]
    assert critical == [], "Critical Qt/QML diagnostics:\n" + "\n".join(critical)


def test_empty_queue_renders_explicit_empty_page_state(qapp, qml_messages) -> None:
    view, page, bridge, _service = _queue_page(qapp, [])
    try:
        assert page.property("pageState") == page.property("stateEmpty")
        assert _delegates(page) == []
        _assert_no_critical_messages(qml_messages)
    finally:
        bridge.shutdown()
        view.close()
        view.deleteLater()


def test_populated_queue_renders_canonical_delegate_order(qapp, qml_messages) -> None:
    items = [
        {"title": "Alpha", "artist": "One", "duration": 61},
        {"title": "Beta", "artist": "Two", "duration": 122},
    ]
    view, page, bridge, _service = _queue_page(qapp, items, current_index=0)
    try:
        delegates = _delegates(page)
        assert [delegate.property("itemTitle") for delegate in delegates] == [
            "Alpha",
            "Beta",
        ]
        assert [delegate.property("itemArtist") for delegate in delegates] == [
            "One",
            "Two",
        ]
        _assert_no_critical_messages(qml_messages)
    finally:
        bridge.shutdown()
        view.close()
        view.deleteLater()


def test_current_queue_delegate_follows_canonical_index(qapp, qml_messages) -> None:
    items = [{"title": "First"}, {"title": "Current"}, {"title": "Last"}]
    view, page, bridge, _service = _queue_page(qapp, items, current_index=1)
    try:
        delegates = _delegates(page)
        assert [delegate.property("itemIsCurrent") for delegate in delegates] == [
            False,
            True,
            False,
        ]
        assert delegates[1].property("itemTitle") == "Current"
        _assert_no_critical_messages(qml_messages)
    finally:
        bridge.shutdown()
        view.close()
        view.deleteLater()


def test_reorder_updates_rendered_rows_without_stale_delegate(qapp, qml_messages) -> None:
    items = [{"title": "First"}, {"title": "Second"}, {"title": "Third"}]
    view, page, bridge, service = _queue_page(qapp, items, current_index=0)
    try:
        result = service.reorder(0, 2)
        assert result["ok"] is True
        _process(qapp)

        delegates = _delegates(page)
        assert [delegate.property("itemTitle") for delegate in delegates] == [
            "Second",
            "Third",
            "First",
        ]
        assert [delegate.property("itemIsCurrent") for delegate in delegates] == [
            False,
            False,
            True,
        ]
        _assert_no_critical_messages(qml_messages)
    finally:
        bridge.shutdown()
        view.close()
        view.deleteLater()
