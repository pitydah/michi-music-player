"""Server connection dialog — add Navidrome/Jellyfin server."""

from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QPushButton, QLabel, QDialogButtonBox, QMessageBox,
    QApplication,
)

from streaming.subsonic_client import ServerConfig, SubsonicClient


class ServerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Añadir servidor")
        self.setMinimumWidth(420)
        from ui.theme import apply_dialog_shadow
        apply_dialog_shadow(self)
        self._server = None

        layout = QFormLayout(self)
        layout.setSpacing(10)

        self._name = QLineEdit()
        self._name.setPlaceholderText("ej: Mi Casa")
        layout.addRow("Nombre:", self._name)

        self._url = QLineEdit()
        self._url.setPlaceholderText("https://navidrome.example.com")
        layout.addRow("URL:", self._url)

        self._user = QLineEdit()
        self._user.setPlaceholderText("admin")
        layout.addRow("Usuario:", self._user)

        self._pass = QLineEdit()
        self._pass.setEchoMode(QLineEdit.Password)
        self._pass.setPlaceholderText("••••••••")
        layout.addRow("Contraseña:", self._pass)

        self._type = QComboBox()
        self._type.addItem("Navidrome", "navidrome")
        self._type.addItem("Jellyfin", "jellyfin")
        layout.addRow("Tipo:", self._type)

        # ── Test button ──
        test_row = QHBoxLayout()
        self._status = QLabel("")
        self._status.setStyleSheet("color: #8e8e93; font-size: 12px;")
        test_row.addWidget(self._status)
        test_row.addStretch()
        self._test_btn = QPushButton("Probar conexión")
        self._test_btn.clicked.connect(self._test)
        test_row.addWidget(self._test_btn)
        layout.addRow(test_row)

        # ── OK / Cancel ──
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def _test(self):
        url = self._url.text().strip()
        user = self._user.text().strip()
        pwd = self._pass.text()

        if not url:
            self._status.setText("Introduce una URL")
            return

        self._status.setText("Conectando...")
        self._status.setStyleSheet("color: #ff9800; font-size: 12px;")
        QApplication.processEvents()

        try:
            cfg = ServerConfig(
                name=self._name.text().strip() or "Servidor",
                url=url, username=user, password=pwd,
                stype=self._type.currentData(),
            )
            client = SubsonicClient(cfg)
            if client.ping():
                self._status.setText("✅ Conexión exitosa")
                self._status.setStyleSheet("color: #4caf50; font-size: 12px;")
                self._server = cfg
            else:
                self._status.setText("❌ El servidor rechazó la conexión")
                self._status.setStyleSheet("color: #ef5350; font-size: 12px;")
        except Exception as e:
            self._status.setText(f"❌ Error: {e}")
            self._status.setStyleSheet("color: #ef5350; font-size: 12px;")

    def _on_accept(self):
        if not self._server:
            # Try test first
            self._test()
        if self._server:
            self.accept()
        else:
            QMessageBox.warning(
                self, "Error",
                "Primero prueba la conexión para verificar el servidor.")

    @property
    def server(self):
        return self._server
