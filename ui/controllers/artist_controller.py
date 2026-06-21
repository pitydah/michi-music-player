"""Artist controller — artist grid and detail navigation logic."""
import os



class ArtistController:
    def __init__(self, window):
        self._win = window

    def show_artists_view(self, mode: str):
        self._win._ctx.artist_grid.set_view_mode(mode)
        self._win._ctx.fade_to("artist_grid")

    def open_artist_detail(self, artist_key: str):
        repo = self._win._ctx.artist_repo
        group = repo.get_group(artist_key)
        if not group:
            return
        repo.current_key = artist_key
        self._win._ctx.artist_detail.set_artist(group)

        self._win._ctx.section_title.setText(group.display_name)
        parts = [f"{group.album_count} álbumes", f"{group.track_count} canciones"]
        if group.total_duration:
            s = int(group.total_duration)
            parts.append(
                f"{s // 3600} h {(s % 3600) // 60} min" if s >= 3600
                else f"{s // 60} min")
        self._win._ctx.section_subtitle.setText(" · ".join(parts))
        self._win._ctx.view_switcher.set_available_modes([])
        self._win._ctx.fade_to("artist_detail")

    def show_artists_overview(self):
        self._win._ctx.artist_repo.clear_current()
        self._win._ctx.configure_header("artists")
        self.show_artists_view(self._win._ctx.view_mode)

    def artist_filepaths(self, artist_key: str) -> list[str]:
        return self._win._ctx.artist_repo.filepaths(artist_key)

    def play_artist(self, artist_key: str, shuffle: bool = False):
        fps = self.artist_filepaths(artist_key)
        if fps:
            if shuffle:
                import random
                random.shuffle(fps)
            self._win._play_filepaths(fps, play_now=True)

    def queue_artist(self, artist_key: str):
        fps = self.artist_filepaths(artist_key)
        if fps:
            self._win._ctx.playback.enqueue(fps, play_now=False)

    def create_playlist_from_artist(self, artist_key: str):
        repo = self._win._ctx.artist_repo
        group = repo.get_group(artist_key)
        if not group:
            return
        pid = self._win._ctx.db.create_playlist(group.display_name)
        for fp in [t.filepath for t in group.all_tracks if os.path.isfile(t.filepath)]:
            self._win._ctx.db.add_to_playlist(pid, fp)
        self._win._ctx.rebuild_sidebar()
        self._win._ctx.toast.show(f"Playlist creada: {group.display_name}", "success")

    def edit_artist_metadata(self, artist_key: str):
        fps = self.artist_filepaths(artist_key)
        if fps:
            self.open_metadata_for_files(fps)

    def open_metadata_for_files(self, filepaths: list[str]):
        self._win._ctx.metadata_editor.load_files(filepaths)
        self._win._ctx.configure_header("metadata_editor")
        self._win._ctx.fade_to("metadata_editor")
