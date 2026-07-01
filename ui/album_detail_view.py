"""Album Detail View — premium audiophile album detail panel."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QAbstractItemView,
)

from ui.central.central_styles import (
    glass_button_qss, table_qss, table_header_qss,
    card_desc_qss, transparent_scrollbar_qss,
    section_title_qss,
)
from ui.effects.michi_glass import AcrylicBrush


class AlbumDetailView(QWidget):
    track_play_requested = Signal(str)

    play_album_requested = Signal(list)
    queue_album_requested = Signal(list)
    play_next_requested = Signal(list)
    playlist_album_requested = Signal(list)
    metadata_album_requested = Signal(list)
    cover_album_requested = Signal(object)
    quality_album_requested = Signal(list)
    send_to_server_requested = Signal(list)
    sync_mobile_requested = Signal(list)
    open_folder_requested = Signal(str)
    track_queue_requested = Signal(str)
    track_metadata_requested = Signal(str)
    track_analyze_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("albumDetailView")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(transparent_scrollbar_qss())

        content = QWidget()
        content.setObjectName("albumDetailContent")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(32, 16, 32, 40)
        cl.setSpacing(16)

        self._banner = _AlbumBanner()
        cl.addWidget(self._banner)

        self._tech_panel = _TechPanel()
        cl.addWidget(self._tech_panel)

        self._action_row = _ActionRow()
        cl.addWidget(self._action_row)

        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(
            ["#", "Canción", "Artista", "Duración", "Formato", "Calidad", "Estado"])
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setFrameShape(QFrame.NoFrame)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self._table.setColumnWidth(0, 40)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.setColumnWidth(2, 150)
        self._table.setColumnWidth(3, 70)
        self._table.setColumnWidth(4, 60)
        self._table.setColumnWidth(5, 80)
        self._table.setColumnWidth(6, 60)
        self._table.setStyleSheet(table_qss() + table_header_qss())
        self._table.setMinimumHeight(120)
        self._table.doubleClicked.connect(self._on_track_dbl)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_track_context_menu)
        cl.addWidget(self._table, 1)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        self._tracks = []

        self._action_row.play_clicked.connect(lambda: self.play_album_requested.emit(self._tracks))
        self._action_row.queue_clicked.connect(lambda: self.queue_album_requested.emit(self._tracks))
        self._action_row.playlist_clicked.connect(lambda: self.playlist_album_requested.emit(self._tracks))
        self._action_row.metadata_clicked.connect(lambda: self.metadata_album_requested.emit(self._tracks))
        self._action_row.cover_clicked.connect(lambda: self.cover_album_requested.emit(self._tracks))
        self._action_row.quality_clicked.connect(lambda: self.quality_album_requested.emit(self._tracks))
        self._action_row.server_clicked.connect(lambda: self.send_to_server_requested.emit(self._tracks))
        self._action_row.mobile_clicked.connect(lambda: self.sync_mobile_requested.emit(self._tracks))

    def set_album(self, title, artist, year="",
                  cover_pixmap=None, tracks=None,
                  total_duration="", format_info="",
                  quality_info=None, health_info=None,
                  track_count=0, disc_count=1):
        # Resolve cover via AlbumCoverService if not provided
        if cover_pixmap is None and tracks:
            try:
                from library.album_cover_service import AlbumCoverService
                result = AlbumCoverService().resolve_cover(tracks)
                cover_pixmap = result.pixmap
            except Exception:
                pass

        self._banner.set_album(title, artist, year, cover_pixmap,
                               total_duration, format_info)
        self._tech_panel.update_info(format_info, quality_info, health_info)
        self._tracks = tracks or []
        self._populate_tracks()
        self._action_row.set_mobile_available(False)

    def _on_track_dbl(self, idx):
        t = self._tracks[idx.row()] if idx.isValid() and hasattr(self, '_tracks') else None
        if t:
            fp = getattr(t, "filepath", "")
            if fp:
                self.track_play_requested.emit(fp)

    def _on_track_context_menu(self, pos):
        idx = self._table.indexAt(pos)
        if not idx.isValid():
            return
        t = self._tracks[idx.row()] if hasattr(self, '_tracks') else None
        if not t:
            return
        fp = getattr(t, "filepath", "")
        from PySide6.QtWidgets import QMenu
        from ui.central.central_styles import menu_qss
        menu = QMenu(self)
        menu.setStyleSheet(menu_qss())
        play_action = menu.addAction("Reproducir")
        queue_action = menu.addAction("Añadir a cola")
        menu.addSeparator()
        metadata_action = menu.addAction("Editar metadata")
        analyze_action = menu.addAction("Analizar calidad")
        folder_action = menu.addAction("Abrir carpeta")
        chosen = menu.exec(self._table.viewport().mapToGlobal(pos))
        if fp:
            if chosen == play_action:
                self.track_play_requested.emit(fp)
            elif chosen == queue_action:
                self.track_queue_requested.emit(fp)
            elif chosen == metadata_action:
                self.track_metadata_requested.emit(fp)
            elif chosen == analyze_action:
                self.track_analyze_requested.emit(fp)
            elif chosen == folder_action:
                import os
                folder = os.path.dirname(fp)
                self.open_folder_requested.emit(folder)

    def _populate_tracks(self):
        self._table.setRowCount(len(self._tracks))
        for i, t in enumerate(self._tracks):
            tn = getattr(t, "track_number", 0) or i + 1
            title = getattr(t, "title", "") or getattr(t, "filename", "—")
            artist = getattr(t, "artist", "") or "—"
            dur = getattr(t, "duration", 0) or 0
            dur_s = f"{int(dur // 60)}:{int(dur % 60):02d}" if dur else "—"
            ext = str(getattr(t, "ext", "") or "").lstrip(".").upper() or "—"
            quality = self._quality_for_track(t)
            status = self._status_for_track(t)

            self._table.setItem(i, 0, QTableWidgetItem(str(tn)))
            self._table.setItem(i, 1, QTableWidgetItem(title))
            self._table.setItem(i, 2, QTableWidgetItem(artist))
            self._table.setItem(i, 3, QTableWidgetItem(dur_s))
            self._table.setItem(i, 4, QTableWidgetItem(ext))
            self._table.setItem(i, 5, QTableWidgetItem(quality))
            self._table.setItem(i, 6, QTableWidgetItem(status))

    def _quality_for_track(self, t) -> str:
        sr = int(getattr(t, "sample_rate", 0) or 0)
        int(getattr(t, "bit_depth", 0) or 0)
        ext = str(getattr(t, "ext", "") or "").lstrip(".").upper()
        if ext in ("DSF", "DFF"):
            return "DSD"
        if sr > 48000:
            return "Hi-Res"
        if ext in ("FLAC", "ALAC", "WAV", "AIFF"):
            return "Lossless"
        return "—"

    def _status_for_track(self, t) -> str:
        import os
        fp = str(getattr(t, "filepath", "") or "")
        if not fp or not os.path.isfile(fp):
            return "Falta"
        title = str(getattr(t, "title", "") or getattr(t, "filename", "") or "").strip()
        if not title:
            return "Incompleto"
        return "OK"


class _AlbumBanner(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("albumBanner")
        self._brush = AcrylicBrush(tint_opacity=0.10, specular_opacity=22)
        self.setAttribute(Qt.WA_StyledBackground, False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(24)

        self._cover = QLabel()
        self._cover.setFixedSize(200, 200)
        self._cover.setAlignment(Qt.AlignCenter)
        self._cover.setStyleSheet(
            "QLabel { background: rgba(255,255,255,0.04); border-radius: 14px; }")
        layout.addWidget(self._cover)

        info = QVBoxLayout()
        info.setSpacing(6)

        self._title = QLabel("")
        self._title.setStyleSheet(section_title_qss())
        self._title.setWordWrap(True)
        info.addWidget(self._title)

        self._artist = QLabel("")
        self._artist.setStyleSheet(card_desc_qss())
        info.addWidget(self._artist)

        self._meta = QLabel("")
        self._meta.setStyleSheet(
            "color: rgba(255,255,255,0.56); font-size: 12px; background: transparent;")
        info.addWidget(self._meta)

        self._format = QLabel("")
        self._format.setStyleSheet(
            "color: rgba(143,183,255,0.60); font-size: 11px; background: transparent;")
        info.addWidget(self._format)

        info.addStretch()
        layout.addLayout(info, 1)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self._brush.paint(self, painter, clip_radius=18)
        painter.end()

    def set_album(self, title, artist, year="", cover_pixmap=None,
                  total_duration="", format_info=""):
        self._title.setText(title)
        self._artist.setText(artist)
        meta_parts = [p for p in [year, total_duration] if p]
        self._meta.setText(" · ".join(meta_parts))
        self._format.setText(format_info)
        if cover_pixmap and not cover_pixmap.isNull():
            self._cover.setPixmap(
                cover_pixmap.scaled(196, 196, Qt.KeepAspectRatio,
                                    Qt.SmoothTransformation))


class _TechPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("techPanel")
        self._brush = AcrylicBrush(tint_opacity=0.06, specular_opacity=18)
        self.setAttribute(Qt.WA_StyledBackground, False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(20)

        self._quality_label = QLabel("Calidad: —")
        self._quality_label.setStyleSheet(
            "color: rgba(143,183,255,0.75); font-size: 12px; background: transparent;")
        layout.addWidget(self._quality_label)

        self._format_label = QLabel("Formato: —")
        self._format_label.setStyleSheet(
            "color: rgba(255,255,255,0.55); font-size: 12px; background: transparent;")
        layout.addWidget(self._format_label)

        self._health_label = QLabel("")
        self._health_label.setStyleSheet(
            "color: rgba(255,255,255,0.50); font-size: 12px; background: transparent;")
        layout.addWidget(self._health_label, 1)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self._brush.paint(self, painter, clip_radius=14)
        painter.end()

    def update_info(self, format_info="", quality_info=None, health_info=None):
        if quality_info:
            self._quality_label.setText(f"Calidad: {quality_info}")
        if format_info:
            self._format_label.setText(f"Formato: {format_info}")
        if health_info:
            self._health_label.setText(health_info)


class _ActionRow(QFrame):
    play_clicked = Signal()
    queue_clicked = Signal()
    playlist_clicked = Signal()
    metadata_clicked = Signal()
    cover_clicked = Signal()
    quality_clicked = Signal()
    server_clicked = Signal()
    mobile_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(8)

        actions = [
            ("▶ Reproducir", self.play_clicked),
            ("Cola", self.queue_clicked),
            ("Playlist", self.playlist_clicked),
            ("Metadata", self.metadata_clicked),
            ("Carátula", self.cover_clicked),
            ("Calidad", self.quality_clicked),
            ("Servidor", self.server_clicked),
            ("Móvil", self.mobile_clicked),
        ]
        self._buttons = []
        for text, sig in actions:
            btn = QPushButton(text)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(glass_button_qss("secondary"))
            btn.setFixedHeight(32)
            btn.clicked.connect(sig.emit)
            layout.addWidget(btn)
            self._buttons.append(btn)

    def set_mobile_available(self, available: bool):
        """Enable or disable the Mobile sync button."""
        if len(self._buttons) >= 8:
            btn = self._buttons[7]
            btn.setEnabled(available)
            if not available:
                btn.setToolTip("Disponible cuando Michi Sync Suite esté configurado")
            else:
                btn.setToolTip("")
