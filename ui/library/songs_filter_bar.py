"""SongsFilterBar — filter bar for the premium songs view.

Emits filters_changed with a SongsFilterState.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QComboBox, QCheckBox, QLineEdit,
)

from library.songs_view_state import SongsFilterState


class SongsFilterBar(QWidget):
    filters_changed = Signal(SongsFilterState)

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
        self._quality_combo.addItem("Todas calidades", "")
        self._quality_combo.addItem("Hi-Res", "hires")
        self._quality_combo.addItem("Lossless", "lossless")
        self._quality_combo.addItem("Lossy", "lossy")
        self._quality_combo.addItem("DSD", "dsd")
        self._quality_combo.currentIndexChanged.connect(self._emit)
        layout.addWidget(QLabel("Calidad:"))
        layout.addWidget(self._quality_combo)

        self._sr_input = QLineEdit()
        self._sr_input.setPlaceholderText("Sample Rate min (kHz)")
        self._sr_input.setFixedWidth(100)
        self._sr_input.textChanged.connect(self._emit)
        layout.addWidget(self._sr_input)

        self._fav_check = QCheckBox("♥ Favoritos")
        self._fav_check.stateChanged.connect(self._emit)
        layout.addWidget(self._fav_check)

        self._meta_check = QCheckBox("Sin metadata")
        self._meta_check.stateChanged.connect(self._emit)
        layout.addWidget(self._meta_check)

        self._cover_check = QCheckBox("Sin carátula")
        self._cover_check.stateChanged.connect(self._emit)
        layout.addWidget(self._cover_check)

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

    def _emit(self, _=None):
        f = self._format_combo.currentData() or None
        q = self._quality_combo.currentData() or None
        sr_text = self._sr_input.text().strip()
        sr_min = None
        if sr_text:
            import contextlib
            with contextlib.suppress(ValueError):
                sr_min = int(float(sr_text) * 1000)
        state = SongsFilterState(
            formats=frozenset({f}) if f else frozenset(),
            qualities=frozenset({q}) if q else frozenset(),
            sample_rate_min=sr_min,
            only_favorites=bool(self._fav_check.isChecked()),
            only_missing_metadata=bool(self._meta_check.isChecked()),
            only_missing_cover=bool(self._cover_check.isChecked()),
        )
        self.filters_changed.emit(state)
