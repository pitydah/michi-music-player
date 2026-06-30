"""SongsFilterBar — chip-based filter bar for the premium songs view."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QComboBox, QLineEdit,
)


class SongsFilterBar(QWidget):
    """Compact filter bar with format, quality, genre, year, and text search.

    Emits filters_changed with a dict of active filters.
    """

    filters_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._format_combo = QComboBox()
        self._format_combo.addItem("Todos los formatos", "")
        self._format_combo.currentIndexChanged.connect(self._emit)
        layout.addWidget(QLabel("Formato:"))
        layout.addWidget(self._format_combo)

        self._quality_combo = QComboBox()
        self._quality_combo.addItem("Todas las calidades", "")
        self._quality_combo.addItem("Hi-Res", "hires")
        self._quality_combo.addItem("Lossless", "lossless")
        self._quality_combo.addItem("Lossy", "lossy")
        self._quality_combo.addItem("DSD", "dsd")
        self._quality_combo.currentIndexChanged.connect(self._emit)
        layout.addWidget(QLabel("Calidad:"))
        layout.addWidget(self._quality_combo)

        self._fav_check = QLineEdit()
        self._fav_check.setPlaceholderText("Solo favoritos")
        self._fav_check.setClearButtonEnabled(True)
        layout.addWidget(self._fav_check)

        layout.addStretch()

    def set_formats(self, formats: list[str]):
        current = self._format_combo.currentData()
        self._format_combo.blockSignals(True)
        self._format_combo.clear()
        self._format_combo.addItem("Todos los formatos", "")
        for f in formats:
            self._format_combo.addItem(f, f)
        idx = self._format_combo.findData(current)
        if idx >= 0:
            self._format_combo.setCurrentIndex(idx)
        self._format_combo.blockSignals(False)

    def _emit(self):
        f = self._format_combo.currentData() or None
        q = self._quality_combo.currentData() or None
        payload = {}
        if f:
            payload["formats"] = {f}
        if q:
            payload["quality"] = q
        self.filters_changed.emit(payload)
