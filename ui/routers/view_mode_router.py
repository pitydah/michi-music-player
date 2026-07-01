"""ViewModeRouter — dispatches view mode changes to the correct section handler."""

from __future__ import annotations

from typing import TYPE_CHECKING



if TYPE_CHECKING:
    from ui.window import MainWindow


class ViewModeRouter:
    """Routes view mode changes (list/grid/coverflow) to section-specific handlers."""

    def __init__(self, window: MainWindow):
        self._win = window

    @staticmethod
    def _section_key(w) -> str:
        return getattr(w, '_current_route_key', None) or w._current_section_key

    def on_mode_changed(self, mode: str):
        w = self._win
        w._restore_central_opacity()
        available = w._current_available_views()
        if mode not in available:
            return
        sec = self._section_key(w)
        if mode == "coverflow" and sec != "albums":
            return
        w._view_mode = mode
        self._show_current_section_view(mode)
        w._restore_central_opacity()

    def show_list_view(self):
        w = self._win
        w._view_switcher.set_view("list", emit=False)
        self.on_mode_changed("list")

    def show_grid_view(self):
        w = self._win
        w._view_switcher.set_view("grid", emit=False)
        self.on_mode_changed("grid")

    def _show_current_section_view(self, mode: str):
        w = self._win
        section = self._section_key(w)

        if section == "library":
            if mode == "list":
                w._songs_stack.setCurrentIndex(0)
                self._refresh_songs_list(w)
                w._fade_content("library_hub")
            elif mode == "grid":
                w._songs_stack.setCurrentIndex(1)
                w._show_song_grid()
                w._fade_content("library_hub")

        elif section == "albums":
            if mode == "grid":
                w._albums_stack.setCurrentIndex(0)
                w._show_album_grid()
                w._fade_content("library_hub")
            elif mode == "coverflow":
                w._show_coverflow()
            else:
                w._albums_stack.setCurrentIndex(0)
                w._show_album_grid()
                w._fade_content("library_hub")

        elif section == "artists":
            w._show_artists_view(mode)

        elif section == "playlists":
            if not w._playlist_refs:
                w._views.show("empty")
                return
            if mode == "list":
                w._model.populate(w._playlist_refs)
                pc = getattr(w, '_playback_ctrl', None)
                if pc:
                    pc.attach_track_table(w._generic_tracks_table, w._model)
                else:
                    w._generic_tracks_table.setModel(w._model)
                w._fade_content("library_hub")
            elif mode == "grid":
                w._generic_song_grid.set_items(w._playlist_refs, card_size=170)
                w._fade_content("library_hub")

        elif section == "folders":
            w._fade_content("library_hub")

        elif section == "genres":
            w._show_library_hub_page()
            if w._library_hub_page:
                w._library_hub_page.set_current_section("genres")

        elif section == "radio":
            w._fade_content("radio")

        elif section == "playlist_hub":
            w._playlist_hub.set_playlists(w._db.get_playlists())
            w._fade_content("playlist_hub")

        elif section in ("favs", "recent", "mix_unplayed"):
            refs = getattr(w, "_current_refs", [])
            if not refs:
                w._views.show("empty")
                return
            if mode == "list":
                w._model.populate(refs)
                pc = getattr(w, '_playback_ctrl', None)
                if pc:
                    pc.attach_track_table(w._generic_tracks_table, w._model)
                else:
                    w._generic_tracks_table.setModel(w._model)
                w._fade_content("library_hub")
            elif mode == "grid":
                w._generic_song_grid.set_items(refs, card_size=170)
                w._fade_content("library_hub")

    @staticmethod
    def _refresh_songs_list(w):
        """Refresh songs list view using premium page if available."""
        songs_ctrl = getattr(w, '_songs_ctrl', None)
        premium_page = getattr(w, '_songs_premium_page', None)
        if songs_ctrl and premium_page:
            songs_ctrl.apply_filter(text=getattr(w, '_search_text', ""))
            vs = songs_ctrl.view_state()
            premium_page.load_data(
                vs.items,
                fav_set=set(vs.favorite_track_ids),
                status_cache=dict(vs.status_cache),
            )
            return
        w._apply_filters()

    def _do_nothing(self):
        pass
