"""AudioLabPage — main hub with 5 section cards, now-playing status header."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QSizePolicy,
)

from ui.icons import get_pixmap
from ui.central.central_styles import glass_card_qss, glass_button_qss

_SECTIONS = [
    {
        "key": "audio_lab_diagnostics", "icon": "sidebar_identifier",
        "title": "Diagnóstico",
        "subtitle": "Analiza calidad real, detecta formatos falsos\n"
                     "y verifica la integridad de tu biblioteca.",
        "status": "experimental", "nav": "audio_lab_diagnostics",
    },
    {
        "key": "audio_lab_identifier", "icon": "metadata_editor",
        "title": "Identificador de Audios",
        "subtitle": "Edita metadatos, identifica con MusicBrainz,\n"
                     "gestiona carátulas y letras.",
        "status": "experimental", "nav": "audio_lab_identifier",
    },
    {
        "key": "audio_lab_backup", "icon": "sidebar_devices",
        "title": "Respaldar",
        "subtitle": "Ripea CDs, digitaliza vinilos, convierte\n"
                     "formatos y organiza tus archivos.",
        "status": "experimental", "nav": "audio_lab_backup",
    },
    {
        "key": "audio_lab_output", "icon": "home_audio",
        "title": "Perfiles de Salida",
        "subtitle": "Configura salida bit-perfect, upsampling,\n"
                     "corrección de sala y perfiles DAC.",
        "status": "experimental", "nav": "audio_lab_output",
    },
    {
        "key": "audio_lab_intelligence", "icon": "sidebar_mix",
        "title": "Inteligencia Local",
        "subtitle": "Extrae BPM, key y energía. Genera radio\n"
                     "local y recomendaciones musicales.",
        "status": "experimental", "nav": "audio_lab_intelligence",
    },
]

_STATUS_STYLES = {
    "disponible": ("rgba(100,220,100,0.18)", "rgba(100,220,100,0.90)", "Disponible"),
    "experimental": ("rgba(143,183,255,0.18)", "rgba(143,183,255,0.90)", "Experimental"),
    "proximamente": ("rgba(255,255,255,0.06)", "rgba(255,255,255,0.50)", "Próximamente"),
    "no_disponible": ("rgba(255,100,100,0.12)", "rgba(255,100,100,0.70)", "No disponible"),
}


class AudioLabPage(QWidget):
    navigate_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("audioLabPage")
        self._status_label: QLabel | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setObjectName("audioLabScroll")

        content = QWidget()
        content.setObjectName("audioLabContent")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(40, 32, 40, 32)
        cl.setSpacing(20)

        title = QLabel("Audio Lab")
        title.setObjectName("audioLabTitle")
        title.setStyleSheet(
            "color: rgba(255,255,255,0.92); font-size: 22px; "
            "font-weight: 700; background: transparent; border: none;"
        )
        cl.addWidget(title)

        subtitle = QLabel("Preserva, analiza y optimiza tu música.")
        subtitle.setObjectName("audioLabSubtitle")
        subtitle.setStyleSheet(
            "color: rgba(255,255,255,0.56); font-size: 13px; "
            "background: transparent; border: none;"
        )
        subtitle.setWordWrap(True)
        cl.addWidget(subtitle)

        status_frame = QFrame()
        status_frame.setObjectName("audioLabStatusFrame")
        status_frame.setStyleSheet(
            "QFrame#audioLabStatusFrame {"
            "  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "    stop:0 rgba(255,255,255,0.030), stop:1 rgba(255,255,255,0.015));"
            "  border: 1px solid rgba(255,255,255,0.035);"
            "  border-radius: 12px;"
            "}"
        )
        sl = QHBoxLayout(status_frame)
        sl.setContentsMargins(16, 10, 16, 10)
        self._status_label = QLabel("Sin reproducción activa.")
        self._status_label.setObjectName("audioLabStatusText")
        self._status_label.setStyleSheet(
            "color: rgba(255,255,255,0.62); font-size: 12px; background: transparent;"
        )
        self._status_label.setWordWrap(True)
        sl.addWidget(self._status_label, 1)
        cl.addWidget(status_frame)

        grid = QGridLayout()
        grid.setSpacing(16)

        for i, sec in enumerate(_SECTIONS):
            card = self._build_section_card(sec)
            row = 0 if i < 3 else 1
            col = i if i < 3 else i - 3
            grid.addWidget(card, row, col)

        for col in range(3):
            grid.setColumnStretch(col, 1)
        cl.addLayout(grid)
        cl.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _build_section_card(self, sec: dict) -> QFrame:
        key = sec["key"]
        card = QFrame()
        card.setObjectName(f"audioLabCard_{key}")
        card.setMinimumHeight(180)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)

        cv = QVBoxLayout(card)
        cv.setContentsMargins(20, 20, 20, 20)
        cv.setSpacing(8)

        pix = get_pixmap(sec["icon"], size=40)
        icon_lbl = QLabel()
        if pix and not pix.isNull():
            icon_lbl.setPixmap(pix)
        icon_lbl.setFixedSize(44, 44)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(
            "background: rgba(143,183,255,0.06);"
            "border: 1px solid rgba(143,183,255,0.06);"
            "border-radius: 10px;"
        )
        cv.addWidget(icon_lbl)

        t = QLabel(sec["title"])
        t.setStyleSheet(
            "color: rgba(255,255,255,0.88); font-size: 16px; "
            "font-weight: 600; background: transparent; border: none;"
        )
        cv.addWidget(t)

        d = QLabel(sec["subtitle"])
        d.setStyleSheet(
            "color: rgba(255,255,255,0.52); font-size: 11px; "
            "background: transparent; border: none;"
        )
        d.setWordWrap(True)
        cv.addWidget(d)

        cv.addStretch()

        row = QHBoxLayout()
        row.setSpacing(10)

        bg, fg, label = _STATUS_STYLES.get(
            sec["status"], ("rgba(255,255,255,0.04)", "rgba(255,255,255,0.35)", "")
        )
        badge = QLabel(label)
        badge.setStyleSheet(
            f"color: {fg}; font-size: 10px; font-weight: 600; "
            f"background: transparent; border: none; padding: 0;"
        )
        row.addWidget(badge)
        row.addStretch()

        btn = QPushButton("Abrir")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(glass_button_qss("primary"))
        btn.setFixedWidth(80)
        btn.clicked.connect(
            lambda checked=False, k=sec["nav"]: self.navigate_requested.emit(k)
        )
        row.addWidget(btn)

        cv.addLayout(row)
        card.setStyleSheet(glass_card_qss(f"audioLabCard_{key}", "elevated"))
        return card

    def set_status_text(self, text: str):
        if self._status_label:
            self._status_label.setText(text)
