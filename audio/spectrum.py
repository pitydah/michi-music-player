"""Real-time spectrum analyzer — FFT via numpy, 60-band logarithmic display."""

import numpy as np
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QPainterPath,
)
from PySide6.QtWidgets import QWidget

# 60 log-spaced bands (20 Hz – 20000 Hz)
SPEC_BANDS = 60
SPEC_MIN_HZ = 20
SPEC_MAX_HZ = 20000
SPEC_FREQS = np.logspace(np.log10(SPEC_MIN_HZ), np.log10(SPEC_MAX_HZ), SPEC_BANDS)

SPECTRUM_PALETTE = [
    QColor("#FF7A00"), QColor("#FF7A00"), QColor("#2eb8e6"), QColor("#20c0e0"),
    QColor("#18c8d8"), QColor("#10d0cc"), QColor("#18d8b8"), QColor("#28e0a0"),
    QColor("#40e880"), QColor("#60f058"), QColor("#80f838"), QColor("#a0f820"),
    QColor("#c0f010"), QColor("#dce808"), QColor("#f0d800"), QColor("#f8c000"),
    QColor("#f8a800"), QColor("#f88800"), QColor("#f06800"), QColor("#e84800"),
]


class SpectrumWidget(QWidget):
    """FFT spectrum analyzer. Feed it audio data, it paints bars."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = np.zeros(SPEC_BANDS, dtype=np.float64)
        self._peak = np.zeros(SPEC_BANDS, dtype=np.float64)
        self._decay = 0.85  # exponential decay per frame
        self._peak_decay = 0.95
        self._mode = "bars"  # bars | line | both
        self.setMinimumHeight(120)
        self.setStyleSheet("background: #090B11; border: 1px solid rgba(255,255,255,0.06); border-radius: 12px;")

    def set_mode(self, mode: str):
        self._mode = mode
        self.update()

    def push_fft(self, fft_data: np.ndarray, sample_rate: int = 44100):
        """Push FFT data (full rfft result) and map to log-spaced bands."""
        if len(fft_data) < 2:
            return
        freqs = np.fft.rfftfreq(len(fft_data) * 2 - 2, 1.0 / sample_rate)
        mag = np.abs(fft_data)
        mag_db = 20.0 * np.log10(mag + 1e-12)

        # Map to SPEC_BANDS log-spaced
        mapped = np.zeros(SPEC_BANDS, dtype=np.float64)
        for i in range(SPEC_BANDS):
            lo = SPEC_FREQS[i] / 1.1
            hi = SPEC_FREQS[i] * 1.1 if i < SPEC_BANDS - 1 else SPEC_MAX_HZ * 1.5
            mask = (freqs >= lo) & (freqs < hi)
            if mask.any():
                mapped[i] = np.max(mag_db[mask])

        # Normalize to [0, 1] range (from -60 dB to 0 dB)
        mapped = np.clip((mapped + 60.0) / 60.0, 0.0, 1.0)

        # Exponential smoothing
        self._data = np.maximum(mapped, self._data * self._decay)
        self._peak = np.maximum(self._data, self._peak * self._peak_decay)

        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        margin = 8
        bar_w = (w - margin * 2) / SPEC_BANDS

        # ── Background ──
        p.fillRect(self.rect(), QColor("#090B11"))

        # ── Grid lines ──
        p.setPen(QPen(QColor(255, 255, 255, 15), 1))
        for frac in [0.25, 0.5, 0.75]:
            y = int(h * frac)
            p.drawLine(margin, y, w - margin, y)

        # ── Frequency labels ──
        p.setFont(QFont("sans-serif", 8))
        p.setPen(QColor(255, 255, 255, 45))
        for f_hz in [30, 60, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]:
            idx = int(np.searchsorted(SPEC_FREQS, f_hz))
            x = margin + idx * bar_w
            label = f"{f_hz // 1000}k" if f_hz >= 1000 else str(f_hz)
            p.drawText(int(x - 10), h - 2, label)

        # ── Bars ──
        if self._mode in ("bars", "both"):
            for i in range(SPEC_BANDS):
                bar_h = self._data[i] * (h - margin * 2)
                if bar_h < 1:
                    continue
                x = margin + i * bar_w
                # Color from palette based on position
                ci = min(i * len(SPECTRUM_PALETTE) // SPEC_BANDS, len(SPECTRUM_PALETTE) - 1)
                p.fillRect(QRectF(x, h - margin - bar_h, max(bar_w - 1, 1), bar_h),
                          SPECTRUM_PALETTE[ci])

        # ── Line mode ──
        if self._mode in ("line", "both"):
            path = QPainterPath()
            first = True
            for i in range(SPEC_BANDS):
                y = h - margin - self._data[i] * (h - margin * 2)
                x = margin + i * bar_w + bar_w / 2
                if first:
                    path.moveTo(x, y)
                    first = False
                else:
                    path.lineTo(x, y)
            p.setPen(QPen(QColor("#FF7A00"), 1.5))
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)

        # ── Peak dots ──
        if self._mode in ("bars", "both"):
            p.setPen(QPen(QColor("#ffffff"), 1))
            for i in range(SPEC_BANDS):
                y = h - margin - self._peak[i] * (h - margin * 2)
                if self._peak[i] > 0.05:
                    x = margin + i * bar_w + bar_w / 2
                    p.drawEllipse(int(x - 2), int(y - 2), 4, 4)
