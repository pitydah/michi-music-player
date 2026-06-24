"""HTTP REST API server for wireless music sync.

Inspired by LocalSend's hyper server architecture (Rust).
Uses Python stdlib http.server + ThreadPoolExecutor for concurrent requests.

Endpoints:
    POST /api/register        Device handshake → session token
    GET  /api/library          Full library JSON
    GET  /api/stream/{id}     Range-request audio streaming
    GET  /api/cover/{id}      Album art image
    POST /api/sync/state      Play counts & favorites
    GET  /api/ping            Health check
    GET  /api/search?q=X      Search library
"""

import os
import json
import logging
import threading
import hashlib
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from concurrent.futures import ThreadPoolExecutor

from sync.sync_protocol import (
    SessionToken, TrackDto, LibraryResponse,
    RegisterRequest, RegisterResponse,
    SyncStateRequest, make_track_id, make_device_id,
)
from library.library_db import LibraryDB
from PySide6.QtCore import QObject, Signal


class SyncRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for sync API."""
    server_ref = None  # reference to SyncServer instance

    def log_message(self, format, *args):
        pass  # suppress logs

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8") if isinstance(data, dict) else data.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, msg: str, status=400):
        self._send_json({"error": msg}, status)

    def _read_body(self) -> str:
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length).decode("utf-8") if length else ""

    def _check_token(self) -> str | None:
        """Check Authorization header. Returns device_alias or None."""
        session = self._check_token_session()
        return session.device_alias if session else None

    def _check_token_session(self) -> "SessionToken | None":
        """Check Authorization header. Returns full SessionToken or None."""
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        token = auth[7:]
        srv = self.server_ref
        if srv is None:
            return None
        session = srv._sessions.get(token)
        if session is None or session.is_expired():
            return None
        return session

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, Range")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        srv = self.server_ref

        if path == "/api/ping":
            self._send_json({"status": "ok", "version": "1.0"})

        elif path == "/api/sync/manifest":
            session = self._check_token_session()
            if not session:
                return self._send_error("Unauthorized", 401)
            if srv is None or srv._manifest_provider is None:
                return self._send_error("Manifest service not available", 503)
            qs = urllib.parse.parse_qs(
                self.path.split("?")[1] if "?" in self.path else "")
            device_id = (qs.get("device_id") or [""])[0]
            if not device_id:
                return self._send_error("Missing device_id parameter", 400)
            if session.client_device_id and device_id != session.client_device_id:
                return self._send_error("Forbidden: token does not match device_id", 403)
            manifest = srv._manifest_provider(device_id)
            if manifest is None:
                return self._send_error("No manifest for this device", 404)
            self._send_json(manifest)

        elif path == "/api/sync/manifest/delta":
            session = self._check_token_session()
            if not session:
                return self._send_error("Unauthorized", 401)
            if srv is None or srv._delta_provider is None:
                return self._send_error("Delta manifest not available", 503)
            qs = urllib.parse.parse_qs(
                self.path.split("?")[1] if "?" in self.path else "")
            device_id = (qs.get("device_id") or [""])[0]
            since_str = (qs.get("since") or ["0"])[0]
            if not device_id:
                return self._send_error("Missing device_id parameter", 400)
            if session.client_device_id and device_id != session.client_device_id:
                return self._send_error("Forbidden: token does not match device_id", 403)
            try:
                since = float(since_str)
            except ValueError:
                logging.getLogger("michi.sync").warning(
                    "Invalid since parameter in delta manifest: %r", since_str)
                since = 0.0
            delta = srv._delta_provider(device_id, since)
            if delta is None:
                return self._send_error("No delta for this device", 404)
            self._send_json(delta)

        elif path == "/api/library":
            if not self._check_token():
                return self._send_error("Unauthorized", 401)
            if srv is None or srv._db is None:
                return self._send_error("No library", 503)
            items = srv._db.get_all()
            tracks = []
            for item in items:
                cover_hash = ""
                if item.album:
                    cover_hash = hashlib.md5(item.album.encode()).hexdigest()
                tuid = getattr(item, "track_uid", "") if hasattr(item, "track_uid") else ""
                td = TrackDto(
                    id=make_track_id(item.filepath, tuid),
                    title=item.title or item.filename,
                    artist=item.artist, album=item.album,
                    duration=int(item.duration), size=item.size,
                    format=item.ext.upper().lstrip("."),
                    bitrate=item.bitrate, sample_rate=item.sample_rate,
                    channels=item.channels, track_number=item.track_number,
                    year=item.year, cover_id=cover_hash,
                )
                tracks.append(td.to_dict())
            resp = LibraryResponse(
                tracks=tracks, total=len(tracks),
                artists=len(set(t.artist for t in items if t.artist)),
                albums=len(set(t.album for t in items if t.album)),
            )
            self._send_json(json.loads(resp.to_json()))

        elif path.startswith("/api/stream/"):
            if not self._check_token():
                return self._send_error("Unauthorized", 401)
            track_hash = path.split("/")[-1]
            if srv is None:
                return self._send_error("No server", 503)
            filepath = srv._resolve_track(track_hash)
            if not filepath or not os.path.exists(filepath):
                return self._send_error("Track not found", 404)

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

            range_header = self.headers.get("Range", "")
            if range_header.startswith("bytes="):
                start, end = 0, size - 1
                parts = range_header[6:].split("-")
                if parts[0]:
                    start = int(parts[0])
                if len(parts) > 1 and parts[1]:
                    end = min(int(parts[1]), size - 1)
                if end < start:
                    end = size - 1

                self.send_response(206)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                self.send_header("Content-Length", end - start + 1)
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                with open(filepath, "rb") as f:
                    f.seek(start)
                    remaining = end - start + 1
                    chunk = 65536
                    while remaining > 0:
                        data = f.read(min(chunk, remaining))
                        if not data:
                            break
                        self.wfile.write(data)
                        remaining -= len(data)
            else:
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", size)
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                with open(filepath, "rb") as f:
                    while True:
                        data = f.read(65536)
                        if not data:
                            break
                        self.wfile.write(data)

        elif path.startswith("/api/cover/"):
            if not self._check_token():
                return self._send_error("Unauthorized", 401)
            cover_hash = path.split("/")[-1]
            if srv is None or srv._db is None:
                return self._send_error("No library", 503)
            row = srv._db._conn.execute(
                "SELECT mime, data FROM album_art_cache WHERE album_hash=?",
                (cover_hash,)).fetchone()
            if row:
                self.send_response(200)
                self.send_header("Content-Type", row[0] or "image/jpeg")
                self.send_header("Content-Length", len(row[1]))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(row[1])
            else:
                self._send_error("Cover not found", 404)

        elif path == "/api/search":
            if not self._check_token():
                return self._send_error("Unauthorized", 401)
            query = ""
            if "q=" in self.path:
                query = self.path.split("q=", 1)[1].split("&")[0]
                query = urllib.parse.unquote(query)
            if not query:
                self._send_json({"results": []})
                return
            if srv is None or srv._db is None:
                self._send_json({"results": []})
                return
            items = srv._db.search_advanced(query) if hasattr(srv._db, 'search_advanced') else []
            results = []
            for item in items[:50]:
                tuid = getattr(item, "track_uid", "") if hasattr(item, "track_uid") else ""
                results.append({
                    "id": make_track_id(item.filepath, tuid),
                    "title": item.title or item.filename,
                    "artist": item.artist, "album": item.album,
                    "duration": int(item.duration),
                })
            self._send_json({"results": results, "query": query})

        elif path == "/api/favorites":
            if not self._check_token():
                return self._send_error("Unauthorized", 401)
            if srv is None or srv._db is None:
                self._send_json({"tracks": []})
                return
            favs = srv._db.get_favorites()
            self._send_json({"tracks": favs})

        elif path == "/api/history":
            if not self._check_token():
                return self._send_error("Unauthorized", 401)
            if srv is None or srv._db is None:
                self._send_json({"entries": []})
                return
            history = srv._db.get_play_history()
            self._send_json({"entries": history})

        else:
            self._send_error("Not found", 404)

    def do_POST(self):
        path = self.path.split("?")[0]
        body = self._read_body()
        srv = self.server_ref

        if path == "/api/register":
            try:
                req = RegisterRequest.from_json(body)
            except Exception:
                return self._send_error("Invalid request")
            client_id = req.client_device_id or f"{req.alias}_{req.device_model or req.device}"
            server_id = make_device_id()
            token = SessionToken.generate(
                device_alias=req.alias,
                client_device_id=client_id,
                device_type=req.device,
                device_model=req.device_model,
            )
            if srv:
                srv._sessions[token.token] = token
                library_size = srv._db.get_stats()["total"] if srv._db else 0
            else:
                library_size = 0
            resp = RegisterResponse(
                session_token=token.token,
                server_device_id=server_id,
                client_device_id=client_id,
                library_size=library_size,
            )
            if srv:
                srv.client_connected.emit(req.alias)
            self._send_json(json.loads(resp.to_json()))

        elif path == "/api/sync/state":
            try:
                req = SyncStateRequest.from_json(body)
            except Exception:
                return self._send_error("Invalid request")
            if not srv or req.session_token not in srv._sessions:
                return self._send_error("Invalid token", 401)
            synced = 0
            device = srv._sessions[req.session_token].device_alias
            for entry in req.tracks:
                tid = entry.get("track_id", "")
                play_count = entry.get("play_count", 0)
                favorite = entry.get("favorite", False)
                if srv._db:
                    filepath = srv._resolve_track(tid)
                    if filepath:
                        if play_count > 0:
                            for _ in range(play_count):
                                srv._db.update_play_history(tid, device)
                        if favorite:
                            srv._db.toggle_favorite(tid, device)
                        synced += 1
            self._send_json({"synced": synced})

        else:
            self._send_error("Not found", 404)


class SyncServer(QObject):
    """HTTP server for music sync, runs on a QThread via ThreadPoolExecutor."""

    client_connected = Signal(str)     # device alias
    server_started = Signal(int)       # port
    server_stopped = Signal()
    sync_error = Signal(str)

    def __init__(self, db: LibraryDB, port: int = 53318, parent=None):
        super().__init__(parent)
        self._db = db
        self._port = port
        self._httpd: HTTPServer | None = None
        self._executor: ThreadPoolExecutor | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._sessions: dict[str, SessionToken] = {}
        self._track_index: dict[str, str] = {}
        self._manifest_provider: callable | None = None
        self._delta_provider: callable | None = None

    def set_manifest_provider(self, provider):
        """Register a callable that returns public manifest dict for a device_id."""
        self._manifest_provider = provider

    def set_delta_provider(self, provider):
        """Register a callable for GET /api/sync/manifest/delta."""
        self._delta_provider = provider

    def _build_index(self):
        """Build track_id → filepath lookup (prefers track_uid when available)."""
        if not self._db:
            return
        items = self._db.get_all()
        self._track_index = {}
        for item in items:
            fp = item.filepath
            tuid = getattr(item, "track_uid", "") if hasattr(item, "track_uid") else ""
            tid = make_track_id(fp, tuid)
            self._track_index[tid] = fp

    def _resolve_track(self, track_id: str) -> str | None:
        if track_id not in self._track_index:
            self._build_index()
        return self._track_index.get(track_id)

    def start(self):
        if self._running:
            return
        self._build_index()

        SyncRequestHandler.server_ref = self
        self._httpd = HTTPServer(("0.0.0.0", self._port), SyncRequestHandler)
        self._executor = ThreadPoolExecutor(max_workers=8)
        self._running = True

        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        self.server_started.emit(self._port)

    def _serve(self):
        while self._running and self._httpd:
            try:
                self._httpd.handle_request()
            except Exception as e:
                if self._running:
                    self.sync_error.emit(str(e))

    def stop(self):
        self._running = False
        if self._httpd:
            try:
                self._httpd.server_close()
            except Exception:
                logging.getLogger("michi").debug("Sync server operation failed")
        if self._executor:
            self._executor.shutdown(wait=False)
        self._sessions.clear()
        self.server_stopped.emit()

    @property
    def is_running(self) -> bool:
        return self._running
