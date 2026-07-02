"""RadioLiveTab — wraps the existing RadioWidget inside the Broadcast hub."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout

from streaming.radio_widget import RadioWidget
from streaming.radio_manager import RadioManager


class RadioLiveTab(QWidget):
    station_selected = Signal(str, str)
    add_station_requested = Signal()

    def __init__(self, radio_manager: RadioManager | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("radioLiveTab")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._radio_widget = RadioWidget(radio_manager)
        self._radio_widget.station_selected.connect(self._on_station_selected)
        layout.addWidget(self._radio_widget)

    def _on_station_selected(self, url: str, name: str):
        self.station_selected.emit(url, name)

    def set_filter(self, text: str):
        self._radio_widget.set_filter(text)

    def add_station(self):
        self._radio_widget._add_station()
