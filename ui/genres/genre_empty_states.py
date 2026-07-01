"""GenreEmptyState — reusable empty/error/initial state for genres sections."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QVBoxLayout, QLabel, QPushButton, QFrame,
)

from ui.central.central_styles import glass_button_qss

_TEXT = "rgba(255,255,255,0.95)"
_TEXT3 = "rgba(255,255,255,0.62)"
_ACCENT = "#8FB7FF"


class GenreEmptyState(QFrame):
    primary_clicked = Signal()
    secondary_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("genreEmpty")
        self.setStyleSheet(
            "QFrame#genreEmpty { background: transparent; border: none; }")

        v = QVBoxLayout(self)
        v.setAlignment(Qt.AlignCenter)
        v.setSpacing(12)

        icon = QLabel("🎵")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size: 48px; background: transparent;")
        v.addWidget(icon)

        self._title = QLabel("")
        self._title.setAlignment(Qt.AlignCenter)
        self._title.setStyleSheet(f"font-size: 16px; color: {_TEXT}; font-weight: 600; background: transparent;")
        v.addWidget(self._title)

        self._subtitle = QLabel("")
        self._subtitle.setAlignment(Qt.AlignCenter)
        self._subtitle.setStyleSheet(f"font-size: 12px; color: {_TEXT3}; background: transparent;")
        self._subtitle.setWordWrap(True)
        v.addWidget(self._subtitle)

        btn_row = QVBoxLayout()
        btn_row.setAlignment(Qt.AlignCenter)
        btn_row.setSpacing(6)

        self._primary_btn = QPushButton("")
        self._primary_btn.setCursor(Qt.PointingHandCursor)
        self._primary_btn.setStyleSheet(glass_button_qss("primary"))
        self._primary_btn.setFixedWidth(200)
        self._primary_btn.clicked.connect(self.primary_clicked.emit)
        self._primary_btn.setVisible(False)
        btn_row.addWidget(self._primary_btn)

        self._secondary_btn = QPushButton("")
        self._secondary_btn.setCursor(Qt.PointingHandCursor)
        self._secondary_btn.setStyleSheet(glass_button_qss("ghost"))
        self._secondary_btn.setFixedWidth(200)
        self._secondary_btn.clicked.connect(self.secondary_clicked.emit)
        self._secondary_btn.setVisible(False)
        btn_row.addWidget(self._secondary_btn)

        v.addLayout(btn_row)
        v.setContentsMargins(40, 40, 40, 40)

    def show_no_genres(self):
        self._title.setText("No se encontraron géneros en tu biblioteca")
        self._subtitle.setText(
            "Puedes analizar metadata, aplicar géneros manualmente "
            "o abrir Audio Lab para diagnosticar la biblioteca.")
        self._primary_btn.setText("Analizar biblioteca")
        self._primary_btn.setVisible(True)
        self._secondary_btn.setText("Abrir Audio Lab")
        self._secondary_btn.setVisible(True)

    def show_empty_genre(self):
        self._title.setText("Este género no tiene canciones asociadas")
        self._subtitle.setText(
            "Puede deberse a una regla de limpieza o a metadata incompleta.")
        self._primary_btn.setVisible(False)
        self._secondary_btn.setVisible(False)

    def show_issues_found(self, dup_count: int = 0, untagged: int = 0,
                          junk: int = 0, rare: int = 0):
        self._title.setText("Tu biblioteca tiene géneros, pero se detectaron inconsistencias")
        parts = []
        if dup_count:
            parts.append(f"{dup_count} duplicados")
        if untagged:
            parts.append(f"{untagged} sin género")
        if junk:
            parts.append(f"{junk} géneros basura")
        if rare:
            parts.append(f"{rare} géneros raros")
        self._subtitle.setText(" · ".join(parts))
        self._primary_btn.setText("Revisar limpieza")
        self._primary_btn.setVisible(True)
        self._secondary_btn.setVisible(False)

    def show_error(self, message: str):
        self._title.setText("Error al cargar géneros")
        self._subtitle.setText(message)
        self._primary_btn.setVisible(False)
        self._secondary_btn.setVisible(False)
