"""Radio Dialog — dialog to add/edit radio stations."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QDialogButtonBox, QLabel,
)


class RadioDialog(QDialog):
    def __init__(self, parent=None, name: str = "", url: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Añadir emisora" if not name else "Editar emisora")
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self._name_edit = QLineEdit(name)
        self._name_edit.setPlaceholderText("Ej: Radio Nacional")
        form.addRow("Nombre:", self._name_edit)

        self._url_edit = QLineEdit(url)
        self._url_edit.setPlaceholderText("https://ejemplo.com/stream.mp3")
        form.addRow("URL:", self._url_edit)

        help_label = QLabel(
            "Formatos soportados: MP3, OGG, AAC, Opus, etc.\n"
            "Busca enlaces .pls, .m3u o streams directos."
        )
        help_label.setStyleSheet("color: #8e8e93; font-size: 11px;")
        help_label.setWordWrap(True)
        form.addRow("", help_label)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        from ui.theme import apply_dialog_shadow
        apply_dialog_shadow(self)

    def get_data(self) -> tuple:
        return self._name_edit.text().strip(), self._url_edit.text().strip()
