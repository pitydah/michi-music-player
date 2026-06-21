"""Home Assistant REST client — non-blocking via QNetworkAccessManager."""
import json

from PySide6.QtCore import QObject, Signal, QUrl, QByteArray
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply


class HomeAssistantClient(QObject):
    connection_tested = Signal(bool, str)  # ok, message
    entities_loaded = Signal(list)  # list[dict] raw entity data
    service_called = Signal(bool, str)  # ok, message
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._nam = QNetworkAccessManager(self)
        self._base_url = ""
        self._token = ""
        self._verify_ssl = True

    def configure(self, base_url: str, token: str, verify_ssl: bool = True):
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._verify_ssl = verify_ssl

    def test_connection(self):
        if not self._base_url or not self._token:
            self.connection_tested.emit(False, "URL o token vacios")
            return
        self._get("/api/", self._on_test_response)

    def get_states(self):
        self._get("/api/states", self._on_states_response)

    def get_media_players(self):
        self._get("/api/states", self._on_media_players_response)

    def call_service(self, domain: str, service: str, data: dict):
        path = f"/api/services/{domain}/{service}"
        body = json.dumps(data, ensure_ascii=False).encode()
        self._post(path, body, self._on_service_response)

    def play_media(self, entity_id: str, media_url: str,
                   media_content_type: str = "music", metadata: dict = None):
        data = {"entity_id": entity_id, "media_content_id": media_url,
                "media_content_type": media_content_type}
        if metadata:
            data["extra"] = {"metadata": metadata}
        self.call_service("media_player", "play_media", data)

    def media_play(self, entity_id: str):
        self.call_service("media_player", "media_play",
                          {"entity_id": entity_id})

    def media_pause(self, entity_id: str):
        self.call_service("media_player", "media_pause",
                          {"entity_id": entity_id})

    def media_stop(self, entity_id: str):
        self.call_service("media_player", "media_stop",
                          {"entity_id": entity_id})

    def set_volume(self, entity_id: str, volume_level: float):
        self.call_service("media_player", "volume_set",
                          {"entity_id": entity_id,
                           "volume_level": volume_level})

    def volume_up(self, entity_id: str):
        self.call_service("media_player", "volume_up",
                          {"entity_id": entity_id})

    def volume_down(self, entity_id: str):
        self.call_service("media_player", "volume_down",
                          {"entity_id": entity_id})

    def mute(self, entity_id: str, muted: bool):
        self.call_service("media_player", "volume_mute",
                          {"entity_id": entity_id,
                           "is_volume_muted": muted})

    # ── Internal HTTP ──

    def _get(self, path: str, callback):
        url = QUrl(self._base_url + path)
        req = QNetworkRequest(url)
        req.setRawHeader(b"Authorization",
                         f"Bearer {self._token}".encode())
        req.setRawHeader(b"Content-Type", b"application/json")
        if not self._verify_ssl:
            from PySide6.QtNetwork import QSslConfiguration
            ssl_config = QSslConfiguration.defaultConfiguration()
            ssl_config.setPeerVerifyMode(
                QSslConfiguration.PeerVerifyMode.VerifyNone)
            req.setSslConfiguration(ssl_config)
        reply = self._nam.get(req)
        reply.finished.connect(lambda r=reply, cb=callback: self._handle(r, cb))

    def _post(self, path: str, body: bytes, callback):
        url = QUrl(self._base_url + path)
        req = QNetworkRequest(url)
        req.setRawHeader(b"Authorization",
                         f"Bearer {self._token}".encode())
        req.setRawHeader(b"Content-Type", b"application/json")
        if not self._verify_ssl:
            from PySide6.QtNetwork import QSslConfiguration
            ssl_config = QSslConfiguration.defaultConfiguration()
            ssl_config.setPeerVerifyMode(
                QSslConfiguration.PeerVerifyMode.VerifyNone)
            req.setSslConfiguration(ssl_config)
        reply = self._nam.post(req, QByteArray(body))
        reply.finished.connect(lambda r=reply, cb=callback: self._handle(r, cb))

    def _handle(self, reply: QNetworkReply, callback):
        err = reply.error()
        if err != QNetworkReply.NoError:
            msg = reply.errorString()
            self.error_occurred.emit(f"HTTP {err}: {msg}")
            if callback:
                callback(False, None)
            reply.deleteLater()
            return
        data = bytes(reply.readAll()).decode("utf-8", errors="replace")
        reply.deleteLater()
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError:
            self.error_occurred.emit("Respuesta no es JSON valido")
            if callback:
                callback(False, None)
            return
        if callback:
            callback(True, parsed)

    # ── Response handlers ──

    def _on_test_response(self, ok, data):
        if ok and isinstance(data, dict) and data.get("message"):
            self.connection_tested.emit(True,
                f"Conectado: {data['message']}")
        elif ok:
            self.connection_tested.emit(True, "Conexion exitosa")
        else:
            self.connection_tested.emit(False, "No se pudo conectar")

    def _on_states_response(self, ok, data):
        if ok and isinstance(data, list):
            self.entities_loaded.emit(data)
        else:
            self.entities_loaded.emit([])

    def _on_media_players_response(self, ok, data):
        if ok and isinstance(data, list):
            media = [e for e in data
                     if e.get("entity_id", "").startswith("media_player.")]
            self.entities_loaded.emit(media)
        else:
            self.entities_loaded.emit([])

    def _on_service_response(self, ok, data):
        self.service_called.emit(ok, "Servicio ejecutado" if ok else "Error")


def entity_to_device(entity: dict) -> dict:
    """Convert a raw HA entity dict to a device dict for HomeAudioView."""
    attrs = entity.get("attributes", {})
    entity_id = entity.get("entity_id", "")

    is_cast = any(x in entity_id.lower() for x in ("cast", "chromecast"))
    if not is_cast:
        app = (attrs.get("app_name") or "").lower()
        name = (attrs.get("friendly_name") or "").lower()
        is_cast = any(x in app or x in name
                      for x in ("cast", "chromecast", "nest"))

    return {
        "id": entity_id,
        "entity_id": entity_id,
        "name": attrs.get("friendly_name",
                          entity_id.replace("media_player.", "").replace("_", " ")),
        "state": entity.get("state", "unavailable"),
        "area": attrs.get("area_id") or "",
        "room": "",
        "device_type": "media_player",
        "backend": "home_assistant",
        "supported_features": attrs.get("supported_features", 0),
        "volume_level": attrs.get("volume_level"),
        "muted": attrs.get("is_volume_muted", False),
        "media_title": attrs.get("media_title", ""),
        "media_artist": attrs.get("media_artist", ""),
        "media_album": attrs.get("media_album_name", ""),
        "source": attrs.get("source", ""),
        "app_name": attrs.get("app_name", ""),
        "entity_picture": attrs.get("entity_picture", ""),
        "is_cast": is_cast,
        "is_snapclient": False,
        "available": entity.get("state", "unavailable") not in
                     ("unavailable", "unknown"),
    }
