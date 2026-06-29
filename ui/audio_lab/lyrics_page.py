"""LyricsPage — view, edit, and embed lyrics from lrclib.net or manually."""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QLineEdit, QPlainTextEdit,
    QScrollArea, QProgressBar, QMessageBox,
)

from ui.central.central_styles import (
    glass_card_qss, glass_button_qss, glass_input_qss,
    glass_progress_qss,
)

logger = logging.getLogger("michi.lyrics.ui")


class LyricsPage(QWidget):
    navigate_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("lyricsPage")
        self._client = None
        self._current_lyrics = ""
        self._current_title = ""
        self._current_artist = ""
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

        title = QLabel("Letras")
        title.setStyleSheet(
            "color: rgba(255,255,255,0.92); font-size: 22px; "
            "font-weight: 700; background: transparent;"
        )
        cl.addWidget(title)

        sub = QLabel(
            "Busca letras de canciones en lrclib.net o edítalas "
            "manualmente. Las letras se guardan en los archivos de música."
        )
        sub.setStyleSheet(
            "color: rgba(255,255,255,0.56); font-size: 13px; "
            "background: transparent;"
        )
        sub.setWordWrap(True)
        cl.addWidget(sub)

        # Search
        search_card = QFrame()
        search_card.setStyleSheet(glass_card_qss("lyrSearchCard"))
        svl = QVBoxLayout(search_card)
        svl.setContentsMargins(20, 16, 20, 16)
        svl.setSpacing(10)

        sl = QLabel("Buscar letras")
        sl.setStyleSheet(
            "color: rgba(255,255,255,0.88); font-size: 14px; "
            "font-weight: 600; background: transparent;"
        )
        svl.addWidget(sl)

        search_row = QHBoxLayout()
        self._title_input = QLineEdit()
        self._title_input.setStyleSheet(glass_input_qss())
        self._title_input.setPlaceholderText("Título de la canción")
        search_row.addWidget(self._title_input, 1)

        self._artist_input = QLineEdit()
        self._artist_input.setStyleSheet(glass_input_qss())
        self._artist_input.setPlaceholderText("Artista")
        search_row.addWidget(self._artist_input, 1)

        self._search_btn = QPushButton("Buscar")
        self._search_btn.setCursor(Qt.PointingHandCursor)
        self._search_btn.setStyleSheet(glass_button_qss("primary"))
        self._search_btn.clicked.connect(self._search_lyrics)
        search_row.addWidget(self._search_btn)

        svl.addLayout(search_row)
        self._search_progress = QProgressBar()
        self._search_progress.setRange(0, 0)
        self._search_progress.setVisible(False)
        self._search_progress.setStyleSheet(glass_progress_qss())
        svl.addWidget(self._search_progress)
        cl.addWidget(search_card)

        # Lyrics editor
        edit_card = QFrame()
        edit_card.setStyleSheet(glass_card_qss("lyrEditCard"))
        evl = QVBoxLayout(edit_card)
        evl.setContentsMargins(20, 16, 20, 16)
        evl.setSpacing(10)

        el = QLabel("Letra")
        el.setStyleSheet(
            "color: rgba(255,255,255,0.88); font-size: 14px; "
            "font-weight: 600; background: transparent;"
        )
        evl.addWidget(el)

        self._info_label = QLabel(
            "Busca una canción para ver su letra."
        )
        self._info_label.setStyleSheet(
            "color: rgba(255,255,255,0.50); font-size: 11px; "
            "background: transparent;"
        )
        evl.addWidget(self._info_label)

        self._lyrics_edit = QPlainTextEdit()
        self._lyrics_edit.setStyleSheet(
            "QPlainTextEdit { background: rgba(255,255,255,0.02); "
            "border: 1px solid rgba(255,255,255,0.04); "
            "border-radius: 8px; color: rgba(255,255,255,0.82); "
            "font-size: 13px; padding: 12px; "
            "selection-background-color: rgba(143,183,255,0.30); "
            "font-family: monospace; min-height: 200px; }"
        )
        self._lyrics_edit.setPlaceholderText(
            "Escribe o pega la letra aquí...\n\n"
            "Formato sincronizado LRC:\n"
            "[00:12.34]Primera línea\n"
            "[00:18.56]Segunda línea"
        )
        evl.addWidget(self._lyrics_edit)

        btn_row = QHBoxLayout()
        self._save_btn = QPushButton("Guardar en archivo")
        self._save_btn.setCursor(Qt.PointingHandCursor)
        self._save_btn.setStyleSheet(glass_button_qss("primary"))
        self._save_btn.clicked.connect(self._save_lyrics)
        btn_row.addWidget(self._save_btn)

        self._clear_btn = QPushButton("Limpiar")
        self._clear_btn.setCursor(Qt.PointingHandCursor)
        self._clear_btn.setStyleSheet(glass_button_qss("ghost"))
        self._clear_btn.clicked.connect(self._clear_lyrics)
        btn_row.addWidget(self._clear_btn)

        btn_row.addStretch()
        evl.addLayout(btn_row)
        cl.addWidget(edit_card)

        cl.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _get_client(self):
        if self._client is None:
            from lyrics.lrclib_client import LrcLibClient
            self._client = LrcLibClient()
        return self._client

    def _search_lyrics(self):
        title = self._title_input.text().strip()
        artist = self._artist_input.text().strip()
        if not title:
            return

        self._search_progress.setVisible(True)
        self._search_btn.setEnabled(False)

        try:
            client = self._get_client()
            result = client.get_lyrics(title, artist, "", 0)

            if result and (result.plain or result.lines):
                if result.lines:
                    lrc_lines = "\n".join(
                        f"[{int(line.timestamp // 60):02d}:"
                        f"{int(line.timestamp % 60):02d}.{int((line.timestamp % 1) * 100):02d}]"
                        f"{line.text}"
                        for line in result.lines
                    )
                    self._lyrics_edit.setPlainText(lrc_lines)
                else:
                    self._lyrics_edit.setPlainText(result.plain)

                self._current_lyrics = self._lyrics_edit.toPlainText()
                self._current_title = title
                self._current_artist = artist
                self._info_label.setText(
                    f"Letra de \"{title}\""
                    f"{f' — {artist}' if artist else ''}"
                    f"  (fuente: {result.source})"
                )
            else:
                self._lyrics_edit.setPlainText("")
                self._info_label.setText(
                    f"No se encontraron letras para \"{title}\"."
                )

        except Exception as e:
            logger.exception("Lyrics search failed")
            self._info_label.setText(f"Error: {e}")

        self._search_progress.setVisible(False)
        self._search_btn.setEnabled(True)

    def _save_lyrics(self):
        text = self._lyrics_edit.toPlainText().strip()
        if not text:
            QMessageBox.information(
                self, "Letras",
                "No hay texto para guardar."
            )
            return

        if not self._current_title:
            self._current_title = self._title_input.text().strip() or "Canción"

        try:
            from metadata.tag_writer import write_tags
            from metadata.tag_model import TrackTags

            tags = TrackTags(
                title=self._current_title,
                artist=self._current_artist or "",
                lyrics=text,
            )
            tags.mark_dirty("lyrics")

            reply = QMessageBox.question(
                self, "Guardar letra",
                "¿Guardar la letra en los metadatos del archivo?\n\n"
                "Necesitas seleccionar el archivo de audio.",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

            from PySide6.QtWidgets import QFileDialog
            fp, _ = QFileDialog.getOpenFileName(
                self, "Seleccionar archivo de audio", "",
                "Audio (*.flac *.mp3 *.m4a *.ogg *.opus)"
            )
            if fp:
                tags.filepath = fp
                write_tags(fp, tags)
                self._info_label.setText(
                    f"Letra guardada en {fp.split('/')[-1]}"
                )
                logger.info("Lyrics saved to %s", fp)

        except Exception as e:
            logger.exception("Failed to save lyrics")
            QMessageBox.warning(self, "Error", f"No se pudo guardar: {e}")

    def _clear_lyrics(self):
        self._lyrics_edit.setPlainText("")
        self._current_lyrics = ""
        self._info_label.setText("Editor limpiado.")
