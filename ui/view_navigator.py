"""View navigator — fade transitions and opacity management for the central stack."""
import os
import logging

from PySide6.QtCore import QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QGraphicsOpacityEffect


class ViewNavigator:
    def __init__(self, content_stack, views, controller):
        self._content = content_stack
        self._views = views
        self._ctrl = controller  # ViewController instance
        self._fade_anim = None

    def show(self, target: str):
        if self._ctrl.current() == target:
            return

        if self._fade_anim is not None:
            self._fade_anim.stop()
            self._fade_anim = None

        self.restore_opacity()
        self._ctrl.show(target)

        effect = QGraphicsOpacityEffect(self._content)
        effect.setOpacity(0.88)
        self._content.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(100)
        anim.setStartValue(0.88)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_anim = anim

        def _finish():
            effect.setOpacity(1.0)
            self._content.setGraphicsEffect(None)
            self._fade_anim = None

        anim.finished.connect(_finish)
        anim.start()

    def restore_opacity(self, all_widgets: list = None):
        if self._fade_anim is not None:
            self._fade_anim.stop()
            self._fade_anim = None

        widgets = all_widgets or getattr(self, '_widgets', [])
        for w in widgets:
            if w is None:
                continue
            try:
                eff = w.graphicsEffect()
                if isinstance(eff, QGraphicsOpacityEffect):
                    eff.setOpacity(1.0)
                    w.setGraphicsEffect(None)
                w.setEnabled(True)
            except Exception:
                logging.getLogger("michi").debug("Opacity restore failed on a child widget")

        try:
            cw = self._content.parentWidget()
            if cw:
                eff = cw.graphicsEffect()
                if isinstance(eff, QGraphicsOpacityEffect):
                    eff.setOpacity(1.0)
                    cw.setGraphicsEffect(None)
                cw.setEnabled(True)
        except Exception:
            logging.getLogger("michi").debug("Central opacity restore failed")

        if os.getenv("MICHI_UI_DEBUG") == "1":
            self._debug_state(all_widgets)

    def _debug_state(self, widgets):
        for i, w in enumerate(widgets or []):
            if w is None:
                continue
            eff = w.graphicsEffect()
            opacity = eff.opacity() if isinstance(eff, QGraphicsOpacityEffect) else None
            print(
                f"[MICHI UI DEBUG] widget[{i}]: "
                f"enabled={w.isEnabled()} "
                f"visible={w.isVisible()} "
                f"effect={type(eff).__name__ if eff else 'None'} "
                f"opacity={opacity}"
            )
