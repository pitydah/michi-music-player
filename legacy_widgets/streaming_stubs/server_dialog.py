"""Stub for legacy test compatibility."""
from PySide6.QtWidgets import QDialog
class ServerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
