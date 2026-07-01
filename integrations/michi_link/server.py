"""Michi Link API v1 — server-side request handler.

Mounted as a mixin on the existing SyncRequestHandler.
Routes are dispatched from /api/v1/ by MichiLinkRouter.
Official contract: https://github.com/pitydah/michi-link
"""
from __future__ import annotations

import json
import logging
import os
import secrets
import urllib.parse

from sync.sync_protocol import SessionToken, make_track_id, make_cover_id, make_device_id
from integrations.michi_link.models import (
    ServerInfo, PlaybackStateDto, QueueDto,
    V1PairStartResponse,
    V1PairConfirmRequest, V1PairConfirmResponse,
)
from integrations.michi_link.permissions import V1_ENDPOINT_PERMISSIONS

logger = logging.getLogger("michi.link.server")


def _v1_error(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def _send_v1_error(handler, code: str, message: str, status=400, details=None):
    handler._send_json(_v1_error(code, message, details), status)


class MichiLinkServer:
    """Mounts /api/v1/* routes by hooking into SyncRequestHandler.

    Usage:
        MichiLinkServer.mount(handler_class)
    Must be called once before SyncServer.start().
    """
    _playback: object | None = None
    _player_service: object | None = None
    _window_ref: object | None = None

    @classmethod
    def mount(cls, handler_class: type, playback=None, player_service=None, window=None):
        cls._playback = playback
        cls._player_service = player_service
        cls._window_ref = window
        V1_MIXIN._playback = playback
        V1_MIXIN._player_service = player_service
        V1_MIXIN._window_ref = window
        _orig_get = handler_class.do_GET
        _orig_post = handler_class.do_POST

        def do_get(self):
            if self.path.startswith("/api/v1/"):
                V1_MIXIN.handle_get(self)
                return
            _orig_get(self)

        def do_post(self):
            if self.path.startswith("/api/v1/"):
                V1_MIXIN.handle_post(self)
                return
            _orig_post(self)

        handler_class.do_GET = do_get
        handler_class.do_POST = do_post
        handler_class._v1_mixin = V1_MIXIN


class V1_MIXIN:
    _playback: object | None = None
    _player_service: object | None = None
    _window_ref: object | None = None

    @classmethod
    def _check_v1_permission(cls, handler, method: str, path: str) -> bool:
        route_key = f"{method}{path.rstrip('/')}"
        best = None
        for k, perm in V1_ENDPOINT_PERMISSIONS.items():
            if route_key.startswith(k):
                best = perm
                break
        if best:
            return handler._require_permission(best)
        return True

    # ── GET /api/v1/* ──

    @classmethod
    def handle_get(cls, handler):
        path = handler.path.split("?")[0].rstrip("/")
        srv = handler.server_ref

        # ── Public ──
        if path in ("/api/v1/server/info", "/api/v1/status"):
            has_account = bool(srv and srv._local_account and srv._local_account.exists())
            info = ServerInfo(name=srv._alias if srv else "Michi Music Player")
            d = info.to_dict()
            d["requires_pairing"] = has_account
            d["auth"]["required"] = has_account
            if path == "/api/v1/status":
                d["server_device_id"] = make_device_id()
                d["sync_active"] = srv.is_running if srv else False
                d["local_account"] = has_account
            handler._send_json(d)

        # ── Library ──
        elif path == "/api/v1/library/stats":
            if not cls._check_v1_permission(handler, "GET", path):
                return
            if srv is None or srv._db is None:
                return _send_v1_error(handler, "LIBRARY_UNAVAILABLE", "No library", 503)
            stats = srv._db.get_stats()
            handler._send_json(stats)

        elif path == "/api/v1/tracks":
            if not cls._check_v1_permission(handler, "GET", path):
                return
            if srv is None or srv._db is None:
                return _send_v1_error(handler, "LIBRARY_UNAVAILABLE", "No library", 503)
            items = srv._db.get_all()
            tracks = []
            for item in items:
                artist = item.artist or ""
                album_name = item.album or ""
                tuid = getattr(item, "track_uid", "") if hasattr(item, "track_uid") else ""
                tracks.append({
                    "track_id": make_track_id(item.filepath, tuid),
                    "title": item.title or item.filename,
                    "artist": artist,
                    "album": album_name,
                    "duration": float(item.duration or 0),
                    "format": str(getattr(item, "ext", "") or "").lstrip("."),
                    "cover_id": make_cover_id(album_name, artist),
                    "size": getattr(item, "size", 0),
                    "year": getattr(item, "year", 0),
                    "genre": str(getattr(item, "genre", "") or ""),
                    "download_path": f"/api/v1/stream/{make_track_id(item.filepath, tuid)}",
                })
            handler._send_json({"tracks": tracks, "total": len(tracks)})

        elif path == "/api/v1/search":
            if not cls._check_v1_permission(handler, "GET", path):
                return
            query = ""
            if "q=" in handler.path:
                query = handler.path.split("q=", 1)[1].split("&")[0]
                query = urllib.parse.unquote(query)
            if not query or srv is None or srv._db is None:
                handler._send_json({"results": [], "query": query})
                return
            items = srv._db.search_advanced(query) if hasattr(srv._db, "search_advanced") else []
            results = []
            for item in items[:50]:
                tuid = getattr(item, "track_uid", "") if hasattr(item, "track_uid") else ""
                results.append({
                    "track_id": make_track_id(item.filepath, tuid),
                    "title": item.title or item.filename,
                    "artist": item.artist or "",
                    "album": item.album or "",
                    "duration": float(item.duration or 0),
                    "download_path": f"/api/v1/stream/{make_track_id(item.filepath, tuid)}",
                })
            handler._send_json({"results": results, "query": query})

        # ── Sync manifest ──
        elif path == "/api/v1/sync/manifest":
            if not cls._check_v1_permission(handler, "GET", path):
                return
            if srv is None or srv._manifest_provider is None:
                return _send_v1_error(handler, "MANIFEST_UNAVAILABLE",
                                      "Manifest service not available", 503)
            qs = urllib.parse.parse_qs(
                handler.path.split("?")[1] if "?" in handler.path else "")
            device_id = (qs.get("device_id") or [""])[0]
            if not device_id:
                return _send_v1_error(handler, "MISSING_PARAM",
                                      "Missing device_id parameter", 400)
            manifest = srv._manifest_provider(device_id)
            if manifest is None:
                return _send_v1_error(handler, "NO_MANIFEST",
                                      "No manifest for this device", 404)
            handler._send_json(manifest)

        elif path == "/api/v1/sync/manifest/delta":
            if not cls._check_v1_permission(handler, "GET", path):
                return
            if srv is None or srv._delta_provider is None:
                return _send_v1_error(handler, "DELTA_UNAVAILABLE",
                                      "Delta manifest not available", 503)
            qs = urllib.parse.parse_qs(
                handler.path.split("?")[1] if "?" in handler.path else "")
            device_id = (qs.get("device_id") or [""])[0]
            if not device_id:
                return _send_v1_error(handler, "MISSING_PARAM",
                                      "Missing device_id parameter", 400)
            # Priority: cursor > since > manifest_id > 0
            cursor_str = (qs.get("cursor") or [""])[0]
            since_str = (qs.get("since") or [""])[0]
            manifest_id_str = (qs.get("manifest_id") or [""])[0]
            try:
                since = float(cursor_str or since_str or manifest_id_str or "0")
            except ValueError:
                since = 0.0
            delta = srv._delta_provider(device_id, since)
            if delta is None:
                return _send_v1_error(handler, "NO_DELTA",
                                      "No delta for this device", 404)
            # Add cursor to response if provider supports it
            if isinstance(delta, dict):
                delta.setdefault("cursor", str(since))
            handler._send_json(delta)

        # ── Playback ──
        elif path == "/api/v1/playback/state":
            if not cls._check_v1_permission(handler, "GET", path):
                return
            handler._send_json(cls._build_playback_state(srv))

        elif path == "/api/v1/queue":
            if not cls._check_v1_permission(handler, "GET", path):
                return
            handler._send_json(cls._build_queue(srv))

        # ── Stream & Artwork (explicit wrapper, no handler.path mutation) ──
        elif path.startswith("/api/v1/stream/"):
            if not cls._check_v1_permission(handler, "GET", "/api/v1/stream"):
                return
            if srv is None:
                return _send_v1_error(handler, "SERVER_NOT_READY", "Server not ready", 503)
            track_hash = path.split("/")[-1]
            filepath = srv._resolve_track(track_hash)
            if not filepath or not os.path.exists(filepath):
                return _send_v1_error(handler, "TRACK_NOT_FOUND", "Track not found", 404)
            # Stream the file directly with range support
            size = os.path.getsize(filepath)
            ext = os.path.splitext(filepath)[1].lower()
            mime_map = {
                ".mp3": "audio/mpeg", ".flac": "audio/flac",
                ".ogg": "audio/ogg", ".opus": "audio/ogg",
                ".wav": "audio/wav", ".m4a": "audio/mp4",
                ".aac": "audio/aac", ".wma": "audio/x-ms-wma",
                ".dsf": "audio/x-dsf", ".dff": "audio/x-dff",
            }
            content_type = mime_map.get(ext, "application/octet-stream")
            range_header = handler.headers.get("Range", "")
            if range_header.startswith("bytes="):
                start, end = 0, size - 1
                parts = range_header[6:].split("-")
                if parts[0]:
                    start = int(parts[0])
                if len(parts) > 1 and parts[1]:
                    end = min(int(parts[1]), size - 1)
                if end < start:
                    end = size - 1
                handler.send_response(206)
                handler.send_header("Content-Type", content_type)
                handler.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                handler.send_header("Content-Length", end - start + 1)
                handler.send_header("Accept-Ranges", "bytes")
                handler.send_header("Access-Control-Allow-Origin", "*")
                handler.end_headers()
                with open(filepath, "rb") as f:
                    f.seek(start)
                    remaining = end - start + 1
                    chunk = 65536
                    while remaining > 0:
                        data = f.read(min(chunk, remaining))
                        if not data:
                            break
                        handler.wfile.write(data)
                        remaining -= len(data)
            else:
                handler.send_response(200)
                handler.send_header("Content-Type", content_type)
                handler.send_header("Content-Length", size)
                handler.send_header("Accept-Ranges", "bytes")
                handler.send_header("Access-Control-Allow-Origin", "*")
                handler.end_headers()
                with open(filepath, "rb") as f:
                    while True:
                        data = f.read(65536)
                        if not data:
                            break
                        handler.wfile.write(data)

        elif path.startswith("/api/v1/artwork/"):
            if not cls._check_v1_permission(handler, "GET", "/api/v1/artwork"):
                return
            if srv is None or srv._db is None:
                return _send_v1_error(handler, "LIBRARY_UNAVAILABLE", "No library", 503)
            cover_hash = path.split("/")[-1]
            row = srv._db.conn.execute(
                "SELECT mime, data FROM album_art_cache WHERE album_hash=?",
                (cover_hash,)).fetchone()
            if row:
                handler.send_response(200)
                handler.send_header("Content-Type", row[0] or "image/jpeg")
                handler.send_header("Content-Length", len(row[1]))
                handler.send_header("Access-Control-Allow-Origin", "*")
                handler.send_header("Cache-Control", "public, max-age=86400")
                handler.end_headers()
                handler.wfile.write(row[1])
            else:
                _send_v1_error(handler, "ARTWORK_NOT_FOUND", "Cover not found", 404)

        # ── Playlists API ──
        elif path == "/api/v1/playlists/manifest/delta":
            if not cls._check_v1_permission(handler, "GET", path):
                return
            cls._handle_playlist_delta(handler, srv)

        elif path == "/api/v1/playlists/manifest":
            if not cls._check_v1_permission(handler, "GET", path):
                return
            cls._handle_playlist_manifest(handler, srv)

        elif path == "/api/v1/playlists":
            if not cls._check_v1_permission(handler, "GET", path):
                return
            cls._handle_get_playlists(handler, srv)

        elif path.startswith("/api/v1/playlists/") and path.endswith("/tracks"):
            if not cls._check_v1_permission(handler, "GET", "/api/v1/playlists"):
                return
            cls._handle_get_playlist_tracks(handler, srv)

        elif path.startswith("/api/v1/playlists/"):
            if not cls._check_v1_permission(handler, "GET", "/api/v1/playlists"):
                return
            cls._handle_get_playlist(handler, srv)

        # ── Events (SSE not implemented) ──
        elif path == "/api/v1/events":
            _send_v1_error(handler, "NOT_IMPLEMENTED",
                           "SSE events are not implemented by this server.",
                           501)

        else:
            _send_v1_error(handler, "NOT_FOUND", "Not found", 404)

    # ── POST /api/v1/* ──

    @classmethod
    def handle_post(cls, handler):
        path = handler.path.split("?")[0].rstrip("/")
        body = handler._read_body()
        srv = handler.server_ref

        if path == "/api/v1/pair/start":
            cls._handle_pair_start(handler, srv)
        elif path == "/api/v1/pair/confirm":
            cls._handle_pair_confirm(handler, srv, body)
        elif path == "/api/v1/sync/state":
            if not cls._check_v1_permission(handler, "POST", path):
                return
            cls._handle_sync_state(handler, srv, body)
        elif path == "/api/v1/playback/control":
            if not cls._check_v1_permission(handler, "POST", path):
                return
            cls._handle_control(handler, body)
        elif path == "/api/v1/queue/jump":
            if not cls._check_v1_permission(handler, "POST", path):
                return
            cls._handle_queue_jump(handler, body)
        elif path == "/api/v1/queue/items":
            if not cls._check_v1_permission(handler, "POST", path):
                return
            cls._handle_queue_items(handler, body, srv)
        elif path == "/api/v1/queue/transfer":
            if not cls._check_v1_permission(handler, "POST", path):
                return
            cls._handle_queue_transfer(handler, body, srv)
        elif path == "/api/v1/playlists":
            if not cls._check_v1_permission(handler, "POST", path):
                return
            cls._handle_create_playlist(handler, srv, body)
        elif path.startswith("/api/v1/playlists/") and path.endswith("/tracks"):
            if not cls._check_v1_permission(handler, "POST", "/api/v1/playlists"):
                return
            cls._handle_add_playlist_tracks(handler, srv, body, path)
        elif path.startswith("/api/v1/playlists/") and path.endswith("/reorder"):
            if not cls._check_v1_permission(handler, "POST", "/api/v1/playlists"):
                return
            cls._handle_reorder_playlist(handler, srv, body, path)
        elif path.startswith("/api/v1/playlists/"):
            if not cls._check_v1_permission(handler, "DELETE", "/api/v1/playlists"):
                return
            cls._handle_delete_playlist(handler, srv, path)
        elif path == "/api/v1/token/refresh":
            _send_v1_error(handler, "NOT_IMPLEMENTED",
                           "Token refresh is not implemented by this server.", 501)
        else:
            _send_v1_error(handler, "NOT_FOUND", "Not found", 404)

    # ── Pair handlers ──

    @classmethod
    def _handle_pair_start(cls, handler, srv):
        has_account = bool(srv and srv._local_account and srv._local_account.exists())
        server_alias = srv._alias if srv else "Michi Music Player"
        resp = V1PairStartResponse(
            pairing_id=secrets.token_hex(8),
            auth_methods=["password"] if has_account else [],
            server_alias=server_alias,
            auth_required=has_account,
            server_device_id=make_device_id(),
        )
        handler._send_json(json.loads(resp.to_json()))

    @classmethod
    def _handle_pair_confirm(cls, handler, srv, body):
        client_ip = handler.client_address[0]
        if not handler._check_rate_limit(client_ip):
            return _send_v1_error(handler, "RATE_LIMITED",
                                  "Too many attempts, try later", 429)
        try:
            req = V1PairConfirmRequest.from_json(body)
        except Exception:
            return _send_v1_error(handler, "INVALID_REQUEST", "Invalid request", 400)
        if srv is None:
            return _send_v1_error(handler, "SERVER_NOT_READY", "Server not ready", 503)
        client_id = req.client_device_id
        if not client_id:
            handler._send_json(json.loads(V1PairConfirmResponse(
                success=False, error="Missing client_device_id").to_json()))
            return
        acct_exists = bool(srv._local_account and srv._local_account.exists())
        if acct_exists and (
            not req.username or not req.password or
            req.username != srv._local_account.get_username() or
            not srv._local_account.verify(req.password)
        ):
            handler._record_failed_attempt(client_ip)
            logger.warning("Pairing failed (v1): invalid credentials from %s (user=%s)",
                           client_ip, req.username)
            handler._send_json(json.loads(V1PairConfirmResponse(
                success=False, error="Invalid credentials").to_json()))
            return
        registry = srv._device_registry
        if registry and not registry.get(client_id):
            registry.register(
                device_id=client_id,
                name=req.alias or client_id,
                host=client_ip,
                port=req.port or 0,
                device_type="android",
                device_model=req.device_model,
                client_version=req.client_version,
            )
        token_str = secrets.token_hex(32)
        server_id = make_device_id()
        if registry:
            registry.set_token(client_id, token_str)
        session = SessionToken(
            token=token_str, device_alias=client_id, client_device_id=client_id,
        )
        with srv._sessions_lock:
            srv._sessions[token_str] = session
        default_perms = [
            "library.read", "stream.read", "artwork.read",
            "sync.read_manifest", "sync.upload_state",
            "playback.read", "playback.control",
            "queue.read", "queue.write",
            "playlist.read", "playlist.write",
        ]
        resp = V1PairConfirmResponse(
            success=True, device_id=client_id, device_token=token_str,
            permissions=default_perms, server_device_id=server_id,
            server_alias=srv._alias if srv else "Michi Music Player",
        )
        if srv:
            srv.client_connected.emit(client_id)
        handler._send_json(json.loads(resp.to_json()))

    # ── Sync state ──

    @classmethod
    def _handle_sync_state(cls, handler, srv, body):
        if srv is None:
            return _send_v1_error(handler, "SERVER_NOT_READY", "Server not ready", 503)
        try:
            data = json.loads(body)
        except Exception:
            return _send_v1_error(handler, "INVALID_JSON", "Invalid JSON", 400)
        device_alias = handler._check_token() or "unknown"
        synced = 0
        for entry in data.get("tracks", []):
            tid = entry.get("track_id", "")
            play_count = entry.get("play_count", 0)
            favorite = entry.get("favorite", False)
            if srv._db:
                filepath = srv._resolve_track(tid)
                if filepath:
                    if play_count > 0:
                        for _ in range(play_count):
                            srv._db.update_play_history(tid, device_alias)
                    if favorite:
                        srv._db.toggle_favorite(tid, device_alias)
                    synced += 1
        handler._send_json({"synced": synced})

    # ── Playback state builder ──

    @classmethod
    def _build_playback_state(cls, srv) -> dict:
        ps = cls._player_service
        pb = cls._playback
        state = "stopped"
        current_track = None
        position_ms = 0.0
        duration_ms = 0.0
        volume = 70
        shuffle = False
        repeat = "none"

        if ps:
            st = getattr(ps, "state", None)
            if st is not None:
                st_name = getattr(st, "name", "").lower()
                if st_name == "playing":
                    state = "playing"
                elif st_name == "paused":
                    state = "paused"
            position_ms = getattr(ps, "position", 0.0) * 1000.0 if hasattr(ps, "position") else 0.0
            duration_ms = getattr(ps, "duration", 0.0) * 1000.0
            current_fp = getattr(ps, "current", "")
            if current_fp and srv and srv._db:
                items = srv._db.get_all()
                for item in items:
                    if item.filepath == current_fp:
                        tuid = getattr(item, "track_uid", "") if hasattr(item, "track_uid") else ""
                        current_track = {
                            "track_id": make_track_id(current_fp, tuid),
                            "title": item.title or item.filename,
                            "artist": item.artist or "",
                            "album": item.album or "",
                            "duration": float(item.duration or 0),
                            "cover_id": make_cover_id(item.album or "", item.artist or ""),
                        }
                        break

        if pb:
            # Use public API where possible
            volume = getattr(pb, 'volume', None)
            if volume is not None:
                volume = int(volume * 100) if isinstance(volume, float) else int(volume)
            shuffle = getattr(pb, 'shuffle', False) if hasattr(pb, 'shuffle') else shuffle
            repeat = getattr(pb, 'repeat', 'none') if hasattr(pb, 'repeat') else repeat

        return PlaybackStateDto(
            state=state, current_track=current_track,
            position_ms=position_ms, duration_ms=duration_ms,
            volume=volume, shuffle=shuffle, repeat=repeat,
        ).to_dict()

    @classmethod
    def _build_queue(cls, srv) -> dict:
        ps = cls._player_service
        pb = cls._playback
        tracks = []
        current_index = -1

        if ps:
            queue_data = ps.get_queue()
            if queue_data:
                for q in queue_data:
                    fp = q.get("filepath", "")
                    title = q.get("title", "")
                    artist = q.get("artist", "")
                    album = q.get("album", "")
                    tuid = q.get("track_uid", "")
                    tracks.append({
                        "track_id": make_track_id(fp, tuid),
                        "title": title,
                        "artist": artist,
                        "album": album,
                        "download_path": f"/api/v1/stream/{make_track_id(fp, tuid)}",
                    })
            try:
                current_index = pb.get_queue_index() if pb else -1
            except Exception:
                current_index = -1

        return QueueDto(
            tracks=tracks, current_index=current_index,
        ).to_dict()

    # ── Playback control ──

    @classmethod
    def _handle_control(cls, handler, body):
        ps = cls._player_service
        pb = cls._playback
        if not ps and not pb:
            return _send_v1_error(handler, "PLAYBACK_UNAVAILABLE",
                                  "Playback service not available", 503)
        try:
            data = json.loads(body)
        except Exception:
            return _send_v1_error(handler, "INVALID_JSON", "Invalid JSON", 400)

        # Official field is "command", fallback to "action" for legacy compat
        action = data.get("command", data.get("action", ""))

        if action in ("play", "resume"):
            if ps and hasattr(ps, "play_or_resume"):
                ps.play_or_resume()
            elif pb and hasattr(pb, "play_or_resume"):
                pb.play_or_resume()

        elif action == "pause":
            if ps and hasattr(ps, "pause"):
                ps.pause()

        elif action == "toggle":
            if ps and hasattr(ps, "toggle"):
                ps.toggle()
            elif pb and hasattr(pb, "toggle"):
                pb.toggle()
            elif ps:
                from audio.player import PlaybackState
                st = getattr(ps, "state", None)
                if st == PlaybackState.PLAYING:
                    ps.pause()
                else:
                    ps.play_or_resume()

        elif action in ("next", "skip"):
            if ps and hasattr(ps, "play_next"):
                ps.play_next()

        elif action in ("previous", "prev"):
            if ps and hasattr(ps, "play_prev"):
                ps.play_prev()

        elif action == "stop":
            if ps and hasattr(ps, "stop"):
                ps.stop()

        elif action == "seek":
            seek_ms = float(data.get("position_ms", data.get("seek_ms", data.get("value", 0))))
            if ps and hasattr(ps, "seek"):
                ps.seek(seek_ms / 1000.0)

        elif action == "set_volume":
            vol = int(data.get("volume", data.get("value", 70)))
            vol = max(0, min(100, vol))
            if ps and hasattr(ps, "set_volume"):
                ps.set_volume(vol)

        elif action == "mute":
            if ps:
                ps.set_volume(0)

        elif action == "unmute":
            if ps and hasattr(ps, "set_volume"):
                ps.set_volume(70)

        elif action == "shuffle":
            if pb and hasattr(pb, "toggle_shuffle"):
                pb.toggle_shuffle()

        elif action == "repeat":
            if pb and hasattr(pb, "toggle_repeat"):
                pb.toggle_repeat()

        else:
            return _send_v1_error(handler, "UNKNOWN_COMMAND",
                                  f"Unknown command: {action}", 400)

        handler._send_json({"status": "ok", "command": action})

    # ── Queue ──

    @classmethod
    def _handle_queue_jump(cls, handler, body):
        ps = cls._player_service
        pb = cls._playback
        if not ps and not pb:
            return _send_v1_error(handler, "PLAYBACK_UNAVAILABLE",
                                  "Playback service not available", 503)
        try:
            data = json.loads(body)
        except Exception:
            return _send_v1_error(handler, "INVALID_JSON", "Invalid JSON", 400)
        index = int(data.get("index", -1))
        if index < 0:
            return _send_v1_error(handler, "INVALID_INDEX", "Invalid index", 400)
        try:
            if ps and hasattr(ps, "play_queue"):
                queue, _ = ps.get_queue_state()
                ps.play_queue(queue, start_index=index)
            elif pb and hasattr(pb, "play_queue"):
                queue, _ = pb.get_queue_state()
                pb.play_queue(queue, start_index=index)
        except Exception as e:
            logger.warning("Queue jump failed: %s", e)
            return _send_v1_error(handler, "JUMP_FAILED", "Jump failed", 500)
        handler._send_json({"status": "ok", "index": index})

    @classmethod
    def _handle_queue_items(cls, handler, body, srv):
        ps = cls._player_service
        if not ps:
            return _send_v1_error(handler, "PLAYBACK_UNAVAILABLE",
                                  "Playback service not available", 503)
        try:
            data = json.loads(body)
        except Exception:
            return _send_v1_error(handler, "INVALID_JSON", "Invalid JSON", 400)
        uris = data.get("uris", data.get("track_ids", []))
        if not uris:
            return _send_v1_error(handler, "NO_URIS", "No uris or track_ids provided", 400)
        filepaths = []
        for uri in uris:
            fp = srv._resolve_track(uri) if srv else None
            if fp:
                filepaths.append(fp)
        if filepaths:
            ps.enqueue(filepaths, play_now=data.get("play_now", False))
        handler._send_json({"added": len(filepaths)})

    @classmethod
    def _handle_queue_transfer(cls, handler, body, srv):
        ps = cls._player_service
        pb = cls._playback
        if not ps:
            return _send_v1_error(handler, "PLAYBACK_UNAVAILABLE", "Playback service not available", 503)
        try:
            data = json.loads(body)
        except Exception:
            return _send_v1_error(handler, "INVALID_JSON", "Invalid JSON", 400)
        uris = data.get("queue", data.get("uris", data.get("track_ids", [])))
        position_ms = data.get("position_ms", 0)
        if not uris:
            return _send_v1_error(handler, "NO_QUEUE", "No queue provided", 400)
        filepaths = []
        for uri in uris:
            track_id = uri if isinstance(uri, (int, str)) else uri.get("track_id", "")
            fp = srv._resolve_track(track_id) if srv else None
            if fp:
                filepaths.append(fp)
        if filepaths:
            ps.enqueue(filepaths, play_now=False)
        if position_ms > 0:
            import contextlib
            with contextlib.suppress(Exception):
                ps.seek(position_ms / 1000.0)
        if pb and hasattr(pb, "play_or_resume"):
            pb.play_or_resume()
        elif ps and hasattr(ps, "play_or_resume"):
            ps.play_or_resume()
        handler._send_json({"ok": True, "transferred": len(filepaths), "playback_started": True})

    # ── Playlist API handlers ──

    @staticmethod
    def _extract_playlist_id(path: str):
        parts = path.rstrip("/").split("/")
        for i, p in enumerate(parts):
            if p == "playlists" and i + 1 < len(parts):
                try:
                    return int(parts[i + 1])
                except (ValueError, IndexError):
                    return None
        return None

    @staticmethod
    def _get_store(srv):
        if srv is None or srv._db is None:
            return None
        try:
            from library.playlists.playlist_store import PlaylistStore
            conn = srv._db.conn if hasattr(srv._db, 'conn') else None
            if conn is None and hasattr(srv._db, '_conn'):
                conn = srv._db._conn
            return PlaylistStore(conn) if conn else None
        except Exception:
            return None

    @classmethod
    def _handle_get_playlists(cls, handler, srv):
        store = cls._get_store(srv)
        if store is None:
            return _send_v1_error(handler, "LIBRARY_UNAVAILABLE", "No library", 503)
        summaries = store.get_all_playlists(include_stats=True)
        result = []
        for s in summaries:
            result.append({
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "track_count": s.track_count,
                "duration": s.total_duration,
                "is_smart": s.is_smart,
                "is_locked": s.is_locked,
                "cover_id": f"pl_{s.id}",
                "updated_at": s.updated_at,
                "health_score": s.health_score,
                "sync_version": s.sync_version,
            })
        handler._send_json({"playlists": result, "total": len(result)})

    @classmethod
    def _handle_get_playlist(cls, handler, srv, path):
        store = cls._get_store(srv)
        if store is None:
            return _send_v1_error(handler, "LIBRARY_UNAVAILABLE", "No library", 503)
        pid = cls._extract_playlist_id(path)
        if pid is None:
            return _send_v1_error(handler, "INVALID_ID", "Invalid playlist id", 400)
        pl = store.get_playlist(pid)
        if pl is None:
            return _send_v1_error(handler, "PLAYLIST_NOT_FOUND", "Playlist not found", 404)
        summary = store.get_summary(pid)
        handler._send_json({
            "id": pl["id"],
            "name": pl["name"],
            "description": pl.get("description", ""),
            "cover_path": pl.get("cover_path", ""),
            "cover_type": pl.get("cover_type", "none"),
            "is_smart": bool(pl.get("is_smart", 0)),
            "is_locked": bool(pl.get("locked", 0)),
            "track_count": summary.track_count,
            "duration": summary.total_duration,
            "created_at": pl.get("created_at", 0),
            "updated_at": pl.get("updated_at", 0),
            "health_score": pl.get("health_score", 100),
        })

    @classmethod
    def _handle_get_playlist_tracks(cls, handler, srv, path):
        store = cls._get_store(srv)
        if store is None:
            return _send_v1_error(handler, "LIBRARY_UNAVAILABLE", "No library", 503)
        pid = cls._extract_playlist_id(path)
        if pid is None:
            return _send_v1_error(handler, "INVALID_ID", "Invalid playlist id", 400)
        tracks = store.get_playlist_items(pid)
        result = []
        for t in tracks:
            entry = {
                "position": t.position,
                "track_id": t.track_id,
                "title": t.title,
                "artist": t.artist,
                "album": t.album,
                "duration": t.duration,
                "ext": t.ext,
                "quality": t.quality_kind,
            }
            result.append(entry)
        handler._send_json({"tracks": result, "total": len(result)})

    @classmethod
    def _handle_create_playlist(cls, handler, srv, body):
        store = cls._get_store(srv)
        if store is None:
            return _send_v1_error(handler, "LIBRARY_UNAVAILABLE", "No library", 503)
        try:
            data = json.loads(body)
        except Exception:
            return _send_v1_error(handler, "INVALID_JSON", "Invalid JSON", 400)
        name = data.get("name", "").strip()
        if not name:
            return _send_v1_error(handler, "MISSING_NAME", "Playlist name required", 400)
        pid = store.create_playlist(
            name,
            description=data.get("description", ""),
            is_smart=bool(data.get("is_smart", False)),
            rules_json=data.get("rules_json", ""),
        )
        handler._send_json({"status": "ok", "id": pid, "name": name}, 201)

    @classmethod
    def _handle_add_playlist_tracks(cls, handler, srv, body, path):
        store = cls._get_store(srv)
        if store is None:
            return _send_v1_error(handler, "LIBRARY_UNAVAILABLE", "No library", 503)
        pid = cls._extract_playlist_id(path)
        if pid is None:
            return _send_v1_error(handler, "INVALID_ID", "Invalid playlist id", 400)
        try:
            data = json.loads(body)
        except Exception:
            return _send_v1_error(handler, "INVALID_JSON", "Invalid JSON", 400)
        track_ids = data.get("track_ids", data.get("tracks", []))
        if not track_ids:
            return _send_v1_error(handler, "NO_TRACKS", "No tracks provided", 400)
        added = 0
        for tid in track_ids:
            if isinstance(tid, dict):
                fp = tid.get("filepath", "")
                track_id = tid.get("track_id", 0)
            else:
                fp = str(tid)
                track_id = 0
            if track_id and srv and srv._db:
                row = srv._db.conn.execute(
                    "SELECT filepath FROM media_items WHERE id=?", (track_id,)
                ).fetchone()
                if row:
                    fp = row[0]
            if fp:
                store.add_track(pid, filepath=fp, source="api")
                added += 1
        handler._send_json({"status": "ok", "added": added})

    @classmethod
    def _handle_reorder_playlist(cls, handler, srv, body, path):
        store = cls._get_store(srv)
        if store is None:
            return _send_v1_error(handler, "LIBRARY_UNAVAILABLE", "No library", 503)
        pid = cls._extract_playlist_id(path)
        if pid is None:
            return _send_v1_error(handler, "INVALID_ID", "Invalid playlist id", 400)
        try:
            data = json.loads(body)
        except Exception:
            return _send_v1_error(handler, "INVALID_JSON", "Invalid JSON", 400)
        order = data.get("track_ids", data.get("order", []))
        if not order:
            return _send_v1_error(handler, "NO_ORDER", "No track_ids provided", 400)
        if isinstance(order[0], int):
            store.set_playlist_order(pid, ordered_track_ids=order)
        else:
            store.set_playlist_order(pid, ordered_filepaths=order)
        handler._send_json({"status": "ok", "reordered": len(order)})

    @classmethod
    def _handle_delete_playlist(cls, handler, srv, path):
        store = cls._get_store(srv)
        if store is None:
            return _send_v1_error(handler, "LIBRARY_UNAVAILABLE", "No library", 503)
        pid = cls._extract_playlist_id(path)
        if pid is None:
            return _send_v1_error(handler, "INVALID_ID", "Invalid playlist id", 400)
        store.delete_playlist(pid)
        handler._send_json({"status": "ok", "deleted": pid})

    @classmethod
    def _handle_playlist_manifest(cls, handler, srv):
        store = cls._get_store(srv)
        if store is None:
            return _send_v1_error(handler, "LIBRARY_UNAVAILABLE", "No library", 503)
        from library.playlists.playlist_sync_manifest import build_manifest, serialize_manifest_safe
        conn = srv._db.conn if hasattr(srv._db, 'conn') else getattr(srv._db, '_conn', None)
        if conn is None:
            return _send_v1_error(handler, "DB_UNAVAILABLE", "Database not available", 503)
        manifest = build_manifest(store, conn, device_id="michi-link")
        safe = serialize_manifest_safe(manifest)
        handler._send_json(safe)

    @classmethod
    def _handle_playlist_delta(cls, handler, srv):
        store = cls._get_store(srv)
        if store is None:
            return _send_v1_error(handler, "LIBRARY_UNAVAILABLE", "No library", 503)
        qs = urllib.parse.parse_qs(
            handler.path.split("?")[1] if "?" in handler.path else "")
        since_str = (qs.get("since") or [""])[0]
        try:
            since = float(since_str) if since_str else 0.0
        except ValueError:
            since = 0.0
        from library.playlists.playlist_sync_manifest import build_delta
        conn = srv._db.conn if hasattr(srv._db, 'conn') else getattr(srv._db, '_conn', None)
        if conn is None:
            return _send_v1_error(handler, "DB_UNAVAILABLE", "Database not available", 503)
        delta = build_delta(store, conn, since=since, device_id="michi-link")
        handler._send_json(delta)
