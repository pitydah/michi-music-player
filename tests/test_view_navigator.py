"""Tests for ViewNavigator — requires QStackedWidget + ViewController via pytest-qt."""
from PySide6.QtWidgets import QStackedWidget
from ui.view_controller import ViewController
from ui.view_navigator import ViewNavigator


def test_init(qtbot):
    stack = QStackedWidget()
    vc = ViewController(stack)
    nav = ViewNavigator(stack, stack, vc)
    assert nav._content is stack


def test_show(qtbot):
    stack = QStackedWidget()
    vc = ViewController(stack)

    w1 = QStackedWidget()
    w2 = QStackedWidget()
    vc.register("view1", w1)
    vc.register("view2", w2)

    nav = ViewNavigator(stack, stack, vc)
    nav._widgets = [stack]

    nav.show("view2")
    # Should not crash — shows view2 with subtle fade


def test_restore_opacity(qtbot):
    stack = QStackedWidget()
    vc = ViewController(stack)
    nav = ViewNavigator(stack, stack, vc)
    nav._widgets = [stack]

    nav.restore_opacity()
    # Should not crash
