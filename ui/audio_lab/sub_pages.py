"""Sub-pages for Audio Lab — sub-hubs and placeholders."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QFrame, QScrollArea,
)

from ui.icons import get_pixmap
from ui.central.central_styles import glass_card_qss, glass_button_qss


def _build_sub_card(parent, icon_key: str, title: str, subtitle: str,
                    status: str, nav_key: str) -> QFrame:
    card = QFrame()
    key = f"subCard_{nav_key}" if nav_key else f"subCard_{title.lower().replace(' ','_')}"
    card.setObjectName(key)
    card.setMinimumHeight(160)

    cv = QVBoxLayout(card)
    cv.setContentsMargins(16, 16, 16, 16)
    cv.setSpacing(6)

    pix = get_pixmap(icon_key, size=32)
    icon_lbl = QLabel()
    if pix and not pix.isNull():
        icon_lbl.setPixmap(pix)
    icon_lbl.setFixedSize(40, 40)
    icon_lbl.setAlignment(Qt.AlignCenter)
    icon_lbl.setStyleSheet(
        "background: rgba(143,183,255,0.06);"
        "border: 1px solid rgba(143,183,255,0.06);"
        "border-radius: 8px;"
    )
    cv.addWidget(icon_lbl)

    t = QLabel(title)
    t.setStyleSheet(
        "color: rgba(255,255,255,0.88); font-size: 14px; "
        "font-weight: 600; background: transparent; border: none;"
    )
    cv.addWidget(t)

    d = QLabel(subtitle)
    d.setStyleSheet(
        "color: rgba(255,255,255,0.50); font-size: 11px; "
        "background: transparent; border: none;"
    )
    d.setWordWrap(True)
    cv.addWidget(d)

    cv.addStretch()

    row = QHBoxLayout()
    row.setSpacing(8)

    status_styles = {
        "disponible": ("rgba(100,220,100,0.18)", "rgba(100,220,100,0.90)", "Disponible"),
        "experimental": ("rgba(143,183,255,0.18)", "rgba(143,183,255,0.90)", "Experimental"),
        "proximamente": ("rgba(255,255,255,0.06)", "rgba(255,255,255,0.50)", "Próximamente"),
    }
    bg, fg, label = status_styles.get(
        status, ("rgba(255,255,255,0.04)", "rgba(255,255,255,0.35)", "")
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
    btn.setFixedWidth(72)
    btn.clicked.connect(
        lambda checked=False, k=nav_key: parent.navigate_requested.emit(k)
    )
    row.addWidget(btn)

    cv.addLayout(row)
    card.setStyleSheet(glass_card_qss(key, "elevated"))
    return card


class _PlaceholderPage(QWidget):
    navigate_requested = Signal(str)

    def __init__(self, title: str, subtitle: str, icon_key: str,
                 back_key: str = "audio_lab"):
        super().__init__()
        self.setObjectName("audioLabPlaceholder")
        self._back_key = back_key

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 48, 40, 48)
        layout.setAlignment(Qt.AlignCenter)

        icon_lbl = QLabel()
        pix = get_pixmap(icon_key, size=64)
        if pix and not pix.isNull():
            icon_lbl.setPixmap(pix)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setFixedSize(80, 80)
        icon_lbl.setStyleSheet(
            "background: rgba(143,183,255,0.04);"
            "border: 1px solid rgba(143,183,255,0.06);"
            "border-radius: 16px;"
        )
        layout.addWidget(icon_lbl, 0, Qt.AlignCenter)

        t = QLabel(title)
        t.setStyleSheet(
            "color: rgba(255,255,255,0.90); font-size: 22px; "
            "font-weight: 700; background: transparent;"
        )
        t.setAlignment(Qt.AlignCenter)
        layout.addWidget(t)

        s = QLabel(subtitle)
        s.setStyleSheet(
            "color: rgba(255,255,255,0.50); font-size: 13px; "
            "background: transparent;"
        )
        s.setAlignment(Qt.AlignCenter)
        s.setWordWrap(True)
        layout.addWidget(s)

        layout.addSpacing(20)

        btn = QPushButton("Volver a Audio Lab")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(glass_button_qss("secondary"))
        btn.setFixedWidth(200)
        btn.clicked.connect(
            lambda: self.navigate_requested.emit(self._back_key)
        )
        layout.addWidget(btn, 0, Qt.AlignCenter)


class AudioLabIdentifierPage(QWidget):
    navigate_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("audioLabIdentifierPage")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setObjectName("audioLabSubScroll")

        content = QWidget()
        content.setObjectName("audioLabIdentifierContent")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(40, 32, 40, 32)
        cl.setSpacing(16)

        title = QLabel("Identificador de Audios")
        title.setStyleSheet(
            "color: rgba(255,255,255,0.92); font-size: 22px; "
            "font-weight: 700; background: transparent;"
        )
        cl.addWidget(title)

        sub = QLabel(
            "Gestiona, identifica y enriquece los metadatos de tu música."
        )
        sub.setStyleSheet(
            "color: rgba(255,255,255,0.56); font-size: 13px; "
            "background: transparent;"
        )
        sub.setWordWrap(True)
        cl.addWidget(sub)

        grid = QGridLayout()
        grid.setSpacing(14)

        cards = [
            ("metadata_editor", "Editor de Metadatos",
             "Edita tags, artwork, artistas, álbumes y normaliza\n"
             "información de tus archivos.",
             "experimental", "metadata_editor"),
            ("sidebar_identifier", "MusicBrainz",
             "Identifica discos, canciones y artistas usando\n"
             "la base de datos MusicBrainz.",
             "experimental", "audio_lab_musicbrainz"),
            ("sidebar_albums", "Carátulas",
             "Busca, reemplaza e incrusta carátulas en tus\n"
             "archivos de música.",
             "experimental", "audio_lab_artwork"),
            ("sidebar_mix", "Letras",
             "Edita letras sincronizadas o simples para tus\n"
             "canciones.",
             "experimental", "audio_lab_lyrics"),
        ]
        for idx, (icon, title_t, desc, status, nav) in enumerate(cards):
            card = _build_sub_card(self, icon, title_t, desc, status, nav)
            grid.addWidget(card, idx // 2, idx % 2)

        for col in range(2):
            grid.setColumnStretch(col, 1)
        cl.addLayout(grid)
        cl.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)


class AudioLabBackupPage(QWidget):
    navigate_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("audioLabBackupPage")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setObjectName("audioLabSubScroll")

        content = QWidget()
        content.setObjectName("audioLabBackupContent")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(40, 32, 40, 32)
        cl.setSpacing(16)

        title = QLabel("Respaldar")
        title.setStyleSheet(
            "color: rgba(255,255,255,0.92); font-size: 22px; "
            "font-weight: 700; background: transparent;"
        )
        cl.addWidget(title)

        sub = QLabel(
            "Preserva tu música: ripea, digitaliza, convierte y organiza."
        )
        sub.setStyleSheet(
            "color: rgba(255,255,255,0.56); font-size: 13px; "
            "background: transparent;"
        )
        sub.setWordWrap(True)
        cl.addWidget(sub)

        grid = QGridLayout()
        grid.setSpacing(14)

        cards = [
            ("sidebar_devices", "Ripear CD",
             "Extrae CDs a WAV sin compresión. Perfiles\n"
             "FLAC/MP3/Opus requieren herramientas externas.",
             "disponible", "michi_disc_lab"),
            ("home_audio", "Digitalizar Vinilo",
             "Captura desde tu ADC/platina, separa pistas\n"
             "y exporta a FLAC de alta resolución.",
             "experimental", "audio_lab_vinyl_lab"),
             ("sidebar_mix", "Convertir Formatos",
              "Convierte entre formatos preservando\n"
              "metadatos y carátulas.",
              "experimental", "audio_lab_conversion"),
             ("sidebar_folders", "Organizar Archivos",
              "Renombra y reorganiza tu biblioteca por\n"
              "plantillas personalizadas.",
              "experimental", "audio_lab_organize"),
        ]
        for idx, (icon, title_t, desc, status, nav) in enumerate(cards):
            card = _build_sub_card(self, icon, title_t, desc, status, nav)
            grid.addWidget(card, idx // 2, idx % 2)

        for col in range(2):
            grid.setColumnStretch(col, 1)
        cl.addLayout(grid)
        cl.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)


class AudioLabDiagnosticsPage(QWidget):
    navigate_requested = Signal(str)

    def __init__(self, worker_mgr=None):
        super().__init__()
        self.setObjectName("audioLabDiagnosticsPage")
        self._worker_mgr = worker_mgr
        self._inner = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        try:
            from ui.audio_lab.diagnostics_page import DiagnosticsPage
            self._inner = DiagnosticsPage(worker_mgr=self._worker_mgr)
            self._inner.navigate_requested.connect(self.navigate_requested.emit)
            layout.addWidget(self._inner)
        except Exception as e:
            import logging
            logging.getLogger("michi.audio_lab").warning(
                "DiagnosticsPage not available: %s", e
            )
            lbl = QLabel("Diagnóstico no disponible.")
            lbl.setStyleSheet("color: rgba(255,255,255,0.62); font-size: 14px;")
            lbl.setAlignment(Qt.AlignCenter)
            layout.addWidget(lbl)


class AudioLabOutputPage(QWidget):
    navigate_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("audioLabOutputPage")
        self._inner = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        try:
            from ui.audio_lab.dsp_page import DSPPage
            self._inner = DSPPage()
            self._inner.navigate_requested.connect(self.navigate_requested.emit)
            layout.addWidget(self._inner)
        except Exception as e:
            import logging
            logging.getLogger("michi.audio_lab").warning(
                "DSPPage not available: %s", e
            )
            lbl = QLabel("Perfiles de Salida no disponibles.")
            lbl.setStyleSheet("color: rgba(255,255,255,0.62); font-size: 14px;")
            lbl.setAlignment(Qt.AlignCenter)
            layout.addWidget(lbl)


class AudioLabIntelligencePage(QWidget):
    navigate_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("audioLabIntelligencePage")
        self._inner = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        try:
            from ui.audio_lab.intelligence_page import IntelligencePage
            self._inner = IntelligencePage()
            self._inner.navigate_requested.connect(self.navigate_requested.emit)
            layout.addWidget(self._inner)
        except Exception as e:
            import logging
            logging.getLogger("michi.audio_lab").warning(
                "IntelligencePage not available: %s", e
            )
            lbl = QLabel("Inteligencia Local no disponible.")
            lbl.setStyleSheet("color: rgba(255,255,255,0.62); font-size: 14px;")
            lbl.setAlignment(Qt.AlignCenter)
            layout.addWidget(lbl)
