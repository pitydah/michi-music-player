"""HTTP REST API server for wireless music sync.

Protected endpoints require a paired device token with appropriate permissions.
Public endpoints: /api/ping, /api/discovery/info, /api/pair/start, /api/pair/confirm.
All other endpoints require a valid Bearer token and the corresponding permission.

Permission map:
    sync.read_manifest  → /api/library, /api/sync/manifest, /api/search,
                          /api/favorites, /api/history
    sync.download_tracks  → /api/stream/{id}
    sync.download_covers  → /api/cover/{id}
    sync.upload_state     → /api/sync/state

Inspired by LocalSend's hyper server architecture (Rust).
Uses Python stdlib http.server + ThreadPoolExecutor for concurrent requests.
"""

import logging
import os
import json
import threading
import time
import secrets
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from concurrent.futures import ThreadPoolExecutor

from sync.sync_protocol import (
    SessionToken, TrackDto, LibraryResponse,
    RegisterRequest, RegisterResponse,
    PairStartRequest, PairStartResponse,
    PairConfirmRequest, PairConfirmResponse,
    SyncStateRequest, make_track_id, make_cover_id, make_device_id,
)
from library.library_db import LibraryDB
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("michi.sync.server")


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

    # ── Rate limiting (simple IP-based) ──

    _failed_attempts: dict[str, list[float]] = {}  # IP → [timestamps]

    def _check_rate_limit(self, ip: str) -> bool:
        now = time.time()
        attempts = self._failed_attempts.get(ip, [])
        # Prune entries older than 5 minutes
        attempts = [t for t in attempts if now - t < 300.0]
        self._failed_attempts[ip] = attempts
        return len(attempts) < 5

    def _record_failed_attempt(self, ip: str):
        now = time.time()
        self._failed_attempts.setdefault(ip, []).append(now)

    # ── Auth middleware ──

    def _check_token(self) -> str | None:
        session = self._check_token_session()
        return session.device_alias if session else None

    def _check_token_session(self) -> "SessionToken | None":
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

    def _require_permission(self, permission: str) -> bool:
        """Validate token against persistent DeviceRegistry.
        Priority:
          1. X-Michi-Device-Id header → validate against registry directly
          2. Fallback: in-memory session (legacy compat)
        """
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            self._send_error("Unauthorized", 401)
            return False
        token = auth[7:]
        srv = self.server_ref
        if srv is None or srv._device_registry is None:
            self._send_error("Server not ready", 503)
            return False

        # Primary: resolve device_id from X-Michi-Device-Id
        device_id = self.headers.get("X-Michi-Device-Id", "")

        if device_id:
            # Validate against persisted registry (works across restarts)
            if not srv._device_registry.validate_token(device_id, token):
                self._send_error("Token revoked or invalid", 403)
                return False
        else:
            # Fallback: in-memory session (legacy clients)
            session = srv._sessions.get(token)
            if session is None or session.is_expired():
                self._send_error("Unauthorized", 401)
                return False
            device_id = session.client_device_id
            if not device_id:
                self._send_error("Invalid token: no device id", 401)
                return False
            # Also re-validate against registry if we can
            if not srv._device_registry.validate_token(device_id, token):
                self._send_error("Token revoked or invalid", 403)
                return False

        if not srv._device_registry.has_permission(device_id, permission):
            self._send_error("Forbidden: insufficient permissions", 403)
            return False

        srv._device_registry.mark_seen(device_id)
        return True

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, Range")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        srv = self.server_ref

        # ── Public endpoints ──
        if path == "/api/ping":
            self._send_json({"status": "ok", "version": "1.0"})

        elif path == "/api/discovery/info":
            has_account = bool(srv and srv._local_account and srv._local_account.exists())
            self._send_json({
                "server": "MichiMusicPlayer",
                "server_alias": srv._alias if srv else "Michi Music Player",
                "version": "1.0",
                "requires_pairing": has_account,
                "auth_methods": ["password"] if has_account else [],
                "server_device_id": make_device_id(),
            })

        # ── Protected: sync.read_manifest ──
        elif path == "/api/sync/manifest":
            if not self._require_permission("sync.read_manifest"):
                return
            if srv is None or srv._manifest_provider is None:
                return self._send_error("Manifest service not available", 503)
            qs = urllib.parse.parse_qs(
                self.path.split("?")[1] if "?" in self.path else "")
            device_id = (qs.get("device_id") or [""])[0]
            if not device_id:
                return self._send_error("Missing device_id parameter", 400)
            manifest = srv._manifest_provider(device_id)
            if manifest is None:
                return self._send_error("No manifest for this device", 404)
            self._send_json(manifest)

        elif path == "/api/sync/manifest/delta":
            if not self._require_permission("sync.read_manifest"):
                return
            if srv is None or srv._delta_provider is None:
                return self._send_error("Delta manifest not available", 503)
            qs = urllib.parse.parse_qs(
                self.path.split("?")[1] if "?" in self.path else "")
            device_id = (qs.get("device_id") or [""])[0]
            since_str = (qs.get("since") or ["0"])[0]
            if not device_id:
                return self._send_error("Missing device_id parameter", 400)
            try:
                since = float(since_str)
            except ValueError:
                since = 0.0
            delta = srv._delta_provider(device_id, since)
            if delta is None:
                return self._send_error("No delta for this device", 404)
            self._send_json(delta)

        elif path == "/api/library":
            if not self._require_permission("sync.read_manifest"):
                return
            if srv is None or srv._db is None:
                return self._send_error("No library", 503)
            items = srv._db.get_all()
            tracks = []
            for item in items:
                artist = item.artist or ""
                album_name = item.album or ""
                cover_hash = make_cover_id(album_name, artist)
                tuid = getattr(item, "track_uid", "") if hasattr(item, "track_uid") else ""
                td = TrackDto(
                    id=make_track_id(item.filepath, tuid),
                    title=item.title or item.filename,
                    artist=artist, album=album_name,
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

        elif path == "/api/search":
            if not self._require_permission("sync.read_manifest"):
                return
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
            if not self._require_permission("sync.read_manifest"):
                return
            if srv is None or srv._db is None:
                self._send_json({"tracks": []})
                return
            favs = srv._db.get_favorites()
            self._send_json({"tracks": favs})

        elif path == "/api/history":
            if not self._require_permission("sync.read_manifest"):
                return
            if srv is None or srv._db is None:
                self._send_json({"entries": []})
                return
            history = srv._db.get_play_history()
            self._send_json({"entries": history})

        # ── Protected: sync.download_tracks ──
        elif path.startswith("/api/stream/"):
            if not self._require_permission("sync.download_tracks"):
                return
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

        # ── Protected: sync.download_covers ──
        elif path.startswith("/api/cover/"):
            if not self._require_permission("sync.download_covers"):
                return
            cover_hash = path.split("/")[-1]
            if srv is None or srv._db is None:
                return self._send_error("No library", 503)
            row = srv._db.conn.execute(
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

        else:
            self._send_error("Not found", 404)

    def do_POST(self):
        path = self.path.split("?")[0]
        body = self._read_body()
        srv = self.server_ref

        # ── Public: pair/start ──
        if path == "/api/pair/start":
            try:
                req = PairStartRequest.from_json(body)
            except Exception:
                return self._send_error("Invalid request", 400)
            has_account = bool(srv and srv._local_account and srv._local_account.exists())
            server_alias = srv._alias if srv else "Michi Music Player"
            resp = PairStartResponse(
                pairing_id=str(secrets.token_hex(8)),
                auth_methods=["password"] if has_account else [],
                server_alias=server_alias,
                auth_required=has_account,
                server_device_id=make_device_id(),
            )
            self._send_json(json.loads(resp.to_json()))

        # ── Public: pair/confirm ──
        elif path == "/api/pair/confirm":
            client_ip = self.client_address[0]
            if not self._check_rate_limit(client_ip):
                return self._send_error("Too many attempts, try later", 429)

            try:
                req = PairConfirmRequest.from_json(body)
            except Exception:
                return self._send_error("Invalid request", 400)
            if srv is None:
                return self._send_error("Server not ready", 503)

            client_id = req.client_device_id
            if not client_id:
                self._send_json(json.loads(PairConfirmResponse(
                    success=False, error="Missing client_device_id").to_json()))
                return

            # Auth verification
            acct_exists = bool(srv._local_account and srv._local_account.exists())
            if acct_exists and (
                not req.username or not req.password or
                req.username != srv._local_account.get_username() or
                not srv._local_account.verify(req.password)
            ):
                self._record_failed_attempt(client_ip)
                logger.warning("Pairing failed: invalid credentials from %s (user=%s)",
                               client_ip, req.username)
                self._send_json(json.loads(PairConfirmResponse(
                    success=False, error="Invalid credentials").to_json()))
                return

            # Register device if new
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

            # Generate persistent token
            token_str = secrets.token_hex(32)
            server_id = make_device_id()

            # Persist in registry
            if registry:
                registry.set_token(client_id, token_str)

            # In-memory session (for legacy fallback)
            session = SessionToken(
                token=token_str,
                device_alias=client_id,
                client_device_id=client_id,
            )
            with srv._sessions_lock:
                srv._sessions[token_str] = session

            default_perms = [
                "sync.read_manifest", "sync.download_tracks",
                "sync.download_covers", "sync.download_playlists",
                "sync.upload_state",
            ]
            resp = PairConfirmResponse(
                success=True,
                device_id=client_id,
                device_token=token_str,
                permissions=default_perms,
                server_device_id=server_id,
                server_alias=srv._alias if srv else "Michi Music Player",
            )
            srv.client_connected.emit(client_id)
            self._send_json(json.loads(resp.to_json()))

        # ── Legacy register: blocked when local account exists ──
        elif path == "/api/register":
            if srv and srv._local_account and srv._local_account.exists():
                return self._send_json({
                    "error": "pairing_required",
                    "message": "Use /api/pair/start and /api/pair/confirm",
                }, 403)
            # Fallback for backward compatibility (no local account)
            try:
                req = RegisterRequest.from_json(body)
            except Exception:
                return self._send_error("Invalid request", 400)
            client_id = req.client_device_id or f"{req.alias}_{req.device_model or req.device}"
            server_id = make_device_id()
            token = SessionToken.generate(
                device_alias=req.alias,
                client_device_id=client_id,
                device_type=req.device,
                device_model=req.device_model,
            )
            if srv:
                with srv._sessions_lock:
                    srv._sessions[token.token] = token
                library_size = srv._db.get_stats().get("total", 0) if srv._db else 0
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

        # ── Protected: sync/state (sync.upload_state) ──
        elif path == "/api/sync/state":
            if not self._require_permission("sync.upload_state"):
                return
            try:
                req = SyncStateRequest.from_json(body)
            except Exception:
                return self._send_error("Invalid request", 400)
            if not srv:
                return self._send_error("Server not ready", 503)
            device_alias = self._check_token() or "unknown"
            synced = 0
            for entry in req.tracks:
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
            self._send_json({"synced": synced})

        else:
            self._send_error("Not found", 404)


class SyncServer(QObject):
    """HTTP server for music sync, runs on a QThread via ThreadPoolExecutor."""

    client_connected = Signal(str)     # device alias
    server_started = Signal(int)       # port
    server_stopped = Signal()
    sync_error = Signal(str)

    def __init__(self, db: LibraryDB, port: int = 53318, parent=None,
                 alias: str = "Michi Music Player"):
        super().__init__(parent)
        self._alias = alias
        self._db = db
        self._port = port
        self._httpd: HTTPServer | None = None
        self._executor: ThreadPoolExecutor | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._sessions: dict[str, SessionToken] = {}
        self._sessions_lock = threading.Lock()
        self._track_index: dict[str, str] = {}
        self._track_index_lock = threading.Lock()
        self._track_index_built = False
        self._manifest_provider: callable | None = None
        self._delta_provider: callable | None = None
        self._local_account: object | None = None
        self._device_registry: object | None = None

    def set_manifest_provider(self, provider):
        """Register a callable that returns public manifest dict for a device_id."""
        self._manifest_provider = provider

    def set_delta_provider(self, provider):
        """Register a callable for GET /api/sync/manifest/delta."""
        self._delta_provider = provider

    def set_local_account_manager(self, mgr):
        """Set LocalAccountManager for pairing auth."""
        self._local_account = mgr

    def set_device_registry(self, registry):
        """Set DeviceRegistry for token validation and permissions."""
        self._device_registry = registry

    def _purge_expired_sessions(self):
        """Remove expired sessions to prevent memory leak."""
        with self._sessions_lock:
            expired = [k for k, v in self._sessions.items() if v.is_expired()]
            for k in expired:
                del self._sessions[k]

    def _build_index(self):
        """Build track_id → filepath lookup (prefers track_uid when available)."""
        if not self._db:
            return
        items = self._db.get_all()
        new_index = {}
        for item in items:
            fp = item.filepath
            tuid = getattr(item, "track_uid", "") if hasattr(item, "track_uid") else ""
            tid = make_track_id(fp, tuid)
            new_index[tid] = fp
        with self._track_index_lock:
            self._track_index = new_index
            self._track_index_built = True

    def _resolve_track(self, track_id: str) -> str | None:
        with self._track_index_lock:
            if not self._track_index_built:
                self._track_index_lock.release()
                self._build_index()
                self._track_index_lock.acquire()
            return self._track_index.get(track_id)

    def start(self):
        if self._running:
            return
        self._build_index()

        SyncRequestHandler.server_ref = self
        try:
            self._httpd = HTTPServer(("0.0.0.0", self._port), SyncRequestHandler)
        except OSError as e:
            self.sync_error.emit(f"SyncServer: {e}")
            return
        self._executor = ThreadPoolExecutor(max_workers=8)
        self._running = True

        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        self.server_started.emit(self._port)

    def _serve(self):
        purge_counter = 0
        while self._running and self._httpd:
            try:
                self._httpd.handle_request()
                purge_counter += 1
                if purge_counter >= 50:
                    self._purge_expired_sessions()
                    purge_counter = 0
            except Exception as e:
                if self._running:
                    self.sync_error.emit(str(e))

    def stop(self):
        self._running = False
        if self._httpd:
            try:
                self._httpd.server_close()
            except Exception:
                import logging
                logging.getLogger("michi").debug("Sync server close failed")
        if self._executor:
            self._executor.shutdown(wait=False)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        self._sessions.clear()
        self.server_stopped.emit()

    @property
    def is_running(self) -> bool:
        return self._running
