from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel


class ReceiverWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(QLabel("Snapcast receiver wizard migrated to QML"))
