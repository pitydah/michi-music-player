"""Artist Grid — premium mosaic/list of artists with cards and context menu."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QColor, QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QGridLayout,
    QLabel, QFrame, QListWidget, QListWidgetItem,
    QMenu,
)

from library.artist_grouping import ArtistGroup
from library.album_art import load_cover_pixmap
from ui.central.central_styles import menu_qss

_BG = "#090B11"
_PANEL = "rgba(255,255,255,0.035)"
_HOVER = "rgba(255,255,255,0.075)"
_SELECTED = "rgba(255,255,255,0.115)"
_BORDER = "rgba(255,255,255,0.075)"
_TEXT = "#FFFFFF"
_TEXT2 = "rgba(255,255,255,0.78)"
_TEXT3 = "rgba(255,255,255,0.62)"


def _format_dur(secs: float) -> str:
    if secs <= 0:
        return ""
    s = int(secs)
    h = s // 3600
    m = (s % 3600) // 60
    return f"{h} h {m} min" if h > 0 else f"{m} min"


class ArtistGridWidget(QWidget):
    artist_selected = Signal(str)           # artist key
    artist_play_requested = Signal(str)
    artist_queue_requested = Signal(str)
    artist_playlist_requested = Signal(str)
    artist_metadata_requested = Signal(str)

    artist_enrich_requested = Signal(str)  # artist key

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {_BG};")
        self._artists: list[ArtistGroup] = []
        self._view_mode = "grid"
        self._cover_size = 180
        self._selected_key = ""
        self._last_cols = -1

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._scroll.setStyleSheet(f"""
            QScrollArea {{ background: {_BG}; border: none; }}
            QScrollBar:vertical {{
                background: rgba(255,255,255,0.025); width: 10px;
                margin: 4px; border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255,255,255,0.18); min-height: 44px; border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{ background: rgba(255,255,255,0.30); }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._grid = QGridLayout(self._container)
        self._grid.setSpacing(18)
        self._grid.setContentsMargins(24, 20, 24, 24)
        self._grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self._scroll.setWidget(self._container)

        self._list = QListWidget()
        self._list.setStyleSheet(f"""
            QListWidget {{
                background: transparent; border: none; color: {_TEXT2}; font-size: 13px;
            }}
            QListWidget::item {{ padding: 10px 14px; border-radius: 10px; margin: 2px 8px; }}
            QListWidget::item:hover {{ background: {_HOVER}; color: {_TEXT}; }}
            QListWidget::item:selected {{ background: {_SELECTED}; color: {_TEXT}; }}
        """)
        self._list.itemClicked.connect(self._on_list_item_clicked)
        self._list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_list_context)
        self._list.hide()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._scroll)
        outer.addWidget(self._list)

        self._empty_label = QLabel(
            "No hay artistas en tu biblioteca\n\n"
            "Escanea una carpeta musical o revisa los\n"
            "metadatos de tus archivos.")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setWordWrap(True)
        self._empty_label.setStyleSheet(
            "font-size: 14px; color: rgba(255,255,255,0.54);"
            "background: transparent; border: none; padding: 48px;")
        self._empty_label.hide()
        outer.addWidget(self._empty_label)

    def set_artists(self, artists: list[ArtistGroup]):
        self._artists = artists
        self._last_cols = -1  # force rebuild on new artist list
        self._refresh()

    def set_view_mode(self, mode: str):
        self._view_mode = mode
        self._refresh()

    def _refresh(self):
        if self._view_mode == "grid":
            self._list.hide()
            self._scroll.show()
            self._rebuild_grid()
        else:
            self._scroll.hide()
            self._list.show()
            self._rebuild_list()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._view_mode == "grid":
            self._rebuild_grid()

    def _clear_grid(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _rebuild_grid(self):
        if not self._artists:
            self._clear_grid()
            self._last_cols = -1
            self._empty_label.show()
            self._scroll.hide()
            return
        self._empty_label.hide()
        self._scroll.show()

        cols = max(1, (self._scroll.viewport().width() - 48) // (self._cover_size + 40))
        if cols == self._last_cols and self._grid.count() > 0:
            return
        self._last_cols = cols
        self._clear_grid()

        for i, artist in enumerate(self._artists):
            card = _ArtistCard(artist, self._cover_size, i)
            card.clicked.connect(lambda k=artist.key: self.artist_selected.emit(k))
            card.context_action.connect(lambda act, k=artist.key: self._handle_context(act, k))
            if artist.key == self._selected_key:
                card.set_active(True)
            row = i // cols
            col = i % cols
            self._grid.addWidget(card, row, col, Qt.AlignTop)

    def _rebuild_list(self):
        if not self._artists:
            self._list.clear()
            self._empty_label.show()
            self._list.hide()
            return
        self._empty_label.hide()
        self._list.show()
        self._list.clear()
        for artist in self._artists:
            dur = _format_dur(artist.total_duration)
            meta = f"{artist.album_count} álbumes · {artist.track_count} canciones"
            if dur:
                meta += f" · {dur}"
            if artist.genres:
                meta += f" · {', '.join(artist.genres[:3])}"

            it = QListWidgetItem(f"{artist.display_name}\n{meta}")
            it.setData(Qt.UserRole, artist.key)
            if artist.cover_paths:
                cover = load_cover_pixmap(artist.cover_paths[0], 48)
                if cover and not cover.isNull():
                    it.setIcon(QIcon(cover))
            self._list.addItem(it)

    def _on_list_item_clicked(self, item):
        key = item.data(Qt.UserRole)
        if key:
            self.artist_selected.emit(key)

    def _on_list_context(self, pos):
        item = self._list.itemAt(pos)
        if not item:
            return
        key = item.data(Qt.UserRole)
        if key:
            self._show_context_menu(self._list.viewport().mapToGlobal(pos), key)

    def _handle_context(self, action: str, artist_key: str):
        if action == "open":
            self.artist_selected.emit(artist_key)
        elif action == "play":
            self.artist_play_requested.emit(artist_key)
        elif action == "queue":
            self.artist_queue_requested.emit(artist_key)
        elif action == "playlist":
            self.artist_playlist_requested.emit(artist_key)
        elif action == "metadata":
            self.artist_metadata_requested.emit(artist_key)
        elif action == "refresh_info":
            self.artist_enrich_requested.emit(artist_key)

    def _show_context_menu(self, pos, artist_key: str):
        menu = QMenu(self)
        menu.setStyleSheet(menu_qss())

        acts = {
            "Abrir artista": "open",
            "Reproducir todo": "play",
            "Anadir a la cola": "queue",
            "Crear playlist": "playlist",
            "Editar metadatos": "metadata",
            "Actualizar info externa": "refresh_info",
        }
        for label, action in acts.items():
            menu.addAction(label, lambda checked=False, a=action, k=artist_key: self._handle_context(a, k))

        menu.exec(pos)


class _ArtistCard(QFrame):
    clicked = Signal(str)
    context_action = Signal(str)

    def __init__(self, artist: ArtistGroup, size: int, index: int):
        super().__init__()
        self._artist = artist
        self._active = False
        card_w = size + 24
        card_h = size + 155
        self.setFixedSize(card_w, card_h)
        self.setCursor(Qt.PointingHandCursor)
        self._apply_qss()

        v = QVBoxLayout(self)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(6)

        # Cover area — external thumb if available, else mosaic
        cover_area = QFrame()
        cover_area.setFixedSize(size, size)
        cover_area.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.035); border-radius: 24px; }")
        c_layout = QGridLayout(cover_area)
        c_layout.setContentsMargins(4, 4, 4, 4)
        c_layout.setSpacing(4)

        # Try external thumb first — use model field set by enrichment service + repository
        external_img = None
        thumb_path = getattr(artist, 'thumb_path', '') or ''
        if thumb_path:
            import os as _os
            if _os.path.exists(thumb_path):
                external_img = QPixmap(thumb_path)

        if external_img and not external_img.isNull():
            thumb_lbl = QLabel()
            thumb_lbl.setPixmap(
                external_img.scaled(size - 8, size - 8,
                                     Qt.KeepAspectRatio, Qt.SmoothTransformation))
            thumb_lbl.setAlignment(Qt.AlignCenter)
            c_layout.addWidget(thumb_lbl, 0, 0, 2, 2, Qt.AlignCenter)
        elif artist.cover_paths:
            for ci in range(min(4, len(artist.cover_paths))):
                pix = load_cover_pixmap(artist.cover_paths[ci], size // 2 - 4)
                lbl = QLabel()
                if pix and not pix.isNull():
                    lbl.setPixmap(pix.scaled(size // 2 - 8, size // 2 - 8,
                                              Qt.KeepAspectRatio, Qt.SmoothTransformation))
                else:
                    lbl.setStyleSheet(
                        "background: rgba(255,255,255,0.04); border-radius: 8px;")
                lbl.setAlignment(Qt.AlignCenter)
                c_layout.addWidget(lbl, ci // 2, ci % 2, Qt.AlignCenter)
        else:
            place = QLabel()
            place.setPixmap(_artist_placeholder(size))
            place.setAlignment(Qt.AlignCenter)
            c_layout.addWidget(place, 0, 0, 2, 2, Qt.AlignCenter)

        v.addWidget(cover_area)

        # Name
        name = artist.display_name
        if len(name) > 24:
            name = name[:23] + "\u2026"
        name_lbl = QLabel(name)
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setWordWrap(False)
        name_lbl.setStyleSheet(
            f"color: {_TEXT}; font-size: 13px; font-weight: 700; background: transparent;")
        v.addWidget(name_lbl)

        # Badge row: enriched + meta
        badge_row = QHBoxLayout()
        badge_row.setAlignment(Qt.AlignCenter)
        badge_row.setSpacing(6)
        if artist.enrichment_status == "loaded":
            ext_badge = QLabel("Info")
            ext_badge.setStyleSheet(
                "background: rgba(143,183,255,0.14); color: rgba(143,183,255,0.88);"
                "font-size: 9px; font-weight: 700; border-radius: 5px; padding: 1px 6px;")
            ext_badge.setFixedHeight(16)
            badge_row.addWidget(ext_badge)
        elif artist.enrichment_status == "loading":
            ext_badge = QLabel("Cargando")
            ext_badge.setStyleSheet(
                "background: rgba(143,183,255,0.08); color: rgba(143,183,255,0.56);"
                "font-size: 9px; font-weight: 600; border-radius: 5px; padding: 1px 6px;")
            ext_badge.setFixedHeight(16)
            badge_row.addWidget(ext_badge)
        elif artist.enrichment_status == "error":
            ext_badge = QLabel("Error")
            ext_badge.setStyleSheet(
                "background: rgba(143,183,255,0.06); color: rgba(143,183,255,0.52);"
                "font-size: 9px; font-weight: 600; border-radius: 5px; padding: 1px 6px;")
            ext_badge.setFixedHeight(16)
            badge_row.addWidget(ext_badge)
        elif artist.enrichment_status == "not_found":
            ext_badge = QLabel("Sin info")
            ext_badge.setStyleSheet(
                "background: rgba(255,255,255,0.03); color: rgba(255,255,255,0.44);"
                "font-size: 9px; font-weight: 600; border-radius: 5px; padding: 1px 6px;")
            ext_badge.setFixedHeight(16)
            badge_row.addWidget(ext_badge)

        meta = f"{artist.album_count} alb · {artist.track_count} canc"
        if len(meta) > 28:
            meta = meta[:27] + "\u2026"
        meta_lbl = QLabel(meta)
        meta_lbl.setAlignment(Qt.AlignCenter)
        meta_lbl.setStyleSheet(f"color: {_TEXT3}; font-size: 10px; background: transparent;")
        badge_row.addWidget(meta_lbl)
        v.addLayout(badge_row)

        # Genres / years
        extra = ""
        if artist.genres:
            extra = ", ".join(artist.genres[:2])
        if artist.years:
            y_str = f"{artist.years[0]}\u2013{artist.years[-1]}" if len(artist.years) > 1 else str(artist.years[0])
            extra = f"{extra} \u00b7 {y_str}" if extra else y_str
        if extra:
            extra_lbl = QLabel(extra[:28])
            extra_lbl.setAlignment(Qt.AlignCenter)
            extra_lbl.setStyleSheet(
                f"color: {_TEXT3}; font-size: 10px; background: transparent;")
            v.addWidget(extra_lbl)

        v.addStretch()

    def _apply_qss(self):
        self.setObjectName("artistCard")
        self.setStyleSheet("""
            QFrame#artistCard {
                background: rgba(255,255,255,0.030);
                border: 1px solid rgba(255,255,255,0.025);
                border-radius: 18px;
            }
            QFrame#artistCard:hover {
                background: rgba(255,255,255,0.050);
                border: 1px solid rgba(143,183,255,0.10);
            }
            QFrame#artistCard[active="true"] {
                background: rgba(143,183,255,0.10);
                border: 1px solid rgba(143,183,255,0.14);
            }
        """)

    def set_active(self, active: bool):
        if self._active == active:
            return
        self._active = active
        self.setProperty("active", str(active).lower())
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._artist.key)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._artist.key)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet(menu_qss())

        menu.addAction("Abrir artista", lambda: self.context_action.emit("open"))
        menu.addSeparator()
        menu.addAction("Reproducir todo", lambda: self.context_action.emit("play"))
        menu.addAction("Anadir a la cola", lambda: self.context_action.emit("queue"))
        menu.addAction("Crear playlist", lambda: self.context_action.emit("playlist"))
        menu.addAction("Editar metadatos", lambda: self.context_action.emit("metadata"))
        menu.addSeparator()
        menu.addAction("Actualizar info externa", lambda: self.context_action.emit("refresh_info"))
        menu.exec(event.globalPos())


def _artist_placeholder(size: int) -> QPixmap:
    from PySide6.QtGui import QPainter, QPen
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor(255, 255, 255, 20), 2))
    p.setBrush(QColor(255, 255, 255, 8))
    p.drawRoundedRect(8, 8, size - 16, size - 16, 20, 20)
    p.end()
    return pix
