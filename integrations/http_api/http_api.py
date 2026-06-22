"""Michi HTTP API — exposes player control for Home Assistant integration."""
import json
import os
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread


API_PORT_DEFAULT = 8124


class _AstraHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Michi API. Reads from AppStateStore, writes via MichiApiBridge."""

    def __init__(self, *args, state_store=None, bridge=None, token="", db=None, **kwargs):
        self._store = state_store
        self._bridge = bridge
        self._token = token
        self._db = db
        super().__init__(*args, **kwargs)

    def _check_auth(self) -> bool:
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            self._send_json(401, {"error": "missing_token"})
            return False
        if auth[7:] != self._token:
            self._send_json(403, {"error": "invalid_token"})
            return False
        return True

    def _send_json(self, code: int, data: dict):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def do_GET(self):
        path = self.path.split("?")[0]
        if not self._check_auth():
            return

        if path == "/api/player/status":
            snap = self._store.player_snapshot() if self._store else {}
            data = {
                "state": snap.get("state", "idle"),
                "title": snap.get("title", ""),
                "artist": snap.get("artist", ""),
                "album": snap.get("album", ""),
                "duration": snap.get("duration", 0),
                "position": snap.get("position", 0),
                "volume": snap.get("volume", 70),
                "source_type": snap.get("source_type", "local_file"),
                "source_label": snap.get("source_label", ""),
                "destination": snap.get("destination", "local"),
                "cover_url": snap.get("cover_url", ""),
            }
            self._send_json(200, data)

        elif path == "/api/library/browse":
            self._handle_library_browse()
            return

        elif path.startswith("/api/library/item/"):
            media_id = path[len("/api/library/item/"):]
            self._handle_library_item(media_id)
            return

        else:
            self._send_json(404, {"error": "not_found"})

    def do_POST(self):
        if not self._check_auth():
            return
        body = self._read_json()

        if self.path == "/api/player/play":
            if self._bridge:
                self._bridge.play_requested.emit()
            self._send_json(200, {"status": "ok"})

        elif self.path == "/api/player/pause":
            if self._bridge:
                self._bridge.pause_requested.emit()
            self._send_json(200, {"status": "ok"})

        elif self.path == "/api/player/stop":
            if self._bridge:
                self._bridge.stop_requested.emit()
            self._send_json(200, {"status": "ok"})

        elif self.path == "/api/player/next":
            if self._bridge:
                self._bridge.next_requested.emit()
            self._send_json(200, {"status": "ok"})

        elif self.path == "/api/player/previous":
            if self._bridge:
                self._bridge.previous_requested.emit()
            self._send_json(200, {"status": "ok"})

        elif self.path == "/api/player/volume":
            vol = body.get("volume", 70)
            if self._bridge:
                self._bridge.volume_requested.emit(int(vol))
            self._send_json(200, {"status": "ok", "volume": vol})

        elif self.path == "/api/player/play_media":
            if self._bridge:
                self._bridge.play_media_requested.emit(body)
            self._send_json(200, {"status": "ok"})

        elif self.path == "/api/player/select_destination":
            dest_id = body.get("id", "local") or "local"
            if self._bridge:
                self._bridge.select_destination_requested.emit(dest_id)
            self._send_json(200, {"status": "ok"})

        elif self.path == "/api/library/play":
            if self._bridge:
                self._bridge.library_play_requested.emit(body)
            self._send_json(200, {"status": "ok"})

        else:
            self._send_json(404, {"error": "not_found"})

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()

    # ── Library browsing ──

    def _handle_library_browse(self):
        from urllib.parse import urlparse, parse_qs
        qs = parse_qs(urlparse(self.path).query or "")
        parent_id = (qs.get("parent_id", [None])[0] or "").strip()

        db = self._db
        if not db:
            self._send_json(200, {"parent_id": parent_id, "items": []})
            return

        if not parent_id:
            self._send_json(200, {
                "parent_id": None,
                "children": [
                    {"id": "folders", "title": "Carpetas",
                     "media_class": "directory", "can_expand": True},
                    {"id": "artists", "title": "Artistas",
                     "media_class": "directory", "can_expand": True},
                    {"id": "albums", "title": "Albumes",
                     "media_class": "directory", "can_expand": True},
                    {"id": "playlists", "title": "Playlists",
                     "media_class": "directory", "can_expand": True},
                    {"id": "favs", "title": "Favoritos",
                     "media_class": "directory", "can_expand": True},
                    {"id": "recent", "title": "Recientes",
                     "media_class": "directory", "can_expand": True},
                ],
            })
            return

        items = []

        if parent_id == "folders":
            all_items = getattr(self, '_all_items', []) or db.get_all()
            dirs = sorted(set(os.path.dirname(i.filepath) for i in all_items))
            for d in dirs[:50]:
                items.append({
                    "id": f"folder:{d}", "title": os.path.basename(d) or d,
                    "media_class": "directory",
                    "can_expand": True,
                    "thumbnail": "",
                })

        elif parent_id == "artists":
            all_items = getattr(self, '_all_items', []) or db.get_all()
            artists = sorted(set(i.artist for i in all_items if i.artist))
            for a in artists[:100]:
                items.append({
                    "id": f"artist:{a}", "title": a,
                    "media_class": "directory",
                    "can_expand": True,
                    "thumbnail": "",
                })

        elif parent_id == "albums":
            all_items = getattr(self, '_all_items', []) or db.get_all()
            from library.album_art import group_by_album
            groups = group_by_album(all_items)
            for album, artist, _tracks in groups[:50]:
                items.append({
                    "id": f"album:{album}",
                    "title": f"{artist} — {album}" if artist else album,
                    "media_class": "album",
                    "can_expand": True,
                    "thumbnail": "",
                })

        elif parent_id == "playlists":
            for p in db.get_playlists():
                items.append({
                    "id": f"playlist:{p['id']}", "title": p.get("name", "Playlist"),
                    "media_class": "playlist",
                    "can_expand": True,
                    "thumbnail": "",
                })

        elif parent_id == "favs":
            favs = db.get_all(kind="fav")
            items = _tracks_to_media_items(favs)

        elif parent_id == "recent":
            recent = db.get_all(kind="recent")
            items = _tracks_to_media_items(recent)

        elif parent_id.startswith("folder:"):
            folder = parent_id[len("folder:"):]
            all_items = getattr(self, '_all_items', []) or db.get_all()
            tracks = [i for i in all_items if os.path.dirname(i.filepath) == folder]
            items = _tracks_to_media_items(tracks)

        elif parent_id.startswith("artist:"):
            artist_name = parent_id[len("artist:"):]
            tracks = db.search_advanced(f"artist:{artist_name}") if hasattr(db, 'search_advanced') else []
            items = _tracks_to_media_items(tracks)

        elif parent_id.startswith("album:"):
            album_name = parent_id[len("album:"):]
            all_items = getattr(self, '_all_items', []) or db.get_all()
            tracks = [i for i in all_items if i.album == album_name]
            items = _tracks_to_media_items(tracks)

        elif parent_id.startswith("playlist:"):
            pid = int(parent_id[len("playlist:"):])
            tracks = db.get_playlist_items(pid)
            items = _tracks_to_media_items(tracks)

        self._send_json(200, {"parent_id": parent_id, "children": items})

    def handle_library_item(self, media_id: str):
        db = self._db
        all_items = getattr(self, '_all_items', []) or (db.get_all() if db else [])
        for i in all_items:
            if i.filepath == media_id:
                self._send_json(200, _track_to_item(i))
                return
        self._send_json(404, {"error": "not_found"})

    def log_message(self, format, *args):
        pass  # suppress stderr logging


def _tracks_to_media_items(tracks) -> list[dict]:
    """Convert MediaItem list to API media items."""
    return [_track_to_item(t) for t in tracks]


def _track_to_item(track) -> dict:
    """Convert a single MediaItem to API media item dict."""
    fp = getattr(track, 'filepath', '')
    return {
        "media_id": fp,
        "title": getattr(track, 'title', '') or os.path.basename(fp),
        "artist": getattr(track, 'artist', ''),
        "album": getattr(track, 'album', ''),
        "duration": getattr(track, 'duration', 0) or 0,
        "media_class": "track",
        "media_content_type": "music",
        "can_play": True,
        "can_expand": False,
        "thumbnail": "",
    }


def make_handler(store, bridge, token, db):
    """Factory to create handler instances with state store, bridge, token, and db."""
    def _handler(*args, **kwargs):
        return _AstraHandler(*args, state_store=store, bridge=bridge, token=token, db=db, **kwargs)
    return _handler


class MichiHttpApi:
    """Manages the Michi HTTP API server lifecycle."""

    def __init__(self, window, port: int = API_PORT_DEFAULT):
        self._window = window
        self._port = port
        self._token = ""
        self._server = None
        self._thread = None
        self._running = False
        self._store = None
        self._bridge = None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def port(self) -> int:
        return self._port

    @property
    def token(self) -> str:
        return self._token

    def generate_token(self) -> str:
        self._token = uuid.uuid4().hex[:32]
        from core.settings_manager import set_
        set_("home_audio/michi_api_token", self._token)
        return self._token

    def configure(self, port: int = API_PORT_DEFAULT, token: str = ""):
        self._port = port
        if token:
            self._token = token
        elif not self._token:
            from core.settings_manager import get
            saved = get("home_audio/michi_api_token") or ""
            self._token = saved or self.generate_token()

    def set_store_and_bridge(self, store, bridge):
        self._store = store
        self._bridge = bridge

    def start(self):
        if self._running or not self._store or not self._bridge:
            return
        host = "127.0.0.1"
        self._server = HTTPServer(
            (host, self._port),
            make_handler(self._store, self._bridge, self._token,
                        getattr(self._window, '_db', None)))
        self._thread = Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self._running = True

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server = None
        self._thread = None
        self._running = False
