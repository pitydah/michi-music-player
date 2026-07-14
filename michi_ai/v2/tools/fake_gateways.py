from __future__ import annotations

from typing import Any


_LIBRARY_DATA: dict[str, list[dict[str, Any]]] = {
    "tracks": [
        {"id": "1", "title": "Song A", "artist": "Artist X", "album": "Album 1", "duration": 240, "format": "FLAC", "bitrate": 960},
        {"id": "2", "title": "Song B", "artist": "Artist X", "album": "Album 1", "duration": 200, "format": "FLAC", "bitrate": 960},
        {"id": "3", "title": "Song C", "artist": "Artist Y", "album": "Album 2", "duration": 180, "format": "MP3", "bitrate": 320},
    ],
    "albums": [
        {"id": "a1", "title": "Album 1", "artist": "Artist X", "year": 2020, "track_count": 2},
        {"id": "a2", "title": "Album 2", "artist": "Artist Y", "year": 2022, "track_count": 1},
    ],
    "artists": [
        {"id": "ar1", "name": "Artist X", "album_count": 1},
        {"id": "ar2", "name": "Artist Y", "album_count": 1},
    ],
    "playlists": [
        {"id": "pl1", "name": "Favorites", "track_count": 5},
        {"id": "pl2", "name": "Rock Classics", "track_count": 10},
    ],
}


class FakePlaybackGateway:
    def __init__(self) -> None:
        self._state: dict[str, Any] = {
            "is_playing": False, "is_paused": False,
            "current_track": None, "volume": 80,
            "repeat": "none", "shuffle": False,
            "position": 0.0,
        }

    def play_track(self, track_id: str, **kwargs: Any) -> dict[str, Any]:
        self._state["is_playing"] = True
        self._state["is_paused"] = False
        self._state["current_track"] = {"id": track_id}
        self._state["position"] = 0.0
        return {"ok": True, "state": self._state}

    def play_album(self, album_id: str, **kwargs: Any) -> dict[str, Any]:
        self._state["is_playing"] = True
        self._state["is_paused"] = False
        self._state["current_track"] = {"album_id": album_id}
        return {"ok": True, "state": self._state}

    def play_artist(self, artist_id: str, **kwargs: Any) -> dict[str, Any]:
        self._state["is_playing"] = True
        return {"ok": True, "state": self._state}

    def play_playlist(self, playlist_id: str, **kwargs: Any) -> dict[str, Any]:
        self._state["is_playing"] = True
        return {"ok": True, "state": self._state}

    def pause(self, **kwargs: Any) -> dict[str, Any]:
        if not self._state["is_playing"]:
            return {"ok": False, "error": "NOT_PLAYING", "state": self._state}
        self._state["is_paused"] = True
        self._state["is_playing"] = False
        return {"ok": True, "state": self._state}

    def resume(self, **kwargs: Any) -> dict[str, Any]:
        if not self._state["is_paused"]:
            return {"ok": False, "error": "NOT_PAUSED", "state": self._state}
        self._state["is_playing"] = True
        self._state["is_paused"] = False
        return {"ok": True, "state": self._state}

    def stop(self, **kwargs: Any) -> dict[str, Any]:
        self._state["is_playing"] = False
        self._state["is_paused"] = False
        self._state["current_track"] = None
        return {"ok": True, "state": self._state}

    def next(self, **kwargs: Any) -> dict[str, Any]:
        if not self._state["is_playing"] and not self._state["is_paused"]:
            return {"ok": False, "error": "NOT_PLAYING", "state": self._state}
        return {"ok": True, "state": self._state}

    def previous(self, **kwargs: Any) -> dict[str, Any]:
        if not self._state["is_playing"] and not self._state["is_paused"]:
            return {"ok": False, "error": "NOT_PLAYING", "state": self._state}
        return {"ok": True, "state": self._state}

    def seek(self, position_seconds: float, **kwargs: Any) -> dict[str, Any]:
        if not self._state["is_playing"]:
            return {"ok": False, "error": "NOT_PLAYING"}
        self._state["position"] = position_seconds
        return {"ok": True, "state": self._state}

    def set_volume(self, volume: float, **kwargs: Any) -> dict[str, Any]:
        if volume < 0 or volume > 100:
            return {"ok": False, "error": "INVALID_VOLUME"}
        self._state["volume"] = volume
        return {"ok": True, "state": self._state}

    def set_repeat(self, mode: str, **kwargs: Any) -> dict[str, Any]:
        if mode not in ("none", "one", "all"):
            return {"ok": False, "error": "INVALID_MODE"}
        self._state["repeat"] = mode
        return {"ok": True, "state": self._state}

    def set_shuffle(self, enabled: bool, **kwargs: Any) -> dict[str, Any]:
        self._state["shuffle"] = enabled
        return {"ok": True, "state": self._state}

    def get_state(self) -> dict[str, Any]:
        return {"ok": True, "state": self._state}

    @property
    def state(self) -> dict[str, Any]:
        return self._state


class FakeLibraryGateway:
    def __init__(self) -> None:
        self._data = _LIBRARY_DATA

    def search(self, query: str, **filters: Any) -> dict[str, Any]:
        q = query.lower()
        results = [t for t in self._data["tracks"] if q in t["title"].lower() or q in t["artist"].lower()]
        return {"ok": True, "total": len(results), "results": results}

    def get_track(self, track_id: str) -> dict[str, Any]:
        for t in self._data["tracks"]:
            if t["id"] == track_id:
                return {"ok": True, "track": t}
        return {"ok": False, "error": "NOT_FOUND"}

    def get_album(self, album_id: str) -> dict[str, Any]:
        for a in self._data["albums"]:
            if a["id"] == album_id:
                return {"ok": True, "album": a}
        return {"ok": False, "error": "NOT_FOUND"}

    def get_artist(self, artist_id: str) -> dict[str, Any]:
        for a in self._data["artists"]:
            if a["id"] == artist_id:
                return {"ok": True, "artist": a}
        return {"ok": False, "error": "NOT_FOUND"}

    def list_recent(self, limit: int = 20) -> dict[str, Any]:
        return {"ok": True, "tracks": self._data["tracks"][:limit], "total": len(self._data["tracks"])}

    def list_unplayed(self, limit: int = 20) -> dict[str, Any]:
        return {"ok": True, "tracks": [], "total": 0}

    def list_favorites(self, limit: int = 20) -> dict[str, Any]:
        return {"ok": True, "tracks": self._data["tracks"][:limit], "total": len(self._data["tracks"])}

    def find_metadata_gaps(self) -> dict[str, Any]:
        return {"ok": True, "gaps": [], "total": 0}


class FakeQueueGateway:
    def __init__(self) -> None:
        self._queue: list[dict[str, Any]] = []

    def get_queue(self) -> dict[str, Any]:
        return {"ok": True, "queue": self._queue, "count": len(self._queue)}

    def add_to_queue(self, track_ids: list[str], **kwargs: Any) -> dict[str, Any]:
        for tid in track_ids:
            self._queue.append({"id": tid})
        return {"ok": True, "added": len(track_ids), "count": len(self._queue)}

    def play_next(self, track_ids: list[str], **kwargs: Any) -> dict[str, Any]:
        for tid in reversed(track_ids):
            self._queue.insert(0, {"id": tid})
        return {"ok": True, "count": len(self._queue)}

    def replace_queue(self, track_ids: list[str], **kwargs: Any) -> dict[str, Any]:
        self._queue = [{"id": tid} for tid in track_ids]
        return {"ok": True, "count": len(self._queue)}

    def remove_from_queue(self, position: int, **kwargs: Any) -> dict[str, Any]:
        if 0 <= position < len(self._queue):
            self._queue.pop(position)
            return {"ok": True, "count": len(self._queue)}
        return {"ok": False, "error": "INVALID_POSITION"}

    def clear_queue(self, **kwargs: Any) -> dict[str, Any]:
        self._queue.clear()
        return {"ok": True, "count": 0}

    def reorder_queue(self, from_pos: int, to_pos: int, **kwargs: Any) -> dict[str, Any]:
        if 0 <= from_pos < len(self._queue) and 0 <= to_pos < len(self._queue):
            item = self._queue.pop(from_pos)
            self._queue.insert(to_pos, item)
            return {"ok": True}
        return {"ok": False, "error": "INVALID_POSITION"}


class FakePlaylistGateway:
    def __init__(self) -> None:
        self._playlists: dict[str, dict[str, Any]] = {
            "pl1": {"id": "pl1", "name": "Favorites", "tracks": []},
            "pl2": {"id": "pl2", "name": "Rock Classics", "tracks": []},
        }

    def list_playlists(self) -> dict[str, Any]:
        return {"ok": True, "playlists": list(self._playlists.values())}

    def get_playlist(self, playlist_id: str) -> dict[str, Any]:
        pl = self._playlists.get(playlist_id)
        if pl:
            return {"ok": True, "playlist": pl}
        return {"ok": False, "error": "NOT_FOUND"}

    def create_playlist(self, name: str, track_ids: list[str] | None = None, **kwargs: Any) -> dict[str, Any]:
        pl_id = f"pl{len(self._playlists) + 1}"
        self._playlists[pl_id] = {"id": pl_id, "name": name, "tracks": track_ids or []}
        return {"ok": True, "playlist": self._playlists[pl_id]}

    def add_to_playlist(self, playlist_id: str, track_ids: list[str], **kwargs: Any) -> dict[str, Any]:
        pl = self._playlists.get(playlist_id)
        if not pl:
            return {"ok": False, "error": "NOT_FOUND"}
        pl["tracks"].extend(track_ids)
        return {"ok": True, "count": len(pl["tracks"])}

    def remove_from_playlist(self, playlist_id: str, position: int, **kwargs: Any) -> dict[str, Any]:
        pl = self._playlists.get(playlist_id)
        if not pl:
            return {"ok": False, "error": "NOT_FOUND"}
        if 0 <= position < len(pl["tracks"]):
            pl["tracks"].pop(position)
            return {"ok": True}
        return {"ok": False, "error": "INVALID_POSITION"}

    def reorder_playlist(self, playlist_id: str, from_pos: int, to_pos: int, **kwargs: Any) -> dict[str, Any]:
        pl = self._playlists.get(playlist_id)
        if not pl:
            return {"ok": False, "error": "NOT_FOUND"}
        tracks = pl["tracks"]
        if 0 <= from_pos < len(tracks) and 0 <= to_pos < len(tracks):
            item = tracks.pop(from_pos)
            tracks.insert(to_pos, item)
            return {"ok": True}
        return {"ok": False, "error": "INVALID_POSITION"}


class FakeAudioLabGateway:
    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}

    def probe_audio(self, track_id: str) -> dict[str, Any]:
        return {"ok": True, "format": "FLAC", "sample_rate": 44100, "bit_depth": 16, "channels": 2}

    def analyze_audio(self, track_ids: list[str]) -> dict[str, Any]:
        return {"ok": True, "analyzed": len(track_ids), "features": {"bpm": 120, "key": "C", "energy": 0.8}}

    def recommend_conversion(self, track_ids: list[str], target: str = "mobile", **kwargs: Any) -> dict[str, Any]:
        return {"ok": True, "plan_id": "conv_plan_1", "estimated_size_mb": 50, "target_format": target}

    def preview_conversion(self, plan_id: str) -> dict[str, Any]:
        return {"ok": True, "plan_id": plan_id, "tracks": 3, "estimated_size_mb": 50}

    def start_conversion(self, plan_id: str) -> dict[str, Any]:
        job_id = f"job_{len(self._jobs) + 1}"
        self._jobs[job_id] = {"id": job_id, "plan_id": plan_id, "status": "running", "progress": 0}
        return {"ok": True, "job_id": job_id, "status": "JOB_STARTED", "progress": 0}

    def cancel_conversion(self, job_id: str) -> dict[str, Any]:
        job = self._jobs.get(job_id)
        if job:
            job["status"] = "cancelled"
            return {"ok": True, "status": "cancelled"}
        return {"ok": False, "error": "NOT_FOUND"}

    def analyze_replaygain(self, track_ids: list[str]) -> dict[str, Any]:
        return {"ok": True, "results": {tid: {"track_gain": -6.5, "album_gain": -5.0} for tid in track_ids}}

    def check_integrity(self, track_ids: list[str]) -> dict[str, Any]:
        return {"ok": True, "results": {tid: {"valid": True} for tid in track_ids}}

    def compare_audio(self, track_id_a: str, track_id_b: str) -> dict[str, Any]:
        return {"ok": True, "similarity": 0.85, "differences": []}

    def get_status(self) -> dict[str, Any]:
        return {"ok": True, "pending_jobs": len(self._jobs), "active": True}


class FakeDeviceGateway:
    def __init__(self) -> None:
        self._sync_jobs: dict[str, dict[str, Any]] = {}

    def list_devices(self) -> dict[str, Any]:
        return {"ok": True, "devices": [{"id": "d1", "name": "Phone", "type": "android", "status": "paired"}]}

    def diagnose_ecosystem(self) -> dict[str, Any]:
        return {"ok": True, "status": "healthy", "services": {"sync": True, "server": True}}

    def diagnose_server(self) -> dict[str, Any]:
        return {"ok": True, "host": "localhost", "port": 53318, "reachable": True}

    def diagnose_home_audio(self) -> dict[str, Any]:
        return {"ok": True, "snapcast": {"active": False}, "zones": 0}

    def diagnose_pairing(self) -> dict[str, Any]:
        return {"ok": True, "paired": True, "device": "Phone"}

    def plan_sync(self, playlist_id: str, device_id: str, **kwargs: Any) -> dict[str, Any]:
        return {"ok": True, "plan_id": "sync_plan_1", "tracks": 10, "estimated_size_mb": 100, "device_id": device_id}

    def start_sync(self, plan_id: str) -> dict[str, Any]:
        job_id = f"sync_job_{len(self._sync_jobs) + 1}"
        self._sync_jobs[job_id] = {"id": job_id, "plan_id": plan_id, "status": "running", "progress": 0}
        return {"ok": True, "job_id": job_id, "status": "JOB_STARTED"}

    def cancel_sync(self, job_id: str) -> dict[str, Any]:
        job = self._sync_jobs.get(job_id)
        if job:
            job["status"] = "cancelled"
            return {"ok": True, "status": "cancelled"}
        return {"ok": False, "error": "NOT_FOUND"}


class FakeSettingsGateway:
    def __init__(self) -> None:
        self._settings: dict[str, Any] = {
            "audio/volume": 80,
            "audio/output_device": "default",
            "playback/repeat": "none",
            "playback/shuffle": False,
            "library/path": "/home/user/music",
            "ai/model": "llama3.2",
            "ai/provider": "ollama",
        }
        self._defaults: dict[str, Any] = {
            "audio/volume": 80,
            "playback/repeat": "none",
            "playback/shuffle": False,
        }

    def get_setting(self, key: str) -> dict[str, Any]:
        if key in self._settings:
            return {"ok": True, "key": key, "value": self._settings[key]}
        return {"ok": False, "error": "NOT_FOUND"}

    def suggest_change(self, key: str, value: Any) -> dict[str, Any]:
        if key not in self._settings:
            return {"ok": False, "error": "UNKNOWN_KEY"}
        return {"ok": True, "key": key, "old_value": self._settings[key], "new_value": value}

    def preview_change(self, key: str, value: Any) -> dict[str, Any]:
        if key not in self._settings:
            return {"ok": False, "error": "UNKNOWN_KEY"}
        return {"ok": True, "key": key, "old_value": self._settings[key], "new_value": value, "restart_required": False, "rollback_available": True}

    def apply_change(self, key: str, value: Any) -> dict[str, Any]:
        if key not in self._settings:
            return {"ok": False, "error": "UNKNOWN_KEY"}
        old = self._settings[key]
        self._settings[key] = value
        return {"ok": True, "key": key, "old_value": old, "new_value": value}

    def list_settings(self) -> dict[str, Any]:
        return {"ok": True, "settings": [{"key": k, "value": v} for k, v in self._settings.items()]}


class FakeDiagnosticsGateway:
    def get_diagnostics(self) -> dict[str, Any]:
        return {"ok": True, "audio": {"engine": "gstreamer", "active": True}, "library": {"tracks": 3, "healthy": True}}

    def get_audio_diagnostics(self) -> dict[str, Any]:
        return {"ok": True, "output": "default", "sample_rate": 44100, "bit_perfect": False}

    def get_network_diagnostics(self) -> dict[str, Any]:
        return {"ok": True, "connectivity": True, "local_ip": "192.168.1.100"}


class FakeMixGateway:
    def __init__(self) -> None:
        self._mixes: dict[str, dict[str, Any]] = {}

    def create_mix(self, strategy: str, **params: Any) -> dict[str, Any]:
        mix_id = f"mix_{len(self._mixes) + 1}"
        self._mixes[mix_id] = {"id": mix_id, "strategy": strategy, "tracks": 15, "status": "ready"}
        return {"ok": True, "mix_id": mix_id, "tracks": self._mixes[mix_id]}

    def explain_mix(self, mix_id: str) -> dict[str, Any]:
        mix = self._mixes.get(mix_id)
        if mix:
            return {"ok": True, "mix": mix, "explanation": f"Mix based on {mix['strategy']} strategy"}
        return {"ok": False, "error": "NOT_FOUND"}

    def save_mix_as_playlist(self, mix_id: str, name: str) -> dict[str, Any]:
        if mix_id in self._mixes:
            return {"ok": True, "playlist_id": "pl_new", "name": name, "tracks": self._mixes[mix_id]["tracks"]}
        return {"ok": False, "error": "NOT_FOUND"}

    def cancel_mix(self, job_id: str) -> dict[str, Any]:
        return {"ok": True, "status": "cancelled"}


class FakeJobGateway:
    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}

    def list_jobs(self) -> dict[str, Any]:
        return {"ok": True, "jobs": list(self._jobs.values())}

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        job = self._jobs.get(job_id)
        if job:
            job["status"] = "cancelled"
            return {"ok": True}
        return {"ok": False, "error": "NOT_FOUND"}

    def get_job_status(self, job_id: str) -> dict[str, Any]:
        job = self._jobs.get(job_id)
        if job:
            return {"ok": True, "job": job}
        return {"ok": False, "error": "NOT_FOUND"}
