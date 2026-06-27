"""CoverFlow controller — 3D album browser actions: play, queue, snap, enrich, banner."""
import hashlib
import os

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox, QVBoxLayout, QWidget

from library.album_art import load_cover_pixmap, load_covers_for_albums
from library.coverflow import CoverFlowWidget


def _album_key(item, tracks: list = None) -> str:
    """Stable SHA1 album key from albumartist/artist + album title."""
    artist_val = ""
    album = item.title or ""
    if tracks:
        artist_val = getattr(tracks[0], 'albumartist', '') or getattr(
            tracks[0], 'artist', '') or ""
    if not artist_val and item.subtitle:
        artist_val = item.subtitle.split(" \u00b7 ")[0]
    raw = f"{artist_val}|{album}".lower().strip()
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


class CoverFlowController:
    def __init__(self, window):
        self._win = window
        self._snapped_index = 0

    # ── Show / view mode ──

    def show_view(self):
        self._win._view_switcher.set_view("coverflow", emit=False)
        self._win._on_view_mode_changed("coverflow")

    def show(self):
        items = self._win._filtered_album_items()

        # Cache key — stable signature to skip rebuild when nothing changed
        sig_parts = [str(len(items)), self._win._album_sort_key,
                     self._win._album_filter_mode, self._win._search_text]
        for i in items[:100]:  # only hash first 100 for performance
            sig_parts.append(getattr(i, 'filepath', '') or '')
            sig_parts.append(getattr(i, 'album', '') or '')
            sig_parts.append(getattr(i, 'artist', '') or '')
            sig_parts.append(str(getattr(i, 'mtime', 0) or 0))
        import hashlib
        cache_key = hashlib.sha1("|".join(sig_parts).encode()).hexdigest()

        if self._win._coverflow is not None and cache_key == self._win._coverflow_cache_key:
            self._snapped_index = self._win._coverflow.current_index()
            self._win._albums_stack.setCurrentIndex(2)
            self._win._fade_content("library_hub")
            self._win._count.setText(f"{self._win._coverflow.count()} álbumes")
            self._win._coverflow.setFocus()
            return
        self._win._coverflow_cache_key = cache_key

        covers = load_covers_for_albums(items, 260, lazy=True)

        if not covers:
            self._win._views.show("empty")
            self._win._count.setText("0 álbumes")
            return

        if self._win._coverflow is None:
            self._win._coverflow = CoverFlowWidget()
            self._win._coverflow.double_clicked.connect(self.on_dbl)
            self._win._coverflow.cover_snapped.connect(self.on_snap)
            self._win._coverflow.request_cover.connect(self.on_cover_request)
            self._win._coverflow.play_album_requested.connect(self.on_play_album)
            self._win._coverflow.queue_album_requested.connect(self.on_queue_album)
            self._win._coverflow.playlist_album_requested.connect(self.on_playlist_album)
            self._win._coverflow.metadata_album_requested.connect(self.on_metadata_album)
            self._win._coverflow.details_album_requested.connect(self.on_details_album)
            self._win._coverflow.cover_search_requested.connect(self.on_search_cover)
            self._win._coverflow.open_folder_requested.connect(self.on_open_folder)

            # AlbumInfoBanner below CoverFlow
            from ui.album_info_banner import AlbumInfoBanner
            self._win._album_banner = AlbumInfoBanner()
            self._win._album_banner.play_requested.connect(self.on_banner_play)
            self._win._album_banner.queue_requested.connect(self.on_banner_queue)
            self._win._album_banner.details_requested.connect(self.on_banner_details)

            coverflow_page = QWidget()
            coverflow_page.setStyleSheet("background: #090B11;")
            cv_layout = QVBoxLayout(coverflow_page)
            cv_layout.setContentsMargins(0, 0, 0, 0)
            cv_layout.setSpacing(8)
            cv_layout.addWidget(self._win._coverflow, stretch=1)
            cv_layout.addWidget(self._win._album_banner, stretch=0)
            self._win._albums_stack.addWidget(coverflow_page)

        # Preserve current album selection across rebuilds
        prev_key = self._win._coverflow.current_key() if self._win._coverflow else ""
        self._win._coverflow.set_items(covers)
        if prev_key:
            idx = self._win._coverflow.index_for_key(prev_key)
            if idx >= 0:
                self._win._coverflow.set_current_index(idx, animated=False)
        self._win._albums_stack.setCurrentIndex(2)
        self._win._fade_content("library_hub")
        self._win._count.setText(f"{len(covers)} álbumes")
        self._win._coverflow.setFocus()

    # ── CoverFlow item access ──

    def album_tracks(self, idx: int) -> list:
        item = self._win._coverflow.item_at(idx) if self._win._coverflow else None
        if not item or not item.data:
            return []
        return item.data.get("tracks", [])

    def _build_minimal_summary(self, item, tracks, key):
        """Build a minimal AlbumSummary from CoverFlow item data (fallback)."""
        from metadata.album_info_repository import AlbumSummary
        artist = ""
        if item.subtitle:
            parts = item.subtitle.split("·")
            if parts:
                artist = parts[0].strip()
        duration = sum(getattr(t, 'duration', 0) or 0 for t in tracks)
        year = ""
        for t in tracks:
            y = getattr(t, 'year', 0) or 0
            if y:
                year = str(y)
                break
        return AlbumSummary(
            album_key=key,
            title=item.title or "",
            artist=artist,
            year=year,
            genre="",
            duration=duration,
            track_count=len(tracks),
            description="",
            source="local",
            cover_path="",
            track_list=[getattr(t, 'filepath', '') or '' for t in tracks],
        )

    # ── CoverFlow signal handlers ──

    def on_dbl(self, index: int):
        cf = self._win._coverflow
        if not cf or index >= cf.count():
            return
        item = cf.item_at(index)
        data = item.data if item and item.data else {}
        tracks = data.get("tracks", [])
        if not tracks:
            return

        from library.trackref_model import TrackRef
        refs = [TrackRef(uri=t.filepath,
                         title=t.title or os.path.basename(t.filepath),
                         artist=t.artist, album=t.album,
                         duration=t.duration, year=t.year, genre=t.genre)
                for t in tracks]

        self._win._model.populate(refs)
        self._win._current_refs = refs
        self._win._count.setText(f"{len(refs)} canciones")

        album_name = item.title or "Álbum"
        artist_name = ""
        if item.subtitle:
            parts = item.subtitle.split("·")
            if parts:
                artist_name = parts[0].strip()
        self._win._section_title.setText(album_name)
        self._win._section_subtitle.setText(artist_name)

        self._win._table.setModel(self._win._model)
        self._win._table.setColumnHidden(7, True)
        self._win._table.setColumnWidth(0, 72)
        self._win._table.setColumnWidth(1, 260)
        self._win._table.setColumnWidth(2, 170)
        self._win._table.setColumnWidth(3, 170)
        self._win._table.setColumnWidth(4, 55)
        self._win._table.setColumnWidth(5, 110)
        self._win._table.setColumnWidth(6, 75)

        self._win._fade_content("library_hub")
        self._win._search.show()

    def on_snap(self, index: int):
        self._snapped_index = index
        cf = self._win._coverflow
        if not cf or index >= cf.count():
            return

        # Update album info banner using repository
        if hasattr(self._win, '_album_banner') and hasattr(self._win, '_album_repo'):
            item = cf.item_at(index)
            tracks = item.data.get("tracks", []) if item and item.data else []
            key = _album_key(item, tracks)
            summary = self._win._album_repo.get_summary(key, fallback_data=tracks)
            if summary:
                self._win._album_banner.set_album_summary(summary)
            elif item:
                # Fallback: build minimal summary from CoverFlow item data
                self._win._album_banner.set_album_summary(
                    self._build_minimal_summary(item, tracks, key))

            # Trigger MusicBrainz album enrichment for external metadata
            self.enrich_album_background(key, item, tracks)

            # Trigger artist enrichment for CoverFlow-navigated artist
            if hasattr(self._win, '_artist_enrich') and item and item.subtitle:
                from library.artist_grouping import normalize_artist_name
                artist_key = normalize_artist_name(item.subtitle)
                self._win._artist_enrich.enrich_artist_by_key(artist_key, item.subtitle)

            # Precarga vecinos ±2
            for off in (-2, -1, 1, 2):
                ni = index + off
                n_item = cf.item_at(ni)
                if n_item and n_item.data:
                    n_tracks = n_item.data.get("tracks", [])
                    n_key = _album_key(n_item, n_tracks)
                    if not self._win._album_repo.has(n_key):
                        self._win._album_repo.get_summary(n_key, fallback_data=n_tracks)

    def on_play_album(self, idx: int):
        tracks = self.album_tracks(idx)
        fps = [t.filepath for t in tracks if os.path.isfile(t.filepath)]
        if fps:
            self._win._play_filepaths(fps, play_now=True)

    def on_queue_album(self, idx: int):
        tracks = self.album_tracks(idx)
        fps = [t.filepath for t in tracks if os.path.isfile(t.filepath)]
        if fps:
            self._win._playback.enqueue(fps, play_now=False)

    def on_playlist_album(self, idx: int):
        tracks = self.album_tracks(idx)
        if not tracks:
            return
        album_name = tracks[0].album or "Álbum"
        pid = self._win._db.create_playlist(album_name)
        for t in tracks:
            if os.path.isfile(t.filepath):
                self._win._db.add_to_playlist(pid, t.filepath)
        self._win._rebuild_sidebar()
        self._win._toast_svc.show(f"Playlist creada: {album_name}", "success")

    def on_metadata_album(self, idx: int):
        tracks = self.album_tracks(idx)
        fps = [t.filepath for t in tracks if os.path.isfile(t.filepath)]
        if fps:
            self._win._open_metadata_for_files(fps)

    def on_details_album(self, idx: int):
        item = self._win._coverflow.item_at(idx) if self._win._coverflow else None
        if not item:
            return
        tracks = item.data.get("tracks", [])
        count = len(tracks)
        dur = sum(getattr(t, 'duration', 0) or 0 for t in tracks)
        dur_str = f"{int(dur // 60)}:{int(dur % 60):02d}" if dur > 0 else "—"
        exts = set((getattr(t, 'ext', '') or '').upper().lstrip(".") for t in tracks if getattr(t, 'ext', ''))
        fmt_str = ", ".join(sorted(exts)) or "—"
        msg = (f"Álbum: {item.title}\nArtista: {item.subtitle or '—'}\n"
               f"Canciones: {count}\nDuración: {dur_str}\nFormatos: {fmt_str}")
        QMessageBox.information(self._win, "Detalles del álbum", msg)

    def on_search_cover(self, idx: int):
        tracks = self.album_tracks(idx)
        if tracks:
            d = os.path.dirname(tracks[0].filepath) if tracks else ""
            self._win._toast_svc.show(f"Buscar carátula en: {d}", "info")

    def on_open_folder(self, idx: int):
        tracks = self.album_tracks(idx)
        if tracks:
            d = os.path.dirname(tracks[0].filepath)
            QDesktopServices.openUrl(QUrl.fromLocalFile(d))

    # ── Banner signal handlers ──

    def on_banner_play(self, album_key: str = ""):
        self.on_play_album(self._snapped_index)

    def on_banner_queue(self, album_key: str = ""):
        self.on_queue_album(self._snapped_index)

    def on_banner_details(self, album_key: str = ""):
        self.on_details_album(self._snapped_index)

    # ── Cover lazy-load ──

    def on_cover_request(self, idx: int, item):
        """Lazy-load cover art via WorkerManager (non-blocking)."""
        tracks = item.data.get("tracks", []) if item.data else []
        if not tracks:
            return
        # Deduplicate — skip if already pending for this album key
        if not hasattr(self, '_pending_cover_keys'):
            self._pending_cover_keys = set()
        key = self._win._coverflow.item_key_at(idx)
        if key in self._pending_cover_keys:
            return
        self._pending_cover_keys.add(key)

        filepath = tracks[0].filepath
        size = self._win._coverflow.cover_size()
        cache_key = self._win._coverflow_cache_key

        if self._win._workers:
            self._win._workers.run_task(
                f"cf_cover_{idx}",
                lambda fp=filepath, sz=size: load_cover_pixmap(fp, sz),
                on_done=lambda pix: self._on_cover_loaded(
                    idx, pix, key, cache_key))
        else:
            pix = load_cover_pixmap(filepath, size)
            if pix and not pix.isNull():
                self._win._coverflow.set_cover(idx, pix)

    def _on_cover_loaded(self, idx: int, pix, key: str, cache_key: str):
        if hasattr(self, '_pending_cover_keys'):
            self._pending_cover_keys.discard(key)
        if self._win._coverflow_cache_key != cache_key:
            return
        if not pix or pix.isNull():
            return
        current_key = self._win._coverflow.item_key_at(idx)
        if current_key != key:
            new_idx = self._win._coverflow.index_for_key(key)
            if new_idx >= 0:
                self._win._coverflow.set_cover(new_idx, pix)
            return
        self._win._coverflow.set_cover(idx, pix)

    # ── Album enrichment ──

    def enrich_album_background(self, key: str, item, tracks):
        """Trigger MusicBrainz album enrichment for CoverFlow-navigated albums."""
        if not key or not tracks:
            return
        try:
            from integrations.artist_metadata.album_enrichment_service import AlbumEnrichmentService
            from library.album_key import make_artist_key
            if not hasattr(self._win, '_album_enrich'):
                self._win._album_enrich = AlbumEnrichmentService()
                self._win._album_enrich.album_enriched.connect(self.on_album_enriched)
            album_name = getattr(tracks[0], 'album', '') if tracks else ''
            artist_name = item.subtitle if item and item.subtitle else (
                getattr(tracks[0], 'albumartist', '') or getattr(tracks[0], 'artist', ''))
            if album_name and artist_name:
                artist_key = make_artist_key(artist_name)
                self._win._album_enrich.enrich_album(key, album_name, artist_key, artist_name)
        except Exception:
            pass

    def on_album_enriched(self, album_key: str, data: dict):
        """Handle MusicBrainz album enrichment result — update banner if visible."""
        if not hasattr(self._win, '_album_repo') or not data:
            return
        self._win._album_repo.update_enrichment(album_key, data)
        if hasattr(self._win, '_album_banner') and self._win._album_banner:
            summary = self._win._album_repo.get_cached(album_key)
            if summary:
                self._win._album_banner.set_album_summary(summary)
