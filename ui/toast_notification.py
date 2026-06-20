"""Toast Notification — floating, animated popup messages."""

from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QTimer, Signal
from PySide6.QtWidgets import QFrame, QLabel, QHBoxLayout, QGraphicsOpacityEffect

_TOASTS: list["ToastNotification"] = []


class ToastNotification(QFrame):
    dismissed = Signal()

    def __init__(self, text: str, parent=None, duration: int = 4000,
                 kind: str = "info"):
        super().__init__(parent)
        self._duration = duration

        colors = {
            "info": ("#1d9bf0", "#e8f0fe"),
            "warning": ("#ff7a00", "#3a2a10"),
            "error": ("#ff3c48", "#3a1015"),
            "success": ("#34c759", "#0a1a0e"),
        }
        bg, border = colors.get(kind, colors["info"])

        self.setObjectName("toast")
        self.setFixedWidth(340)
        self.setMinimumHeight(44)
        self.setStyleSheet(f"""
            #toast {{
                background: rgba(30,30,35,240);
                border: 1px solid {bg}44;
                border-left: 3px solid {bg};
                border-radius: 8px;
                padding: 0;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        self._label = QLabel(text)
        self._label.setStyleSheet(
            "color: rgba(245,245,247,0.9); font-size: 12px; "
            "background: transparent; border: none;")
        self._label.setWordWrap(True)
        layout.addWidget(self._label, stretch=1)

        # Opacity effect for fade animation
        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(0.0)
        self.setGraphicsEffect(self._effect)

        self._fade_in = QPropertyAnimation(self._effect, b"opacity")
        self._fade_in.setDuration(250)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.OutCubic)

        self._fade_out = QPropertyAnimation(self._effect, b"opacity")
        self._fade_out.setDuration(300)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.InCubic)
        self._fade_out.finished.connect(self._on_dismiss)

    def show_toast(self, parent):
        if parent:
            parent_rect = parent.rect()
            x = parent_rect.width() - self.width() - 20
            y = 20 + sum(
                t.height() + 8 for t in _TOASTS
                if t.parent() is parent and t.isVisible()
            )
            self.setParent(parent)
            self.move(x, y)
            self.show()
            self.raise_()

        _TOASTS.append(self)
        self._fade_in.start()
        QTimer.singleShot(self._duration, self._fade_out.start)

    @classmethod
    def info(cls, text: str, parent=None, duration: int = 4000):
        toast = cls(text, parent, duration, "info")
        toast.show_toast(parent)
        return toast

    @classmethod
    def warning(cls, text: str, parent=None, duration: int = 5000):
        toast = cls(text, parent, duration, "warning")
        toast.show_toast(parent)
        return toast

    @classmethod
    def error(cls, text: str, parent=None, duration: int = 6000):
        toast = cls(text, parent, duration, "error")
        toast.show_toast(parent)
        return toast

    @classmethod
    def success(cls, text: str, parent=None, duration: int = 3000):
        toast = cls(text, parent, duration, "success")
        toast.show_toast(parent)
        return toast

    def _on_dismiss(self):
        self.hide()
        if self in _TOASTS:
            _TOASTS.remove(self)
        self.dismissed.emit()
        self.deleteLater()
