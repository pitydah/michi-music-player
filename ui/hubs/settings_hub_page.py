"""SettingsHubPage — application preferences grouped by category."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QFrame, QScrollArea, QPushButton,
)

from ui.central.central_styles import glass_card_qss, glass_button_qss


class SettingsHubPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("settingsHubPage")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setObjectName("settingsHubScroll")

        content = QWidget()
        content.setObjectName("settingsHubContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(40, 32, 40, 32)
        content_layout.setSpacing(20)

        title = QLabel("Configuración")
        title.setObjectName("settingsHubTitle")
        content_layout.addWidget(title)

        subtitle = QLabel(
            "General, apariencia, biblioteca, reproducción, conexiones y ajustes avanzados."
        )
        subtitle.setObjectName("settingsHubSubtitle")
        subtitle.setWordWrap(True)
        content_layout.addWidget(subtitle)

        sections = [
            ("general", "General", "Inicio, carpetas y comportamiento."),
            ("appearance", "Apariencia", "Tema, fuentes y opacidad."),
            ("library", "Biblioteca", "Escaneo, indexado y carpetas."),
            ("playback", "Reproducción", "Crossfade, replaygain y buffer."),
            ("audio", "Audio / DAC", "Dispositivo, perfil y calidad."),
            ("connections", "Conexiones", "Servidores, Home Audio y Snapcast."),
            ("advanced", "Avanzado", "Cache, logs, depuración y modo seguro."),
        ]

        for key, label, desc in sections:
            card = self._build_card(key, label, desc)
            content_layout.addWidget(card)

        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

        self._apply_qss()

    def _build_card(self, key: str, title: str, description: str) -> QFrame:
        card = QFrame()
        card.setObjectName(f"settingsCard_{key}")

        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(20, 20, 20, 20)
        c_layout.setSpacing(8)

        c_title = QLabel(title)
        c_layout.addWidget(c_title)

        c_desc = QLabel(description)
        c_desc.setWordWrap(True)
        c_layout.addWidget(c_desc)

        btn = QPushButton(f"Configurar {title}")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda checked=None, k=key: self._navigate(k))
        c_layout.addWidget(btn)

        card.setStyleSheet(glass_card_qss(f"settingsCard_{key}"))
        return card

    def _navigate(self, target: str):
        w = self.window()
        if w and hasattr(w, '_show_preferences'):
            w._show_preferences(target)

    def _apply_qss(self):
        self.setStyleSheet("""
            QWidget#settingsHubPage { background: #090B11; }
            QScrollArea#settingsHubScroll { background: transparent; border: none; }
            QWidget#settingsHubContent { background: transparent; }
            QLabel#settingsHubTitle { color: rgba(255,255,255,0.92); font-size: 22px; font-weight: 700; }
            QLabel#settingsHubSubtitle { color: rgba(255,255,255,0.56); font-size: 13px; }
        """)
        for key in ("general", "appearance", "library", "playback", "audio", "connections", "advanced"):
            card = self.findChild(QFrame, f"settingsCard_{key}")
            if card:
                for lbl in card.findChildren(QLabel):
                    if "font-size" not in (lbl.styleSheet() or ""):
                        lbl.setStyleSheet(
                            "QLabel { color: rgba(255,255,255,0.62); font-size: 12px; "
                            "background: transparent; border: none; }"
                        )
                for btn in card.findChildren(QPushButton):
                    btn.setStyleSheet(glass_button_qss("primary"))
