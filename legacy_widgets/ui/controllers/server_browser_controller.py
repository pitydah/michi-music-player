"""LEGACY - reemplazado por ui_qml_bridge correspondiente."""

"""Server browser controller — add/open/remove Subsonic servers, radio playback."""
from PySide6.QtWidgets import QMessageBox

from sources.base_source import TrackRef
from streaming.subsonic_client import (
    SubsonicClient, load_servers, save_servers,
    SubsonicError, AuthError, ServerNotFoundError,
)
from streaming.server_dialog import ServerDialog
from streaming.remote_browser import RemoteBrowser


class ServerBrowserController:
    def __init__(self, window):
        self._win = window

    def add_server(self):
        dlg = ServerDialog(self._win)
        if dlg.exec() and dlg.server:
            servers = load_servers()
            servers.append(dlg.server)
            save_servers(servers)
            self._win._rebuild_sidebar()

    def open_server(self, name: str):
        servers = load_servers()
        srv_data = next((s for s in servers if s.name == name), None)
        if not srv_data:
            QMessageBox.warning(self._win, "Error", f"Servidor '{name}' no encontrado.")
            return

        try:
            client = SubsonicClient(srv_data)
            self._win._remote_browser = RemoteBrowser(client, name)
            self._win._remote_browser._workers = self._win._workers
            self._win._remote_browser.track_selected.connect(self.play_stream)
            self._win._views.replace("remote", self._win._remote_browser)
            self._win._views.show("remote")

            self._win._remote_browser.load_artists()
            self._win._section_title.setText(name)
            from sources.subsonic_source import SubsonicSource
            srv_key = f"srv:{name}"
            self._win._search_ctrl.register(srv_key, SubsonicSource(client))
            self._win._search_ctrl.set_active(srv_key)
            self._win._search.show()
        except AuthError as e:
            QMessageBox.warning(self._win, "Error de autenticación",
                f"No se pudo autenticar con '{name}':\n{e}")
        except ServerNotFoundError as e:
            QMessageBox.warning(self._win, "Servidor no encontrado",
                f"No se puede conectar a '{name}':\n{e}")
        except SubsonicError as e:
            QMessageBox.warning(self._win, "Error de conexión",
                f"No se pudo conectar a '{name}':\n{e}")
        except Exception as e:
            QMessageBox.warning(self._win, "Error", f"No se pudo conectar:\n{e}")

    def remove_server(self, name: str):
        if QMessageBox.question(self._win, "Eliminar",
            f"¿Eliminar servidor '{name}'?") == QMessageBox.Yes:
            servers = [s for s in load_servers() if s.name != name]
            save_servers(servers)
            self._win._rebuild_sidebar()
            self._win._load_library()

    def play_stream(self, url: str, title: str, artist: str, album: str = ""):
        self._win._play_trackref(TrackRef(
            uri=url, title=title, artist=artist, album=album,
            source_type="remote_stream", source_label="Servidor remoto"))

    def play_radio(self, url: str, name: str):
        self._win._play_trackref(TrackRef(
            uri=url, title=name, artist="Radio",
            source_type="radio", source_label=name))

    def on_radio_count(self, visible: int, total: int):
        if self._win._current_section_key == "radio":
            if visible != total:
                self._win._count.setText(f"{visible} de {total} emisoras")
            else:
                self._win._count.setText(f"{total} emisoras")

    def show_radio(self, key):
        self._win._search_ctrl.set_active("radio")
        self._win._current_section_key = "radio"
        self._win._radio_widget.reload()
        self._win._fade_content("radio")
