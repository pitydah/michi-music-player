"""AlbumSortMenu — builds and wires album sort/filter dropdown menus."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu

if TYPE_CHECKING:
    from ui.window import MainWindow


class AlbumSortMenu:
    """Constructs the sort and filter QMenus for the album grid view."""

    def __init__(self, window: MainWindow):
        self._win = window

    def build_sort(self):
        w = self._win
        sort_menu = QMenu(w)
        sort_menu.setStyleSheet(_MENU_QSS)
        for label, key in [
            ("Título", "title"),
            ("Artista", "artist"),
            ("Año", "year"),
            ("Duración", "duration"),
            ("Canciones", "tracks"),
        ]:
            action = sort_menu.addAction(label)
            action.setData(key)
            action.triggered.connect(
                lambda checked=False, k=key, _w=w: self._on_sort(k))
        w._album_sort_btn.setMenu(sort_menu)

    def build_filter(self):
        w = self._win
        filter_menu = QMenu(w)
        filter_menu.setStyleSheet(_MENU_QSS)
        for label, key in [
            ("Todos", "all"),
            ("Sin carátula", "no_cover"),
            ("Incompletos", "incomplete"),
            ("FLAC", "flac"),
            ("MP3", "mp3"),
        ]:
            action = filter_menu.addAction(label)
            action.setData(key)
            action.triggered.connect(
                lambda checked=False, k=key, _w=w: self._on_filter(k))
        w._album_filter_btn.setMenu(filter_menu)

    def _on_sort(self, key: str):
        w = self._win
        w._album_sort_key = key
        w._coverflow_cache_key = None
        if w._current_section_key == "albums":
            w._refresh_active_library_tab(force=True)

    def _on_filter(self, key: str):
        w = self._win
        w._album_filter_mode = key
        w._coverflow_cache_key = None
        if w._current_section_key == "albums":
            w._refresh_active_library_tab(force=True)


_MENU_QSS = """
    QMenu {
        background: rgba(22,24,31,0.97);
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 10px;
        padding: 6px 4px;
        color: rgba(255,255,255,0.88); font-size: 12.5px;
    }
    QMenu::item {
        padding: 7px 32px 7px 16px;
        border-radius: 6px;
    }
    QMenu::item:selected {
        background: rgba(255,255,255,0.09);
    }
"""
