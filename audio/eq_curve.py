"""Frequency response curve widget — QPainterPath from biquad evaluation."""

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QPainter, QColor, QPen, QFont, QPainterPath,
)
from PySide6.QtWidgets import QWidget

from audio.eq_biquad import eval_response


class EqCurveWidget(QWidget):
    """Plots combined frequency response of all active EQ bands."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bands = []
        self._preamp_db = 0.0
        self._freqs = np.logspace(1.3, 4.3, 512)  # 20Hz–20kHz log
        self._response = np.zeros(512)
        self.setMinimumHeight(100)
        self.setStyleSheet("background: #090B11; border: 1px solid rgba(255,255,255,0.06); border-radius: 12px;")

    def set_bands(self, bands: list[dict], preamp_db: float = 0.0):
        self._bands = bands
        self._preamp_db = preamp_db
        self._response = eval_response(bands, self._freqs, preamp_db)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        margin = 8

        p.fillRect(self.rect(), QColor("#090B11"))

        # ── Grid ──
        p.setPen(QPen(QColor(255, 255, 255, 15), 1))
        # Horizontal: dB lines
        for db in [-9, -6, -3, 0, 3, 6, 9]:
            y = margin + (h - margin * 2) * (1.0 - (db + 12.0) / 24.0)
            p.drawLine(margin, int(y), w - margin, int(y))

        # Vertical: octave lines
        p.setFont(QFont("sans-serif", 8))
        p.setPen(QColor(255, 255, 255, 45))
        for f in [30, 60, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]:
            idx = np.searchsorted(self._freqs, f)
            x = margin + (w - margin * 2) * idx / len(self._freqs)
            p.drawLine(int(x), margin, int(x), h - margin)
            label = f"{f // 1000}k" if f >= 1000 else str(f)
            p.drawText(int(x) - 10, h - 2, label)

        # ── Zero line ──
        zero_y = margin + (h - margin * 2) * 0.5
        p.setPen(QPen(QColor(255, 255, 255, 25), 1, Qt.DashLine))
        p.drawLine(margin, int(zero_y), w - margin, int(zero_y))

        # ── Response curve ──
        if len(self._response) < 2:
            return

        path = QPainterPath()
        for i, db in enumerate(self._response):
            x = margin + (w - margin * 2) * i / (len(self._response) - 1)
            y = margin + (h - margin * 2) * (1.0 - (db + 12.0) / 24.0)
            y = max(margin, min(h - margin, y))
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)

        # Fill under curve
        fill_path = QPainterPath(path)
        fill_path.lineTo(w - margin, zero_y)
        fill_path.lineTo(margin, zero_y)
        fill_path.closeSubpath()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 122, 0, 30))
        p.setOpacity(0.25)
        p.drawPath(fill_path)
        p.setOpacity(1.0)

        # Curve line
        p.setPen(QPen(QColor("#FF7A00"), 2))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
