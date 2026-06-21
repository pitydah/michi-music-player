"""CentralLoadingState — simple indeterminate loading indicator."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QProgressBar


class CentralLoadingState(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("loadingState")
        self.setStyleSheet("background: transparent; border: none;")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)

        layout.addStretch(2)

        self._bar = QProgressBar()
        self._bar.setRange(0, 0)  # indeterminate
        self._bar.setFixedWidth(240)
        self._bar.setFixedHeight(4)
        self._bar.setTextVisible(False)
        self._bar.setStyleSheet("""
            QProgressBar {
                background: rgba(255,255,255,0.06);
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background: rgba(143,183,255,0.50);
                border-radius: 2px;
            }
        """)
        layout.addWidget(self._bar, 0, Qt.AlignCenter)

        self._label = QLabel("Cargando...")
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setStyleSheet(
            "font-size:13px; color:rgba(255,255,255,0.56); background:transparent;")
        layout.addWidget(self._label)

        layout.addStretch(3)

    def set_text(self, text: str):
        self._label.setText(text)
