"""31-band graphic equalizer widget — basic mode."""

from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QFont, QPen
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QScrollArea,
)

from audio.eq_presets import ISO_31_LABELS


def _db_to_y(db: float, h: int) -> int:
    """Map dB value [-12, +12] to Y position [h-1, 0]."""
    ratio = (db + 12.0) / 24.0
    return int((1.0 - ratio) * (h - 1))


def _y_to_db(y: int, h: int) -> float:
    """Map Y position to dB [-12, +12]."""
    ratio = 1.0 - (y / max(h - 1, 1))
    return round((ratio * 24.0 - 12.0) * 10) / 10.0


class BandSlider(QWidget):
    """Single vertical EQ band: slider + frequency label."""
    value_changed = Signal(float)

    def __init__(self, freq_label: str, parent=None):
        super().__init__(parent)
        self._value = 0.0
        self._hover = False
        self._dragging = False
        self._label = freq_label
        self.setFixedWidth(22)
        self.setMinimumHeight(100)
        self.setMouseTracking(True)

    def set_value(self, db: float):
        self._value = max(-12.0, min(12.0, db))
        self.update()

    def value(self) -> float:
        return self._value

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        label_h = 14
        db_h = 14

        # ── Groove ──
        groove_x = 5; groove_w = 12
        groove_rect = QRectF(groove_x, 2, groove_w, h - label_h - db_h - 6)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 18))
        p.drawRoundedRect(groove_rect, 4, 4)

        # ── Zero line ──
        zero_y = 2 + _db_to_y(0, h - label_h - db_h - 6)
        p.setPen(QPen(QColor(255, 255, 255, 30), 1))
        p.drawLine(int(groove_x), int(zero_y), int(groove_x + groove_w), int(zero_y))

        # ── Fill ──
        fill_top = 2 + _db_to_y(self._value, h - label_h - db_h - 6)
        fill_bottom = zero_y if self._value >= 0 else fill_top
        fill_h = abs(fill_bottom - fill_top)
        if fill_h > 0:
            gradient = QLinearGradient(0, 0, 0, h)
            gradient.setColorAt(0, QColor(255, 122, 0, 160))
            gradient.setColorAt(1, QColor(232, 0, 109, 120))
            p.setBrush(gradient)
            fill_rect = QRectF(groove_x, min(fill_top, fill_bottom),
                              groove_w, fill_h + 0.5)
            p.drawRoundedRect(fill_rect, 3, 3)

        # ── Handle ──
        handle_y = 2 + _db_to_y(self._value, h - label_h - db_h - 6)
        handle_size = 20 if self._hover or self._dragging else 16
        p.setBrush(QColor("#ffffff"))
        p.setPen(QPen(QColor(255, 122, 0, 80), 1.5))
        hx = (w - handle_size) // 2
        p.drawRoundedRect(QRectF(hx, handle_y - 4, handle_size, 8), 3, 3)

        # ── Label (Hz) ──
        p.setPen(QColor(255, 255, 255, 85))
        p.setFont(QFont("sans-serif", 8.5))
        p.drawText(QRectF(0, h - label_h - db_h, w, label_h),
                   Qt.AlignHCenter | Qt.AlignTop, self._label)

        # ── Value (dB) ──
        db_str = f"{self._value:+.1f}" if self._value != 0 else "0"
        p.setPen(QColor(255, 255, 255, 100) if self._value == 0 else
                 QColor(255, 122, 0, 180) if self._value > 0 else
                 QColor(255, 100, 80, 160))
        p.setFont(QFont("sans-serif", 8))
        p.drawText(QRectF(0, h - db_h - 2, w, db_h),
                   Qt.AlignHCenter | Qt.AlignTop, db_str)

    def mousePressEvent(self, event):
        self._dragging = True
        self._update_from_pos(event.position().y())
        self.update()

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._update_from_pos(event.position().y())
            self.update()

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self.update()

    def mouseDoubleClickEvent(self, event):
        """Double click resets band to 0 dB."""
        self.set_value(0.0)
        self.value_changed.emit(0.0)

    def enterEvent(self, event):
        self._hover = True; self.update()

    def leaveEvent(self, event):
        self._hover = False; self.update()

    def _update_from_pos(self, y: float):
        h = self.height() - 16 - 8
        self._value = _y_to_db(int(y - 2), h)
        self._value = max(-12.0, min(12.0, self._value))
        self.value_changed.emit(self._value)


class GraphicEqWidget(QWidget):
    """31-band graphic EQ with horizontal scroll."""
    bands_changed = Signal(int, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bands: list[BandSlider] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Band sliders in a scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        band_layout = QHBoxLayout(container)
        band_layout.setContentsMargins(4, 4, 4, 4)
        band_layout.setSpacing(1)

        for i, label in enumerate(ISO_31_LABELS):
            band = BandSlider(label)
            band.value_changed.connect(lambda v, idx=i: self.bands_changed.emit(idx, v))
            band_layout.addWidget(band)
            self._bands.append(band)

        band_layout.addStretch()
        self._scroll.setWidget(container)
        layout.addWidget(self._scroll)

    def set_bands(self, values: list[float]):
        """Set all 31 band values from a list."""
        for i, v in enumerate(values):
            if i < len(self._bands):
                self._bands[i].set_value(v)

    def get_bands(self) -> list[float]:
        return [b.value() for b in self._bands]

    def reset(self):
        self.set_bands([0.0] * 31)
