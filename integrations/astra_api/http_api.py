"""Astra HTTP API — exposes player control for Home Assistant integration."""
import json
import os
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread


API_PORT_DEFAULT = 8124


class _AstraHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Astra API."""

    def __init__(self, *args, window=None, token="", **kwargs):
        self._window = window
        self._token = token
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
        win = self._window

        if path == "/api/player/status":
            state = "idle"
            if hasattr(win, '_playback'):
                st = getattr(win._playback, 'state', None)
                from audio.player import PlaybackState
                if st == PlaybackState.PLAYING:
                    state = "playing"
                elif st == PlaybackState.PAUSED:
                    state = "paused"
                elif st == PlaybackState.STOPPED:
                    state = "idle"
            current = getattr(win, '_playback', None)
            current_path = current.current if current else ""

            ref = getattr(win, '_current_ref', None)
            data = {
                "state": state,
                "title": ref.title if ref else os.path.basename(current_path) if current_path else "",
                "artist": ref.artist if ref else "",
                "album": ref.album if ref else "",
                "duration": int(ref.duration) if ref else 0,
                "position": 0,
                "volume": getattr(win, '_player_bar', None)._vol.value() if hasattr(win, '_player_bar') else 70,
                "source_type": ref.source_type if ref else "local_file",
                "source_label": ref.source_label if ref else "",
                "destination": "local",
                "cover_url": ref.cover_path if ref else "",
            }
            self._send_json(200, data)

        elif path == "/api/player/destinations":
            groups = []
            zones = []
            if hasattr(win, '_group_mgr'):
                groups = win._group_mgr.groups()
            if hasattr(win, '_home_audio_view') and hasattr(win, '_ha_connected') and win._ha_connected:
                zones = [
                    {"id": d["id"], "name": d["name"], "type": d.get("backend", "home_assistant")}
                    for d in win._home_audio_view._devices if d.get("available")]
            dests = [
                {"id": "local", "name": "Este equipo", "type": "local"},
            ]
            for g in groups:
                dests.append({"id": g["id"], "name": g["name"], "type": "snapcast_group"})
            for z in zones:
                dests.append(z)
            self._send_json(200, dests)

        elif path == "/api/library/browse":
            self._handle_library_browse(win)

        elif path.startswith("/api/library/item/"):
            media_id = path[len("/api/library/item/"):]
            self._handle_library_item(win, media_id)

        else:
            self._send_json(404, {"error": "not_found"})

    def do_POST(self):
        if not self._check_auth():
            return
        win = self._window
        body = self._read_json()

        if self.path == "/api/player/play":
            if hasattr(win, '_playback') and hasattr(win._playback, 'play'):
                win._playback.play()
            self._send_json(200, {"status": "ok"})

        elif self.path == "/api/player/pause":
            if hasattr(win, '_playback') and hasattr(win._playback, 'pause'):
                win._playback.pause()
            self._send_json(200, {"status": "ok"})

        elif self.path == "/api/player/stop":
            if hasattr(win, '_playback') and hasattr(win._playback, 'stop'):
                win._playback.stop()
            self._send_json(200, {"status": "ok"})

        elif self.path == "/api/player/next":
            if hasattr(win, '_playback') and hasattr(win._playback, 'play_next'):
                win._playback.play_next()
            self._send_json(200, {"status": "ok"})

        elif self.path == "/api/player/previous":
            if hasattr(win, '_playback') and hasattr(win._playback, 'play_prev'):
                win._playback.play_prev()
            self._send_json(200, {"status": "ok"})

        elif self.path == "/api/player/volume":
            vol = body.get("volume", 70)
            if hasattr(win, '_player_bar'):
                win._player_bar.volume_changed.emit(int(vol))
            self._send_json(200, {"status": "ok", "volume": vol})

        elif self.path == "/api/player/play_media":
            self._handle_play_media(win, body)

        elif self.path == "/api/player/select_destination":
            dest_id = body.get("id", "local")
            if dest_id == "local":
                if hasattr(win, '_ctx'):
                    win._ctx.player_bar.set_transmit_active(False)
            elif hasattr(win, '_group_mgr'):
                win._group_mgr.activate_group(dest_id)
                for g in win._group_mgr.groups():
                    if g["id"] == dest_id:
                        win._ctx.player_bar.set_transmit_active(True, g["name"])
            self._send_json(200, {"status": "ok"})

        elif self.path == "/api/library/play":
            self._handle_library_play(win, body)

        else:
            self._send_json(404, {"error": "not_found"})

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()

    # ── Library browsing ──

    def _handle_library_browse(self, win):
        from urllib.parse import urlparse, parse_qs
        qs = parse_qs(urlparse(self.path).query or "")
        parent_id = (qs.get("parent_id", [None])[0] or "").strip()

        db = getattr(win, '_db', None)
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
            all_items = getattr(win, '_all_items', []) or db.get_all()
            dirs = sorted(set(os.path.dirname(i.filepath) for i in all_items))
            for d in dirs[:50]:
                items.append({
                    "id": f"folder:{d}", "title": os.path.basename(d) or d,
                    "media_class": "directory",
                    "can_expand": True,
                    "thumbnail": "",
                })

        elif parent_id == "artists":
            all_items = getattr(win, '_all_items', []) or db.get_all()
            artists = sorted(set(i.artist for i in all_items if i.artist))
            for a in artists[:100]:
                items.append({
                    "id": f"artist:{a}", "title": a,
                    "media_class": "directory",
                    "can_expand": True,
                    "thumbnail": "",
                })

        elif parent_id == "albums":
            all_items = getattr(win, '_all_items', []) or db.get_all()
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
            all_items = getattr(win, '_all_items', []) or db.get_all()
            tracks = [i for i in all_items if os.path.dirname(i.filepath) == folder]
            items = _tracks_to_media_items(tracks)

        elif parent_id.startswith("artist:"):
            artist_name = parent_id[len("artist:"):]
            tracks = db.search_advanced(f"artist:{artist_name}") if hasattr(db, 'search_advanced') else []
            items = _tracks_to_media_items(tracks)

        elif parent_id.startswith("album:"):
            album_name = parent_id[len("album:"):]
            all_items = getattr(win, '_all_items', []) or db.get_all()
            tracks = [i for i in all_items if i.album == album_name]
            items = _tracks_to_media_items(tracks)

        elif parent_id.startswith("playlist:"):
            pid = int(parent_id[len("playlist:"):])
            tracks = db.get_playlist_items(pid)
            items = _tracks_to_media_items(tracks)

        self._send_json(200, {"parent_id": parent_id, "children": items})

    def _handle_library_item(self, win, media_id: str):
        db = getattr(win, '_db', None)
        all_items = getattr(win, '_all_items', []) or (db.get_all() if db else [])
        for i in all_items:
            if i.filepath == media_id:
                self._send_json(200, _track_to_item(i))
                return
        self._send_json(404, {"error": "not_found"})

    def _handle_play_media(self, win, body):
        media_id = body.get("media_id", "")
        dest = body.get("destination", "local")
        if dest != "local" and hasattr(win, '_group_mgr'):
            win._group_mgr.activate_group(dest)
        if media_id.startswith("http"):
            track = type('TrackRef', (), {
                'uri': media_id,
                'title': body.get("title", ""),
                'artist': body.get("artist", ""),
                'album': body.get("album", ""),
                'duration': 0.0,
                'cover_path': body.get("image_url", ""),
                'source_type': 'home_assistant',
                'source_label': 'Home Assistant',
            })()
            if hasattr(win, '_playback_ctrl'):
                win._playback_ctrl.play_trackref(track)
        elif os.path.isfile(media_id):
            from sources.base_source import TrackRef
            track = TrackRef(
                uri=media_id,
                title=body.get("title", os.path.basename(media_id)),
                artist=body.get("artist", ""),
                album=body.get("album", ""),
            )
            if hasattr(win, '_playback_ctrl'):
                win._playback_ctrl.play_trackref(track)
        self._send_json(200, {"status": "ok"})

    def _handle_library_play(self, win, body):
        media_id = body.get("media_id", "")
        dest = body.get("destination", "local")
        if dest != "local" and hasattr(win, '_group_mgr'):
            win._group_mgr.activate_group(dest)
        if os.path.isfile(media_id):
            from sources.base_source import TrackRef
            track = TrackRef(
                uri=media_id,
                title=os.path.basename(media_id),
            )
            if hasattr(win, '_playback_ctrl'):
                win._playback_ctrl.play_trackref(track)
        self._send_json(200, {"status": "ok"})

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


def make_handler(window, token):
    """Factory to create handler instances with window and token."""
    def _handler(*args, **kwargs):
        return _AstraHandler(*args, window=window, token=token, **kwargs)
    return _handler


class AstraHttpApi:
    """Manages the Astra HTTP API server lifecycle."""

    def __init__(self, window, port: int = API_PORT_DEFAULT):
        self._window = window
        self._port = port
        self._token = ""
        self._server = None
        self._thread = None
        self._running = False

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
        set_("home_audio/astra_api_token", self._token)
        return self._token

    def configure(self, port: int = API_PORT_DEFAULT, token: str = ""):
        self._port = port
        if token:
            self._token = token
        elif not self._token:
            from core.settings_manager import get
            saved = get("home_audio/astra_api_token") or ""
            self._token = saved or self.generate_token()

    def start(self):
        if self._running:
            return
        host = "127.0.0.1"
        self._server = HTTPServer(
            (host, self._port),
            make_handler(self._window, self._token))
        self._thread = Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self._running = True

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server = None
        self._thread = None
        self._running = False
