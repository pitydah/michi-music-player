"""Remote browser — artist → album → track navigation with thumbnails."""

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QApplication, QFrame,
)
import urllib.request
import urllib.error
import socket

from streaming.subsonic_client import (
    SubsonicClient, RemoteArtist, RemoteAlbum, RemoteTrack,
    SubsonicError, AuthError, ServerNotFoundError,
)


def _download_pixmap(url: str, size: int = 64) -> QPixmap:
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "AstraMusicPlayer/1.0")
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = resp.read()
        pix = QPixmap()
        pix.loadFromData(data)
        if pix.isNull():
            return QPixmap()
        return pix.scaled(size, size, Qt.KeepAspectRatio,
                         Qt.SmoothTransformation)
    except (urllib.error.URLError, socket.timeout, TimeoutError):
        return QPixmap()
    except Exception:
        return QPixmap()


class RemoteBrowser(QWidget):
    track_selected = Signal(str, str, str, str)

    def __init__(self, client: SubsonicClient, server_name: str, parent=None):
        super().__init__(parent)
        self._client = client
        self._server_name = server_name
        self._history = []  # stack of (type, id, name)
        self._current_type = "artists"
        self._current_id = ""

        self.setStyleSheet("background: #090B11;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── Breadcrumb bar ──
        bc_frame = QFrame()
        bc_frame.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.035);"
            "border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; }")
        bc = QHBoxLayout(bc_frame)
        bc.setContentsMargins(12, 8, 12, 8)
        self._bc_btn = QPushButton(f"🏠 {server_name} > Artistas")
        self._bc_btn.setFlat(True)
        self._bc_btn.setStyleSheet(
            "QPushButton { color: rgba(255,255,255,0.78); font-size: 13px; font-weight: 650; }"
            "QPushButton:hover { color: #FF7A00; }")
        self._bc_btn.clicked.connect(self._go_top)
        bc.addWidget(self._bc_btn)
        bc.addStretch()
        layout.addWidget(bc_frame)

        # ── List ──
        self._list = QListWidget()
        self._list.setIconSize(QSize(56, 56))
        self._list.setFrameShape(QFrame.NoFrame)
        self._list.setStyleSheet("""
            QListWidget { background: #090B11; border: none; outline: none; }
            QListWidget::item {
                padding: 10px 14px; margin: 2px 8px; border-radius: 12px;
                color: rgba(255,255,255,0.78); font-size: 13px;
                border: 1px solid transparent;
            }
            QListWidget::item:hover {
                background: rgba(255,255,255,0.06); color: #fff;
                border: 1px solid rgba(255,255,255,0.08);
            }
            QListWidget::item:selected {
                background: rgba(255,255,255,0.105); color: #fff;
                border: 1px solid rgba(255,255,255,0.14);
            }
        """)
        self._list.doubleClicked.connect(self._on_item)
        layout.addWidget(self._list)

        # ── Status ──
        self._status = QLabel("Cargando...")
        self._status.setAlignment(Qt.AlignCenter)
        self._status.setStyleSheet(
            "color: rgba(255,255,255,0.40); padding: 32px; font-size: 14px;")
        layout.addWidget(self._status)
        self._status.hide()

    def load_artists(self):
        self._history.clear()
        self._current_type = "artists"
        self._current_id = ""
        self._bc_btn.setText(f"🏠 {self._server_name} > Artistas")
        self._do_load("artistas", lambda: self._client.get_artists(),
                      self._populate_artists)

    def _go_top(self):
        if len(self._history) <= 1:
            self.load_artists()
            return
        prev = self._history.pop()
        if prev[0] == "artist":
            self.load_artists()
        elif prev[0] == "album":
            self._current_type = "artist"
            self._current_id = prev[1]
            self._bc_btn.setText(f"🏠 {self._server_name} > Artistas")
            self._do_load("álbumes",
                         lambda: self._client.get_albums(self._current_id),
                         self._populate_albums)

    def _on_item(self, item):
        data = item.data(Qt.UserRole)
        if not data:
            return

        kind, obj_id, name = data

        if kind == "artist":
            self._history.append(("artist", self._current_id, ""))
            self._current_type = "artist"
            self._current_id = obj_id
            self._bc_btn.setText(f"🏠 {self._server_name} > Artistas > {name}")
            self._do_load("álbumes",
                         lambda: self._client.get_albums(obj_id),
                         self._populate_albums)

        elif kind == "album":
            self._history.append(("album", self._current_id, name))
            self._current_type = "album"
            self._current_id = obj_id
            self._bc_btn.setText(
                f"🏠 {self._server_name} > Artistas > {name}")
            self._do_load("temas",
                         lambda: self._client.get_album_tracks(obj_id),
                         self._populate_tracks)

        elif kind == "track":
            url = self._client.get_stream_url(obj_id)
            self.track_selected.emit(url, name, data[3] if len(data) > 3 else "",
                                    self._bc_btn.text().replace("🏠 ", ""))

    def _do_load(self, label: str, loader, populator):
        self._list.clear()
        self._status.setText(f"Cargando {label}...")
        self._status.show()
        QApplication.processEvents()

        try:
            data = loader()
            populator(data)
            self._status.hide()
        except AuthError as e:
            self._status.setText(
                f"Error de autenticación: {e}\n"
                f"Verifica usuario/contraseña en preferencias.")
            self._status.show()
        except ServerNotFoundError as e:
            self._status.setText(
                f"Servidor no encontrado: {e}\n"
                f"Verifica la URL y que el servidor esté encendido.")
            self._status.show()
        except SubsonicError as e:
            self._status.setText(f"{e}")
            self._status.show()
        except Exception as e:
            self._status.setText(f"Error inesperado: {e}")
            self._status.show()

    def _populate_artists(self, artists: list[RemoteArtist]):
        self._list.clear()
        for a in artists:
            item = QListWidgetItem(f"{a.name}")
            item.setData(Qt.UserRole, ("artist", a.id, a.name))
            item.setSizeHint(QSize(0, 56))
            self._list.addItem(item)

    def _populate_albums(self, albums: list[RemoteAlbum]):
        self._list.clear()
        for a in albums:
            text = f"{a.name}"
            if a.artist:
                text += f"\n{a.artist}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, ("album", a.id, a.name))
            item.setSizeHint(QSize(0, 62))
            if a.cover_id:
                url = self._client.get_cover_url(a.cover_id, 100)
                pix = _download_pixmap(url, 52)
                if not pix.isNull():
                    item.setIcon(QIcon(pix))
            self._list.addItem(item)

    def _populate_tracks(self, tracks: list[RemoteTrack]):
        self._list.clear()
        for t in tracks:
            dur = f"{t.duration // 60}:{t.duration % 60:02d}" if t.duration else ""
            text = f"  {t.track:02d}  {t.title}    {dur}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, ("track", t.id, t.title, t.artist))
            item.setSizeHint(QSize(0, 42))
            if t.artist:
                item.setToolTip(f"{t.artist} — {t.album}")
            self._list.addItem(item)
