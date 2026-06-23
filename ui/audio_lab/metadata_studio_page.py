"""MetadataStudioPage — wrapper for existing metadata editor + Smart Tagging."""

from __future__ import annotations

import contextlib

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QPushButton, QFrame, QSplitter,
)

from ui.audio_lab.services.smart_tagging_service import SmartTaggingService
from ui.audio_lab.models import TagSuggestion


class MetadataStudioPage(QWidget):
    def __init__(self, metadata_editor: QWidget,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("metadataStudioPage")
        self._editor = metadata_editor
        self._st_service = SmartTaggingService()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("metadataStudioHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 12, 20, 12)

        title_row = QVBoxLayout()
        title = QLabel("Metadata Studio")
        title.setObjectName("metadataStudioTitle")
        title_row.addWidget(title)

        subtitle = QLabel(
            "Edita metadatos, caratulas y organiza tu biblioteca."
        )
        subtitle.setObjectName("metadataStudioSubtitle")
        subtitle.setWordWrap(True)
        title_row.addWidget(subtitle)

        self._smart_btn = QPushButton("Buscar metadata con MusicBrainz")
        self._smart_btn.setObjectName("smartTagBtn")
        self._smart_btn.setCursor(Qt.PointingHandCursor)
        self._smart_btn.clicked.connect(self._on_start_smart_tagging)
        self._smart_btn.setVisible(False)
        title_row.addWidget(self._smart_btn)

        header_layout.addLayout(title_row)
        layout.addWidget(header)

        splitter = QSplitter(Qt.Vertical)
        splitter.setObjectName("metadataStudioSplitter")

        editor_container = QWidget()
        editor_layout = QVBoxLayout(editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.addWidget(self._editor)
        splitter.addWidget(editor_container)

        from ui.audio_lab.smart_tagging_panel import SmartTaggingPanel
        self._st_panel = SmartTaggingPanel()
        self._st_panel.suggestions_accepted.connect(self._on_suggestions_accepted)
        self._st_panel.setVisible(False)
        splitter.addWidget(self._st_panel)

        splitter.setSizes([500, 200])
        layout.addWidget(splitter, 1)

        self.setStyleSheet("""
            QWidget#metadataStudioPage {
                background: #090B11;
            }
            QFrame#metadataStudioHeader {
                background: transparent;
                border-bottom: 1px solid rgba(255,255,255,0.03);
            }
            QLabel#metadataStudioTitle {
                color: rgba(255,255,255,0.92);
                font-size: 16px;
                font-weight: 600;
            }
            QLabel#metadataStudioSubtitle {
                color: rgba(255,255,255,0.52);
                font-size: 12px;
                margin-top: 2px;
            }
            QSplitter#metadataStudioSplitter::handle {
                background: rgba(255,255,255,0.03);
                height: 1px;
            }
        """)
        from ui.central.central_styles import glass_button_qss
        self._smart_btn.setStyleSheet(glass_button_qss("primary"))

        self._editor.files_saved.connect(self._on_files_loaded)

    def _on_files_loaded(self):
        self._smart_btn.setVisible(True)
        self._smart_btn.setText("Buscar metadata con MusicBrainz")

    def _on_start_smart_tagging(self):
        self._smart_btn.setEnabled(False)
        self._st_panel.set_loading(True)
        self._st_panel.setVisible(True)

        suggestions: list[TagSuggestion] = []

        try:
            editor = self._editor
            if hasattr(editor, '_tags') and editor._tags:
                tags = editor._tags[0]
                artist = getattr(tags, 'artist', '') or ''
                title = getattr(tags, 'title', '') or ''
                album = getattr(tags, 'album', '') or ''
                genre = getattr(tags, 'genre', '') or ''

                if title:
                    track = type('Track', (), {
                        'title': title, 'artist': artist,
                        'album': album, 'genre': genre,
                        'track_number': getattr(tags, 'tracknumber', '') or '',
                        'duration': getattr(tags, 'duration', 0) or 0,
                    })()
                    suggestions.extend(self._st_service.suggest_for_track(track))

                if album:
                    suggestions.extend(self._st_service.suggest_for_album(artist, album))

                if artist:
                    norm = self._st_service.normalize_artist_name(artist)
                    if norm.confidence > 0:
                        suggestions.append(norm)

                if genre:
                    genre_sug = self._st_service.suggest_genre(tags)
                    if genre_sug.confidence > 0:
                        suggestions.append(genre_sug)

        except Exception:
            import logging
            logging.getLogger("michi.audio_lab").warning("Smart tagging failed", exc_info=True)

        self._smart_btn.setEnabled(True)
        self._st_panel.set_loading(False)
        self._st_panel.set_suggestions(suggestions)

    def _on_suggestions_accepted(self, suggestions: list[TagSuggestion]):
        editor = self._editor
        if not hasattr(editor, '_tags') or not editor._tags:
            return

        for sug in suggestions:
            if not sug.apply or not sug.suggested:
                continue

            field = sug.field
            value = sug.suggested

            field_map = {
                "album": "album",
                "year": "date",
                "mb_album_id": "musicbrainz_albumid",
                "cover_url": "",
            }
            tag_field = field_map.get(field, field)

            if not tag_field:
                continue

            for tags in editor._tags:
                with contextlib.suppress(Exception):
                    tags.set_field(tag_field, value)

        if hasattr(editor, '_rebuild_after_load'):
            editor._rebuild_after_load()

        self._st_panel.setVisible(False)
