"""AddFeedDialog — dialog for adding a podcast RSS feed."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit,
)

from streaming.podcast_manager import PodcastManager


class AddFeedDialog(QDialog):
    def __init__(self, podcast_manager: PodcastManager | None = None, parent=None):
        super().__init__(parent)
        self._pm = podcast_manager
        self.feed_url: str = ""
        self.setWindowTitle("Añadir podcast RSS")
        self.setMinimumWidth(480)
        self.setStyleSheet("background: #090B11; border-radius: 12px;")

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 20, 24, 20)

        title = QLabel("Añadir podcast RSS")
        title.setStyleSheet(
            "color: rgba(255,255,255,0.90); font-size: 18px; font-weight: 700; "
            "background: transparent; border: none;"
        )
        layout.addWidget(title)

        sub = QLabel("Introduce la URL del feed RSS del podcast.")
        sub.setStyleSheet(
            "color: rgba(255,255,255,0.56); font-size: 12px; "
            "background: transparent; border: none;"
        )
        layout.addWidget(sub)

        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("https://ejemplo.com/feed.xml")
        self._url_input.setStyleSheet(
            "QLineEdit { background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; "
            "color: rgba(255,255,255,0.80); padding: 10px 14px; font-size: 13px; }"
        )
        layout.addWidget(self._url_input)

        self._preview_label = QLabel("")
        self._preview_label.setStyleSheet(
            "color: rgba(255,255,255,0.60); font-size: 12px; "
            "background: transparent; border: none;"
        )
        self._preview_label.setWordWrap(True)
        layout.addWidget(self._preview_label)

        btn_row = QHBoxLayout()
        validate_btn = QPushButton("Validar")
        validate_btn.setCursor(Qt.PointingHandCursor)
        validate_btn.setStyleSheet(self._btn_qss("secondary"))
        validate_btn.clicked.connect(self._validate)
        btn_row.addWidget(validate_btn)

        btn_row.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(self._btn_qss("ghost"))
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self._accept_btn = QPushButton("Añadir podcast")
        self._accept_btn.setCursor(Qt.PointingHandCursor)
        self._accept_btn.setStyleSheet(self._btn_qss("primary"))
        self._accept_btn.setEnabled(False)
        self._accept_btn.clicked.connect(self._accept)
        btn_row.addWidget(self._accept_btn)

        layout.addLayout(btn_row)

    def _validate(self):
        url = self._url_input.text().strip()
        if not url.startswith(("http://", "https://")):
            self._preview_label.setText("La URL debe comenzar con http:// o https://")
            self._accept_btn.setEnabled(False)
            return

        if self._pm is None:
            self._preview_label.setText("Gestor de podcasts no disponible.")
            return

        existing = self._pm._repo.find_show_by_feed_url(url)
        if existing is not None:
            self._preview_label.setText(
                f"Feed ya suscrito: {existing.title}"
            )
            self._accept_btn.setEnabled(False)
            return

        from streaming.podcast_feed_parser import parse_feed
        parsed = parse_feed(url)
        if not parsed.ok:
            msg = parsed.errors[0] if parsed.errors else "Error desconocido"
            self._preview_label.setText(f"Error: {msg}")
            self._accept_btn.setEnabled(False)
            return

        show = parsed.show
        lines = [f"Titulo: {show.title if show else '?'}"]
        if show and show.author:
            lines.append(f"Autor: {show.author}")
        lines.append(f"Episodios: {len(parsed.episodes)}")
        if parsed.warnings:
            lines.append(f"Advertencias: {'; '.join(parsed.warnings)}")
        self._preview_label.setText("\n".join(lines))
        self._feed_url = url
        self._accept_btn.setEnabled(True)

    def _accept(self):
        url = getattr(self, '_feed_url', '') or self._url_input.text().strip()
        if url:
            self.feed_url = url
            self.accept()

    @staticmethod
    def _btn_qss(style: str) -> str:
        if style == "primary":
            return (
                "QPushButton { background: rgba(143,183,255,0.15); "
                "border: 1px solid rgba(143,183,255,0.20); border-radius: 8px; "
                "color: rgba(255,255,255,0.88); font-size: 12px; font-weight: 600; "
                "padding: 8px 18px; }"
                "QPushButton:hover { background: rgba(143,183,255,0.22); }"
                "QPushButton:disabled { background: rgba(255,255,255,0.03); "
                "color: rgba(255,255,255,0.30); border: 1px solid transparent; }"
            )
        if style == "secondary":
            return (
                "QPushButton { background: rgba(255,255,255,0.05); "
                "border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; "
                "color: rgba(255,255,255,0.80); font-size: 12px; font-weight: 500; "
                "padding: 8px 18px; }"
                "QPushButton:hover { background: rgba(255,255,255,0.10); }"
            )
        return (
            "QPushButton { background: transparent; border: none; "
            "color: rgba(255,255,255,0.56); font-size: 12px; padding: 8px 14px; }"
            "QPushButton:hover { color: rgba(255,255,255,0.80); }"
        )
