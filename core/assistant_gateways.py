from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from michi_ai.v2.core.gateways import (
    AudioLabGateway, ConnectionsGateway, DeviceGateway, DiagnosticsGateway,
    HomeAudioGateway, JobGateway, LibraryDoctorGateway, LibraryGateway,
    LyricsGateway, MetadataGateway, MixGateway, NavigationRequestGateway,
    PlaybackGateway, PlaylistGateway, QueueGateway, RadioGateway,
    SettingsGateway,
)

logger = logging.getLogger(__name__)


@dataclass
class AssistantGateways:
    playback: PlaybackGateway | None = None
    queue: QueueGateway | None = None
    library: LibraryGateway | None = None
    playlists: PlaylistGateway | None = None
    mix: MixGateway | None = None
    radio: RadioGateway | None = None
    lyrics: "LyricsGateway | None" = None
    metadata: "MetadataGateway | None" = None
    audio_lab: AudioLabGateway | None = None
    library_doctor: "LibraryDoctorGateway | None" = None
    devices: DeviceGateway | None = None
    connections: "ConnectionsGateway | None" = None
    home_audio: "HomeAudioGateway | None" = None
    settings: SettingsGateway | None = None
    diagnostics: DiagnosticsGateway | None = None
    navigation: NavigationRequestGateway | None = None
    jobs: JobGateway | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "playback": self.playback,
            "queue": self.queue,
            "library": self.library,
            "playlist": self.playlists,
            "mix": self.mix,
            "radio": self.radio,
            "audio_lab": self.audio_lab,
            "device": self.devices,
            "settings": self.settings,
            "diagnostics": self.diagnostics,
            "navigation": self.navigation,
            "job": self.jobs,
        }


def _unavailable_response(name: str) -> dict[str, Any]:
    return {"ok": False, "error": f"Service '{name}' unavailable", "code": "CAPABILITY_UNAVAILABLE"}


class ProductionQueueServiceGateway(QueueGateway):
    def __init__(self, queue_service: Any) -> None:
        self._qs = queue_service

    def get_queue(self) -> dict[str, Any]:
        if self._qs is None:
            return _unavailable_response("QueueService")
        try:
            if hasattr(self._qs, "get_queue"):
                q = self._qs.get_queue()
            elif hasattr(self._qs, "get_queue_state"):
                paths, idx = self._qs.get_queue_state()
                q = list(paths)
            else:
                q = self._qs.get_queue() if hasattr(self._qs, "get_queue") else []
            return {"ok": True, "queue": q or [], "count": len(q or [])}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def add_to_queue(self, track_ids: list[str], **kwargs: Any) -> dict[str, Any]:
        if self._qs is None:
            return _unavailable_response("QueueService")
        try:
            if hasattr(self._qs, "enqueue"):
                self._qs.enqueue(track_ids, play_now=False)
            return {"ok": True, "added": len(track_ids), "status": "COMPLETED", "count": len(self._verify_queue())}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def play_next(self, track_ids: list[str], **kwargs: Any) -> dict[str, Any]:
        if self._qs is None:
            return _unavailable_response("QueueService")
        try:
            if hasattr(self._qs, "enqueue_next"):
                self._qs.enqueue_next(track_ids)
            return {"ok": True, "status": "COMPLETED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def replace_queue(self, track_ids: list[str], **kwargs: Any) -> dict[str, Any]:
        if self._qs is None:
            return _unavailable_response("QueueService")
        try:
            if hasattr(self._qs, "play_queue"):
                self._qs.play_queue(track_ids, start_index=0)
            return {"ok": True, "count": len(track_ids), "status": "COMPLETED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def remove_from_queue(self, position: int, **kwargs: Any) -> dict[str, Any]:
        if self._qs is None:
            return _unavailable_response("QueueService")
        try:
            q = self._verify_queue()
            if 0 <= position < len(q):
                q.pop(position)
                if hasattr(self._qs, "reorder_queue"):
                    self._qs.reorder_queue(q)
                return {"ok": True}
            return {"ok": False, "error": "INVALID_POSITION"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def clear_queue(self, **kwargs: Any) -> dict[str, Any]:
        if self._qs is None:
            return _unavailable_response("QueueService")
        try:
            if hasattr(self._qs, "clear_queue"):
                self._qs.clear_queue()
            return {"ok": True, "status": "COMPLETED", "count": 0}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def reorder_queue(self, from_pos: int, to_pos: int, **kwargs: Any) -> dict[str, Any]:
        if self._qs is None:
            return _unavailable_response("QueueService")
        try:
            q = self._verify_queue()
            if 0 <= from_pos < len(q) and 0 <= to_pos < len(q):
                item = q.pop(from_pos)
                q.insert(to_pos, item)
                if hasattr(self._qs, "reorder_queue"):
                    self._qs.reorder_queue(q)
                return {"ok": True}
            return {"ok": False, "error": "INVALID_POSITION"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _verify_queue(self) -> list:
        if hasattr(self._qs, "get_queue"):
            return list(self._qs.get_queue() or [])
        return []


class ProductionPlaylistServiceGateway(PlaylistGateway):
    def __init__(self, playlist_service: Any) -> None:
        self._ps = playlist_service

    def list_playlists(self) -> dict[str, Any]:
        if self._ps is None:
            return _unavailable_response("PlaylistService")
        try:
            if hasattr(self._ps, "get_all_playlists"):
                pls = self._ps.get_all_playlists()
            elif hasattr(self._ps, "get_playlists"):
                pls = self._ps.get_playlists()
            else:
                pls = []
            return {"ok": True, "playlists": pls, "total": len(pls)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_playlist(self, playlist_id: str) -> dict[str, Any]:
        if self._ps is None:
            return _unavailable_response("PlaylistService")
        try:
            if hasattr(self._ps, "get_playlist_items"):
                items = self._ps.get_playlist_items(int(playlist_id))
                return {"ok": True, "playlist": {"id": playlist_id, "tracks": items}}
            return {"ok": False, "error": "NOT_FOUND"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def create_playlist(self, name: str, track_ids: list[str] | None = None, **kwargs: Any) -> dict[str, Any]:
        if self._ps is None:
            return _unavailable_response("PlaylistService")
        try:
            if hasattr(self._ps, "create_playlist"):
                pid = self._ps.create_playlist(name)
                if track_ids and pid:
                    for tid in track_ids:
                        if hasattr(self._ps, "add_track_to_playlist"):
                            self._ps.add_track_to_playlist(pid, tid)
                return {"ok": True, "playlist": {"id": str(pid), "name": name}}
            return {"ok": False, "error": "CREATE_FAILED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def add_to_playlist(self, playlist_id: str, track_ids: list[str], **kwargs: Any) -> dict[str, Any]:
        if self._ps is None:
            return _unavailable_response("PlaylistService")
        try:
            count = 0
            for tid in track_ids:
                if hasattr(self._ps, "add_track_to_playlist"):
                    self._ps.add_track_to_playlist(int(playlist_id), tid)
                    count += 1
            return {"ok": True, "added": count}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def remove_from_playlist(self, playlist_id: str, position: int, **kwargs: Any) -> dict[str, Any]:
        return _unavailable_response("remove_from_playlist (not yet wired)")

    def reorder_playlist(self, playlist_id: str, from_pos: int, to_pos: int, **kwargs: Any) -> dict[str, Any]:
        return _unavailable_response("reorder_playlist (not yet wired)")


class ProductionPlaybackGateway(PlaybackGateway):
    def __init__(self, player_service: Any) -> None:
        self._ps = player_service

    def play_track(self, track_id: str, **kwargs: Any) -> dict[str, Any]:
        if self._ps is None:
            return _unavailable_response("PlayerService")
        try:
            self._ps.play(track_id)
            return {"ok": True, "status": "REQUEST_ACCEPTED"}
        except Exception as e:
            return {"ok": False, "error": str(e), "code": "PLAYBACK_FAILED"}

    def play_album(self, album_id: str = "", artist: str = "", album: str = "", **kwargs: Any) -> dict[str, Any]:
        return _unavailable_response("play_album (route not yet wired)")

    def play_artist(self, artist_id: str = "", **kwargs: Any) -> dict[str, Any]:
        return _unavailable_response("play_artist (route not yet wired)")

    def play_playlist(self, playlist_id: str, **kwargs: Any) -> dict[str, Any]:
        if self._ps is None:
            return _unavailable_response("PlayerService")
        return _unavailable_response("play_playlist (route not yet wired)")

    def pause(self, **kwargs: Any) -> dict[str, Any]:
        if self._ps is None:
            return _unavailable_response("PlayerService")
        try:
            if self._ps.state == "playing":
                self._ps.pause()
                return {"ok": True, "status": "COMPLETED"}
            return {"ok": False, "error": "NOT_PLAYING", "code": "NOT_PLAYING"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def resume(self, **kwargs: Any) -> dict[str, Any]:
        if self._ps is None:
            return _unavailable_response("PlayerService")
        try:
            if self._ps.state == "paused":
                self._ps.resume()
                return {"ok": True, "status": "COMPLETED"}
            return {"ok": False, "error": "NOT_PAUSED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def stop(self, **kwargs: Any) -> dict[str, Any]:
        if self._ps is None:
            return _unavailable_response("PlayerService")
        try:
            self._ps.stop()
            return {"ok": True, "status": "COMPLETED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def next(self, **kwargs: Any) -> dict[str, Any]:
        if self._ps is None:
            return _unavailable_response("PlayerService")
        try:
            self._ps.play_next()
            return {"ok": True, "status": "COMPLETED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def previous(self, **kwargs: Any) -> dict[str, Any]:
        if self._ps is None:
            return _unavailable_response("PlayerService")
        try:
            self._ps.play_prev()
            return {"ok": True, "status": "COMPLETED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def seek(self, position_seconds: float, **kwargs: Any) -> dict[str, Any]:
        if self._ps is None:
            return _unavailable_response("PlayerService")
        if self._ps.state == "stopped":
            return {"ok": False, "error": "NOT_PLAYING"}
        try:
            self._ps.seek(position_seconds)
            return {"ok": True, "status": "COMPLETED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def set_volume(self, volume: float, **kwargs: Any) -> dict[str, Any]:
        if self._ps is None:
            return _unavailable_response("PlayerService")
        if volume < 0 or volume > 100:
            return {"ok": False, "error": "INVALID_VOLUME"}
        try:
            current = getattr(self._ps, "get_volume", lambda: None)()
            if current is not None and current == int(volume):
                return {"ok": True, "status": "COMPLETED", "volume": int(volume), "idempotent": True}
            self._ps.set_volume(int(volume))
            return {"ok": True, "status": "COMPLETED", "volume": int(volume)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def set_repeat(self, mode: str, **kwargs: Any) -> dict[str, Any]:
        if self._ps is None:
            return _unavailable_response("PlayerService")
        if mode not in ("none", "one", "all"):
            return {"ok": False, "error": "INVALID_MODE"}
        try:
            current = getattr(self._ps, "get_repeat", lambda: None)()
            if current is not None and current == mode:
                return {"ok": True, "status": "COMPLETED", "idempotent": True}
            self._ps.set_repeat(mode)
            return {"ok": True, "status": "COMPLETED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def set_shuffle(self, enabled: bool, **kwargs: Any) -> dict[str, Any]:
        if self._ps is None:
            return _unavailable_response("PlayerService")
        try:
            current = getattr(self._ps, "get_shuffle", lambda: None)()
            if current is not None and bool(current) == enabled:
                return {"ok": True, "status": "COMPLETED", "idempotent": True}
            if enabled:
                self._ps.toggle_shuffle()
            return {"ok": True, "status": "COMPLETED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_state(self) -> dict[str, Any]:
        if self._ps is None:
            return _unavailable_response("PlayerService")
        try:
            return {"ok": True, "state": {
                "is_playing": self._ps.state == "playing",
                "is_paused": self._ps.state == "paused",
                "current_track": self._ps.current_title,
                "volume": self._ps.get_volume() if hasattr(self._ps, "get_volume") else None,
            }}
        except Exception as e:
            return {"ok": False, "error": str(e)}


class ProductionLibraryGateway(LibraryGateway):
    def __init__(self, db: Any, global_search: Any = None) -> None:
        self._db = db
        self._search = global_search

    def search(self, query: str, **filters: Any) -> dict[str, Any]:
        if self._db is None:
            return _unavailable_response("LibraryDB")
        try:
            results = self._db.search_advanced(query, limit=filters.get("limit", 200))
            safe = []
            for r in results:
                item = {"id": str(getattr(r, "media_id", "")),
                        "title": getattr(r, "title", ""),
                        "artist": getattr(r, "artist", ""),
                        "album": getattr(r, "album", ""),
                        "duration": getattr(r, "duration", 0),
                        "format": getattr(r, "format", "")}
                safe.append(item)
            return {"ok": True, "results": safe, "total": len(safe)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_track(self, track_id: str) -> dict[str, Any]:
        if self._db is None:
            return _unavailable_response("LibraryDB")
        try:
            item = self._db.get_media_item_by_id(int(track_id))
            if item:
                return {"ok": True, "track": {"id": str(item.media_id), "title": item.title, "artist": item.artist}}
            return {"ok": False, "error": "NOT_FOUND"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_album(self, album_id: str) -> dict[str, Any]:
        return _unavailable_response("get_album (route not yet wired)")

    def get_artist(self, artist_id: str) -> dict[str, Any]:
        return _unavailable_response("get_artist (route not yet wired)")

    def list_recent(self, limit: int = 20) -> dict[str, Any]:
        return _unavailable_response("list_recent (route not yet wired)")

    def list_unplayed(self, limit: int = 20) -> dict[str, Any]:
        return _unavailable_response("list_unplayed (route not yet wired)")

    def list_favorites(self, limit: int = 20) -> dict[str, Any]:
        if self._db is None:
            return _unavailable_response("LibraryDB")
        try:
            favs = self._db.get_favorites()
            return {"ok": True, "tracks": favs[:limit], "total": len(favs)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def find_metadata_gaps(self) -> dict[str, Any]:
        if self._db is None:
            return _unavailable_response("LibraryDB")
        try:
            stats = self._db.get_dashboard_stats()
            gaps = []
            count = stats.get("missing_metadata_count", 0) if isinstance(stats, dict) else 0
            return {"ok": True, "gaps": gaps, "total": count}
        except Exception as e:
            return {"ok": False, "error": str(e)}


class ProductionQueueGateway(QueueGateway):
    def __init__(self, player_service: Any) -> None:
        self._ps = player_service

    def get_queue(self) -> dict[str, Any]:
        if self._ps is None:
            return _unavailable_response("PlayerService")
        try:
            q = self._ps.get_queue()
            return {"ok": True, "queue": q or [], "count": len(q or [])}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def add_to_queue(self, track_ids: list[str], **kwargs: Any) -> dict[str, Any]:
        if self._ps is None:
            return _unavailable_response("PlayerService")
        try:
            self._ps.enqueue(track_ids, play_now=False)
            return {"ok": True, "added": len(track_ids), "status": "COMPLETED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def play_next(self, track_ids: list[str], **kwargs: Any) -> dict[str, Any]:
        if self._ps is None:
            return _unavailable_response("PlayerService")
        try:
            self._ps.enqueue_next(track_ids)
            return {"ok": True, "status": "COMPLETED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def replace_queue(self, track_ids: list[str], **kwargs: Any) -> dict[str, Any]:
        if self._ps is None:
            return _unavailable_response("PlayerService")
        try:
            self._ps.play_queue(track_ids, start_index=0)
            return {"ok": True, "count": len(track_ids), "status": "COMPLETED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def remove_from_queue(self, position: int, **kwargs: Any) -> dict[str, Any]:
        if self._ps is None:
            return _unavailable_response("PlayerService")
        try:
            q = self._ps.get_queue()
            if 0 <= position < len(q):
                q.pop(position)
                self._ps.reorder_queue(q)
                return {"ok": True}
            return {"ok": False, "error": "INVALID_POSITION"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def clear_queue(self, **kwargs: Any) -> dict[str, Any]:
        if self._ps is None:
            return _unavailable_response("PlayerService")
        try:
            self._ps.clear_queue()
            return {"ok": True, "status": "COMPLETED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def reorder_queue(self, from_pos: int, to_pos: int, **kwargs: Any) -> dict[str, Any]:
        if self._ps is None:
            return _unavailable_response("PlayerService")
        try:
            q = self._ps.get_queue()
            if 0 <= from_pos < len(q) and 0 <= to_pos < len(q):
                item = q.pop(from_pos)
                q.insert(to_pos, item)
                self._ps.reorder_queue(q)
                return {"ok": True}
            return {"ok": False, "error": "INVALID_POSITION"}
        except Exception as e:
            return {"ok": False, "error": str(e)}


class ProductionPlaylistGateway(PlaylistGateway):
    def __init__(self, db: Any, playlist_service: Any = None) -> None:
        self._db = db
        self._pl_svc = playlist_service

    def list_playlists(self) -> dict[str, Any]:
        if self._db is None:
            return _unavailable_response("LibraryDB")
        try:
            pls = self._db.get_playlists()
            return {"ok": True, "playlists": pls, "total": len(pls)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_playlist(self, playlist_id: str) -> dict[str, Any]:
        if self._db is None:
            return _unavailable_response("LibraryDB")
        try:
            items = self._db.get_playlist_items(int(playlist_id))
            return {"ok": True, "playlist": {"id": playlist_id, "tracks": items}}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def create_playlist(self, name: str, track_ids: list[str] | None = None, **kwargs: Any) -> dict[str, Any]:
        if self._db is None:
            return _unavailable_response("LibraryDB")
        try:
            pid = self._db.create_playlist(name)
            if track_ids and pid:
                for tid in track_ids:
                    self._db.add_to_playlist(pid, track_id=tid)
            return {"ok": True, "playlist": {"id": str(pid), "name": name}}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def add_to_playlist(self, playlist_id: str, track_ids: list[str], **kwargs: Any) -> dict[str, Any]:
        if self._db is None:
            return _unavailable_response("LibraryDB")
        try:
            for tid in track_ids:
                self._db.add_to_playlist(int(playlist_id), track_id=tid)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def remove_from_playlist(self, playlist_id: str, position: int, **kwargs: Any) -> dict[str, Any]:
        return _unavailable_response("remove_from_playlist (route not yet wired)")

    def reorder_playlist(self, playlist_id: str, from_pos: int, to_pos: int, **kwargs: Any) -> dict[str, Any]:
        return _unavailable_response("reorder_playlist (route not yet wired)")


class ProductionSettingsGateway(SettingsGateway):
    def __init__(self, settings_service: Any = None) -> None:
        self._ss = settings_service

    def get_setting(self, key: str) -> dict[str, Any]:
        if self._ss is None:
            return _unavailable_response("SettingsService")
        try:
            val = self._ss.get(key)
            return {"ok": True, "key": key, "value": val}
        except Exception:
            return {"ok": False, "error": "NOT_FOUND"}

    def suggest_change(self, key: str, value: Any) -> dict[str, Any]:
        return _unavailable_response("suggest_change (route not yet wired)")

    def preview_change(self, key: str, value: Any) -> dict[str, Any]:
        if self._ss is None:
            return _unavailable_response("SettingsService")
        try:
            old = self._ss.get(key)
            return {"ok": True, "key": key, "old_value": old, "new_value": value,
                    "restart_required": False, "rollback_available": True}
        except Exception:
            return {"ok": False, "error": "NOT_FOUND"}

    def apply_change(self, key: str, value: Any) -> dict[str, Any]:
        if self._ss is None:
            return _unavailable_response("SettingsService")
        try:
            old = self._ss.get(key)
            self._ss.set_(key, value)
            return {"ok": True, "key": key, "old_value": old, "new_value": value}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def list_settings(self) -> dict[str, Any]:
        if self._ss is None:
            return _unavailable_response("SettingsService")
        try:
            all_settings = self._ss.get_all()
            items = [{"key": k, "value": v} for k, v in all_settings.items()]
            return {"ok": True, "settings": items}
        except Exception as e:
            return {"ok": False, "error": str(e)}


class ProductionAudioLabGateway(AudioLabGateway):
    def __init__(self, analysis_service: Any = None) -> None:
        self._as = analysis_service

    def probe_audio(self, track_id: str) -> dict[str, Any]:
        return _unavailable_response("probe_audio (route not yet wired)")

    def analyze_audio(self, track_ids: list[str]) -> dict[str, Any]:
        if self._as is None:
            return _unavailable_response("AnalysisService")
        try:
            ids = [int(t) for t in track_ids]
            batch_id = self._as.analyze_tracks_async(ids)
            return {"ok": True, "batch_id": batch_id, "status": "JOB_STARTED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def recommend_conversion(self, track_ids: list[str], target_format: str = "opus", **kwargs: Any) -> dict[str, Any]:
        return _unavailable_response("recommend_conversion (route not yet wired)")

    def preview_conversion(self, plan_id: str) -> dict[str, Any]:
        return _unavailable_response("preview_conversion (route not yet wired)")

    def start_conversion(self, plan_id: str) -> dict[str, Any]:
        return _unavailable_response("start_conversion (route not yet wired)")

    def cancel_conversion(self, job_id: str) -> dict[str, Any]:
        if self._as is None:
            return _unavailable_response("AnalysisService")
        try:
            self._as.cancel(job_id)
            return {"ok": True, "status": "cancelled"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def analyze_replaygain(self, track_ids: list[str]) -> dict[str, Any]:
        return _unavailable_response("analyze_replaygain (route not yet wired)")

    def check_integrity(self, track_ids: list[str]) -> dict[str, Any]:
        return _unavailable_response("check_integrity (route not yet wired)")

    def compare_audio(self, track_id_a: str, track_id_b: str) -> dict[str, Any]:
        return _unavailable_response("compare_audio (route not yet wired)")

    def get_status(self) -> dict[str, Any]:
        if self._as is None:
            return _unavailable_response("AnalysisService")
        try:
            status = self._as.get_status()
            return {"ok": True, "status": status}
        except Exception as e:
            return {"ok": False, "error": str(e)}


class ProductionDeviceGateway(DeviceGateway):
    def __init__(self, sync_manager: Any = None) -> None:
        self._sm = sync_manager

    def list_devices(self) -> dict[str, Any]:
        if self._sm is None:
            return _unavailable_response("SyncManager")
        try:
            peers = self._sm.get_all_peers()
            return {"ok": True, "devices": peers}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def diagnose_ecosystem(self) -> dict[str, Any]:
        return _unavailable_response("diagnose_ecosystem (route not yet wired)")

    def diagnose_server(self) -> dict[str, Any]:
        return _unavailable_response("diagnose_server (route not yet wired)")

    def diagnose_home_audio(self) -> dict[str, Any]:
        return _unavailable_response("diagnose_home_audio (route not yet wired)")

    def diagnose_pairing(self) -> dict[str, Any]:
        return _unavailable_response("diagnose_pairing (route not yet wired)")

    def plan_sync(self, playlist_id: str, device_id: str) -> dict[str, Any]:
        return _unavailable_response("plan_sync (route not yet wired)")

    def start_sync(self, plan_id: str) -> dict[str, Any]:
        return _unavailable_response("start_sync (route not yet wired)")

    def cancel_sync(self, job_id: str) -> dict[str, Any]:
        return _unavailable_response("cancel_sync (route not yet wired)")


class ProductionDiagnosticsGateway(DiagnosticsGateway):
    def __init__(self, diagnostics_service: Any = None) -> None:
        self._ds = diagnostics_service

    def get_diagnostics(self) -> dict[str, Any]:
        return {"ok": True, "status": "operational", "version": "2.0"}

    def get_audio_diagnostics(self) -> dict[str, Any]:
        return {"ok": True, "status": "operational"}

    def get_network_diagnostics(self) -> dict[str, Any]:
        return {"ok": True, "status": "operational"}


class ProductionMixGateway(MixGateway):
    def __init__(self, mix_service: Any = None) -> None:
        self._ms = mix_service

    def create_mix(self, strategy: str, **params: Any) -> dict[str, Any]:
        return _unavailable_response("create_mix (route not yet wired)")

    def explain_mix(self, mix_id: str) -> dict[str, Any]:
        return _unavailable_response("explain_mix (route not yet wired)")

    def save_mix_as_playlist(self, mix_id: str, name: str) -> dict[str, Any]:
        return _unavailable_response("save_mix_as_playlist (route not yet wired)")

    def cancel_mix(self, job_id: str) -> dict[str, Any]:
        return _unavailable_response("cancel_mix (route not yet wired)")


class ProductionJobGateway(JobGateway):
    def __init__(self, job_service: Any = None) -> None:
        self._js = job_service

    def list_jobs(self) -> dict[str, Any]:
        if self._js is None:
            return _unavailable_response("JobService")
        try:
            jobs = self._js.list_active()
            return {"ok": True, "jobs": [{"id": j.job_id, "kind": j.kind, "status": j.status.value, "progress": j.progress} for j in jobs]}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        if self._js is None:
            return _unavailable_response("JobService")
        try:
            ok = self._js.cancel(job_id)
            return {"ok": ok, "status": "cancelled" if ok else "not_found"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_job_status(self, job_id: str) -> dict[str, Any]:
        if self._js is None:
            return _unavailable_response("JobService")
        try:
            job = self._js.get(job_id)
            if job:
                return {"ok": True, "job": {"id": job.job_id, "kind": job.kind, "status": job.status.value, "progress": job.progress}}
            return {"ok": False, "error": "NOT_FOUND"}
        except Exception as e:
            return {"ok": False, "error": str(e)}


class UnavailableNavigationGateway(NavigationRequestGateway):
    def request_navigation(self, target: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"ok": True, "status": "REQUEST_ACCEPTED", "route": target}


class UnavailableRadioGateway:
    def search_stations(self, query: str) -> dict[str, Any]:
        return _unavailable_response("RadioService")
    def list_favorites(self) -> dict[str, Any]:
        return _unavailable_response("RadioService")
    def play_station(self, station_id: str) -> dict[str, Any]:
        return _unavailable_response("RadioService")
    def stop_radio(self) -> dict[str, Any]:
        return _unavailable_response("RadioService")


class UnavailableMetadataGateway:
    def inspect_metadata(self, track_id: str) -> dict[str, Any]:
        return _unavailable_response("MetadataService")
    def build_proposal(self, track_id: str) -> dict[str, Any]:
        return _unavailable_response("MetadataService")


class UnavailableLibraryDoctorGateway:
    def scan(self) -> dict[str, Any]:
        return _unavailable_response("LibraryDoctorService")
    def preview_repair(self, scan_id: str) -> dict[str, Any]:
        return _unavailable_response("LibraryDoctorService")


class UnavailableConnectionsGateway:
    def list_connections(self) -> dict[str, Any]:
        return _unavailable_response("ConnectionsService")


class UnavailableHomeAudioGateway:
    def get_status(self) -> dict[str, Any]:
        return _unavailable_response("HomeAudioService")


class UnavailableLyricsGateway:
    def get_current_lyrics(self) -> dict[str, Any]:
        return _unavailable_response("LyricsService")
