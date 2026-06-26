"""Genre Grid — premium genre cards with mosaic covers, stats, and family badges."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QGridLayout,
    QLabel, QFrame, QComboBox, QLineEdit, QMenu,
)

from metadata.genre_grouping import GenreGroup
from library.album_art import load_cover_pixmap

_BG = "#090B11"
_PANEL = "rgba(255,255,255,0.025)"
_TEXT = "#FFFFFF"
_TEXT2 = "rgba(255,255,255,0.78)"
_TEXT3 = "rgba(255,255,255,0.62)"
_ACCENT = "#8FB7FF"

_CARD_QSS = """
    QFrame#genreCard {
        background: rgba(255,255,255,0.025);
        border: 1px solid rgba(255,255,255,0.045);
        border-radius: 16px;
    }
    QFrame#genreCard:hover {
        background: rgba(255,255,255,0.048);
        border: 1px solid rgba(143,183,255,0.10);
    }
    QFrame#genreCard QLabel { background: transparent; border: none; }
"""


def _format_dur(secs: float) -> str:
    if secs <= 0:
        return ""
    s = int(secs)
    h = s // 3600
    m = (s % 3600) // 60
    return f"{h} h {m} min" if h > 0 else f"{m} min"


class GenreGridWidget(QWidget):
    genre_selected = Signal(str)
    genre_play_requested = Signal(str)
    genre_shuffle_requested = Signal(str)
    genre_queue_requested = Signal(str)
    genre_playlist_requested = Signal(str)
    genre_metadata_requested = Signal(str)
    genre_normalize_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {_BG};")
        self._genres: list[GenreGroup] = []
        self._filter_family = "All"
        self._search_text = ""
        self._sort_key = "name"

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._scroll.setStyleSheet(
            f"QScrollArea {{ background: {_BG}; border: none; }}"
            "QScrollBar:vertical { background: transparent; width: 4px; margin: 4px; }"
            "QScrollBar::handle:vertical { background: rgba(255,255,255,0.10); border-radius: 2px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(24, 16, 24, 24)
        self._layout.setSpacing(12)

        self._build_hero()
        self._build_controls()
        self._build_grid()

        self._scroll.setWidget(self._container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._scroll)

    def _build_hero(self):
        hero = QFrame()
        hero.setObjectName("genreHero")
        hero.setStyleSheet(
            "QFrame#genreHero { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 rgba(255,255,255,0.04),stop:1 rgba(143,183,255,0.06));"
            "border: 1px solid rgba(143,183,255,0.08); border-radius: 18px; }"
            "QLabel { background: transparent; border: none; }")
        hero.setMinimumHeight(100)

        hl = QVBoxLayout(hero)
        hl.setContentsMargins(20, 14, 20, 14)
        hl.setSpacing(4)

        title = QLabel("Atlas de géneros")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {_TEXT};")
        hl.addWidget(title)

        self._hero_sub = QLabel("Explora tu biblioteca por estilos, escenas y épocas")
        self._hero_sub.setStyleSheet(f"font-size: 12px; color: {_TEXT3};")
        hl.addWidget(self._hero_sub)
        hl.addStretch()

        self._layout.addWidget(hero)

    def _build_controls(self):
        row = QHBoxLayout()
        row.setSpacing(8)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Buscar género...")
        self._search.setClearButtonEnabled(True)
        self._search.setFixedWidth(200)
        self._search.setStyleSheet(
            f"QLineEdit {{ background: rgba(255,255,255,0.06); color: {_TEXT};"
            f"border: 1px solid rgba(255,255,255,0.06); border-radius: 10px;"
            f"padding: 5px 10px; font-size: 12px; }}"
            f"QLineEdit:focus {{ border: 1px solid rgba(143,183,255,0.20); }}")
        self._search.textChanged.connect(self._on_search)
        row.addWidget(self._search)

        self._family_combo = QComboBox()
        self._family_combo.addItem("Todas las familias", "All")
        self._family_combo.setStyleSheet(
            f"QComboBox {{ background: rgba(255,255,255,0.06); color: {_TEXT};"
            f"border: 1px solid rgba(255,255,255,0.06); border-radius: 10px;"
            f"padding: 5px 10px; font-size: 12px; }}")
        self._family_combo.currentIndexChanged.connect(self._on_filter)
        row.addWidget(self._family_combo)

        self._sort_combo = QComboBox()
        for label, key in [("Nombre", "name"), ("Canciones", "track_count"),
                            ("Artistas", "artist_count"), ("Álbumes", "album_count")]:
            self._sort_combo.addItem(label, key)
        self._sort_combo.setStyleSheet(self._family_combo.styleSheet())
        self._sort_combo.currentIndexChanged.connect(self._on_sort)
        row.addWidget(self._sort_combo)

        self._stats_lbl = QLabel("")
        self._stats_lbl.setStyleSheet(f"color: {_TEXT3}; font-size: 11px;")
        row.addWidget(self._stats_lbl)
        row.addStretch()

        self._layout.addLayout(row)

    def _build_grid(self):
        self._grid = QGridLayout()
        self._grid.setSpacing(14)
        self._grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._layout.addLayout(self._grid)

    def set_genres(self, genres: list[GenreGroup], families: list[str] = None):
        self._genres = genres
        # Update family combo
        self._family_combo.blockSignals(True)
        self._family_combo.clear()
        self._family_combo.addItem("Todas las familias", "All")
        if families:
            for f in families:
                self._family_combo.addItem(f, f)
        self._family_combo.blockSignals(False)
        self._refresh()

    def _refresh(self):
        genres = self._genres

        # Filter
        if self._filter_family != "All":
            genres = [g for g in genres if g.family == self._filter_family]
        if self._search_text:
            q = self._search_text.lower()
            genres = [g for g in genres if q in g.name.lower()]

        # Sort
        key = self._sort_key

        if key == "name":
            genres = sorted(genres, key=lambda g: (g.key == "untagged", g.name.lower()))
        else:
            genres = sorted(genres, key=lambda g: (g.key == "untagged", -getattr(g, key, 0)))

        # Stats
        tagged = sum(1 for g in genres if g.key != "untagged")
        untagged = sum(1 for g in genres if g.key == "untagged")
        total = sum(g.track_count for g in genres)
        stat_parts = [f"{tagged} géneros", f"{total} canciones"]
        if untagged:
            stat_parts.append(f"{[g.track_count for g in genres if g.key == 'untagged'][0] if untagged else 0} sin género")
        self._stats_lbl.setText(" · ".join(stat_parts))

        # Rebuild grid
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cols = max(1, (self._scroll.viewport().width() - 48) // 260)
        for i, g in enumerate(genres):
            card = _GenreCard(g)
            card.clicked.connect(lambda k=g.key: self.genre_selected.emit(k))
            card.context_action.connect(lambda act, k=g.key: self._handle_ctx(act, k))
            self._grid.addWidget(card, i // cols, i % cols, Qt.AlignTop)

    def _on_search(self, text: str):
        self._search_text = text.strip()
        self._refresh()

    def _on_filter(self):
        self._filter_family = self._family_combo.currentData()
        self._refresh()

    def _on_sort(self):
        self._sort_key = self._sort_combo.currentData()
        self._refresh()

    def _handle_ctx(self, action: str, key: str):
        if action == "open":
            self.genre_selected.emit(key)
        elif action == "play":
            self.genre_play_requested.emit(key)
        elif action == "shuffle":
            self.genre_shuffle_requested.emit(key)
        elif action == "queue":
            self.genre_queue_requested.emit(key)
        elif action == "playlist":
            self.genre_playlist_requested.emit(key)
        elif action == "metadata":
            self.genre_metadata_requested.emit(key)
        elif action == "normalize":
            self.genre_normalize_requested.emit(key)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh()


class _GenreCard(QFrame):
    clicked = Signal(str)
    context_action = Signal(str, str)

    def __init__(self, genre: GenreGroup):
        super().__init__()
        self._genre = genre
        self.setObjectName("genreCard")
        self.setFixedSize(240, 200)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(_CARD_QSS)

        v = QVBoxLayout(self)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(6)

        # Mosaic cover
        cover = QFrame()
        cover.setFixedSize(216, 80)
        cover.setStyleSheet("background: transparent; border-radius: 10px;")
        cl = QGridLayout(cover)
        cl.setContentsMargins(2, 0, 2, 0)
        cl.setSpacing(2)
        for ci, cp in enumerate(genre.cover_paths[:4]):
            pix = load_cover_pixmap(cp, 50) if cp else None
            lbl = QLabel()
            if pix and not pix.isNull():
                lbl.setPixmap(pix.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                lbl.setStyleSheet("background: rgba(255,255,255,0.03); border-radius: 6px;")
            lbl.setAlignment(Qt.AlignCenter)
            cl.addWidget(lbl, ci // 2, ci % 2)
        v.addWidget(cover)

        # Name
        name = genre.name
        if len(name) > 22:
            name = name[:21] + "…"
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"color: {_TEXT}; font-size: 14px; font-weight: 700;")
        v.addWidget(name_lbl)

        # Family + stats
        meta = f"{genre.family}"
        if len(meta) > 30:
            meta = meta[:29] + "…"
        meta_lbl = QLabel(meta)
        meta_lbl.setStyleSheet(f"color: {_TEXT3}; font-size: 10px;")
        v.addWidget(meta_lbl)

        stats = f"{genre.track_count} canc · {genre.artist_count} art · {genre.album_count} alb"
        if len(stats) > 35:
            stats = stats[:34] + "…"
        s_lbl = QLabel(stats)
        s_lbl.setStyleSheet(f"color: {_TEXT3}; font-size: 10px;")
        v.addWidget(s_lbl)

        # Quality badge
        if genre.quality_summary:
            q = QLabel(genre.quality_summary)
            q.setStyleSheet(
                f"background: rgba(143,183,255,0.10); color: {_ACCENT};"
                f"font-size: 9px; font-weight: 600; border-radius: 5px; padding: 1px 6px;")
            v.addWidget(q)

        v.addStretch()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._genre.key)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: rgba(20,22,28,0.97); border: 1px solid rgba(255,255,255,0.06);"
            "border-radius: 10px; padding: 4px; color: rgba(255,255,255,0.88); }"
            "QMenu::item { padding: 6px 24px 6px 12px; border-radius: 6px; }"
            "QMenu::item:selected { background: rgba(143,183,255,0.16); }")
        menu.addAction("Abrir género", lambda: self.context_action.emit("open", self._genre.key))
        menu.addSeparator()
        menu.addAction("Reproducir todo", lambda: self.context_action.emit("play", self._genre.key))
        menu.addAction("Aleatorio", lambda: self.context_action.emit("shuffle", self._genre.key))
        menu.addAction("Añadir a cola", lambda: self.context_action.emit("queue", self._genre.key))
        menu.addAction("Crear playlist", lambda: self.context_action.emit("playlist", self._genre.key))
        menu.addSeparator()
        menu.addAction("Normalizar género", lambda: self.context_action.emit("normalize", self._genre.key))
        menu.exec(event.globalPos())
