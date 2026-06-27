"""MixHubPage — dynamic smart mix hub with inline previews, play/view actions, and scopes."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QPushButton, QGridLayout,
    QComboBox,
)

from ui.central.central_styles import (
    glass_card_qss, glass_button_qss,
    card_title_qss, card_desc_qss,
    page_title_qss, page_subtitle_qss,
)

if TYPE_CHECKING:
    from ui.controllers.smart_mix_preview import SmartMixPreview

logger = logging.getLogger("michi.mix_hub")


class MixHubPage(QWidget):
    """Dynamic mix hub — shows smart mix cards with counts, inline play, and quick scopes."""

    def __init__(self, preview: SmartMixPreview | None = None,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("mixHubPage")
        self._preview = preview
        self._build_ui()
        self._apply_qss()

    # ── Build UI ──

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setObjectName("mixHubScroll")

        content = QWidget()
        content.setObjectName("mixHubContent")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(40, 32, 40, 40)
        cl.setSpacing(20)

        # ── Title ──
        title = QLabel("Mix")
        title.setObjectName("mixHubTitle")
        cl.addWidget(title)

        subtitle = QLabel(
            "Smart mixes, escucha inmediata y combinaciones de fuentes locales y remotas.")
        subtitle.setObjectName("mixHubSubtitle")
        subtitle.setWordWrap(True)
        cl.addWidget(subtitle)

        # ── Dynamic mix cards (2-column grid) ──
        self._mix_cards_grid = QGridLayout()
        self._mix_cards_grid.setSpacing(16)
        cl.addLayout(self._mix_cards_grid)

        # ── Quick scopes ──
        cl.addWidget(self._build_quick_scopes())

        # ── Mix builder (placeholder) ──
        cl.addWidget(self._build_mix_builder())

        cl.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

    # ── Dynamic mix cards ──

    def refresh(self):
        """Rebuild all mix cards from current preview data."""
        self._rebuild_mix_cards()

    def _rebuild_mix_cards(self):
        # Clear existing cards
        while self._mix_cards_grid.count():
            item = self._mix_cards_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self._preview is None:
            return

        previews = self._preview.get_all_previews()
        for i, pv in enumerate(previews):
            card = self._build_mix_card(pv)
            self._mix_cards_grid.addWidget(card, i // 2, i % 2)

    def _build_mix_card(self, pv) -> QFrame:
        card = QFrame()
        card.setObjectName(f"mixCard_{pv.key}")
        card.setStyleSheet(glass_card_qss(f"mixCard_{pv.key}"))
        card.setMinimumHeight(160)

        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 18, 20, 18)
        cl.setSpacing(6)

        # Title
        card_title = QLabel(pv.label)
        card_title.setStyleSheet(card_title_qss())
        cl.addWidget(card_title)

        # Description
        card_desc = QLabel(pv.description)
        card_desc.setWordWrap(True)
        card_desc.setStyleSheet(card_desc_qss())
        cl.addWidget(card_desc)

        # Count or empty reason
        if pv.count > 0:
            count_lbl = QLabel(f"{pv.count} canciones")
            count_lbl.setStyleSheet(
                "QLabel { color: rgba(143,183,255,0.78); font-size: 13px; font-weight: 600;"
                "  background: transparent; border: none; }")
            cl.addWidget(count_lbl)
        else:
            empty_lbl = QLabel(pv.empty_reason)
            empty_lbl.setWordWrap(True)
            empty_lbl.setStyleSheet(
                "QLabel { color: rgba(255,255,255,0.38); font-size: 11px;"
                "  background: transparent; border: none; }")
            cl.addWidget(empty_lbl)

        cl.addStretch()

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        if pv.count > 0:
            play_btn = QPushButton("Reproducir")
            play_btn.setCursor(Qt.PointingHandCursor)
            play_btn.setStyleSheet(glass_button_qss("accent"))
            play_btn.clicked.connect(
                lambda checked=False, files=pv.files, _w=self.window():
                self._play_files(files, _w))
            btn_row.addWidget(play_btn)

            view_btn = QPushButton("Ver")
            view_btn.setCursor(Qt.PointingHandCursor)
            view_btn.setStyleSheet(glass_button_qss("ghost"))
            view_btn.clicked.connect(
                lambda checked=False, key=pv.key: self._navigate(key))
            btn_row.addWidget(view_btn)

        cl.addLayout(btn_row)
        return card

    def _play_files(self, files: list[str], win):
        """Enqueue files and start playback."""
        if not files or not win:
            return
        if hasattr(win, '_play_filepaths'):
            win._play_filepaths(files, play_now=True)
        elif hasattr(win, '_playback') and hasattr(win._playback, 'play_queue'):
            win._playback.play_queue(files, 0)

    def _navigate(self, target: str):
        w = self.window()
        if w and hasattr(w, '_on_sidebar_navigate'):
            w._on_sidebar_navigate(target)

    # ── Quick scopes ──

    def _build_quick_scopes(self) -> QFrame:
        card = QFrame()
        card.setObjectName("mixScopesCard")
        card.setStyleSheet(glass_card_qss("mixScopesCard"))

        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.setSpacing(8)

        title = QLabel("Scopes rápidos")
        title.setStyleSheet(card_title_qss())
        cl.addWidget(title)

        desc = QLabel("Accesos directos a tus secciones de música.")
        desc.setStyleSheet(card_desc_qss())
        cl.addWidget(desc)

        chips_layout = QHBoxLayout()
        chips_layout.setSpacing(8)

        scopes = [
            ("Toda la biblioteca", "library"),
            ("Favoritos", "favs"),
            ("No escuchadas", "mix_unplayed"),
            ("Más escuchadas", "mix_popular"),
            ("Recientes", "recent"),
        ]
        for label, key in scopes:
            chip = QPushButton(label)
            chip.setCursor(Qt.PointingHandCursor)
            chip.setStyleSheet(glass_button_qss("ghost"))
            chip.clicked.connect(
                lambda checked=False, k=key: self._navigate(k))
            chips_layout.addWidget(chip)

        chips_layout.addStretch()
        cl.addLayout(chips_layout)
        return card

    # ── Mix builder placeholder ──

    def _build_mix_builder(self) -> QFrame:
        card = QFrame()
        card.setObjectName("mixBuilderCard")
        card.setStyleSheet(glass_card_qss("mixBuilderCard"))

        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.setSpacing(8)

        title = QLabel("Constructor de mix")
        title.setStyleSheet(card_title_qss())
        cl.addWidget(title)

        desc = QLabel(
            "Personalizá tu propia mezcla eligiendo fuente, criterio y duración."
            " Disponible próximamente.")
        desc.setWordWrap(True)
        desc.setStyleSheet(card_desc_qss())
        cl.addWidget(desc)

        row = QHBoxLayout()
        row.setSpacing(12)

        source_cb = QComboBox()
        source_cb.addItem("Música local")
        source_cb.setEnabled(False)
        source_cb.setStyleSheet(
            "QComboBox { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);"
            "  border-radius: 8px; padding: 6px 12px; color: rgba(255,255,255,0.48); }")
        row.addWidget(source_cb)

        criteria_cb = QComboBox()
        criteria_cb.addItems(["Aleatorio", "Por género", "Por artista"])
        criteria_cb.setEnabled(False)
        criteria_cb.setStyleSheet(
            "QComboBox { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);"
            "  border-radius: 8px; padding: 6px 12px; color: rgba(255,255,255,0.48); }")
        row.addWidget(criteria_cb)

        gen_btn = QPushButton("Generar mix")
        gen_btn.setEnabled(False)
        gen_btn.setCursor(Qt.PointingHandCursor)
        gen_btn.setStyleSheet(glass_button_qss("ghost"))
        row.addWidget(gen_btn)

        row.addStretch()
        cl.addLayout(row)
        return card

    # ── QSS ──

    def _apply_qss(self):
        self.setStyleSheet(
            page_title_qss() + page_subtitle_qss() + """
            QWidget#mixHubPage { background: #090B11; }
            QScrollArea#mixHubScroll { background: transparent; border: none; }
            QWidget#mixHubContent { background: transparent; }
            QLabel#mixHubTitle { color: rgba(255,255,255,0.92); font-size: 22px; font-weight: 700; }
            QLabel#mixHubSubtitle { color: rgba(255,255,255,0.56); font-size: 13px; }
        """)
