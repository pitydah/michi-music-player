"""CentralContentSurface — dark glass container for header + stacked views."""
from PySide6.QtWidgets import QWidget

from ui.central.central_styles import content_surface_qss


class CentralContentSurface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("contentSurface")
        self.setStyleSheet(content_surface_qss())
        # Layout created externally by window.py via QVBoxLayout(cw)

    def set_header(self, header_widget):
        self.layout().insertWidget(0, header_widget)

    def set_content(self, stack_widget):
        self.layout().addWidget(stack_widget, 1)
