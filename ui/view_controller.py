"""ViewController — named view manager for QStackedWidget."""

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QStackedWidget, QWidget


class ViewController(QObject):
    view_changed = Signal(str)

    def __init__(self, stack: QStackedWidget, parent=None):
        super().__init__(parent)
        self._stack = stack
        self._views: dict[str, int] = {}
        self._current = ""

    def register(self, name: str, widget: QWidget):
        idx = self._stack.addWidget(widget)
        self._views[name] = idx

    def show(self, name: str):
        if name in self._views:
            self._stack.setCurrentIndex(self._views[name])
            self._current = name
            self.view_changed.emit(name)

    def current(self) -> str:
        return self._current

    def widget(self, name: str) -> QWidget | None:
        if name in self._views:
            return self._stack.widget(self._views[name])
        return None
