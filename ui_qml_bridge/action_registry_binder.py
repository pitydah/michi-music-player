"""ActionRegistryBinder — injects real action handlers into ActionRegistry.

Registered in BridgeFactory after all bridges are created.
Every registered action receives a real handler; none returns NO_HANDLER.

Handler strategy (no execute() payload is passed, so handlers source their
target from the shared ``selection_context`` bridge when one is required):
  - Direct no-arg bridge call  → actions mapping to a parameterless method.
  - Selection-arg bridge call  → actions whose target (filepath, album_key,
    artist, folder, source path, track id) is read from the selection.
  - Navigation                 → actions with no suitable bridge method
    (open album/artist, edit metadata, audio lab, library doctor, sync, ...).

All handlers are bound unconditionally; bridge availability is checked at
call time so a missing bridge yields a graceful ``METHOD_UNAVAILABLE`` /
``NO_NAVIGATION`` / ``NO_SELECTION`` dict instead of NO_HANDLER.
"""
from __future__ import annotations

import logging
import sys

from PySide6.QtCore import QObject, Signal

from ui_qml_bridge.action_registry import ActionRegistry

logger = logging.getLogger("michi.action_binder")


class ActionRegistryBinder(QObject):
    dataChanged = Signal()

    def __init__(self, registry: ActionRegistry, bridges: dict[str, object], parent=None):
        super().__init__(parent)
        self._registry = registry
        self._bridges = bridges

    def bind_all(self):
        self._bind_navigation()
        self._bind_playback()
        self._bind_library()
        self._bind_playlist()
        self._bind_metadata()
        self._bind_system()
        self._bind_tracks()
        self._bind_albums()
        self._bind_artists()
        self._bind_folders()
        self._bind_sources()
        self._bind_radio()
        self._bind_diagnostics()

    def refresh(self):
        self.dataChanged.emit()

    # ── bridge accessors ────────────────────────────────────────────────
    def _nav(self):
        return self._bridges.get("navigation")

    def _playback(self):
        return self._bridges.get("nowplaying")

    def _library(self):
        return self._bridges.get("library")

    def _playlists(self):
        return self._bridges.get("playlists")

    def _queue(self):
        return self._bridges.get("queue")

    def _sources(self):
        return self._bridges.get("library_sources")

    def _audio_lab(self):
        return self._bridges.get("audio_lab")

    def _selection(self):
        return self._bridges.get("selection_context")

    # ── selection extractors ────────────────────────────────────────────
    def _sel_data(self) -> dict:
        sel = self._selection()
        if not sel:
            return {}
        try:
            data = sel.selectedData
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}

    def _sel_field(self, *keys: str):
        data = self._sel_data()
        for k in keys:
            v = data.get(k)
            if v not in (None, ""):
                return v
        return ""

    def _sel_track_id(self) -> int:
        v = self._sel_field("id", "track_id")
        try:
            return int(v) if v != "" else 0
        except (ValueError, TypeError):
            return 0

    def _sel_filepath(self) -> str:
        return self._sel_field("filepath", "path", "file_path", "file")

    def _sel_album_key(self) -> str:
        return self._sel_field("album_key", "albumKey")

    def _sel_artist(self) -> str:
        return self._sel_field("artist", "artist_name", "artistName")

    def _sel_folder(self) -> str:
        return self._sel_field("folder", "folder_path", "folderPath", "path")

    def _sel_source_path(self) -> str:
        return self._sel_field("path", "source_path", "sourcePath")

    # ── generic handler factories ───────────────────────────────────────
    def _navigate_handler(self, route: str):
        def handler():
            nav = self._nav()
            if not nav or not hasattr(nav, "navigate"):
                return {"ok": False, "error": "NO_NAVIGATION"}
            nav.navigate(route)
            return {"ok": True}
        return handler

    def _no_arg_handler(self, bridge_key: str, method: str):
        def handler():
            bridge = self._bridges.get(bridge_key)
            if not bridge or not hasattr(bridge, method):
                return {"ok": False, "error": "METHOD_UNAVAILABLE"}
            fn = getattr(bridge, method)
            if not callable(fn):
                return {"ok": False, "error": "METHOD_UNAVAILABLE"}
            try:
                result = fn()
                return result if isinstance(result, dict) else {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return handler

    def _sel_arg_handler(self, bridge_key: str, method: str, arg_fn, empty=None):
        def handler():
            bridge = self._bridges.get(bridge_key)
            if not bridge or not hasattr(bridge, method):
                return {"ok": False, "error": "METHOD_UNAVAILABLE"}
            arg = arg_fn()
            if empty is not None and empty(arg):
                return {"ok": False, "error": "NO_SELECTION"}
            try:
                result = getattr(bridge, method)(arg)
                return result if isinstance(result, dict) else {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return handler

    def _play_with_shuffle_handler(self, base_handler):
        def handler():
            result = base_handler()
            if isinstance(result, dict) and result.get("ok"):
                np = self._playback()
                if np and hasattr(np, "shuffleEnabled") and hasattr(np, "toggleShuffle"):
                    try:
                        if not np.shuffleEnabled:
                            np.toggleShuffle()
                    except Exception:
                        pass
            return result if isinstance(result, dict) else {"ok": True}
        return handler

    # ── navigation actions ──────────────────────────────────────────────
    def _bind_navigation(self):
        routes = {
            "navigate_home": "home",
            "navigate_library": "library",
            "navigate_playlists": "playlists",
            "navigate_radio": "radio",
            "navigate_lyrics": "lyrics",
            "navigate_settings": "settings",
            "navigate_eq": "equalizer",
            "navigate_library_sources": "library.sources",
            "navigate_jobs": "jobs",
            "navigate_queue": "queue",
            "navigate_history": "history",
            "navigate_home_audio": "home_audio",
            "navigate_diagnostics": "diagnostics",
            "navigate_library_doctor": "library_doctor",
            "navigate_mix": "mix",
        }
        for action_id, route in routes.items():
            action = self._registry.get(action_id)
            if action:
                action.handler = self._navigate_handler(route)

    # ── playback actions ────────────────────────────────────────────────
    def _volume_step_handler(self, delta: int):
        def handler():
            np = self._playback()
            if not np or not hasattr(np, "setVolume"):
                return {"ok": False, "error": "METHOD_UNAVAILABLE"}
            try:
                cur = getattr(np, "volume", 50)
                if callable(cur):
                    cur = cur()
                target = max(0, min(100, int(cur) + delta))
                result = np.setVolume(target)
                return result if isinstance(result, dict) else {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return handler

    def _seek_relative_handler(self, seconds: int):
        def handler():
            np = self._playback()
            if not np or not hasattr(np, "seekRelative"):
                return {"ok": False, "error": "METHOD_UNAVAILABLE"}
            try:
                result = np.seekRelative(seconds)
                return result if isinstance(result, dict) else {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return handler

    def _bind_playback(self):
        reg = self._registry
        simple = {
            "playback_playpause": "togglePlay",
            "playback_next": "next",
            "playback_prev": "previous",
            "playback_mute": "toggleMute",
        }
        for action_id, method in simple.items():
            action = reg.get(action_id)
            if action:
                action.handler = self._no_arg_handler("nowplaying", method)
        action = reg.get("playback_volume_up")
        if action:
            action.handler = self._volume_step_handler(10)
        action = reg.get("playback_volume_down")
        if action:
            action.handler = self._volume_step_handler(-10)
        action = reg.get("playback_seek_forward")
        if action:
            action.handler = self._seek_relative_handler(10)
        action = reg.get("playback_seek_back")
        if action:
            action.handler = self._seek_relative_handler(-10)

    # ── library actions ─────────────────────────────────────────────────
    def _bind_library(self):
        reg = self._registry
        action = reg.get("library_refresh")
        if action:
            action.handler = self._no_arg_handler("library", "refresh")
        action = reg.get("library_add_folder")
        if action:
            action.handler = self._no_arg_handler("library", "scanMusicFolder")
        action = reg.get("library_scan")
        if action:
            action.handler = self._no_arg_handler("library_sources", "scanAllSources")

    # ── playlist actions ────────────────────────────────────────────────
    def _bind_playlist(self):
        action = self._registry.get("playlist_create")
        if action:
            def handler():
                pl = self._playlists()
                if not pl or not hasattr(pl, "createPlaylist"):
                    return {"ok": False, "error": "METHOD_UNAVAILABLE"}
                try:
                    result = pl.createPlaylist("Nueva lista")
                    return result if isinstance(result, dict) else {"ok": True}
                except Exception as e:
                    return {"ok": False, "error": str(e)}
            action.handler = handler

    # ── metadata actions ────────────────────────────────────────────────
    def _bind_metadata(self):
        action = self._registry.get("metadata_edit")
        if action:
            action.handler = self._navigate_handler("metadata.single")
        action = self._registry.get("metadata_smart_tagging")
        if action:
            action.handler = self._navigate_handler("tagging")

    # ── system actions ──────────────────────────────────────────────────
    def _bind_system(self):
        action = self._registry.get("app_quit")
        if action:
            action.handler = lambda: sys.exit(0) or {"ok": True}

    # ── track actions ───────────────────────────────────────────────────
    def _track_play_handler(self):
        def handler():
            lib = self._library()
            fp = self._sel_filepath()
            if fp and lib and hasattr(lib, "play_song"):
                try:
                    result = lib.play_song(fp)
                    return result if isinstance(result, dict) else {"ok": True}
                except Exception as e:
                    return {"ok": False, "error": str(e)}
            tid = self._sel_track_id()
            if tid and lib and hasattr(lib, "playTrackById"):
                try:
                    result = lib.playTrackById(tid)
                    return result if isinstance(result, dict) else {"ok": True}
                except Exception as e:
                    return {"ok": False, "error": str(e)}
            return {"ok": False, "error": "NO_SELECTION"}
        return handler

    def _track_enqueue_handler(self):
        def handler():
            np = self._playback()
            fp = self._sel_filepath()
            if fp and np and hasattr(np, "enqueueSong"):
                try:
                    result = np.enqueueSong(fp)
                    return result if isinstance(result, dict) else {"ok": True}
                except Exception as e:
                    return {"ok": False, "error": str(e)}
            lib = self._library()
            tid = self._sel_track_id()
            if tid and lib and hasattr(lib, "enqueueTrackById"):
                try:
                    result = lib.enqueueTrackById(tid)
                    return result if isinstance(result, dict) else {"ok": True}
                except Exception as e:
                    return {"ok": False, "error": str(e)}
            return {"ok": False, "error": "NO_SELECTION"}
        return handler

    def _track_favorite_handler(self):
        def handler():
            lib = self._library()
            tid = self._sel_track_id()
            if tid and lib and hasattr(lib, "toggleFavoriteById"):
                try:
                    result = lib.toggleFavoriteById(tid)
                    return result if isinstance(result, dict) else {"ok": True}
                except Exception as e:
                    return {"ok": False, "error": str(e)}
            fp = self._sel_filepath()
            if fp and lib and hasattr(lib, "toggleFavorite"):
                try:
                    result = lib.toggleFavorite(fp)
                    return result if isinstance(result, dict) else {"ok": True}
                except Exception as e:
                    return {"ok": False, "error": str(e)}
            return {"ok": False, "error": "NO_SELECTION"}
        return handler

    def _open_album_handler(self):
        def handler():
            nav = self._nav()
            if not nav or not hasattr(nav, "navigate"):
                return {"ok": False, "error": "NO_NAVIGATION"}
            album_key = self._sel_album_key()
            if album_key and hasattr(nav, "navigateWithParams"):
                nav.navigateWithParams("library.album_detail", {"album_key": album_key})
            else:
                nav.navigate("library.albums")
            return {"ok": True}
        return handler

    def _open_artist_handler(self):
        def handler():
            nav = self._nav()
            if not nav or not hasattr(nav, "navigate"):
                return {"ok": False, "error": "NO_NAVIGATION"}
            artist = self._sel_artist()
            if artist and hasattr(nav, "navigateWithParams"):
                nav.navigateWithParams("library.artist_detail", {"artist": artist})
            else:
                nav.navigate("library.artists")
            return {"ok": True}
        return handler

    def _reveal_track_handler(self):
        def handler():
            fp = self._sel_filepath()
            lib = self._library()
            if fp and lib and hasattr(lib, "revealInFileManager"):
                try:
                    result = lib.revealInFileManager(fp)
                    return result if isinstance(result, dict) else {"ok": True}
                except Exception as e:
                    return {"ok": False, "error": str(e)}
            return self._navigate_handler("library.folders")()
        return handler

    def _track_detail_handler(self):
        def handler():
            nav = self._nav()
            if not nav or not hasattr(nav, "navigate"):
                return {"ok": False, "error": "NO_NAVIGATION"}
            tid = self._sel_track_id()
            if tid and hasattr(nav, "navigateWithParams"):
                nav.navigateWithParams("library.track_detail", {"track_id": tid})
            else:
                nav.navigate("library.songs")
            return {"ok": True}
        return handler

    def _audio_lab_file_handler(self, method: str, fallback_route: str):
        def handler():
            fp = self._sel_filepath()
            lab = self._audio_lab()
            if fp and lab and hasattr(lab, method):
                try:
                    result = getattr(lab, method)(fp)
                    return result if isinstance(result, dict) else {"ok": True}
                except Exception as e:
                    return {"ok": False, "error": str(e)}
            return self._navigate_handler(fallback_route)()
        return handler

    def _bind_tracks(self):
        reg = self._registry
        for aid in ("track_play_now", "track_replace_queue"):
            action = reg.get(aid)
            if action:
                action.handler = self._track_play_handler()
        action = reg.get("track_play_next")
        if action:
            action.handler = self._sel_arg_handler(
                "library", "playNextTrackById", self._sel_track_id,
                empty=lambda v: v == 0)
        action = reg.get("track_add_to_queue")
        if action:
            action.handler = self._track_enqueue_handler()
        for aid in ("track_favorite", "track_unfavorite"):
            action = reg.get(aid)
            if action:
                action.handler = self._track_favorite_handler()
        action = reg.get("track_radio")
        if action:
            action.handler = self._navigate_handler("streaming.radio")
        action = reg.get("track_add_to_playlist")
        if action:
            action.handler = self._navigate_handler("playlists")
        action = reg.get("track_open_album")
        if action:
            action.handler = self._open_album_handler()
        action = reg.get("track_open_artist")
        if action:
            action.handler = self._open_artist_handler()
        action = reg.get("track_open_folder")
        if action:
            action.handler = self._reveal_track_handler()
        action = reg.get("track_show_properties")
        if action:
            action.handler = self._track_detail_handler()
        action = reg.get("track_edit_metadata")
        if action:
            action.handler = self._navigate_handler("metadata.single")
        for aid, method, route in (
            ("track_analyze_audio_lab", "startAnalysis", "audio_lab.analysis"),
            ("track_convert", "startConversion", "audio_lab.conversion"),
            ("track_calculate_replaygain", "previewReplayGain", "audio_lab.replaygain"),
        ):
            action = reg.get(aid)
            if action:
                action.handler = self._audio_lab_file_handler(method, route)
        for aid in ("track_check_integrity", "track_find_duplicates", "track_relocate",
                    "track_delete_from_disk", "track_delete_from_library", "track_exclude"):
            action = reg.get(aid)
            if action:
                action.handler = self._navigate_handler("library_doctor")
        action = reg.get("track_send_to_device")
        if action:
            action.handler = self._navigate_handler("sync")

    # ── album actions ───────────────────────────────────────────────────
    def _bind_albums(self):
        reg = self._registry
        play = self._sel_arg_handler("library", "playAlbum", self._sel_album_key,
                                     empty=lambda v: not v)
        action = reg.get("album_play")
        if action:
            action.handler = play
        action = reg.get("album_shuffle")
        if action:
            action.handler = self._play_with_shuffle_handler(play)
        enqueue = self._sel_arg_handler("library", "enqueueAlbum", self._sel_album_key,
                                        empty=lambda v: not v)
        for aid in ("album_queue", "album_play_next"):
            action = reg.get(aid)
            if action:
                action.handler = enqueue
        action = reg.get("album_add_to_playlist")
        if action:
            action.handler = self._navigate_handler("playlists")
        action = reg.get("album_favorite")
        if action:
            action.handler = self._navigate_handler("library.favorites")
        for aid in ("album_edit_metadata", "album_change_artwork"):
            action = reg.get(aid)
            if action:
                action.handler = self._navigate_handler("metadata.batch")
        action = reg.get("album_open_folder")
        if action:
            action.handler = self._navigate_handler("library.folders")
        action = reg.get("album_analyze")
        if action:
            action.handler = self._navigate_handler("audio_lab.analysis")
        action = reg.get("album_convert")
        if action:
            action.handler = self._navigate_handler("audio_lab.conversion")
        action = reg.get("album_sync")
        if action:
            action.handler = self._navigate_handler("sync")

    # ── artist actions ──────────────────────────────────────────────────
    def _artist_queue_handler(self):
        def handler():
            artist = self._sel_artist()
            if not artist:
                return {"ok": False, "error": "NO_SELECTION"}
            lib = self._library()
            queue = self._queue()
            if not lib or not hasattr(lib, "getArtistTracks"):
                return {"ok": False, "error": "METHOD_UNAVAILABLE"}
            if not queue or not hasattr(queue, "add"):
                return {"ok": False, "error": "METHOD_UNAVAILABLE"}
            try:
                tracks = lib.getArtistTracks(artist)
                if not tracks:
                    return {"ok": False, "error": "NO_TRACKS"}
                result = queue.add(tracks)
                return result if isinstance(result, dict) else {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return handler

    def _bind_artists(self):
        reg = self._registry
        play = self._sel_arg_handler("library", "playArtist", self._sel_artist,
                                     empty=lambda v: not v)
        action = reg.get("artist_play")
        if action:
            action.handler = play
        action = reg.get("artist_shuffle")
        if action:
            action.handler = self._play_with_shuffle_handler(play)
        action = reg.get("artist_queue")
        if action:
            action.handler = self._artist_queue_handler()
        action = reg.get("artist_add_to_playlist")
        if action:
            action.handler = self._navigate_handler("playlists")
        action = reg.get("artist_radio")
        if action:
            action.handler = self._navigate_handler("streaming.radio")

    # ── folder actions ──────────────────────────────────────────────────
    def _folder_queue_handler(self):
        def handler():
            folder = self._sel_folder()
            if not folder:
                return {"ok": False, "error": "NO_SELECTION"}
            lib = self._library()
            queue = self._queue()
            if not lib or not hasattr(lib, "getFolderTracks"):
                return {"ok": False, "error": "METHOD_UNAVAILABLE"}
            if not queue or not hasattr(queue, "add"):
                return {"ok": False, "error": "METHOD_UNAVAILABLE"}
            try:
                tracks = lib.getFolderTracks(folder)
                if not tracks:
                    return {"ok": False, "error": "NO_TRACKS"}
                result = queue.add(tracks)
                return result if isinstance(result, dict) else {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return handler

    def _folder_open_filesystem_handler(self):
        def handler():
            folder = self._sel_folder()
            lib = self._library()
            if folder and lib and hasattr(lib, "openFolder"):
                try:
                    result = lib.openFolder(folder)
                    return result if isinstance(result, dict) else {"ok": True}
                except Exception as e:
                    return {"ok": False, "error": str(e)}
            return self._navigate_handler("library.folders")()
        return handler

    def _bind_folders(self):
        reg = self._registry
        action = reg.get("folder_play")
        if action:
            action.handler = self._sel_arg_handler("library", "playFolder", self._sel_folder,
                                                    empty=lambda v: not v)
        action = reg.get("folder_queue")
        if action:
            action.handler = self._folder_queue_handler()
        action = reg.get("folder_open_filesystem")
        if action:
            action.handler = self._folder_open_filesystem_handler()
        action = reg.get("folder_exclude")
        if action:
            action.handler = self._sel_arg_handler("library_sources", "setExclusion",
                                                    self._sel_folder, empty=lambda v: not v)
        action = reg.get("folder_rescan")
        if action:
            action.handler = self._sel_arg_handler("library_sources", "scanFolder",
                                                    self._sel_folder, empty=lambda v: not v)

    # ── source actions ──────────────────────────────────────────────────
    def _source_sel_or_nav_handler(self, method: str):
        def handler():
            path = self._sel_source_path()
            bridge = self._sources()
            if path and bridge and hasattr(bridge, method):
                try:
                    result = getattr(bridge, method)(path)
                    return result if isinstance(result, dict) else {"ok": True}
                except Exception as e:
                    return {"ok": False, "error": str(e)}
            return self._navigate_handler("library.sources")()
        return handler

    def _source_enable_handler(self, enabled: bool):
        def handler():
            path = self._sel_source_path()
            bridge = self._sources()
            if path and bridge and hasattr(bridge, "setSourceEnabled"):
                try:
                    result = bridge.setSourceEnabled(path, enabled)
                    return result if isinstance(result, dict) else {"ok": True}
                except Exception as e:
                    return {"ok": False, "error": str(e)}
            return self._navigate_handler("library.sources")()
        return handler

    def _bind_sources(self):
        reg = self._registry
        action = reg.get("source_scan")
        if action:
            action.handler = self._no_arg_handler("library_sources", "scanAllSources")
        action = reg.get("source_cancel_scan")
        if action:
            action.handler = self._navigate_handler("jobs")
        for aid in ("source_add", "source_edit"):
            action = reg.get(aid)
            if action:
                action.handler = self._navigate_handler("library.sources")
        action = reg.get("source_remove")
        if action:
            action.handler = self._source_sel_or_nav_handler("removeSource")
        action = reg.get("source_enable")
        if action:
            action.handler = self._source_enable_handler(True)
        action = reg.get("source_disable")
        if action:
            action.handler = self._source_enable_handler(False)

    # ── radio + diagnostics actions ─────────────────────────────────────
    def _bind_radio(self):
        action = self._registry.get("radio_add_station")
        if action:
            action.handler = self._navigate_handler("streaming.radio")

    def _bind_diagnostics(self):
        action = self._registry.get("diagnostics_show")
        if action:
            action.handler = self._navigate_handler("diagnostics")
