from PySide6.QtWidgets import QWidget, QVBoxLayout


class VinylLabPage(QWidget):
    def __init__(self, worker_mgr=None, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
