"""Marquee Label — smooth horizontal scrolling for long titles."""

from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QPainter, QFontMetrics
from PySide6.QtWidgets import QLabel


class MarqueeLabel(QLabel):
    """Auto-scrolls text horizontally if it exceeds the widget width."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._offset = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self._full_text = text
        self._needs_marquee = False
        self._direction = -1  # scroll left
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

    def setText(self, text: str):
        self._full_text = text
        self._offset = 0.0
        fm = QFontMetrics(self.font())
        self._needs_marquee = fm.horizontalAdvance(text) > self.width() - 10
        if self._needs_marquee:
            super().setText(text)
            self._timer.start(40)
        else:
            super().setText(text)
            self._timer.stop()

    def _step(self):
        self._offset += 0.5
        self.update()

    def paintEvent(self, event):
        if not self._needs_marquee:
            super().paintEvent(event)
            return
        painter = QPainter(self)
        painter.setPen(self.palette().windowText().color())
        painter.setFont(self.font())
        fm = QFontMetrics(self.font())
        text_width = fm.horizontalAdvance(self._full_text)
        if text_width <= self.width():
            painter.drawText(self.rect(), self.alignment(), self._full_text)
            painter.end()
            return

        # Calculate scroll offset
        max_offset = text_width + self.width()
        current_offset = self._offset % max_offset

        # Draw text twice for seamless loop
        x = self.width() - current_offset
        painter.drawText(QPointF(x, (self.height() + fm.ascent()) / 2 - 2),
                        self._full_text)
        painter.drawText(QPointF(x + text_width + 40,
                        (self.height() + fm.ascent()) / 2 - 2),
                        self._full_text)
        painter.end()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Re-check if marquee is needed
        if self._full_text:
            self.setText(self._full_text)
