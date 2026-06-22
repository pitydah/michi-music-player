"""TransmitController — network transmit device management (HTTP/Snapcast)."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QPushButton, QListWidget, QListWidgetItem,
    QMessageBox, QDialogButtonBox,
)


class TransmitController:
    """Manages TransmitManager network devices — add, remove, activate.

    Network transmit (TCP) is separate from the local audio output branch.
    """

    def __init__(self, window, services=None):
        self._win = window
        self._svc = services

    def activate_device(self, device):
        """Activate a network transmit device, or None for local-only."""
        if device is not None:
            # Validate DAC route supports transmit
            try:
                from audio.output_profiles import get_profile
                profile_key = self._win._ctx.playback._engine._audio_profile if hasattr(self._win._ctx.playback, '_engine') else "standard"
                profile = get_profile(profile_key)
                if not profile.allows_transmit:
                    self._win._ctx.toast.show(
                        f"El perfil '{profile.name}' no permite transmisión", "warning")
            except Exception:
                pass
            self._win._ctx.transmit_mgr.set_active(device)
            self._win._ctx.playback.set_transmit_device(device)
            self._win._ctx.player_bar.set_transmit_active(True, device.name)
        else:
            self._win._ctx.transmit_mgr.set_active(None)
            self._win._ctx.playback.set_transmit_device(None)
            self._win._ctx.player_bar.set_transmit_active(False)

    def on_active_changed(self):
        """Called when TransmitManager.active_changed fires."""
        device = self._win._ctx.transmit_mgr.get_active()
        if device:
            self._win._ctx.player_bar.set_transmit_active(True, device.name)
        else:
            self._win._ctx.player_bar.set_transmit_active(False)

    def add_device(self):
        """Open dialog to add a new network transmit device."""
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
            self._win._ctx.transmit_mgr.add_device(
                name.text().strip(), stype.currentData(),
                addr.text().strip(), port_val)

    def manage_devices(self):
        """Open dialog to manage existing network transmit devices."""
        from ui.theme import apply_dialog_shadow

        devices = self._win._ctx.transmit_mgr.get_devices()
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
                self._win._ctx.transmit_mgr.remove_device(dname)
                dlg.accept()
                self.manage_devices()

        def _do_activate():
            sel = lst.currentItem()
            if sel:
                dname = sel.text().split("  ·  ")[0]
                dev = next((d for d in self._win._ctx.transmit_mgr.get_devices()
                            if d.name == dname), None)
                if dev:
                    self.activate_device(dev)
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
