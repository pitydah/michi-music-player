from PySide6.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox, QLabel


class ServerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(QLabel("Server management migrated to QML"))
        self.layout().addWidget(QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
