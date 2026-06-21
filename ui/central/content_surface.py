"""CentralContentSurface — dark glass container for header + stacked views."""
from PySide6.QtWidgets import QWidget, QVBoxLayout

from ui.central.central_styles import content_surface_qss


class CentralContentSurface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("contentSurface")
        self.setStyleSheet(content_surface_qss())

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

    def set_header(self, header_widget):
        self._main_layout.insertWidget(0, header_widget)

    def set_content(self, stack_widget):
        self._main_layout.addWidget(stack_widget, 1)
