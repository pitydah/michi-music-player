"""Radio Widget — premium card mosaic of radio stations."""

import os

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QScrollArea, QGridLayout, QFrame, QMenu, QMessageBox,
    QFileDialog, QLineEdit, QDialog, QFormLayout, QDialogButtonBox,
)


class RadioWidget(QWidget):
    station_selected = Signal(str, str)  # url, name

    def __init__(self, parent=None):
        super().__init__(parent)
        self._manager = RadioManager()
        self._stations = []

        self.setStyleSheet("background: #090B11;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Header
        header = QHBoxLayout()
        header.setContentsMargins(16, 12, 16, 4)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_lbl = QLabel("Emisoras")
        title_lbl.setStyleSheet(
            "color: rgba(255,255,255,0.88); font-size: 15px; font-weight: 650;"
            "background: transparent;")
        subtitle = QLabel("Agrega radios por URL y organízalas como mosaico")
        subtitle.setStyleSheet(
            "color: rgba(255,255,255,0.40); font-size: 11px; background: transparent;")
        title_col.addWidget(title_lbl)
        title_col.addWidget(subtitle)
        header.addLayout(title_col)
        header.addStretch()

        self._add_btn = QPushButton("+ Añadir emisora")
        self._add_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,122,0,0.10);
                border: 1px solid rgba(255,122,0,0.22);
                border-radius: 10px;
                padding: 7px 16px;
                color: #FF7A00;
                font-size: 12px;
                font-weight: 550;
            }
            QPushButton:hover {
                background: rgba(255,122,0,0.18);
                border-color: rgba(255,122,0,0.40);
            }
        """)
        self._add_btn.clicked.connect(self._add_station)
        header.addWidget(self._add_btn)
        layout.addLayout(header)

        # Scroll area with card grid
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._scroll.setStyleSheet(
            "QScrollArea { background: #090B11; border: none; }"
            "QScrollBar:vertical { width: 8px; background: rgba(255,255,255,0.025);"
            "  border-radius: 4px; }"
            "QScrollBar::handle:vertical { background: rgba(255,255,255,0.16);"
            "  min-height: 40px; border-radius: 4px; }"
            "QScrollBar::handle:vertical:hover { background: rgba(255,122,0,0.42); }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._grid = QGridLayout(self._container)
        self._grid.setContentsMargins(16, 8, 16, 16)
        self._grid.setSpacing(14)
        self._grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll)

        self._status = QLabel("")
        self._status.setAlignment(Qt.AlignCenter)
        self._status.setStyleSheet(
            "color: rgba(255,255,255,0.35); font-size: 13px; padding: 32px;"
            "background: transparent;")
        self._status.hide()
        layout.addWidget(self._status)

        self._load_stations()

    def _load_stations(self):
        self._stations = self._manager.get_all()

        # Clear grid
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._stations:
            self._status.setText("No hay emisoras. ¡Añade una!")
            self._status.show()
            self._scroll.hide()
            return

        self._status.hide()
        self._scroll.show()

        cols = max(1, (self._scroll.viewport().width() - 32) // 210)
        for i, station in enumerate(self._stations):
            card = _StationCard(station)
            card.play_clicked.connect(
                lambda url=station.url, name=station.name:
                self.station_selected.emit(url, name))
            card.edit_requested.connect(lambda s=station: self._edit_station(s))
            card.delete_requested.connect(lambda s=station: self._delete_station(s))
            row = i // cols
            col = i % cols
            self._grid.addWidget(card, row, col, Qt.AlignTop)

            if i == 0:
                self._grid.setColumnMinimumWidth(col, 200)

    def _add_station(self):
        dialog = RadioDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, url, image_path = dialog.get_data()
            if name and url:
                self._manager.add(name, url, image_path)
                self._load_stations()
            else:
                QMessageBox.warning(self, "Datos incompletos",
                                    "Por favor, ingresa nombre y URL.")

    def _edit_station(self, station):
        dialog = RadioDialog(self, station.name, station.url, station.image_path)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, url, image_path = dialog.get_data()
            if name and url:
                self._manager.update(station.id, name, url, image_path)
                self._load_stations()

    def _delete_station(self, station):
        reply = QMessageBox.question(
            self, "Eliminar emisora",
            f"¿Eliminar '{station.name}'?",
            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self._manager.remove(station.id)
            self._load_stations()


class _StationCard(QFrame):
    play_clicked = Signal()
    edit_requested = Signal()
    delete_requested = Signal()

    def __init__(self, station, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 210)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QFrame {
                background: rgba(255,255,255,0.045);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 14px;
            }
            QFrame:hover {
                background: rgba(255,255,255,0.075);
                border: 1px solid rgba(255,122,0,0.25);
            }
        """)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_menu)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Image or placeholder
        img_label = QLabel()
        img_label.setFixedSize(184, 100)
        img_label.setAlignment(Qt.AlignCenter)
        img_label.setStyleSheet(
            "QLabel { background: rgba(255,255,255,0.035); border-radius: 8px; }")

        if station.image_path and os.path.exists(station.image_path):
            pix = QPixmap(station.image_path)
            if not pix.isNull():
                pix = pix.scaled(180, 96, Qt.KeepAspectRatio,
                                 Qt.SmoothTransformation)
                img_label.setPixmap(pix)
            else:
                img_label.setText("📻")
                img_label.setStyleSheet(
                    "QLabel { background: rgba(255,255,255,0.035);"
                    "  color: rgba(255,255,255,0.15); font-size: 36px;"
                    "  border-radius: 8px; }")
        else:
            img_label.setText("📻")
            img_label.setStyleSheet(
                "QLabel { background: rgba(255,255,255,0.035);"
                "  color: rgba(255,255,255,0.15); font-size: 36px;"
                "  border-radius: 8px; }")
        layout.addWidget(img_label, alignment=Qt.AlignCenter)

        # Name
        name = station.name[:25] + "..." if len(station.name) > 25 else station.name
        name_lbl = QLabel(name)
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.84); font-size: 12px;"
            "  font-weight: 550; background: transparent; }")
        name_lbl.setWordWrap(False)
        layout.addWidget(name_lbl)

        # URL abbreviated
        url_short = station.url[:35] + "..." if len(station.url) > 35 else station.url
        url_lbl = QLabel(url_short)
        url_lbl.setAlignment(Qt.AlignCenter)
        url_lbl.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.35); font-size: 9px;"
            "  background: transparent; }")
        layout.addWidget(url_lbl)

        # Play button
        play_btn = QPushButton("▶ Reproducir")
        play_btn.setFlat(True)
        play_btn.setStyleSheet(
            "QPushButton { color: #FF7A00; font-size: 11px; font-weight: 550;"
            "  background: transparent; border-radius: 8px; padding: 4px; }"
            "QPushButton:hover { background: rgba(255,122,0,0.12); }")
        play_btn.clicked.connect(self.play_clicked.emit)
        layout.addWidget(play_btn)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.play_clicked.emit()

    def _on_menu(self, pos):
        menu = QMenu(self)
        menu.addAction("Editar", self.edit_requested.emit)
        menu.addAction("Eliminar", self.delete_requested.emit)
        menu.exec(self.mapToGlobal(pos))


class RadioDialog(QDialog):
    def __init__(self, parent=None, name: str = "", url: str = "",
                 image_path: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Añadir emisora" if not name else "Editar emisora")
        self.setMinimumWidth(420)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog { background: #181C25; border-radius: 14px; }
            QLabel { color: rgba(255,255,255,0.6); font-size: 12px; }
            QLineEdit {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 8px; padding: 8px 12px;
                color: rgba(255,255,255,0.88); font-size: 13px;
            }
            QPushButton {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 8px; padding: 8px 16px;
                color: rgba(255,255,255,0.78); font-size: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(8)

        self._name_edit = QLineEdit(name)
        self._name_edit.setPlaceholderText("Ej: Radio Nacional")
        form.addRow("Nombre:", self._name_edit)

        self._url_edit = QLineEdit(url)
        self._url_edit.setPlaceholderText("https://ejemplo.com/stream.mp3")
        form.addRow("URL:", self._url_edit)

        # Image row
        img_row = QHBoxLayout()
        self._image_path = image_path
        self._image_label = QLabel(
            os.path.basename(image_path) if image_path else "Sin imagen")
        self._image_label.setStyleSheet(
            "color: rgba(255,255,255,0.40); font-size: 11px;"
            "background: rgba(255,255,255,0.04); border-radius: 6px; padding: 5px 10px;")
        img_btn = QPushButton("Seleccionar imagen")
        img_btn.clicked.connect(self._pick_image)
        img_row.addWidget(self._image_label, 1)
        img_row.addWidget(img_btn)
        form.addRow("Logo:", img_row)

        layout.addLayout(form)

        help_lbl = QLabel(
            "Formatos soportados: MP3, OGG, AAC, Opus, etc.\n"
            "Busca enlaces .pls, .m3u o streams directos.")
        help_lbl.setStyleSheet("color: rgba(255,255,255,0.30); font-size: 10px;")
        help_lbl.setWordWrap(True)
        layout.addWidget(help_lbl)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _pick_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar imagen", os.path.expanduser("~"),
            "Imágenes (*.png *.jpg *.jpeg *.webp *.svg)")
        if path:
            self._image_path = path
            self._image_label.setText(os.path.basename(path))

    def get_data(self) -> tuple:
        return (self._name_edit.text().strip(),
                self._url_edit.text().strip(),
                self._image_path)


# Import at bottom to avoid circular imports
from streaming.radio_manager import RadioManager
