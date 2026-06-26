"""Album grid — premium 2D glass mosaic of album cards with metadata."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QIcon, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QGridLayout,
    QPushButton, QLabel, QFrame, QMenu,
    QGraphicsDropShadowEffect,
)

from library.album_art import load_covers_for_albums, CoverFlowItem
from library.library_db import MediaItem

_EMPTY_STATE_CSS = """
    QLabel {
        color: #FFFFFF; font-size: 16px; font-weight: 600;
        background: transparent; border: none;
    }
"""
_EMPTY_SUB_CSS = """
    QLabel {
        color: rgba(255,255,255,0.68); font-size: 12px;
        background: transparent; border: none; padding: 4px 0 16px 0;
    }
"""


def _format_duration(seconds: int) -> str:
    if seconds <= 0:
        return ""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    if h > 0:
        return f"{h} h {m} min"
    return f"{m} min"


def _tracks_label(count: int) -> str:
    if count == 1:
        return "1 canción"
    return f"{count} canciones"


class AlbumGridWidget(QWidget):
    """Scrollable premium album mosaic — responsive, sortable, filterable."""

    album_double_clicked = Signal(list)
    album_selected = Signal(object)
    queue_requested = Signal(list)
    playlist_requested = Signal(list)
    cover_search_requested = Signal(object)
    open_folder_requested = Signal(str)
    details_requested = Signal(object)
    add_folder_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[MediaItem] = []
        self._groups: list[CoverFlowItem] = []
        self._cover_size = 200
        self._sort_key = "title"
        self._filter_mode = "all"
        self._group_mode = None
        self._last_sig = None
        self._groups_cache = None
        self._last_cols = -1
        self._selected_index = -1
        self._cards: list[_AlbumCard] = []
        self._worker_mgr = None
        self._pending_covers = False

        self.setStyleSheet("background: transparent;")

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        from ui.central.central_styles import scrollbar_qss
        self._scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }" +
            scrollbar_qss())

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._grid = QGridLayout(self._container)
        self._grid.setSpacing(20)
        self._grid.setContentsMargins(24, 20, 24, 24)
        self._grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self._scroll.setWidget(self._container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._scroll)

    # ── public API ──

    def set_items(self, items, cover_size=200, sort_key="title",
                  filter_mode="all", group_mode=None):
        self._items = list(items)
        self._cover_size = cover_size
        self._sort_key = sort_key
        self._filter_mode = filter_mode
        self._group_mode = group_mode
        self._selected_index = -1
        self._groups_cache = None
        self._last_sig = None
        self._last_cols = -1
        self._groups = []
        self._rebuild_grid()

    # ── responsive layout ──

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rebuild_grid()

    def _calculate_columns(self):
        vp_w = self._scroll.viewport().width()
        width = max(1, vp_w - 48)
        card_w = self._cover_size + 24
        return max(1, width // (card_w + 20))

    def set_worker_manager(self, mgr):
        """Set a WorkerManager for async cover loading. If set, covers load in background."""
        self._worker_mgr = mgr
        if mgr:
            mgr.covers_ready.connect(self._on_covers_ready)

    def _on_covers_ready(self, groups):
        groups = self._apply_filter(groups)
        self._sort_groups(groups)
        self._groups_cache = groups
        self._groups = groups
        self._pending_covers = False
        if not self._items:
            return
        self._rebuild_cards()

    def _rebuild_cards(self):
        groups = self._groups
        cols = self._calculate_columns()
        sig = (cols, len(groups), self._sort_key, self._filter_mode,
               self._group_mode, tuple(g.title for g in groups[:50]))
        if sig == self._last_sig:
            return
        self._last_sig = sig
        self._render_cards(groups)

    def _rebuild_cards_from(self, cached_groups):
        self._render_cards(cached_groups)

    def _rebuild_grid(self):
        cols = self._calculate_columns()

        if self._groups_cache is not None and cols == self._last_cols:
            sig = (cols, len(self._groups_cache), self._sort_key,
                   self._filter_mode, self._group_mode)
            if sig == self._last_sig:
                return
        self._last_cols = cols

        # Offload cover loading to WorkerManager if available
        if self._worker_mgr and self._items:
            self._pending_covers = True
            self._worker_mgr.load_covers(self._items, self._cover_size)
            # Show cached groups while loading
            if self._groups_cache:
                self._rebuild_cards_from(self._groups_cache)
            return

        # Synchronous fallback
        groups = load_covers_for_albums(self._items, self._cover_size)
        groups = self._apply_filter(groups)
        self._sort_groups(groups)
        self._groups_cache = groups
        self._groups = groups
        self._rebuild_cards()

    def _render_cards(self, groups):
        cols = self._calculate_columns()
        if self._selected_index >= len(groups):
            self._selected_index = -1
        while self._grid.count():
            w = self._grid.takeAt(0).widget()
            if w:
                w.deleteLater()
        self._cards = []

        if not groups:
            self._build_empty_state()
            return

        for i, group in enumerate(groups):
            card = _AlbumCard(group, self._cover_size, i)
            tracks = group.data.get("tracks", [])
            fps = [t.filepath for t in tracks]

            card.double_clicked.connect(
                lambda f=fps: self.album_double_clicked.emit(f))
            card.context_action.connect(
                lambda action, idx=i: self._handle_context(action, idx))
            card.selected.connect(self._select_card)

            if self._selected_index == i:
                card.set_active(True)

            self._cards.append(card)
            row = i // cols
            col = i % cols
            self._grid.addWidget(card, row, col, Qt.AlignTop)

    # ── sorting ──

    def _sort_groups(self, groups):
        key = self._sort_key
        if key == "title":
            groups.sort(key=lambda g: g.title.lower())
        elif key == "artist":
            groups.sort(key=lambda g: (g.subtitle or "").lower())
        elif key == "year":
            groups.sort(key=self._year_sort_key)
        elif key == "tracks":
            groups.sort(key=lambda g: len(g.data.get("tracks", [])), reverse=True)
        elif key == "duration":
            groups.sort(
                key=lambda g: sum(
                    getattr(t, 'duration', 0) or 0
                    for t in g.data.get("tracks", [])),
                reverse=True)

    @staticmethod
    def _year_sort_key(group):
        tracks = group.data.get("tracks", [])
        years = []
        for t in tracks:
            y = getattr(t, 'year', 0) or 0
            if y:
                years.append(y)
        return years[0] if years else 9999

    # ── filtering ──

    def _apply_filter(self, groups):
        mode = self._filter_mode
        if mode == "all":
            return groups
        if mode == "no_cover":
            return [g for g in groups if g.pixmap is None or g.pixmap.isNull()]
        if mode == "incomplete":
            return [g for g in groups if len(g.data.get("tracks", [])) < 2]
        if mode in ("flac", "mp3", "wav", "aac", "ogg"):
            ext = mode
            return [g for g in groups if any(
                (getattr(t, 'ext', '') or '').lower().lstrip('.') == ext
                for t in g.data.get("tracks", []))]
        return groups

    # ── selection ──

    def _select_card(self, idx: int):
        for i, card in enumerate(self._cards):
            card.set_active(i == idx)
        self._selected_index = idx
        if 0 <= idx < len(self._groups):
            self.album_selected.emit(self._groups[idx])

    def _handle_context(self, action: str, idx: int):
        if idx < 0 or idx >= len(self._groups):
            return
        group = self._groups[idx]
        tracks = group.data.get("tracks", [])
        fps = [t.filepath for t in tracks]

        if action == "play":
            self.album_double_clicked.emit(fps)
        elif action == "queue":
            self.queue_requested.emit(fps)
        elif action == "playlist":
            self.playlist_requested.emit(fps)
        elif action == "cover":
            self.cover_search_requested.emit(group)
        elif action == "folder":
            if fps:
                import os
                d = os.path.dirname(fps[0])
                self.open_folder_requested.emit(d)
        elif action == "details":
            self.details_requested.emit(group)

    # ── empty state ──

    def _build_empty_state(self):
        wrapper = QFrame()
        wrapper.setFixedWidth(420)
        wrapper.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.025);"
            " border: 1px solid rgba(255,255,255,0.06);"
            " border-radius: 18px; }")
        v = QVBoxLayout(wrapper)
        v.setAlignment(Qt.AlignCenter)
        v.setContentsMargins(60, 48, 60, 48)
        v.setSpacing(2)

        icon = QLabel()
        icon.setPixmap(_placeholder_album_icon(72))
        icon.setAlignment(Qt.AlignCenter)
        v.addWidget(icon)

        title = QLabel("No hay álbumes detectados")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(_EMPTY_STATE_CSS)
        v.addWidget(title)

        sub = QLabel("Añade una carpeta musical para construir tu biblioteca de álbumes")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(_EMPTY_SUB_CSS)
        v.addWidget(sub)

        btn = QPushButton("Agregar carpeta")
        btn.setFixedSize(160, 38)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 19px;
                color: rgba(255,255,255,0.88); font-size: 12.5px; font-weight: 500;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.13);
                border: 1px solid rgba(255,255,255,0.18);
            }
        """)
        btn.clicked.connect(self.add_folder_requested.emit)
        v.addWidget(btn, alignment=Qt.AlignCenter)

        self._grid.addWidget(wrapper, 0, 0, -1, -1, Qt.AlignCenter)


def _placeholder_album_icon(size=72) -> QPixmap:
    from PySide6.QtGui import QPainter, QColor, QPen
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    # Flat disc shape
    p.setPen(QPen(QColor(255, 255, 255, 25), 2))
    p.setBrush(QColor(255, 255, 255, 10))
    p.drawRoundedRect(4, 4, size - 8, size - 8, 14, 14)
    # Inner hole
    p.setBrush(QColor(9, 11, 17))
    hole = size // 6
    p.drawEllipse((size - hole * 2) // 2, (size - hole * 2) // 2, hole * 2, hole * 2)
    p.end()
    return pix


# ═══════════════════════════════════════════════════════════
# _AlbumCard — premium glass album card
# ═══════════════════════════════════════════════════════════

class _AlbumCard(QFrame):
    double_clicked = Signal()
    selected = Signal(int)          # card index
    context_action = Signal(str)    # action name

    def __init__(self, cover_item: CoverFlowItem, cover_size: int, index: int):
        super().__init__()
        self._item = cover_item
        self._index = index
        self._active = False

        card_w = cover_size + 24
        card_h = cover_size + 126
        self.setFixedSize(card_w, card_h)
        self.setCursor(Qt.PointingHandCursor)
        self._apply_qss()

        # subtle shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 70))
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(7)

        # ── Cover ──
        cover = QPushButton()
        cover.setFixedSize(cover_size, cover_size)
        cover.setIconSize(QSize(cover_size - 8, cover_size - 8))
        cover.setFlat(True)
        cover.setCursor(Qt.PointingHandCursor)
        cover.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.050);
                border: 1px solid rgba(255,255,255,0.04);
                border-radius: 14px;
                padding: 0px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.070);
                border: 1px solid rgba(255,255,255,0.13);
            }
        """)

        if cover_item.pixmap and not cover_item.pixmap.isNull():
            scaled = cover_item.pixmap.scaled(
                cover_size - 8, cover_size - 8,
                Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            cover.setIcon(QIcon(scaled))
        else:
            # placeholder with glass disc icon
            place = QLabel()
            place.setPixmap(_placeholder_album_icon(cover_size - 8))
            place.setAlignment(Qt.AlignCenter)
            place.setStyleSheet("background: transparent;")
            place.setParent(cover)
            place.setGeometry(4, 4, cover_size - 8, cover_size - 8)

        cover.clicked.connect(lambda: self.selected.emit(self._index))
        layout.addWidget(cover, alignment=Qt.AlignCenter)

        # ── Title ──
        title_text = cover_item.title
        if len(title_text) > 30:
            title_text = title_text[:29] + "…"
        title_lbl = QLabel(title_text)
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setWordWrap(False)
        title_lbl.setStyleSheet(
            "QLabel { color: #FFFFFF; font-size: 13px; font-weight: 700;"
            "  background: transparent; }")
        layout.addWidget(title_lbl)

        # ── Subtitle (artist + year) ──
        # subtitle from load_covers_for_albums already contains "artist · year · N ♪"
        # let's parse it into a cleaner format
        artist, year_str = _parse_subtitle(cover_item)
        display_sub = artist or "—"
        if year_str:
            display_sub = f"{display_sub} · {year_str}"
        if len(display_sub) > 34:
            display_sub = display_sub[:33] + "…"

        sub_lbl = QLabel(display_sub)
        sub_lbl.setAlignment(Qt.AlignCenter)
        sub_lbl.setWordWrap(False)
        sub_lbl.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.82); font-size: 11.2px; font-weight: 500;"
            "  background: transparent; }")
        layout.addWidget(sub_lbl)

        # ── Track count + duration ──
        tracks = cover_item.data.get("tracks", [])
        count = len(tracks)
        dur = sum(getattr(t, 'duration', 0) or 0 for t in tracks)
        dur_str = _format_duration(dur)

        info_parts = []
        if count:
            info_parts.append(_tracks_label(count))
        if dur_str:
            info_parts.append(dur_str)

        info_lbl = QLabel(" · ".join(info_parts))
        info_lbl.setAlignment(Qt.AlignCenter)
        info_lbl.setWordWrap(False)
        info_lbl.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.66); font-size: 10.5px;"
            "  background: transparent; }")
        layout.addWidget(info_lbl)

        # ── Format badge ──
        fmt_str = ""
        if tracks:
            exts = set(
                (getattr(t, 'ext', '') or '').upper().lstrip(".")
                for t in tracks if getattr(t, 'ext', ''))
            if exts:
                fmt_str = " · ".join(sorted(exts))[:22]

        # Detect special states for badge coloring
        no_cover = cover_item.pixmap is None or cover_item.pixmap.isNull()
        incomplete = count < 2

        badge_texts = []
        if fmt_str:
            badge_texts.append(fmt_str)
        if no_cover:
            badge_texts.append("Sin carátula")
        if incomplete:
            badge_texts.append("Incompleto")

        if badge_texts:
            badge = QLabel("  ·  ".join(badge_texts))
            badge.setAlignment(Qt.AlignCenter)
            badge.setWordWrap(False)
            # special styling for "incomplete" or "no cover" warnings
            warn = no_cover or incomplete
            badge.setStyleSheet(f"""
                QLabel {{
                    color: rgba(255,255,255,0.78);
                    font-size: 9.5px;
                    background: rgba(255,255,255,{0.06 if warn else 0.04});
                    border: 1px solid rgba(255,255,255,{0.05 if warn else 0.03});
                    border-radius: 7px;
                    padding: 2px 7px;
                }}
            """)
            layout.addWidget(badge, alignment=Qt.AlignCenter)

        # ── Tooltip with full metadata ──
        tooltip_parts = [cover_item.title, artist or "—"]
        if year_str:
            tooltip_parts.append(year_str)
        if count:
            tooltip_parts.append(_tracks_label(count))
        if dur_str:
            tooltip_parts.append(dur_str)
        if fmt_str:
            tooltip_parts.append(fmt_str)
        self.setToolTip("\n".join(tooltip_parts))

    # ── visual state ──

    def _apply_qss(self):
        self.setObjectName("albumCard")
        self.setStyleSheet("""
            QFrame#albumCard {
                background: rgba(255,255,255,0.030);
                border: 1px solid rgba(255,255,255,0.025);
                border-radius: 18px;
            }
            QFrame#albumCard:hover {
                background: rgba(255,255,255,0.048);
                border: 1px solid rgba(143,183,255,0.10);
            }
            QFrame#albumCard[active="true"] {
                background: rgba(143,183,255,0.12);
                border: 1px solid rgba(143,183,255,0.16);
            }
        """)

    def set_active(self, active: bool):
        if self._active == active:
            return
        self._active = active
        self.setProperty("active", str(active).lower())
        self.style().unpolish(self)
        self.style().polish(self)

    # ── mouse events ──

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selected.emit(self._index)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        from ui.central.central_styles import menu_qss
        menu = QMenu(self)
        menu.setStyleSheet(menu_qss())

        play_action = menu.addAction("Reproducir álbum")
        queue_action = menu.addAction("Añadir a la cola")
        menu.addSeparator()
        playlist_action = menu.addAction("Crear playlist")
        menu.addSeparator()
        cover_action = menu.addAction("Buscar carátula")
        folder_action = menu.addAction("Abrir carpeta")
        details_action = menu.addAction("Ver detalles")

        action_chosen = menu.exec(event.globalPos())
        if action_chosen == play_action:
            self.context_action.emit("play")
        elif action_chosen == queue_action:
            self.context_action.emit("queue")
        elif action_chosen == playlist_action:
            self.context_action.emit("playlist")
        elif action_chosen == cover_action:
            self.context_action.emit("cover")
        elif action_chosen == folder_action:
            self.context_action.emit("folder")
        elif action_chosen == details_action:
            self.context_action.emit("details")


def _parse_subtitle(item: CoverFlowItem) -> tuple[str, str]:
    """Extract artist and year from the raw subtitle string."""
    raw = item.subtitle or ""
    parts = [p.strip() for p in raw.split("·")]
    artist = ""
    year = ""
    for p in parts:
        if p.isdigit() and len(p) == 4:
            year = p
        elif "♪" not in p and not artist:
            artist = p
    return artist, year
