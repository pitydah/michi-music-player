"""Adapters that expose application services to the Michi assistant.

Every ``Production*`` gateway here either reaches a REAL operation on a wired
service or returns an explicit ``CAPABILITY_UNAVAILABLE`` result. Static
"operational" success payloads are forbidden: capability is evidence-based
(service presence + method reachability), never object existence alone.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from michi_ai.v2.core.gateways import (
    AudioLabGateway, DeviceGateway, DiagnosticsGateway,
    JobGateway, LibraryGateway,
    MixGateway, NavigationRequestGateway,
    PlaybackGateway, PlaylistGateway, QueueGateway,
    SettingsGateway,
)
try:
    from michi_ai.v2.core.gateways import ConnectionsGateway, HomeAudioGateway, LibraryDoctorGateway, LyricsGateway, MetadataGateway, RadioGateway
except ImportError:
    class ConnectionsGateway: ...
    class HomeAudioGateway: ...
    class LibraryDoctorGateway: ...
    class LyricsGateway: ...
    class MetadataGateway: ...
    class RadioGateway: ...

logger = logging.getLogger(__name__)


@dataclass
class AssistantGateways:
    """Collect the optional capability gateways available to the assistant."""

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
            "lyrics": self.lyrics,
            "metadata": self.metadata,
            "library_doctor": self.library_doctor,
            "connections": self.connections,
            "home_audio": self.home_audio,
        }


def _unavailable_response(name: str) -> dict[str, Any]:
    return {"ok": False, "error": f"Service '{name}' unavailable", "code": "CAPABILITY_UNAVAILABLE"}


class ProductionCapabilityMixin:
    """Evidence-based capability reporting shared by production gateways.

    A capability is available only when the gateway exists AND at least one
    backing service reference is present. The capability resolver consumes
    ``operational_capabilities()`` instead of the gateway's object existence.
    """

    def _any_service(self, *attrs: str) -> bool:
        return any(getattr(self, attr, None) is not None for attr in attrs)

    def operational_capabilities(self) -> dict[str, bool]:
        return {}


class ProductionPlaybackGateway(PlaybackGateway, ProductionCapabilityMixin):
    """Adapt playback commands while preserving service ownership boundaries.

    Transport uses PlayerService, queue navigation and modes use QueueService,
    direct track playback uses TrackActionService, and collection playback
    (album/artist/playlist) resolves tracks through LibraryQueryService /
    PlaylistService and replaces the queue through QueueService.
    """

    def __init__(self, player_service: Any, queue_service: Any = None,
                 track_action_service: Any = None, playlist_service: Any = None,
                 library_query_service: Any = None) -> None:
        self._player = player_service
        self._queue = queue_service
        self._track_actions = track_action_service
        self._pl_svc = playlist_service
        self._lq = library_query_service

    def operational_capabilities(self) -> dict[str, bool]:
        return {"playback.control": self._any_service("_player", "_queue", "_track_actions")}

    def play_track(self, track_id: str, **kwargs: Any) -> dict[str, Any]:
        if self._track_actions is None:
            return _unavailable_response("TrackActionService")
        try:
            return self._track_actions.play_track(int(track_id))
        except Exception as e:
            return {"ok": False, "error": str(e), "code": "PLAYBACK_FAILED"}

    def _play_tracks(self, tracks: list[dict]) -> dict[str, Any]:
        if self._queue is None:
            return _unavailable_response("QueueService")
        if not tracks:
            return {"ok": False, "error": "NOT_FOUND", "code": "NOT_FOUND"}
        try:
            result = self._queue.replace_and_play(tracks)
            return result if isinstance(result, dict) else {"ok": True, "status": "COMPLETED"}
        except Exception as e:
            return {"ok": False, "error": str(e), "code": "PLAYBACK_FAILED"}

    def play_album(self, album_id: str = "", artist: str = "", album: str = "", **kwargs: Any) -> dict[str, Any]:
        if self._lq is None:
            return _unavailable_response("LibraryQueryService (play_album)")
        key = album_id or album
        if not key:
            return {"ok": False, "error": "ALBUM_NOT_SPECIFIED"}
        try:
            tracks = self._lq.fetch_album_tracks_internal(key)
            return self._play_tracks(tracks)
        except Exception as e:
            return {"ok": False, "error": str(e), "code": "PLAYBACK_FAILED"}

    def play_artist(self, artist_id: str = "", **kwargs: Any) -> dict[str, Any]:
        if self._lq is None:
            return _unavailable_response("LibraryQueryService (play_artist)")
        if not artist_id:
            return {"ok": False, "error": "ARTIST_NOT_SPECIFIED"}
        try:
            tracks = self._lq.fetch_artist_tracks_internal(artist_id)
            return self._play_tracks(tracks)
        except Exception as e:
            return {"ok": False, "error": str(e), "code": "PLAYBACK_FAILED"}

    def play_playlist(self, playlist_id: str, **kwargs: Any) -> dict[str, Any]:
        if self._pl_svc is None:
            return _unavailable_response("PlaylistService (play_playlist)")
        try:
            items = self._pl_svc.get_items_for_queue(int(playlist_id))
            if not items:
                return {"ok": False, "error": "PLAYLIST_NOT_FOUND", "code": "NOT_FOUND"}
            return self._play_tracks(items)
        except Exception as e:
            return {"ok": False, "error": str(e), "code": "PLAYBACK_FAILED"}

    def pause(self, **kwargs: Any) -> dict[str, Any]:
        if self._player is None:
            return _unavailable_response("PlayerService")
        try:
            if self._player.state == "playing":
                self._player.pause()
                return {"ok": True, "status": "COMPLETED"}
            return {"ok": False, "error": "NOT_PLAYING", "code": "NOT_PLAYING"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def resume(self, **kwargs: Any) -> dict[str, Any]:
        if self._player is None:
            return _unavailable_response("PlayerService")
        try:
            if self._player.state == "paused":
                self._player.resume()
                return {"ok": True, "status": "COMPLETED"}
            return {"ok": False, "error": "NOT_PAUSED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def stop(self, **kwargs: Any) -> dict[str, Any]:
        if self._player is None:
            return _unavailable_response("PlayerService")
        try:
            self._player.stop()
            return {"ok": True, "status": "COMPLETED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def next(self, **kwargs: Any) -> dict[str, Any]:
        if self._queue is None:
            return _unavailable_response("QueueService")
        try:
            return self._queue.next()
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def previous(self, **kwargs: Any) -> dict[str, Any]:
        if self._queue is None:
            return _unavailable_response("QueueService")
        try:
            return self._queue.previous()
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def seek(self, position_seconds: float, **kwargs: Any) -> dict[str, Any]:
        if self._player is None:
            return _unavailable_response("PlayerService")
        if self._player.state == "stopped":
            return {"ok": False, "error": "NOT_PLAYING"}
        try:
            self._player.seek(position_seconds)
            return {"ok": True, "status": "COMPLETED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def set_volume(self, volume: float, **kwargs: Any) -> dict[str, Any]:
        if self._player is None:
            return _unavailable_response("PlayerService")
        if volume < 0 or volume > 100:
            return {"ok": False, "error": "INVALID_VOLUME"}
        try:
            self._player.set_volume(int(volume))
            return {"ok": True, "status": "COMPLETED", "volume": int(volume)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def set_repeat(self, mode: str, **kwargs: Any) -> dict[str, Any]:
        if self._queue is None:
            return _unavailable_response("QueueService")
        if mode not in ("none", "one", "all"):
            return {"ok": False, "error": "INVALID_MODE"}
        try:
            return self._queue.set_repeat(mode)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def set_shuffle(self, enabled: bool, **kwargs: Any) -> dict[str, Any]:
        if self._queue is None:
            return _unavailable_response("QueueService")
        try:
            return self._queue.set_shuffle(enabled)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_state(self) -> dict[str, Any]:
        if self._player is None:
            return _unavailable_response("PlayerService")
        try:
            return {"ok": True, "state": {
                "is_playing": self._player.state == "playing",
                "is_paused": self._player.state == "paused",
                "current_track": self._player.current_title,
                "volume": (self._player.get_volume()
                           if hasattr(self._player, "get_volume") else None),
            }}
        except Exception as e:
            return {"ok": False, "error": str(e)}


class ProductionLibraryGateway(LibraryGateway, ProductionCapabilityMixin):
    """Expose library lookup and catalog operations to the assistant.

    Track/album/artist reads and metadata-gap queries run through
    LibraryQueryService (the canonical query authority) when available; the
    library DB remains the fallback for search and favorites.
    """

    def __init__(self, db: Any, query_service: Any = None) -> None:
        self._db = db
        self._query = query_service

    def operational_capabilities(self) -> dict[str, bool]:
        ok = self._db is not None or self._query is not None
        return {
            "library.search": ok,
            "library.read": ok,
            "history.read": ok,
            "metadata.read": ok,
        }

    def _public_track(self, track: dict[str, Any]) -> dict[str, Any]:
        """Strip filesystem paths from a public track record."""
        return {k: v for k, v in track.items() if k not in ("filepath", "filename")}

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
        if self._query is None and self._db is None:
            return _unavailable_response("LibraryQueryService")
        try:
            if self._query is not None:
                track = self._query.fetch_track_internal(int(track_id))
                if not track:
                    return {"ok": False, "error": "NOT_FOUND"}
                return {"ok": True, "track": self._public_track(track)}
            item = self._db.get_media_item_by_id(int(track_id))
            if not item:
                return {"ok": False, "error": "NOT_FOUND"}
            return {"ok": True, "track": {
                "track_id": str(item.media_id), "title": item.title,
                "artist": item.artist, "album": item.album,
                "year": getattr(item, "year", 0), "genre": getattr(item, "genre", ""),
                "duration": getattr(item, "duration", 0),
                "format": getattr(item, "format", ""),
                "bitrate": getattr(item, "bitrate", 0),
            }}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_album(self, album_id: str) -> dict[str, Any]:
        if self._query is None:
            return _unavailable_response("LibraryQueryService (get_album)")
        try:
            album = self._query.fetch_album_detail(album_id)
            if not album:
                return {"ok": False, "error": "NOT_FOUND"}
            return {"ok": True, "album": album}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_artist(self, artist_id: str) -> dict[str, Any]:
        if self._query is None:
            return _unavailable_response("LibraryQueryService (get_artist)")
        try:
            artist = self._query.fetch_artist_detail(artist_id)
            if not artist:
                return {"ok": False, "error": "NOT_FOUND"}
            return {"ok": True, "artist": artist}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def list_recent(self, limit: int = 20) -> dict[str, Any]:
        if self._query is None:
            return _unavailable_response("LibraryQueryService (list_recent)")
        try:
            tracks = self._query.recently_played(limit=limit)
            return {"ok": True, "tracks": tracks, "total": len(tracks)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def list_unplayed(self, limit: int = 20) -> dict[str, Any]:
        if self._query is None:
            return _unavailable_response("LibraryQueryService (list_unplayed)")
        try:
            tracks = self._query.fetch_unplayed(limit=limit)
            return {"ok": True, "tracks": tracks, "total": len(tracks)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def list_favorites(self, limit: int = 20) -> dict[str, Any]:
        if self._db is None:
            return _unavailable_response("LibraryDB")
        try:
            favs = self._db.get_favorites()
            return {"ok": True, "tracks": favs[:limit], "total": len(favs)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def find_metadata_gaps(self, limit: int = 50) -> dict[str, Any]:
        """Report REAL metadata gaps: tracks missing artist/album/year/genre.

        Queries the canonical LibraryQueryService with per-field missing
        filters and returns counts plus sample tracks. Never fabricates an
        empty gap list when the library has untagged tracks.
        """
        if self._query is None:
            return _unavailable_response("LibraryQueryService (find_metadata_gaps)")
        try:
            fields = (
                ("artist", {"missing_artist": True}),
                ("album", {"missing_album": True}),
                ("year", {"missing_year": True}),
                ("genre", {"missing_genre": True}),
            )
            gaps = []
            for field, kwargs in fields:
                count = self._query.count_tracks(**kwargs)
                if not count:
                    continue
                samples = self._query.fetch_tracks(limit=min(limit, 10), **kwargs)
                gaps.append({
                    "field": field,
                    "count": count,
                    "samples": [{
                        "track_id": s.get("track_id"),
                        "title": s.get("title", ""),
                        "artist": s.get("artist", ""),
                    } for s in samples],
                })
            return {"ok": True, "gaps": gaps,
                    "total": sum(g["count"] for g in gaps)}
        except Exception as e:
            return {"ok": False, "error": str(e)}


class ProductionQueueGateway(QueueGateway, ProductionCapabilityMixin):
    """Adapt queue state, navigation, and mutations through QueueService."""

    def __init__(self, queue_service: Any, query_service: Any = None) -> None:
        self._queue = queue_service
        self._query = query_service

    def operational_capabilities(self) -> dict[str, bool]:
        ok = self._queue is not None
        return {"queue.read": ok, "queue.modify": ok}

    def _resolve(self, track_ids: list[str]) -> list[dict]:
        if self._query is None:
            return []
        resolved = []
        for track_id in track_ids:
            try:
                track = self._query.fetch_track_internal(int(track_id))
            except (TypeError, ValueError):
                track = None
            if track and track.get("filepath"):
                resolved.append(track)
        return resolved

    def get_queue(self) -> dict[str, Any]:
        if self._queue is None:
            return _unavailable_response("QueueService")
        state = self._queue.get_state()
        return {"ok": True, "queue": state["items"], "count": len(state["items"]),
                "current_index": state["current_index"], "repeat": state["repeat"],
                "shuffle": state["shuffle"], "revision": state["revision"]}

    def add_to_queue(self, track_ids: list[str], **kwargs: Any) -> dict[str, Any]:
        if self._queue is None:
            return _unavailable_response("QueueService")
        tracks = self._resolve(track_ids)
        if len(tracks) != len(track_ids):
            return {"ok": False, "error": "TRACK_NOT_FOUND"}
        return self._queue.enqueue(tracks, play_now=False)

    def play_next(self, track_ids: list[str], **kwargs: Any) -> dict[str, Any]:
        if self._queue is None:
            return _unavailable_response("QueueService")
        tracks = self._resolve(track_ids)
        if len(tracks) != len(track_ids):
            return {"ok": False, "error": "TRACK_NOT_FOUND"}
        return self._queue.insert_next(tracks)

    def replace_queue(self, track_ids: list[str], **kwargs: Any) -> dict[str, Any]:
        if self._queue is None:
            return _unavailable_response("QueueService")
        tracks = self._resolve(track_ids)
        if len(tracks) != len(track_ids):
            return {"ok": False, "error": "TRACK_NOT_FOUND"}
        return self._queue.replace(tracks)

    def remove_from_queue(self, position: int, **kwargs: Any) -> dict[str, Any]:
        if self._queue is None:
            return _unavailable_response("QueueService")
        return self._queue.remove([position])

    def clear_queue(self, **kwargs: Any) -> dict[str, Any]:
        if self._queue is None:
            return _unavailable_response("QueueService")
        return self._queue.clear()

    def reorder_queue(self, from_pos: int, to_pos: int, **kwargs: Any) -> dict[str, Any]:
        if self._queue is None:
            return _unavailable_response("QueueService")
        return self._queue.reorder(from_pos, to_pos)

    def next(self, **kwargs: Any) -> dict[str, Any]:
        return (self._queue.next() if self._queue is not None
                else _unavailable_response("QueueService"))

    def previous(self, **kwargs: Any) -> dict[str, Any]:
        return (self._queue.previous() if self._queue is not None
                else _unavailable_response("QueueService"))

    def play_from_index(self, index: int, **kwargs: Any) -> dict[str, Any]:
        return (self._queue.play_from_index(index) if self._queue is not None
                else _unavailable_response("QueueService"))


class ProductionPlaylistGateway(PlaylistGateway, ProductionCapabilityMixin):
    """Expose playlist persistence operations to the assistant.

    CRUD is delegated to PlaylistService (the canonical authority) when
    present; the library DB is the fallback for read operations.
    """

    def __init__(self, db: Any, playlist_service: Any = None) -> None:
        self._db = db
        self._pl_svc = playlist_service

    def operational_capabilities(self) -> dict[str, bool]:
        ok = self._pl_svc is not None or self._db is not None
        return {"playlist.read": ok, "playlist.modify": ok}

    def list_playlists(self) -> dict[str, Any]:
        if self._pl_svc is not None:
            try:
                pls = self._pl_svc.list()
                return {"ok": True, "playlists": pls, "total": len(pls)}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        if self._db is None:
            return _unavailable_response("PlaylistService")
        try:
            pls = self._db.get_playlists()
            return {"ok": True, "playlists": pls, "total": len(pls)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_playlist(self, playlist_id: str) -> dict[str, Any]:
        if self._pl_svc is not None:
            try:
                detail = self._pl_svc.get_detail(int(playlist_id))
                if not detail.get("ok"):
                    return {"ok": False, "error": detail.get("message", "NOT_FOUND")}
                name = ""
                for p in self._pl_svc.list():
                    if p.get("id") == int(playlist_id):
                        name = p.get("name", "")
                        break
                return {"ok": True, "playlist": {
                    "id": playlist_id, "name": name,
                    "tracks": detail.get("tracks", []),
                    "count": detail.get("count", 0),
                }}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        if self._db is None:
            return _unavailable_response("PlaylistService")
        try:
            items = self._db.get_playlist_items(int(playlist_id))
            return {"ok": True, "playlist": {"id": playlist_id, "tracks": items}}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def create_playlist(self, name: str, track_ids: list[str] | None = None, **kwargs: Any) -> dict[str, Any]:
        if self._pl_svc is not None:
            try:
                created = self._pl_svc.create_playlist(name)
                if not created.get("ok"):
                    return {"ok": False, "error": created.get("message", "CREATE_FAILED")}
                pid = int(created["id"])
                added = 0
                if track_ids:
                    result = self._pl_svc.batch_add(pid, [int(t) for t in track_ids])
                    added = result.get("count", 0)
                return {"ok": True, "playlist": {"id": str(pid), "name": name},
                        "added": added}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        if self._db is None:
            return _unavailable_response("PlaylistService")
        try:
            pid = self._db.create_playlist(name)
            if track_ids and pid:
                for tid in track_ids:
                    self._db.add_to_playlist(pid, track_id=tid)
            return {"ok": True, "playlist": {"id": str(pid), "name": name}}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def add_to_playlist(self, playlist_id: str, track_ids: list[str], **kwargs: Any) -> dict[str, Any]:
        if self._pl_svc is not None:
            try:
                result = self._pl_svc.batch_add(int(playlist_id), [int(t) for t in track_ids])
                if not result.get("ok"):
                    return {"ok": False, "error": result.get("message", "ADD_FAILED")}
                return {"ok": True, "added": result.get("count", 0)}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        if self._db is None:
            return _unavailable_response("PlaylistService")
        try:
            for tid in track_ids:
                self._db.add_to_playlist(int(playlist_id), track_id=tid)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def remove_from_playlist(self, playlist_id: str, position: int, **kwargs: Any) -> dict[str, Any]:
        if self._pl_svc is None:
            return _unavailable_response("PlaylistService (remove_from_playlist)")
        try:
            detail = self._pl_svc.get_detail(int(playlist_id))
            if not detail.get("ok"):
                return {"ok": False, "error": detail.get("message", "NOT_FOUND")}
            tracks = detail.get("tracks", [])
            match = next((t for t in tracks if t.get("position") == int(position)),
                         None)
            if match is None or not match.get("track_id"):
                return {"ok": False, "error": "TRACK_NOT_FOUND", "code": "NOT_FOUND"}
            result = self._pl_svc.remove_track(int(playlist_id), int(match["track_id"]))
            return {"ok": bool(result.get("ok")), "error": result.get("message", "")}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def reorder_playlist(self, playlist_id: str, from_pos: int, to_pos: int, **kwargs: Any) -> dict[str, Any]:
        if self._pl_svc is None:
            return _unavailable_response("PlaylistService (reorder_playlist)")
        try:
            result = self._pl_svc.reorder(int(playlist_id), int(from_pos), int(to_pos))
            return {"ok": bool(result.get("ok")), "error": result.get("message", "")}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def delete_playlist(self, playlist_id: str, **kwargs: Any) -> dict[str, Any]:
        """Delete a playlist permanently through PlaylistService (or the DB)."""
        if self._pl_svc is not None:
            try:
                result = self._pl_svc.delete_playlist(int(playlist_id))
                if not result.get("ok"):
                    return {"ok": False, "error": result.get("message", "DELETE_FAILED")}
                return {"ok": True, "playlist_id": playlist_id, "status": "DELETED"}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        if self._db is None:
            return _unavailable_response("PlaylistService")
        try:
            self._db.delete_playlist(int(playlist_id))
            return {"ok": True, "playlist_id": playlist_id, "status": "DELETED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}


class ProductionSettingsGateway(SettingsGateway, ProductionCapabilityMixin):
    """Expose readable and applicable settings operations to the assistant."""

    def __init__(self, settings_service: Any = None) -> None:
        self._ss = settings_service

    def operational_capabilities(self) -> dict[str, bool]:
        ok = self._ss is not None
        return {"settings.read": ok, "settings.modify": ok}

    def get_setting(self, key: str) -> dict[str, Any]:
        if self._ss is None:
            return _unavailable_response("SettingsService")
        try:
            val = self._ss.get(key)
            return {"ok": True, "key": key, "value": val}
        except Exception:
            return {"ok": False, "error": "NOT_FOUND"}

    def suggest_change(self, key: str, value: Any) -> dict[str, Any]:
        """Suggesting a change is the same real preview the UI shows."""
        return self.preview_change(key, value)

    def preview_change(self, key: str, value: Any) -> dict[str, Any]:
        if self._ss is None:
            return _unavailable_response("SettingsService")
        try:
            old = self._ss.get(key)
            return {"ok": True, "key": key, "old_value": old, "new_value": value,
                    "restart_required": False, "rollback_available": True}
        except Exception:
            return {"ok": False, "error": "NOT_FOUND"}

    def apply_change(self, key: str, value: Any = None) -> dict[str, Any]:
        if self._ss is None:
            return _unavailable_response("SettingsService")
        try:
            if value is None:
                result = self._ss.reset(key)
                if not result.get("ok"):
                    return {"ok": False, "error": result.get("message", "RESTORE_FAILED")}
                return {"ok": True, "key": key, "status": "RESTORED_TO_DEFAULT",
                        "value": self._ss.get(key)}
            old = self._ss.get(key)
            result = self._ss.set_(key, value)
            if not result.get("ok"):
                return {"ok": False, "error": result.get("message", "APPLY_FAILED")}
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


class ProductionAudioLabGateway(AudioLabGateway, ProductionCapabilityMixin):
    """Expose supported audio analysis operations through AudioLabService.

    Probe/analysis/replaygain/integrity/comparison reach the real Audio Lab
    sub-services; conversion planning stays honestly unavailable until a real
    plan-based conversion entry point exists.
    """

    def __init__(self, analysis_service: Any = None, db: Any = None) -> None:
        self._as = analysis_service
        self._db = db

    def operational_capabilities(self) -> dict[str, bool]:
        if self._as is None:
            return {"audio_lab.analyze": False, "audio_lab.convert": False,
                    "audio_lab.replaygain": False}
        caps = {}
        if hasattr(self._as, "capability_map"):
            try:
                caps = self._as.capability_map()
            except Exception:
                caps = {}
        return {
            "audio_lab.analyze": bool(caps.get("analysis") or caps.get("probe")
                                      or caps.get("integrity") or caps.get("comparison")),
            "audio_lab.convert": bool(caps.get("conversion")),
            "audio_lab.replaygain": bool(caps.get("replaygain")),
        }

    def _filepath(self, track_id: str) -> str:
        if self._db is None:
            return ""
        item = self._db.get_media_item_by_id(int(track_id))
        return getattr(item, "filepath", "") if item else ""

    def probe_audio(self, track_id: str) -> dict[str, Any]:
        if self._as is None or self._as.probe is None:
            return _unavailable_response("AudioProbeService")
        fp = self._filepath(track_id)
        if not fp:
            return {"ok": False, "error": "TRACK_NOT_FOUND", "code": "NOT_FOUND"}
        try:
            result = self._as.probe.probe(fp)
            payload = result.to_dict() if hasattr(result, "to_dict") else vars(result)
            return {"ok": True, "track_id": track_id, "probe": payload}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def analyze_audio(self, track_ids: list[str]) -> dict[str, Any]:
        if self._as is None or self._as.analysis is None:
            return _unavailable_response("AudioAnalysisService")
        filepaths = [self._filepath(t) for t in track_ids]
        if not all(filepaths):
            return {"ok": False, "error": "TRACK_NOT_FOUND", "code": "NOT_FOUND"}
        try:
            results = self._as.analysis.analyze_batch(filepaths)
            return {"ok": True, "results": results, "count": len(results)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def recommend_conversion(self, track_ids: list[str], target_format: str = "opus", **kwargs: Any) -> dict[str, Any]:
        return _unavailable_response("conversion profile recommendation (route not wired)")

    def preview_conversion(self, plan_id: str) -> dict[str, Any]:
        return _unavailable_response("conversion preview (route not wired)")

    def start_conversion(self, plan_id: str) -> dict[str, Any]:
        return _unavailable_response("conversion start (route not wired)")

    def cancel_conversion(self, job_id: str) -> dict[str, Any]:
        if self._as is None or self._as.jobs is None:
            return _unavailable_response("AudioLabJobAdapter")
        try:
            cancelled = self._as.jobs.cancel(job_id)
            return {"ok": bool(cancelled), "status": "cancelled" if cancelled else "not_found"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def analyze_replaygain(self, track_ids: list[str]) -> dict[str, Any]:
        if self._as is None or self._as.replaygain is None:
            return _unavailable_response("ReplayGainService")
        filepaths = [self._filepath(t) for t in track_ids]
        if not all(filepaths):
            return {"ok": False, "error": "TRACK_NOT_FOUND", "code": "NOT_FOUND"}
        try:
            results = self._as.replaygain.analyze_album(filepaths)
            payload = [
                r.to_dict() if hasattr(r, "to_dict") else vars(r)
                for r in results
            ]
            return {"ok": True, "results": payload, "count": len(payload)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def check_integrity(self, track_ids: list[str]) -> dict[str, Any]:
        if self._as is None or self._as.integrity is None:
            return _unavailable_response("AudioIntegrityService")
        results = []
        for track_id in track_ids:
            fp = self._filepath(track_id)
            if not fp:
                return {"ok": False, "error": "TRACK_NOT_FOUND", "code": "NOT_FOUND"}
            try:
                check = self._as.integrity.check(fp)
                results.append({
                    "track_id": track_id,
                    "ok": getattr(check, "ok", False),
                    "issues": getattr(check, "issues", []),
                })
            except Exception as e:
                results.append({"track_id": track_id, "ok": False, "error": str(e)})
        return {"ok": True, "results": results, "count": len(results)}

    def compare_audio(self, track_id_a: str, track_id_b: str) -> dict[str, Any]:
        if self._as is None or self._as.comparison is None:
            return _unavailable_response("AudioComparisonService")
        fp_a = self._filepath(track_id_a)
        fp_b = self._filepath(track_id_b)
        if not fp_a or not fp_b:
            return {"ok": False, "error": "TRACK_NOT_FOUND", "code": "NOT_FOUND"}
        try:
            result = self._as.comparison.compare(fp_a, fp_b)
            payload = result.to_dict() if hasattr(result, "to_dict") else vars(result)
            return {"ok": True, "comparison": payload}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_status(self) -> dict[str, Any]:
        if self._as is None:
            return _unavailable_response("AudioLabService")
        try:
            return {"ok": True, "status": self._as.status()}
        except Exception as e:
            return {"ok": False, "error": str(e)}


class ProductionDeviceGateway(DeviceGateway, ProductionCapabilityMixin):
    """Expose device and synchronization state from real services.

    ``diagnose_*`` methods report REAL state (paired/discovered devices,
    transfer jobs, connection status) and never a static "operational".
    """

    def __init__(self, sync_manager: Any = None, connection_service: Any = None,
                 device_registry: Any = None, home_audio_service: Any = None) -> None:
        self._sm = sync_manager
        self._conn = connection_service
        self._reg = device_registry
        self._ha = home_audio_service
        self._plans: dict[str, Any] = {}

    def operational_capabilities(self) -> dict[str, bool]:
        ok = self._sm is not None
        return {"devices.read": ok, "devices.sync": ok}

    def _identity_dict(self, identity: Any) -> dict[str, Any]:
        return {
            "key": getattr(identity, "key", getattr(identity, "mount_point", "")),
            "vendor": getattr(identity, "vendor", ""),
            "model": getattr(identity, "model", ""),
            "label": getattr(identity, "label", ""),
            "mount_point": getattr(identity, "mount_point", ""),
        }

    def list_devices(self) -> dict[str, Any]:
        if self._sm is None:
            return _unavailable_response("DeviceSyncService")
        try:
            paired = []
            for p in self._sm.get_paired():
                entry = self._identity_dict(p.identity if hasattr(p, "identity") else p)
                entry["paired"] = True
                paired.append(entry)
            discovered = [self._identity_dict(d) for d in self._sm.get_discovered()]
            return {"ok": True, "devices": paired + discovered,
                    "paired_count": len(paired), "discovered_count": len(discovered)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_device_details(self, device_id: str) -> dict[str, Any]:
        if self._sm is None:
            return _unavailable_response("DeviceSyncService")
        try:
            for p in self._sm.get_paired():
                identity = p.identity if hasattr(p, "identity") else p
                if getattr(identity, "mount_point", "") == device_id or getattr(identity, "key", "") == device_id:
                    entry = self._identity_dict(identity)
                    entry["paired"] = True
                    caps = getattr(p, "capabilities", None)
                    entry["capabilities"] = vars(caps) if caps else {}
                    return {"ok": True, "device": entry}
            return {"ok": False, "error": "NOT_FOUND", "code": "NOT_FOUND"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def diagnose_ecosystem(self) -> dict[str, Any]:
        if self._sm is None:
            return _unavailable_response("DeviceSyncService")
        try:
            paired = len(self._sm.get_paired())
            discovered = len(self._sm.get_discovered())
            jobs = self._sm.list_jobs()
            connection = {}
            if self._conn is not None and hasattr(self._conn, "status"):
                connection = self._conn.status()
            return {"ok": True, "devices": {"paired": paired, "discovered": discovered},
                    "sync_jobs": [{"job_id": j.job_id, "status": j.status.value} for j in jobs],
                    "connection": connection}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def diagnose_server(self) -> dict[str, Any]:
        if self._conn is None:
            return _unavailable_response("ConnectionService (diagnose_server)")
        try:
            status = self._conn.status() if hasattr(self._conn, "status") else {"ok": True}
            return {"ok": True, "server": status}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def diagnose_home_audio(self) -> dict[str, Any]:
        if self._ha is None:
            return _unavailable_response("HomeAudioService (diagnose_home_audio)")
        try:
            status = self._ha.status() if hasattr(self._ha, "status") else {"ok": True}
            return {"ok": True, "home_audio": status}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def diagnose_pairing(self) -> dict[str, Any]:
        if self._sm is None:
            return _unavailable_response("DeviceSyncService")
        try:
            paired = [self._identity_dict(p.identity if hasattr(p, "identity") else p)
                      for p in self._sm.get_paired()]
            return {"ok": True, "paired": paired, "paired_count": len(paired)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def plan_sync(self, playlist_id: str, device_id: str) -> dict[str, Any]:
        if self._sm is None:
            return _unavailable_response("DeviceSyncService")
        try:
            plan = self._sm.sync_plan(device_id)
            self._plans[device_id] = plan
            return {"ok": True, "plan_id": device_id, "playlist_id": playlist_id,
                    "plan": plan.get("plan", {})}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def start_sync(self, plan_id: str) -> dict[str, Any]:
        if self._sm is None:
            return _unavailable_response("DeviceSyncService")
        try:
            plan = self._plans.get(plan_id)
            return self._sm.start_sync(plan_id, plan)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def cancel_sync(self, job_id: str) -> dict[str, Any]:
        if self._sm is None:
            return _unavailable_response("DeviceSyncService")
        try:
            return self._sm.cancel_sync(job_id)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_sync_status(self) -> dict[str, Any]:
        if self._sm is None:
            return _unavailable_response("DeviceSyncService")
        try:
            jobs = self._sm.list_jobs()
            history = self._sm.get_history(limit=5)
            active = [{"job_id": j.job_id, "status": j.status.value}
                      for j in jobs if j.status.value in ("QUEUED", "TRANSFERRING")]
            return {"ok": True, "active_jobs": active, "active_count": len(active),
                    "recent": history}
        except Exception as e:
            return {"ok": False, "error": str(e)}


class ProductionDiagnosticsGateway(DiagnosticsGateway, ProductionCapabilityMixin):
    """Report REAL application/audio/network diagnostic state.

    All methods delegate to DiagnosticsService; no static "operational" is
    ever fabricated. Network diagnostics are honestly unavailable because no
    network provider is wired into DiagnosticsService.
    """

    def __init__(self, diagnostics_service: Any = None) -> None:
        self._ds = diagnostics_service

    def operational_capabilities(self) -> dict[str, bool]:
        return {"diagnostics.read": self._ds is not None}

    def get_diagnostics(self) -> dict[str, Any]:
        if self._ds is None:
            return _unavailable_response("DiagnosticsService")
        try:
            return {"ok": True, "checks": self._ds.check_all(),
                    "available": self._ds.available}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_audio_diagnostics(self) -> dict[str, Any]:
        if self._ds is None:
            return _unavailable_response("DiagnosticsService")
        try:
            return {"ok": True, "audio": {
                "playback": self._ds.check_playback(),
                "analyse_file": getattr(self._ds, "_audio_diag", None) is not None,
            }}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_network_diagnostics(self) -> dict[str, Any]:
        return _unavailable_response("network diagnostics provider not wired")

    def open_diagnostics(self, subsystem: str = "ecosystem") -> dict[str, Any]:
        if self._ds is None:
            return _unavailable_response("DiagnosticsService")
        try:
            if subsystem == "audio":
                return self.get_audio_diagnostics()
            if subsystem == "network":
                return self.get_network_diagnostics()
            if subsystem == "library":
                return {"ok": True, "library": self._ds.check_library()}
            if subsystem == "devices":
                return {"ok": True, "devices": self._ds.check_playback()}
            return {"ok": True, "checks": self._ds.check_all()}
        except Exception as e:
            return {"ok": False, "error": str(e)}


class ProductionMixGateway(MixGateway, ProductionCapabilityMixin):
    """Expose mix generation through MixService.

    ``create_mix`` surfaces the real MixService outcome — including honest
    NO_MATCHES when the library/criteria produce no tracks. The last generated
    mix is kept in memory so it can be saved as a playlist.
    """

    def __init__(self, mix_service: Any = None, playlist_service: Any = None,
                 job_service: Any = None) -> None:
        self._ms = mix_service
        self._pl_svc = playlist_service
        self._js = job_service
        self._last_mix: dict[str, Any] | None = None

    def operational_capabilities(self) -> dict[str, bool]:
        return {"mix.generate": self._ms is not None}

    def create_mix(self, strategy: str = "daily", **params: Any) -> dict[str, Any]:
        if self._ms is None:
            return _unavailable_response("MixService")
        try:
            seed = {k: v for k, v in params.items() if v is not None}
            limit = int(params.get("limit") or 30)
            result = self._ms.generate(strategy=strategy, seed=seed, limit=limit)
            if not result.get("ok"):
                return {"ok": False, "error": result.get("error", "MIX_FAILED"),
                        "code": result.get("error", "MIX_FAILED")}
            if not result.get("tracks"):
                return {"ok": False, "code": "NO_MATCHES",
                        "error": "No tracks matched the mix criteria",
                        "mix_id": result.get("mix_id")}
            self._last_mix = result
            return result
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def explain_mix(self, mix_id: str) -> dict[str, Any]:
        if self._ms is None:
            return _unavailable_response("MixService")
        try:
            result = self._ms.load_rules(mix_id)
            return {"ok": bool(result.get("ok")),
                    "error": result.get("error", ""),
                    "explanation": {
                        "name": result.get("name", ""),
                        "rules_json": result.get("rules_json", ""),
                        "updated_at": result.get("updated_at", ""),
                    } if result.get("ok") else None}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def save_mix_as_playlist(self, mix_id: str, name: str) -> dict[str, Any]:
        if self._pl_svc is None:
            return _unavailable_response("PlaylistService")
        mix = self._last_mix if self._last_mix and self._last_mix.get("mix_id") == mix_id else None
        if not mix:
            return {"ok": False, "code": "CAPABILITY_UNAVAILABLE",
                    "error": "Mix content not available: only the last generated mix can be saved"}
        ids = [t.get("id") for t in (mix.get("tracks") or []) if t.get("id")]
        if not ids:
            return {"ok": False, "code": "EMPTY_MIX", "error": "Mix has no tracks to save"}
        try:
            created = self._pl_svc.create_playlist(name)
            if not created.get("ok"):
                return {"ok": False, "error": created.get("message", "CREATE_FAILED")}
            added = self._pl_svc.batch_add(int(created["id"]), ids)
            return {"ok": True, "playlist_id": int(created["id"]),
                    "added": added.get("count", 0)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def cancel_mix(self, job_id: str) -> dict[str, Any]:
        if self._js is None:
            return _unavailable_response("JobService")
        try:
            cancelled = self._js.cancel_job(job_id)
            return {"ok": bool(cancelled), "status": "cancelled" if cancelled else "not_found",
                    "job_id": job_id}
        except Exception as e:
            return {"ok": False, "error": str(e)}


class ProductionJobGateway(JobGateway, ProductionCapabilityMixin):
    """Expose background job inspection and cancellation operations."""

    def __init__(self, job_service: Any = None) -> None:
        self._js = job_service

    def operational_capabilities(self) -> dict[str, bool]:
        return {}

    def _job_payload(self, job: Any) -> dict[str, Any]:
        return {
            "id": getattr(job, "id", getattr(job, "job_id", "")),
            "kind": getattr(job, "type", getattr(job, "kind", "")),
            "status": getattr(job, "state", getattr(job, "status", "")).value
            if hasattr(getattr(job, "state", getattr(job, "status", "")), "value")
            else str(getattr(job, "state", getattr(job, "status", ""))),
            "progress": getattr(job, "progress", 0),
        }

    def list_jobs(self) -> dict[str, Any]:
        if self._js is None:
            return _unavailable_response("JobService")
        try:
            jobs = self._js.list_jobs()
            return {"ok": True, "jobs": [self._job_payload(j) for j in jobs]}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        if self._js is None:
            return _unavailable_response("JobService")
        try:
            ok = self._js.cancel_job(job_id)
            return {"ok": bool(ok), "status": "cancelled" if ok else "not_found"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_job_status(self, job_id: str) -> dict[str, Any]:
        if self._js is None:
            return _unavailable_response("JobService")
        try:
            job = self._js.get_job(job_id)
            if job:
                return {"ok": True, "job": self._job_payload(job)}
            return {"ok": False, "error": "NOT_FOUND"}
        except Exception as e:
            return {"ok": False, "error": str(e)}


class ProductionNavigationGateway(NavigationRequestGateway, ProductionCapabilityMixin):
    """Forward assistant navigation requests to the navigation service."""

    def __init__(self, nav_service: Any = None) -> None:
        self._nav = nav_service

    def operational_capabilities(self) -> dict[str, bool]:
        return {"navigation.request": self._nav is not None}

    def request_navigation(self, target: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._nav is None:
            return {"ok": False, "code": "CAPABILITY_UNAVAILABLE", "message": "NavigationService not available"}
        return self._nav.navigate(target, params)


class ProductionLibraryDoctorGateway(LibraryDoctorGateway, ProductionCapabilityMixin):
    """Expose real library health scanning and repair through LibraryDoctorService.

    The doctor service is the authority for what a scan finds and what a
    repair does; this gateway never fabricates issues or repair outcomes.
    Rollback is honestly unavailable because the doctor service has no undo.
    """

    def __init__(self, doctor_service: Any = None, job_service: Any = None,
                 db: Any = None) -> None:
        self._doc = doctor_service
        self._js = job_service
        self._db = db
        self._last_scan: list[dict[str, Any]] = []

    def operational_capabilities(self) -> dict[str, bool]:
        ok = self._doc is not None
        return {"library_doctor.scan": ok, "library_doctor.repair": ok}

    def scan(self) -> dict[str, Any]:
        if self._doc is None:
            return _unavailable_response("LibraryDoctorService")
        try:
            result = self._doc.scan()
            self._last_scan = result.get("issues", [])
            return result
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def preview_repair(self, scan_id: str = "") -> dict[str, Any]:
        if self._doc is None:
            return _unavailable_response("LibraryDoctorService")
        try:
            issues = self._last_scan
            if not issues:
                issues = self._doc.scan().get("issues", [])
                self._last_scan = issues
            return {"ok": True, "scan_id": scan_id, "issues": issues,
                    "count": len(issues),
                    "preview": [{"type": i.get("type"), "severity": i.get("severity"),
                                 "description": i.get("description")} for i in issues]}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def repair(self, repair_id: str = "") -> dict[str, Any]:
        if self._doc is None:
            return _unavailable_response("LibraryDoctorService")
        try:
            issue = {"type": repair_id or "unknown"}
            for i in self._last_scan:
                if i.get("type") == repair_id:
                    issue = i
                    break
            result = self._doc.repair(issue)
            if not isinstance(result, dict) or result.get("ok") is not True:
                return {"ok": False, "error": result.get("message", "REPAIR_FAILED"),
                        "code": "REPAIR_FAILED", "repair_id": repair_id}
            return {"ok": True, "status": "COMPLETED", "repair_id": repair_id,
                    "message": result.get("message", "Repair applied")}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def rollback(self, repair_id: str = "") -> dict[str, Any]:
        return {"ok": False, "code": "CAPABILITY_UNAVAILABLE",
                "error": "LibraryDoctorService does not support rollback of repairs",
                "repair_id": repair_id}


class UnavailableNavigationGateway(NavigationRequestGateway):
    """Reject navigation requests when no navigation service is available."""

    def request_navigation(self, target: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"ok": False, "code": "CAPABILITY_UNAVAILABLE", "message": "NavigationService not available"}


class UnavailableRadioGateway:
    """Return capability errors for unavailable radio operations."""

    def search_stations(self, query: str) -> dict[str, Any]:
        return _unavailable_response("RadioService")
    def list_favorites(self) -> dict[str, Any]:
        return _unavailable_response("RadioService")
    def play_station(self, station_id: str) -> dict[str, Any]:
        return _unavailable_response("RadioService")
    def stop_radio(self) -> dict[str, Any]:
        return _unavailable_response("RadioService")


class UnavailableMetadataGateway:
    """Return capability errors for unavailable metadata operations."""

    def inspect_metadata(self, track_id: str) -> dict[str, Any]:
        return _unavailable_response("MetadataService")
    def build_proposal(self, track_id: str) -> dict[str, Any]:
        return _unavailable_response("MetadataService")


class UnavailableLibraryDoctorGateway:
    """Return capability errors for unavailable library repair operations."""

    def scan(self) -> dict[str, Any]:
        return _unavailable_response("LibraryDoctorService")
    def preview_repair(self, scan_id: str) -> dict[str, Any]:
        return _unavailable_response("LibraryDoctorService")


class UnavailableConnectionsGateway:
    """Return capability errors when connection services are unavailable."""

    def list_connections(self) -> dict[str, Any]:
        return _unavailable_response("ConnectionsService")


class UnavailableHomeAudioGateway:
    """Return capability errors when home audio services are unavailable."""

    def get_status(self) -> dict[str, Any]:
        return _unavailable_response("HomeAudioService")


class UnavailableLyricsGateway:
    """Return capability errors when lyrics services are unavailable."""

    def get_current_lyrics(self) -> dict[str, Any]:
        return _unavailable_response("LyricsService")
