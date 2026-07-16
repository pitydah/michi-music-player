"""Tests for ViewController."""

import pytest
from PySide6.QtWidgets import QApplication, QStackedWidget, QLabel

from ui.view_controller import ViewController


@pytest.fixture
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def stack(qapp):
    return QStackedWidget()


@pytest.fixture
def vc(stack):
    return ViewController(stack)


def test_register_and_show(vc, stack):
    w1 = QLabel("view1")
    w2 = QLabel("view2")
    vc.register("one", w1)
    vc.register("two", w2)

    assert vc.widget("one") is w1
    assert vc.widget("two") is w2

    vc.show("one")
    assert vc.current() == "one"
    assert stack.currentWidget() is w1

    vc.show("two")
    assert vc.current() == "two"
    assert stack.currentWidget() is w2


def test_replace(vc, stack):
    w1 = QLabel("old")
    w2 = QLabel("new")
    vc.register("main", w1)
    assert vc.widget("main") is w1

    vc.replace("main", w2)
    assert vc.widget("main") is w2
    assert stack.indexOf(w2) >= 0

    # Old widget should be gone from stack
    assert stack.indexOf(w1) < 0


def test_replace_noop(vc, stack):
    w1 = QLabel("same")
    vc.register("main", w1)
    vc.replace("main", w1)  # should be harmless
    assert vc.widget("main") is w1


def test_widget_missing(vc):
    assert vc.widget("nonexistent") is None


def test_show_missing(vc, stack):
    vc.show("nonexistent")
    assert vc.current() == ""  # unchanged


def test_view_changed_signal(vc, qapp):
    w1 = QLabel("view1")
    vc.register("sig", w1)

    emitted = []

    def handler(name):
        emitted.append(name)

    vc.view_changed.connect(handler)
    vc.show("sig")
    assert emitted == ["sig"]
