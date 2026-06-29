"""ViewController — named view manager for QStackedWidget."""

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QStackedWidget, QWidget, QLabel


class ViewController(QObject):
    view_changed = Signal(str)

    def __init__(self, stack: QStackedWidget, parent=None):
        super().__init__(parent)
        self._stack = stack
        self._views: dict[str, QWidget] = {}
        self._current = ""
        self._placeholder = None

    def _ensure_placeholder(self):
        if self._placeholder is None:
            self._placeholder = QLabel("Vista no disponible")
            self._placeholder.setAlignment(
                __import__("PySide6.QtCore").QtCore.Qt.AlignCenter)
            self._placeholder.setStyleSheet(
                "color: rgba(255,255,255,0.42); font-size: 14px; "
                "background: transparent;")
            self._stack.addWidget(self._placeholder)

    def register(self, name: str, widget: QWidget):
        self._views[name] = widget
        if self._stack.indexOf(widget) < 0:
            self._stack.addWidget(widget)

    def replace(self, name: str, widget: QWidget, delete_old: bool = True):
        old = self._views.get(name)
        if old is widget:
            return
        if old is not None:
            self._stack.removeWidget(old)
            if delete_old:
                old.deleteLater()
        self._views[name] = widget
        self._stack.addWidget(widget)

    def show(self, name: str):
        widget = self._views.get(name)
        if widget is None:
            self._ensure_placeholder()
            self._stack.setCurrentWidget(self._placeholder)
            self._current = ""
            return
        self._stack.setCurrentWidget(widget)
        self._current = name
        self.view_changed.emit(name)

    def lazy_register(self, name: str, factory):
        """Register a view if not already registered, using a factory callable.

        The factory is called only if the view has not been registered yet.
        Returns the (possibly newly created) widget.
        """
        widget = self._views.get(name)
        if widget is None:
            widget = factory()
            self.register(name, widget)
        return widget

    def current(self) -> str:
        return self._current

    def widget(self, name: str) -> QWidget | None:
        return self._views.get(name)
