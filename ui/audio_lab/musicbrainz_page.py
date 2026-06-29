"""MusicBrainzPage — search MusicBrainz for artist, album, and recording metadata.

Connects to existing KnowledgeBrokerService for lookups
and SmartTaggingService for applying suggestions.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QLineEdit, QComboBox,
    QScrollArea,     QListWidget,
    QProgressBar, QMessageBox,
)

from ui.central.central_styles import (
    glass_card_qss, glass_button_qss, glass_input_qss,
    glass_progress_qss,
)

logger = logging.getLogger("michi.musicbrainz.ui")


class MusicBrainzPage(QWidget):
    navigate_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("musicbrainzPage")
        self._kb = None
        self._results: list[dict] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(40, 32, 40, 32)
        cl.setSpacing(16)

        title = QLabel("MusicBrainz")
        title.setStyleSheet(
            "color: rgba(255,255,255,0.92); font-size: 22px; "
            "font-weight: 700; background: transparent;"
        )
        cl.addWidget(title)

        sub = QLabel(
            "Busca álbumes, artistas y canciones en la base de datos "
            "MusicBrainz para identificar y enriquecer tu biblioteca."
        )
        sub.setStyleSheet(
            "color: rgba(255,255,255,0.56); font-size: 13px; "
            "background: transparent;"
        )
        sub.setWordWrap(True)
        cl.addWidget(sub)

        # Search
        search_card = QFrame()
        search_card.setStyleSheet(glass_card_qss("mbSearchCard"))
        svl = QVBoxLayout(search_card)
        svl.setContentsMargins(20, 16, 20, 16)
        svl.setSpacing(10)

        sl = QLabel("Buscar")
        sl.setStyleSheet(
            "color: rgba(255,255,255,0.88); font-size: 14px; "
            "font-weight: 600; background: transparent;"
        )
        svl.addWidget(sl)

        search_row = QHBoxLayout()
        self._search_type = QComboBox()
        self._search_type.setStyleSheet(
            "QComboBox { background: rgba(255,255,255,0.055); "
            "border: 1px solid rgba(255,255,255,0.05); "
            "border-radius: 8px; padding: 6px 10px; "
            "color: rgba(255,255,255,0.86); font-size: 12px; }"
        )
        self._search_type.addItems(["Artista", "Álbum", "Canción"])
        search_row.addWidget(self._search_type)

        self._search_input = QLineEdit()
        self._search_input.setStyleSheet(glass_input_qss())
        self._search_input.setPlaceholderText(
            "Buscar en MusicBrainz..."
        )
        self._search_input.returnPressed.connect(self._do_search)
        search_row.addWidget(self._search_input, 1)

        self._search_btn = QPushButton("Buscar")
        self._search_btn.setCursor(Qt.PointingHandCursor)
        self._search_btn.setStyleSheet(glass_button_qss("primary"))
        self._search_btn.clicked.connect(self._do_search)
        search_row.addWidget(self._search_btn)

        svl.addLayout(search_row)

        cl.addWidget(search_card)

        # Results
        results_card = QFrame()
        results_card.setStyleSheet(glass_card_qss("mbResultsCard"))
        rvl = QVBoxLayout(results_card)
        rvl.setContentsMargins(20, 16, 20, 16)
        rvl.setSpacing(10)

        rl = QLabel("Resultados")
        rl.setStyleSheet(
            "color: rgba(255,255,255,0.88); font-size: 14px; "
            "font-weight: 600; background: transparent;"
        )
        rvl.addWidget(rl)

        self._results_list = QListWidget()
        self._results_list.setStyleSheet(
            "QListWidget { background: rgba(255,255,255,0.02); "
            "border: 1px solid rgba(255,255,255,0.04); "
            "border-radius: 8px; color: rgba(255,255,255,0.72); "
            "font-size: 12px; min-height: 200px; }"
        )
        rvl.addWidget(self._results_list)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        self._progress.setStyleSheet(glass_progress_qss())
        rvl.addWidget(self._progress)

        cl.addWidget(results_card)

        cl.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _get_kb(self):
        if self._kb is None:
            try:
                from integrations.knowledge_broker.service import (
                    KnowledgeBrokerService
                )
                self._kb = KnowledgeBrokerService()
            except Exception as e:
                logger.warning("KnowledgeBroker not available: %s", e)
        return self._kb

    def _do_search(self):
        query = self._search_input.text().strip()
        if not query:
            return

        kb = self._get_kb()
        if not kb:
            QMessageBox.warning(
                self, "MusicBrainz",
                "KnowledgeBrokerService no está disponible.\n\n"
                "Verifica que MusicBrainz esté habilitado en "
                "Configuración > Privacidad."
            )
            return

        search_type = self._search_type.currentText()
        self._results_list.clear()
        self._results.clear()
        self._progress.setVisible(True)

        try:
            if search_type == "Artista":
                result = kb.lookup_artist(query)
                if result and isinstance(result, dict):
                    item_text = result.get("name", query)
                    if result.get("mbid"):
                        item_text += f"  [{result['mbid'][:8]}...]"
                    if result.get("disambiguation"):
                        item_text += f"  — {result['disambiguation']}"
                    self._results.append(result)
                    self._results_list.addItem(item_text)

            elif search_type == "Álbum":
                result = kb.lookup_album(query)
                if result and isinstance(result, dict):
                    item_text = result.get("title", query)
                    if result.get("artist"):
                        item_text += f"  — {result['artist']}"
                    if result.get("year"):
                        item_text += f"  ({result['year']})"
                    self._results.append(result)
                    self._results_list.addItem(item_text)

            elif search_type == "Canción":
                result = kb.lookup_recording(query)
                if result and isinstance(result, dict):
                    item_text = result.get("title", query)
                    if result.get("artist"):
                        item_text += f"  — {result['artist']}"
                    self._results.append(result)
                    self._results_list.addItem(item_text)

            if self._results_list.count() == 0:
                self._results_list.addItem(
                    "(Sin resultados. Intenta con otro término.)"
                )

        except Exception as e:
            logger.exception("MusicBrainz search failed")
            self._results_list.addItem(f"Error: {e}")

        self._progress.setVisible(False)
