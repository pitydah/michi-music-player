"""SearchRouter — routes search text to the correct section handler."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.window import MainWindow


class SearchRouter:
    """Dispatches search text changes and search results by section."""

    def __init__(self, window: MainWindow):
        self._win = window

    def on_search(self, text: str):
        w = self._win
        w._search_text = text.strip()
        if w._current_section_key == "albums":
            w._refresh_active_library_tab(force=True)
            return
        if w._current_section_key == "genres":
            w._refresh_active_library_tab(force=True)
            return
        if w._current_section_key == "folders":
            w._folder_browser.set_filter(w._search_text)
            return
        if w._current_section_key in ("favs", "recent", "mix_unplayed"):
            return
        if w._current_section_key == "artists" and not w._artist_repo.current_key:
            query = w._search_text.lower()
            if not query:
                filtered = w._artist_repo.groups
            else:
                filtered = [
                    g for g in w._artist_repo.groups
                    if query in g.display_name.lower()
                    or any(query in a.title.lower() for a in g.albums)
                    or any(query in (t.title or "").lower() for t in g.all_tracks)
                    or any(query in g.lower() for g in g.genres)
                ]
            w._artist_grid.set_artists(filtered)
            w._count.setText(f"{len(filtered)} artistas")
            return
        if w._current_section_key == "radio":
            w._radio_widget.set_filter(w._search_text)
            return
        w._apply_filters()

    def on_results(self, results: list):
        w = self._win
        if w._current_section_key not in ("library",):
            return
        w._model.populate(results)
        n = len(results)
        w._count.setText(f"{n} elementos" if n else "0 elementos")
        if n:
            w._show_library_hub_page()
            if w._library_hub_page:
                w._library_hub_page.set_current_section("library")
            w._songs_stack.setCurrentIndex(0)
            w._table.setModel(w._model)
            w._table.setColumnWidth(0, 72)
            w._table.setColumnWidth(1, 260)
            w._table.setColumnWidth(2, 170)
            w._table.setColumnWidth(3, 170)
            w._table.setColumnWidth(4, 70)
            w._table.setColumnWidth(5, 130)
            w._table.setColumnWidth(6, 80)
            w._table.setColumnWidth(7, 260)
        else:
            w._views.show("empty")
