"""Parametric EQ band row widget — a single configurable filter band."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QComboBox, QSlider, QLabel, QPushButton,
)

from audio.eq_biquad import FILTER_LABELS


class BandRow(QWidget):
    """One parametric EQ band: type combo + freq + gain + Q + remove button."""

    removed = Signal(object)
    changed = Signal()

    def __init__(self, band_index: int,
                 f_type: str = "Peak", freq: float = 1000.0,
                 gain: float = 0.0, Q: float = 1.41, parent=None):
        super().__init__(parent)
        self._index = band_index
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        # ── Label ──
        lbl = QLabel(f"#{band_index + 1}")
        lbl.setFixedWidth(24)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #8e8e93; font-weight: 600;")
        layout.addWidget(lbl)

        # ── Type combo ──
        self._type = QComboBox()
        for key, name in FILTER_LABELS.items():
            self._type.addItem(name, key)
        idx = self._type.findData(f_type)
        if idx >= 0:
            self._type.setCurrentIndex(idx)
        self._type.setFixedWidth(100)
        self._type.currentIndexChanged.connect(lambda: self.changed.emit())
        layout.addWidget(self._type)

        # ── Frequency ──
        layout.addWidget(QLabel("F:"))
        self._freq = self._make_slider(10, 24000, int(freq))
        self._freq.setFixedWidth(100)
        self._freq_label = QLabel(self._freq_label_text(freq))
        self._freq_label.setFixedWidth(42)
        self._freq_label.setAlignment(Qt.AlignCenter)
        self._freq_label.setStyleSheet("color: #8e8e93; font-size: 11px;")
        self._freq.valueChanged.connect(self._on_freq)
        layout.addWidget(self._freq)
        layout.addWidget(self._freq_label)

        # ── Gain ──
        layout.addWidget(QLabel("G:"))
        self._gain = self._make_slider(-120, 120, int(gain * 10))
        self._gain.setFixedWidth(100)
        self._gain_label = QLabel(f"{gain:+.1f}dB")
        self._gain_label.setFixedWidth(42)
        self._gain_label.setAlignment(Qt.AlignCenter)
        self._gain_label.setStyleSheet("color: #8e8e93; font-size: 11px;")
        self._gain.valueChanged.connect(self._on_gain)
        layout.addWidget(self._gain)
        layout.addWidget(self._gain_label)

        # ── Q ──
        layout.addWidget(QLabel("Q:"))
        self._q = self._make_slider(10, 400, int(Q * 10))
        self._q.setFixedWidth(80)
        self._q_label = QLabel(f"{Q:.2f}")
        self._q_label.setFixedWidth(36)
        self._q_label.setAlignment(Qt.AlignCenter)
        self._q_label.setStyleSheet("color: #8e8e93; font-size: 11px;")
        self._q.valueChanged.connect(self._on_q)
        layout.addWidget(self._q)
        layout.addWidget(self._q_label)

        # ── Remove ──
        rm = QPushButton("✕")
        rm.setFlat(True)
        rm.setFixedSize(24, 24)
        rm.setStyleSheet("QPushButton { color: #8e8e93; } QPushButton:hover { color: #FF3C48; }")
        rm.clicked.connect(lambda: self.removed.emit(self))
        layout.addWidget(rm)

    def _make_slider(self, lo, hi, val):
        s = QSlider(Qt.Horizontal)
        s.setRange(lo, hi)
        s.setValue(val)
        s.setStyleSheet("QSlider::groove:horizontal { height: 3px; }")
        return s

    def _on_freq(self):
        v = self._freq.value()
        self._freq_label.setText(self._freq_label_text(v))
        self.changed.emit()

    def _on_gain(self):
        v = self._gain.value() / 10.0
        self._gain_label.setText(f"{v:+.1f}dB")
        self.changed.emit()

    def _on_q(self):
        v = self._q.value() / 10.0
        self._q_label.setText(f"{v:.2f}")
        self.changed.emit()

    @staticmethod
    def _freq_label_text(freq: int) -> str:
        if freq >= 1000:
            return f"{freq / 1000:.1f}k"
        return str(freq)

    # Public API

    def get_config(self) -> dict:
        return {
            "type": self._type.currentData(),
            "freq": self._freq.value(),
            "gain": self._gain.value() / 10.0,
            "Q": self._q.value() / 10.0,
        }

    def set_config(self, f_type: str, freq: float, gain: float, Q: float):
        idx = self._type.findData(f_type)
        if idx >= 0:
            self._type.setCurrentIndex(idx)
        self._freq.setValue(int(freq))
        self._gain.setValue(int(gain * 10))
        self._q.setValue(int(Q * 10))
        self._on_freq(); self._on_gain(); self._on_q()
