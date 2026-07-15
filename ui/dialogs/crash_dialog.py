"""CrashDialog — muestra al usuario que ocurrio un error y donde esta el reporte."""

from __future__ import annotations

import os


from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
)


class CrashDialog(QDialog):
    def __init__(self, report_path: str, parent=None):
        super().__init__(parent)
        self._report_path = report_path
        self.setWindowTitle("Error inesperado")
        self.setMinimumWidth(520)
        self.setStyleSheet("background: #090B11; border-radius: 12px;")

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(28, 24, 28, 24)

        icon = QLabel("\u26a0\ufe0f")
        icon.setStyleSheet("font-size: 36px; background: transparent; border: none;")
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)

        msg = QLabel("Ocurri\u00f3 un error inesperado en Michi Music Player.")
        msg.setStyleSheet(
            "color: rgba(255,255,255,0.88); font-size: 15px; "
            "font-weight: 600; background: transparent; border: none;"
        )
        msg.setAlignment(Qt.AlignCenter)
        msg.setWordWrap(True)
        layout.addWidget(msg)

        detail = QLabel(
            "Se ha guardado un reporte de diagn\u00f3stico que puedes "
            "compartir para ayudar a resolver el problema."
        )
        detail.setStyleSheet(
            "color: rgba(255,255,255,0.58); font-size: 12px; "
            "background: transparent; border: none;"
        )
        detail.setAlignment(Qt.AlignCenter)
        detail.setWordWrap(True)
        layout.addWidget(detail)

        path_lbl = QLabel(report_path)
        path_lbl.setStyleSheet(
            "color: rgba(143,183,255,0.70); font-size: 11px; "
            "font-family: monospace; background: rgba(255,255,255,0.03); "
            "border: 1px solid rgba(255,255,255,0.04); border-radius: 6px; "
            "padding: 8px;"
        )
        path_lbl.setAlignment(Qt.AlignCenter)
        path_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(path_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        open_btn = QPushButton("\U0001f4c2  Abrir carpeta de reportes")
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.setStyleSheet(self._btn_qss("secondary"))
        open_btn.clicked.connect(self._open_folder)
        btn_row.addWidget(open_btn)

        close_btn = QPushButton("Cerrar")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(self._btn_qss("primary"))
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    def _open_folder(self):
        folder = os.path.dirname(self._report_path)
        if os.path.isdir(folder):
            import contextlib
            with contextlib.suppress(Exception):
                from core.external_process import run_process
                run_process(["xdg-open", folder])

    @staticmethod
    def _btn_qss(style: str) -> str:
        if style == "primary":
            return (
                "QPushButton { background: rgba(143,183,255,0.12); "
                "border: 1px solid rgba(143,183,255,0.20); border-radius: 8px; "
                "color: rgba(255,255,255,0.88); font-size: 12px; font-weight: 600; "
                "padding: 8px 20px; }"
                "QPushButton:hover { background: rgba(143,183,255,0.20); }"
            )
        return (
            "QPushButton { background: rgba(255,255,255,0.05); "
            "border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; "
            "color: rgba(255,255,255,0.80); font-size: 12px; font-weight: 500; "
            "padding: 8px 20px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.10); }"
        )
