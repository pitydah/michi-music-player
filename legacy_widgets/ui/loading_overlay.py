"""Loading Overlay — semi-transparent spinner with fade-in and cancel button."""

from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QConicalGradient
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QGraphicsOpacityEffect

from ui.central.central_styles import glass_button_qss


class LoadingOverlay(QWidget):
    cancelled = __import__("PySide6.QtCore").QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._spin)

        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)

        self._label = QLabel("Cargando...")
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setStyleSheet(
            "color: rgba(245,245,247,0.6); font-size: 13px; "
            "background: transparent;")
        layout.addSpacing(28)
        layout.addWidget(self._label)

        self._cancel_btn = QPushButton("Cancelar")
        self._cancel_btn.setStyleSheet(glass_button_qss("secondary"))
        self._cancel_btn.setFixedWidth(120)
        self._cancel_btn.clicked.connect(self._on_cancel)
        layout.addWidget(self._cancel_btn, alignment=Qt.AlignCenter)

        self._fade_effect = QGraphicsOpacityEffect(self)
        self._fade_effect.setOpacity(1.0)
        self.setGraphicsEffect(self._fade_effect)

        self._delay_timer = QTimer(self)
        self._delay_timer.setSingleShot(True)
        self._delay_timer.timeout.connect(self._show_now)

    def _on_cancel(self):
        self.hide()
        self.cancelled.emit()

    def _show_now(self):
        if self.parent():
            self.setGeometry(self.parent().rect())
        self.setVisible(True)
        self.raise_()
        self._timer.start(30)

    def show(self, delay_ms: int = 300):
        if delay_ms > 0:
            self._delay_timer.start(delay_ms)
        else:
            self._show_now()

    def hide(self):
        self._delay_timer.stop()
        self._timer.stop()
        self.setVisible(False)

    def set_text(self, text: str):
        self._label.setText(text)

    def _spin(self):
        self._angle = (self._angle + 12) % 360
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.parent():
            self.setGeometry(self.parent().rect())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Translucent background
        painter.fillRect(self.rect(), QColor(10, 10, 14, 180))

        # Spinner arc
        cx = self.width() / 2
        cy = self.height() / 2 - 12
        r = 18
        arc_rect = QRectF(cx - r, cy - r, r * 2, r * 2)

        gradient = QConicalGradient(cx, cy, self._angle)
        gradient.setColorAt(0.0, QColor(255, 122, 0, 230))
        gradient.setColorAt(0.5, QColor(255, 122, 0, 60))
        gradient.setColorAt(1.0, QColor(255, 122, 0, 230))

        pen = QPen(gradient, 2.5)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(arc_rect, self._angle * 16, 300 * 16)

        painter.end()
