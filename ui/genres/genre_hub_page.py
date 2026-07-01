"""GenreHubPage — main genres view with health summary, search, filters, and cards."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QGridLayout,
    QLabel, QFrame, QPushButton, QComboBox, QLineEdit,
)

from ui.central.central_styles import (
    glass_button_qss,
)
from ui.genres.genre_card import GenreCard
from ui.genres.genre_empty_states import GenreEmptyState

_BG = "#090B11"
_TEXT = "rgba(255,255,255,0.95)"
_TEXT2 = "rgba(255,255,255,0.78)"
_TEXT3 = "rgba(255,255,255,0.62)"
_ACCENT = "#8FB7FF"


class GenreHubPage(QWidget):
    genre_selected = Signal(str)
    genre_play_requested = Signal(str)
    genre_shuffle_requested = Signal(str)
    genre_queue_requested = Signal(str)
    genre_mix_requested = Signal(str)
    genre_radio_requested = Signal(str)
    genre_playlist_requested = Signal(str)
    genre_cleanup_requested = Signal(str)
    genre_normalize_requested = Signal(str)
    cleanup_page_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {_BG};")
        self._genres = []
        self._filter_family = "All"
        self._filter_health = "All"
        self._search_text = ""
        self._sort_key = "track_count"

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
        self._build_health_bar()
        self._build_controls()
        self._build_grid()
        self._empty_state = GenreEmptyState()
        self._layout.addWidget(self._empty_state)
        self._empty_state.setVisible(False)

        self._scroll.setWidget(self._container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._scroll)

    def _build_hero(self):
        hero = QFrame()
        hero.setObjectName("genreHubHero")
        hero.setStyleSheet(
            "QFrame#genreHubHero { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 rgba(255,255,255,0.04),stop:1 rgba(143,183,255,0.06));"
            "border: 1px solid rgba(143,183,255,0.08); border-radius: 18px; }"
            "QLabel { background: transparent; border: none; }")
        hero.setMinimumHeight(100)

        hl = QVBoxLayout(hero)
        hl.setContentsMargins(20, 14, 20, 14)
        hl.setSpacing(4)

        title = QLabel("Géneros")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {_TEXT};")
        hl.addWidget(title)

        self._hero_sub = QLabel("Ordena, limpia y descubre tu biblioteca por estilos musicales.")
        self._hero_sub.setStyleSheet(f"font-size: 12px; color: {_TEXT3};")
        hl.addWidget(self._hero_sub)

        hl.addStretch()
        self._layout.addWidget(hero)

    def _build_health_bar(self):
        self._health_card = QFrame()
        self._health_card.setObjectName("genreHealth")
        self._health_card.setStyleSheet(
            "QFrame#genreHealth { background: rgba(255,255,255,0.03);"
            "border: 1px solid rgba(255,255,255,0.04); border-radius: 12px; }")
        self._health_card.setVisible(False)
        hlayout = QHBoxLayout(self._health_card)
        hlayout.setContentsMargins(16, 10, 16, 10)
        hlayout.setSpacing(20)

        self._health_pct_lbl = QLabel("Salud: —%")
        self._health_pct_lbl.setStyleSheet(f"color: {_ACCENT}; font-size: 13px; font-weight: 700;")
        hlayout.addWidget(self._health_pct_lbl)

        self._untagged_lbl = QLabel("")
        self._untagged_lbl.setStyleSheet(f"color: {_TEXT3}; font-size: 11px;")
        self._untagged_lbl.setCursor(Qt.PointingHandCursor)
        hlayout.addWidget(self._untagged_lbl)

        self._dup_lbl = QLabel("")
        self._dup_lbl.setStyleSheet(f"color: {_TEXT3}; font-size: 11px;")
        self._dup_lbl.setCursor(Qt.PointingHandCursor)
        hlayout.addWidget(self._dup_lbl)

        self._junk_lbl = QLabel("")
        self._junk_lbl.setStyleSheet(f"color: {_TEXT3}; font-size: 11px;")
        self._junk_lbl.setCursor(Qt.PointingHandCursor)
        hlayout.addWidget(self._junk_lbl)

        hlayout.addStretch()
        self._layout.addWidget(self._health_card)

        self._untagged_lbl.mousePressEvent = lambda e: self.cleanup_page_requested.emit()
        self._dup_lbl.mousePressEvent = lambda e: self.cleanup_page_requested.emit()
        self._junk_lbl.mousePressEvent = lambda e: self.cleanup_page_requested.emit()

    def _build_controls(self):
        row = QHBoxLayout()
        row.setSpacing(8)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Buscar género...")
        self._search.setClearButtonEnabled(True)
        self._search.setFixedWidth(180)
        self._search.setStyleSheet(
            f"QLineEdit {{ background: rgba(255,255,255,0.06); color: {_TEXT};"
            f"border: 1px solid rgba(255,255,255,0.06); border-radius: 10px;"
            f"padding: 5px 10px; font-size: 12px; }}"
            f"QLineEdit:focus {{ border: 1px solid rgba(143,183,255,0.20); }}")
        self._search.textChanged.connect(self._on_search)
        row.addWidget(self._search)

        self._health_combo = QComboBox()
        for label, key in [("Todos", "All"), ("Limpios", "ok"),
                           ("Con advertencias", "warning"), ("Duplicados", "duplicate"),
                           ("Raros", "rare"), ("Sin metadata", "missing")]:
            self._health_combo.addItem(label, key)
        self._health_combo.setStyleSheet(
            f"QComboBox {{ background: rgba(255,255,255,0.06); color: {_TEXT};"
            f"border: 1px solid rgba(255,255,255,0.06); border-radius: 10px;"
            f"padding: 5px 10px; font-size: 12px; }}"
            "QComboBox::drop-down { border: none; width: 20px; }"
            "QComboBox::down-arrow { image: none; border-left: 4px solid transparent;"
            "border-right: 4px solid transparent; border-top: 5px solid rgba(255,255,255,0.4);"
            "margin-right: 6px; }")
        self._health_combo.currentIndexChanged.connect(self._on_filter)
        row.addWidget(self._health_combo)

        self._sort_combo = QComboBox()
        for label, key in [("Canciones", "track_count"), ("Nombre", "name"),
                           ("Álbumes", "album_count"), ("Artistas", "artist_count"),
                           ("Duración", "duration_total")]:
            self._sort_combo.addItem(label, key)
        self._sort_combo.setStyleSheet(self._health_combo.styleSheet())
        self._sort_combo.currentIndexChanged.connect(self._on_sort)
        row.addWidget(self._sort_combo)

        self._stats_lbl = QLabel("")
        self._stats_lbl.setStyleSheet(f"color: {_TEXT3}; font-size: 11px;")
        row.addWidget(self._stats_lbl)
        row.addStretch()

        for label, slot in [
            ("Limpiar géneros", self.cleanup_page_requested.emit),
        ]:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(glass_button_qss("ghost"))
            btn.setFixedHeight(28)
            btn.clicked.connect(slot)
            row.addWidget(btn)

        self._layout.addLayout(row)

    def _build_grid(self):
        self._grid = QGridLayout()
        self._grid.setSpacing(14)
        self._grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._layout.addLayout(self._grid)

    def set_genres(self, genres: list, health_summary: dict = None):
        self._genres = genres
        if health_summary:
            self._update_health(health_summary)
        self._refresh()

    def _update_health(self, h: dict):
        self._health_card.setVisible(True)
        pct = h.get("health_pct", 0)
        self._health_pct_lbl.setText(f"Salud de géneros: {pct}%")
        health_color = _ACCENT if pct >= 70 else ("#FFB347" if pct >= 50 else "#FF6B6B")
        self._health_pct_lbl.setStyleSheet(f"color: {health_color}; font-size: 13px; font-weight: 700;")

        untagged = h.get("missing_metadata", 0)
        self._untagged_lbl.setText(f"{untagged} canciones sin metadatos" if untagged else "")
        self._untagged_lbl.setVisible(untagged > 0)

        self._dup_lbl.setVisible(False)
        self._junk_lbl.setVisible(False)

    def set_health_issues(self, duplicates: int = 0, junk: int = 0, rare: int = 0):
        parts = []
        if duplicates:
            parts.append(f"{duplicates} posibles duplicados")
        if junk:
            parts.append(f"{junk} géneros basura")
        if rare:
            parts.append(f"{rare} géneros raros")
        if parts:
            lbl = " · ".join(parts)
            self._dup_lbl.setText(lbl)
            self._dup_lbl.setVisible(True)

    def _refresh(self):
        genres = self._genres

        if self._filter_health != "All":
            genres = [g for g in genres if g.get("health") == self._filter_health]
        if self._search_text:
            q = self._search_text.lower()
            genres = [g for g in genres if q in g.get("genre", "").lower()]

        key = self._sort_key
        if key == "name":
            genres = sorted(genres, key=lambda g: g.get("genre", "").lower())
        else:
            genres = sorted(genres, key=lambda g: -g.get(key, 0))

        self._stats_lbl.setText(
            f"{len(genres)} géneros · {sum(g.get('track_count', 0) for g in genres)} canciones"
        )

        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not genres:
            self._empty_state.setVisible(True)
            self._empty_state.show_no_genres()
            return
        self._empty_state.setVisible(False)

        cols = max(1, (self._scroll.viewport().width() - 48) // 260)
        for i, g in enumerate(genres):
            card = GenreCard(g)
            card.clicked.connect(lambda k=g.get("genre", ""): self.genre_selected.emit(k))
            card.play_requested.connect(lambda k=g.get("genre", ""): self.genre_play_requested.emit(k))
            card.mix_requested.connect(lambda k=g.get("genre", ""): self.genre_mix_requested.emit(k))
            card.radio_requested.connect(lambda k=g.get("genre", ""): self.genre_radio_requested.emit(k))
            card.playlist_requested.connect(lambda k=g.get("genre", ""): self.genre_playlist_requested.emit(k))
            card.cleanup_requested.connect(lambda k=g.get("genre", ""): self.genre_cleanup_requested.emit(k))
            self._grid.addWidget(card, i // cols, i % cols, Qt.AlignTop)

    def _on_search(self, text: str):
        self._search_text = text.strip()
        self._refresh()

    def _on_filter(self):
        self._filter_health = self._health_combo.currentData()
        self._refresh()

    def _on_sort(self):
        self._sort_key = self._sort_combo.currentData()
        self._refresh()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh()
