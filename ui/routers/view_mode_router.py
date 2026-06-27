"""ViewModeRouter — dispatches view mode changes to the correct section handler."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library.trackref_model import TrackRef

if TYPE_CHECKING:
    from ui.window import MainWindow


class ViewModeRouter:
    """Routes view mode changes (list/grid/coverflow) to section-specific handlers."""

    def __init__(self, window: MainWindow):
        self._win = window

    def on_mode_changed(self, mode: str):
        w = self._win
        w._restore_central_opacity()
        available = w._current_available_views()
        if mode not in available:
            return
        if mode == "coverflow" and w._current_section_key != "albums":
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
        section = w._current_section_key

        if section == "library":
            if mode == "list":
                w._songs_stack.setCurrentIndex(0)
                w._apply_filters()
                w._fade_content("library_hub")
            elif mode == "grid":
                w._songs_stack.setCurrentIndex(1)
                w._show_song_grid()
                w._fade_content("library_hub")

        elif section == "albums":
            if mode == "list":
                w._albums_stack.setCurrentIndex(1)
                self._show_album_list()
                w._fade_content("library_hub")
            elif mode == "grid":
                w._albums_stack.setCurrentIndex(0)
                w._show_album_grid()
                w._fade_content("library_hub")
            elif mode == "coverflow":
                w._show_coverflow()

        elif section == "artists":
            w._show_artists_view(mode)

        elif section == "playlists":
            if not w._playlist_refs:
                w._views.show("empty")
                return
            if mode == "list":
                w._model.populate(w._playlist_refs)
                w._generic_tracks_table.setModel(w._model)
                w._generic_tracks_table.setColumnHidden(7, True)
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
                w._generic_tracks_table.setModel(w._model)
                w._generic_tracks_table.setColumnHidden(7, True)
                w._fade_content("library_hub")
            elif mode == "grid":
                w._generic_song_grid.set_items(refs, card_size=170)
                w._fade_content("library_hub")

    def _show_album_list(self):
        w = self._win
        from library.album_art import group_by_album
        items = w._filtered_album_items()
        groups = group_by_album(items)
        refs = []
        for album, artist, tracks in groups:
            dur = sum(getattr(t, 'duration', 0) or 0 for t in tracks)
            year = tracks[0].year if tracks else ""
            refs.append(TrackRef(
                uri=album, title=album,
                artist=artist, album=album,
                duration=float(dur),
                genre=f"{len(tracks)} canciones",
                year=year,
                cover_path="",
            ))
        w._model.populate(refs)
        w._album_list_table.setModel(w._model)
        w._album_list_table.setColumnHidden(7, True)
        w._album_list_table.setColumnWidth(0, 72)
        w._album_list_table.setColumnWidth(1, 240)
        w._album_list_table.setColumnWidth(2, 170)
        w._album_list_table.setColumnWidth(3, 170)
        w._album_list_table.setColumnWidth(4, 55)
        w._album_list_table.setColumnWidth(5, 110)
        w._album_list_table.setColumnWidth(6, 75)
        w._count.setText(f"{len(groups)} álbumes")
