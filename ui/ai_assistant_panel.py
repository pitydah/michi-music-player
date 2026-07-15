from PySide6.QtWidgets import QWidget, QVBoxLayout


class AiAssistantPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
