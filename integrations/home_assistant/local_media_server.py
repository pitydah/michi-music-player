"""Local Media Server — serves local audio files via HTTP for Home Assistant / Cast."""
import os
import hashlib
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from PySide6.QtCore import QObject, Signal, QTimer


class _MediaHandler(BaseHTTPRequestHandler):
    """Serves registered files with token-based access. No directory listing."""

    def __init__(self, *args, registry=None, token_map=None, **kwargs):
        self._registry = registry or {}
        self._token_map = token_map or {}
        super().__init__(*args, **kwargs)

    def do_GET(self):
        parts = self.path.lstrip("/").split("/", 2)
        if len(parts) < 3 or parts[0] != "media":
            self.send_error(404, "Not found")
            return
        token, filename = parts[1], parts[2]

        # Validate token
        filepath = self._token_map.get(token)
        if not filepath or not os.path.isfile(filepath):
            self.send_error(404, "Not found or expired")
            return
        # Prevent path traversal
        if os.path.basename(filepath) != filename:
            self.send_error(403, "Forbidden")
            return
        # Security: only serve registered paths
        if filepath not in self._registry:
            self.send_error(404, "Not found")
            return

        try:
            size = os.path.getsize(filepath)
            ext = os.path.splitext(filepath)[1].lower()
            mime_map = {
                ".mp3": "audio/mpeg", ".flac": "audio/flac",
                ".wav": "audio/wav", ".ogg": "audio/ogg",
                ".m4a": "audio/mp4", ".aac": "audio/aac",
                ".wma": "audio/x-ms-wma", ".opus": "audio/opus",
            }
            mime = mime_map.get(ext, "audio/mpeg")

            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(size))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with open(filepath, "rb") as f:
                self.wfile.write(f.read())
        except OSError:
            self.send_error(500, "Internal error")

    def log_message(self, format, *args):
        pass


def _make_handler(registry, token_map):
    def handler(*args, **kwargs):
        return _MediaHandler(*args, registry=registry,
                             token_map=token_map, **kwargs)
    return handler


class LocalMediaServer(QObject):
    started = Signal()
    stopped = Signal()
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._server = None
        self._thread = None
        self._running = False
        self._port = 8125
        self._registry = {}  # filepath -> expiry
        self._token_map = {}  # token -> filepath
        self._cleanup_timer = QTimer(self)
        self._cleanup_timer.timeout.connect(self._cleanup_expired)
        self._cleanup_timer.setInterval(60000)

    @property
    def is_running(self) -> bool:
        return self._running

    def configure(self, port: int = 8125):
        self._port = port

    def start(self):
        if self._running:
            return
        try:
            self._server = HTTPServer(
                ("0.0.0.0", self._port),
                _make_handler(self._registry, self._token_map))
            self._thread = Thread(
                target=self._server.serve_forever, daemon=True)
            self._thread.start()
            self._running = True
            self._cleanup_timer.start()
            self.started.emit()
        except OSError as e:
            self.error_occurred.emit(
                f"No se pudo iniciar servidor local: {e}")

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server = None
        self._thread = None
        self._running = False
        self._cleanup_timer.stop()
        self._registry.clear()
        self._token_map.clear()
        self.stopped.emit()

    def register_file(self, filepath: str, ttl_minutes: int = 30) -> str:
        """Register a file and return a public URL. Raises ValueError."""
        if not filepath or not os.path.isfile(filepath):
            raise ValueError(f"No existe: {filepath}")

        # Prevent serving files outside allowed dirs
        allowed = [
            os.path.expanduser("~/Música"),
            os.path.expanduser("~/Music"),
            "/tmp",
        ]
        resolved = os.path.realpath(filepath)
        ok = False
        for d in allowed:
            d = os.path.realpath(os.path.expanduser(d))
            if os.path.commonpath([resolved, d]) == d:
                ok = True
                break
        if not ok:
            raise ValueError("Ruta no permitida")

        token = hashlib.sha256(
            f"{filepath}{time.time()}".encode()).hexdigest()[:24]
        self._registry[filepath] = time.time() + (ttl_minutes * 60)
        self._token_map[token] = filepath
        return f"http://localhost:{self._port}/media/{token}/{os.path.basename(filepath)}"

    def unregister_file(self, token: str):
        filepath = self._token_map.pop(token, None)
        if filepath:
            self._registry.pop(filepath, None)

    def _cleanup_expired(self):
        now = time.time()
        expired_files = [
            fp for fp, exp in self._registry.items() if now > exp]
        for fp in expired_files:
            self._registry.pop(fp, None)
        expired_tokens = [
            t for t, fp in self._token_map.items() if fp not in self._registry]
        for t in expired_tokens:
            self._token_map.pop(t, None)
