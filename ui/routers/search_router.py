"""SearchRouter — routes search text to the correct section handler."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.window import MainWindow


class SearchRouter:
    """Dispatches search text changes and search results by section."""

    def __init__(self, window: MainWindow):
        self._win = window

    def _context(self):
        return (
            getattr(getattr(self._win, "_services", None), "context_svc", None)
            or getattr(getattr(self._win, "_ctx", None), "context_svc", None)
        )

    @staticmethod
    def _section_key(w) -> str:
        return getattr(w, '_current_route_key', None) or w._current_section_key

    def _record_search_performed(self, section: str, result_count: int, query: str = ""):
        ctx = self._context()
        if ctx:
            ctx.record_search_performed(section=section, result_count=result_count, query=query)

    def on_search(self, text: str):
        w = self._win
        w._search_text = text.strip()
        sec = self._section_key(w)

        ctx = self._context()
        query = w._search_text

        if ctx:
            if query:
                ctx.update_selection(
                    scope="search",
                    search_query=query[:80],
                    album="",
                    artist="",
                    genre="",
                    playlist_id=None,
                    playlist_name="",
                    folder_name="",
                    mix_key="",
                )
            else:
                ctx.update_selection(
                    scope="search",
                    search_query="",
                )
                ctx.record_search_cleared(section=sec)

        if sec in ("albums", "genres"):
            w._lib_ctrl.refresh_active_tab(force=True)
            if ctx and query:
                count = None
                try:
                    if hasattr(w, '_model') and w._model:
                        count = w._model.rowCount()
                except Exception:
                    pass
                if count is not None:
                    ctx.record_search_performed(section=sec, result_count=count, query=query)
                else:
                    ctx.record_search_started(section=sec, query=query)
            return
        if sec == "folders":
            w._folder_browser.set_filter(w._search_text)
            if ctx and query:
                visible_count = getattr(w._folder_browser, "visible_count", None)
                if callable(visible_count):
                    try:
                        count = int(visible_count())
                    except Exception:
                        ctx.record_search_started(section=sec, query=query)
                    else:
                        self._record_search_performed(sec, count, query=query)
                else:
                    ctx.record_search_started(section=sec, query=query)
            return
        if sec in ("favs", "recent", "mix_unplayed"):
            return
        if sec == "artists" and not w._artist_repo.current_key:
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
            self._record_search_performed(sec, len(filtered), query=query)
            return
        if sec == "radio":
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
            pc = getattr(w, '_playback_ctrl', None)
            if pc:
                pc.attach_track_table(w._table, w._model)
            else:
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

        ctx = self._context()
        if ctx:
            ctx.record_search_performed(
                section=w._current_section_key,
                result_count=n,
                query=w._search_text,
            )
