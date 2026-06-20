"""Parametric EQ advanced mode widget."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider,
    QLabel, QScrollArea,
)

from audio.eq_band_row import BandRow


class AdvancedEqWidget(QWidget):
    """Parametric equalizer — configurable number of bands with full control."""
    bands_changed = Signal(list)
    preamp_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[BandRow] = []
        self._band_configs: list[dict] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── Header ──
        header = QHBoxLayout()
        add_btn = QPushButton("+ Añadir banda")
        add_btn.clicked.connect(self._add_band)
        header.addWidget(add_btn)
        header.addStretch()
        header.addWidget(QLabel("Preamp:"))
        self._preamp = QSlider(Qt.Horizontal)
        self._preamp.setRange(-120, 120)
        self._preamp.setValue(0)
        self._preamp.setFixedWidth(120)
        self._preamp_label = QLabel("+0.0dB")
        self._preamp_label.setFixedWidth(44)
        self._preamp_label.setAlignment(Qt.AlignCenter)
        self._preamp_label.setStyleSheet("color: #8e8e93; font-size: 11px;")
        self._preamp.valueChanged.connect(self._on_preamp)
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self.reset)
        header.addWidget(self._preamp)
        header.addWidget(self._preamp_label)
        header.addWidget(reset_btn)
        layout.addLayout(header)

        # ── Band scroll area ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._band_container = QWidget()
        self._band_layout = QVBoxLayout(self._band_container)
        self._band_layout.setContentsMargins(0, 0, 0, 0)
        self._band_layout.setSpacing(2)
        self._band_layout.addStretch()
        scroll.setWidget(self._band_container)
        layout.addWidget(scroll)

        # Start with 7 default bands
        defaults = [
            ("LowShelf", 60, 0.0, 0.7),
            ("Peak", 200, 0.0, 1.0),
            ("Peak", 500, 0.0, 1.4),
            ("Peak", 1500, 0.0, 1.0),
            ("Peak", 4000, 0.0, 1.4),
            ("Peak", 8000, 0.0, 1.0),
            ("HighShelf", 12000, 0.0, 0.7),
        ]
        for i, (ft, f, g, q) in enumerate(defaults):
            self._add_band(ft, f, g, q)

    def _add_band(self, f_type="Peak", freq=1000.0, gain=0.0, Q=1.41):
        row = BandRow(len(self._rows), f_type, freq, gain, Q)
        row.changed.connect(self._on_band_change)
        row.removed.connect(self._remove_band)
        # Insert before the stretch
        self._band_layout.insertWidget(len(self._rows), row)
        self._rows.append(row)
        self._on_band_change()

    def _remove_band(self, row):
        if len(self._rows) <= 1:
            return
        self._rows.remove(row)
        self._band_layout.removeWidget(row)
        row.deleteLater()
        # Re-index
        for i, r in enumerate(self._rows):
            r._index = i
        self._on_band_change()

    def _on_band_change(self):
        configs = [r.get_config() for r in self._rows]
        self._band_configs = configs
        self.bands_changed.emit(configs)

    def _on_preamp(self):
        v = self._preamp.value() / 10.0
        self._preamp_label.setText(f"{v:+.1f}dB")
        self.preamp_changed.emit(v)

    def reset(self):
        for r in self._rows.copy():
            self._remove_band(r)
        defaults = [
            ("LowShelf", 60, 0.0, 0.7),
            ("Peak", 200, 0.0, 1.0),
            ("Peak", 500, 0.0, 1.4),
            ("Peak", 1500, 0.0, 1.0),
            ("Peak", 4000, 0.0, 1.4),
            ("Peak", 8000, 0.0, 1.0),
            ("HighShelf", 12000, 0.0, 0.7),
        ]
        for i, (ft, f, g, q) in enumerate(defaults):
            self._add_band(ft, f, g, q)

    def load_preset(self, bands: list[dict], preamp: float = 0.0):
        """Load a complete parametric preset."""
        for r in self._rows.copy():
            self._remove_band(r)
        for b in bands:
            self._add_band(b.get("type", "Peak"), b.get("freq", 1000),
                          b.get("gain", 0.0), b.get("Q", 1.41))
        self._preamp.setValue(int(preamp * 10))

    def get_config(self) -> tuple[list[dict], float]:
        return (self._band_configs, self._preamp.value() / 10.0)
