"""CentralEmptyState — reusable empty state for all views."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QPushButton,
)
from ui.central.central_styles import (
    empty_state_qss, primary_action_button_qss, secondary_action_button_qss,
)


class CentralEmptyState(QFrame):
    primary_clicked = Signal()
    secondary_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("emptyState")
        self.setStyleSheet(empty_state_qss())

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(10)

        layout.addStretch(2)

        self._icon = QLabel()
        self._icon.setObjectName("emptyIcon")
        self._icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._icon)

        self._title = QLabel()
        self._title.setObjectName("emptyTitle")
        self._title.setAlignment(Qt.AlignCenter)
        self._title.setWordWrap(True)
        layout.addWidget(self._title)

        self._subtitle = QLabel()
        self._subtitle.setObjectName("emptySubtitle")
        self._subtitle.setAlignment(Qt.AlignCenter)
        self._subtitle.setWordWrap(True)
        layout.addWidget(self._subtitle)

        btn_row = QVBoxLayout()
        btn_row.setAlignment(Qt.AlignCenter)
        btn_row.setSpacing(8)

        self._primary_btn = QPushButton()
        self._primary_btn.setStyleSheet(primary_action_button_qss())
        self._primary_btn.clicked.connect(self.primary_clicked.emit)
        self._primary_btn.hide()
        btn_row.addWidget(self._primary_btn, 0, Qt.AlignCenter)

        self._secondary_btn = QPushButton()
        self._secondary_btn.setStyleSheet(secondary_action_button_qss())
        self._secondary_btn.clicked.connect(self.secondary_clicked.emit)
        self._secondary_btn.hide()
        btn_row.addWidget(self._secondary_btn, 0, Qt.AlignCenter)

        layout.addLayout(btn_row)
        layout.addStretch(3)

    def set_icon(self, text: str):
        self._icon.setText(text)

    def set_title(self, text: str):
        self._title.setText(text)

    def set_subtitle(self, text: str):
        self._subtitle.setText(text)

    def set_primary_action(self, text: str, callback=None):
        if text:
            self._primary_btn.setText(text)
            self._primary_btn.show()
            if callback:
                self._primary_btn.clicked.connect(callback)
        else:
            self._primary_btn.hide()

    def set_secondary_action(self, text: str, callback=None):
        if text:
            self._secondary_btn.setText(text)
            self._secondary_btn.show()
            if callback:
                self._secondary_btn.clicked.connect(callback)
        else:
            self._secondary_btn.hide()
