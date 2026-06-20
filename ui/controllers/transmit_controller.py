"""Transmit controller — streaming, snapcast, audio output management."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMenu, QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QPushButton, QListWidget, QListWidgetItem,
    QMessageBox, QDialogButtonBox,
)


class TransmitController:
    def __init__(self, window):
        self._win = window

    def show_transmit_menu(self):
        menu = QMenu(self._win)
        menu.setStyleSheet("""
            QMenu { background: rgba(28,28,30,230); border: 1px solid rgba(255,255,255,0.06);
              border-radius: 8px; padding: 4px; }
            QMenu::item { padding: 6px 32px 6px 12px; border-radius: 6px;
              color: rgba(255,255,255,0.8); }
            QMenu::item:selected { background: rgba(255,122,0,0.20); }
            QMenu::separator { height: 1px; background: rgba(255,255,255,0.06);
              margin: 3px 8px; }
        """)

        local = menu.addAction("Local (sin transmitir)")
        local.setCheckable(True)
        active = self._win._transmit_mgr.get_active()
        local.setChecked(active is None)
        local.triggered.connect(lambda: self.activate_transmit_device(None))

        devices = self._win._transmit_mgr.get_devices()
        if devices:
            menu.addSeparator()
            for dev in devices:
                action = menu.addAction(dev.name)
                action.setCheckable(True)
                action.setChecked(active is not None and active.name == dev.name)
                action.triggered.connect(
                    lambda checked, d=dev: self.activate_transmit_device(d))

        menu.addSeparator()
        menu.addAction("Añadir dispositivo...", self.add_transmit_device)

        btn = self._win._player_bar_ctrl.transmit_button()
        menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    def activate_transmit_device(self, device):
        if device is None:
            self._win._transmit_mgr.set_active(None)
            self._win._playback.set_output_device(None)
            self._win._player_bar.set_transmit_active(False)
        else:
            self._win._transmit_mgr.set_active(device)
            self._win._playback.set_output_device(device)
            self._win._player_bar.set_transmit_active(True, device.name)

    def on_transmit_devices_changed(self):
        pass

    def on_transmit_active_changed(self):
        device = self._win._transmit_mgr.get_active()
        if device:
            self._win._player_bar.set_transmit_active(True, device.name)
        else:
            self._win._player_bar.set_transmit_active(False)

    def show_audio_output_menu(self):
        menu = QMenu(self._win)
        menu.setStyleSheet("""
            QMenu { background: rgba(28,28,30,230); border: 1px solid rgba(255,255,255,0.06);
              border-radius: 8px; padding: 4px; }
            QMenu::item { padding: 6px 32px 6px 12px; border-radius: 6px;
              color: rgba(255,255,255,0.8); }
            QMenu::item:selected { background: rgba(255,122,0,0.20); }
            QMenu::separator { height: 1px; background: rgba(255,255,255,0.06);
              margin: 3px 8px; }
        """)

        action_system = menu.addAction("Salida predeterminada del sistema")
        action_system.triggered.connect(
            lambda: self._win._playback.set_output_device(None))

        menu.addSeparator()

        try:
            import gi
            gi.require_version("Gst", "1.0")
            from gi.repository import Gst
            monitor = Gst.DeviceMonitor()
            monitor.add_filter("Audio/Sink", None)
            monitor.start()
            devices = monitor.get_devices()
            monitor.stop()
            if devices:
                for dev in devices:
                    name = dev.get_display_name() or dev.get_device_class() or "Audio device"
                    action = menu.addAction(name)
                    action.triggered.connect(
                        lambda checked=False, d=dev: self._win._playback.set_output_device(d))
            else:
                pass
        except Exception:
            import logging
            logging.getLogger("astra").debug("Audio device detection failed")

        menu.addSeparator()
        action_pipewire = menu.addAction("PipeWire (sistema)")
        action_pipewire.triggered.connect(
            lambda: self._win._playback.set_output_device(None))
        action_pipewire.setEnabled(True)

        from PySide6.QtGui import QCursor
        menu.exec(QCursor.pos())

    def open_mini_player(self):
        from ui.mini_player import MiniPlayer
        from audio.player import PlaybackState
        from library.cover_art_service import CoverArtService

        if not hasattr(self._win, '_mini_player'):
            self._win._mini_player = MiniPlayer(self._win._playback, self._win)
            self._win._mini_player.play_clicked.connect(self._win._playback.toggle)
            self._win._mini_player.prev_clicked.connect(self._win._playback.play_prev)
            self._win._mini_player.next_clicked.connect(self._win._playback.play_next)
            self._win._mini_player.seek_requested.connect(self._win._playback.seek)
            self._win._player.position_changed.connect(
                lambda s: self._win._mini_player.set_position(
                    s, getattr(self._win._player, '_duration', 0)))
            self._win._player.state_changed.connect(
                lambda s: self._win._mini_player.set_state(
                    "playing" if s == PlaybackState.PLAYING else
                    "paused" if s == PlaybackState.PAUSED else "stopped"))

        current = self._win._playback.current
        name = os.path.basename(current) if current else ""
        artist = ""
        if current:
            qual, _ = CoverArtService.quality_label(current)
            item = self._win._items_index.get(current)
            if item:
                artist = item.artist or qual or ""
                title = item.title or name
            else:
                title = name
        else:
            title = "Sin reproducción"
        self._win._mini_player.set_track(title, artist)
        self._win._mini_player.show()
        self._win._mini_player.raise_()
        self._win._mini_player.activateWindow()

    def add_transmit_device(self):
        from ui.theme import apply_dialog_shadow

        dlg = QDialog(self._win)
        dlg.setWindowTitle("Añadir dispositivo")
        dlg.setMinimumWidth(380)
        apply_dialog_shadow(dlg)

        layout = QFormLayout(dlg)
        name = QLineEdit()
        name.setPlaceholderText("ej: Altavoz Salón")
        stype = QComboBox()
        stype.addItem("HTTP Stream (servidor TCP)", "http")
        stype.addItem("Snapcast", "snapcast")
        addr = QLineEdit()
        addr.setPlaceholderText("192.168.1.10")
        port = QLineEdit()
        port.setPlaceholderText("8554")

        layout.addRow("Nombre:", name)
        layout.addRow("Tipo:", stype)
        layout.addRow("IP / URL:", addr)
        layout.addRow("Puerto:", port)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addRow(btns)

        if dlg.exec() == QDialog.DialogCode.Accepted and name.text().strip():
            try:
                port_val = int(port.text()) if port.text().strip() else 0
            except ValueError:
                port_val = 0
            self._win._transmit_mgr.add_device(
                name.text().strip(), stype.currentData(),
                addr.text().strip(), port_val)

    def manage_transmit_devices(self):
        from ui.theme import apply_dialog_shadow

        devices = self._win._transmit_mgr.get_devices()
        if not devices:
            QMessageBox.information(self._win, "Dispositivos",
                                    "No hay dispositivos configurados.")
            return

        dlg = QDialog(self._win)
        dlg.setWindowTitle("Administrar dispositivos")
        dlg.setMinimumWidth(400)
        apply_dialog_shadow(dlg)

        layout = QVBoxLayout(dlg)
        lst = QListWidget()
        for dev in devices:
            item = QListWidgetItem(
                f"{dev.name}  ·  {dev.stype.upper()}  ·  "
                f"{dev.address}:{dev.port or '-'}")
            lst.addItem(item)
        layout.addWidget(lst)

        btn_row = QHBoxLayout()

        def _do_delete():
            sel = lst.currentItem()
            if sel:
                dname = sel.text().split("  ·  ")[0]
                self._win._transmit_mgr.remove_device(dname)
                dlg.accept()
                self.manage_transmit_devices()

        def _do_activate():
            sel = lst.currentItem()
            if sel:
                dname = sel.text().split("  ·  ")[0]
                dev = next((d for d in self._win._transmit_mgr.get_devices()
                           if d.name == dname), None)
                if dev:
                    self.activate_transmit_device(dev)
                    dlg.accept()

        del_btn = QPushButton("Eliminar")
        del_btn.clicked.connect(_do_delete)
        act_btn = QPushButton("Activar")
        act_btn.clicked.connect(_do_activate)
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(dlg.accept)

        btn_row.addWidget(act_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)
        dlg.exec()
