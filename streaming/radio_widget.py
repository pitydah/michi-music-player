"""Radio Widget — premium glass card mosaic of radio stations."""
import os
import re

from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QPixmap, QDesktopServices
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QScrollArea, QGridLayout, QFrame, QMenu, QMessageBox,
    QFileDialog, QLineEdit, QDialog, QFormLayout, QDialogButtonBox,
    QApplication,
)

from streaming.radio_manager import RadioManager
from ui.icon_loader import get_sidebar_icon


class RadioWidget(QWidget):
    station_selected = Signal(str, str)  # url, name
    count_changed = Signal(int, int)     # visible, total

    def __init__(self, manager: RadioManager | None = None, parent=None):
        super().__init__(parent)
        self._manager = manager or RadioManager()
        self._stations = []
        self._filter_text = ""
        self._filtered: list = []

        self.setStyleSheet("background: transparent;")

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
            "color: rgba(255,255,255,0.88); font-size: 15px; font-weight: 600;"
            "background: transparent;")
        subtitle = QLabel("Agrega radios por URL y organízalas como mosaico")
        subtitle.setStyleSheet(
            "color: rgba(255,255,255,0.48); font-size: 11px; background: transparent;")
        title_col.addWidget(title_lbl)
        title_col.addWidget(subtitle)
        header.addLayout(title_col)
        header.addStretch()

        self._add_btn = QPushButton("+ Añadir emisora")
        self._add_btn.setStyleSheet("""
            QPushButton {
                background: rgba(143,183,255,0.12);
                border: 1px solid rgba(143,183,255,0.28);
                border-radius: 10px;
                padding: 7px 16px;
                color: rgba(255,255,255,0.94);
                font-size: 12px;
                font-weight: 550;
            }
            QPushButton:hover {
                background: rgba(143,183,255,0.22);
                border-color: rgba(143,183,255,0.44);
            }
        """)
        self._add_btn.clicked.connect(self._add_station)
        header.addWidget(self._add_btn)
        layout.addLayout(header)

        # Scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { width: 3px; background: transparent; border: none; }"
            "QScrollBar::handle:vertical { background: rgba(255,255,255,0.12);"
            "  min-height: 32px; border-radius: 2px; }"
            "QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.24); }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._grid = QGridLayout(self._container)
        self._grid.setContentsMargins(16, 8, 16, 16)
        self._grid.setSpacing(14)
        self._grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll)

        # Empty state
        self._empty = QFrame()
        self._empty.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.025);"
            "  border: 1px solid rgba(255,255,255,0.06); border-radius: 18px; }")
        ev = QVBoxLayout(self._empty)
        ev.setAlignment(Qt.AlignCenter)
        ev.setContentsMargins(60, 48, 60, 48)
        ev.setSpacing(6)
        self._empty_icon = QLabel()
        self._empty_icon.setPixmap(get_sidebar_icon("radio_speaker", size=48))
        self._empty_icon.setAlignment(Qt.AlignCenter)
        self._empty_icon.setStyleSheet(
            "font-size: 40px; background: transparent; border: none;")
        ev.addWidget(self._empty_icon)
        self._empty_title = QLabel("No hay emisoras")
        self._empty_title.setAlignment(Qt.AlignCenter)
        self._empty_title.setStyleSheet(
            "color: rgba(255,255,255,0.84); font-size: 15px; font-weight: 600;"
            "background: transparent;")
        ev.addWidget(self._empty_title)
        self._empty_sub = QLabel("Añade una URL de radio para empezar")
        self._empty_sub.setAlignment(Qt.AlignCenter)
        self._empty_sub.setStyleSheet(
            "color: rgba(255,255,255,0.52); font-size: 12px; background: transparent;")
        ev.addWidget(self._empty_sub)
        empty_btn = QPushButton("Añadir emisora")
        empty_btn.setFixedSize(160, 38)
        empty_btn.setCursor(Qt.PointingHandCursor)
        empty_btn.setStyleSheet("""
            QPushButton {
                background: rgba(143,183,255,0.12);
                border: 1px solid rgba(143,183,255,0.28);
                border-radius: 10px;
                color: rgba(255,255,255,0.94);
                font-size: 12.5px; font-weight: 550;
            }
            QPushButton:hover {
                background: rgba(143,183,255,0.22);
            }
        """)
        empty_btn.clicked.connect(self._add_station)
        ev.addWidget(empty_btn, alignment=Qt.AlignCenter)
        self._empty.hide()
        layout.addWidget(self._empty)

        self._load_stations()

    def set_filter(self, text: str):
        self._filter_text = text.lower().strip()
        self._load_stations()

    def reload(self):
        self._stations = self._manager.get_all()
        self._load_stations()

    def _load_stations(self):
        self._stations = self._manager.get_all()

        # Apply filter
        if self._filter_text:
            q = self._filter_text
            self._filtered = [
                s for s in self._stations
                if q in s.name.lower() or q in s.url.lower()
                or any(q in t.lower() for t in s.tags)
            ]
        else:
            self._filtered = list(self._stations)

        # Clear grid
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        total = len(self._stations)
        visible = len(self._filtered)
        self.count_changed.emit(visible, total)

        if not self._filtered:
            self._scroll.hide()
            self._empty.show()
            if self._filter_text:
                self._empty_title.setText("Sin resultados")
                self._empty_sub.setText(
                    f"No hay emisoras que coincidan con \"{self._filter_text}\"")
                self._empty_icon.setText("🔍")
            else:
                self._empty_title.setText("No hay emisoras")
                self._empty_sub.setText("Añade una URL de radio para empezar")
                self._empty_icon.setPixmap(get_sidebar_icon("radio_speaker", size=48))
            return

        self._empty.hide()
        self._scroll.show()

        cols = max(1, (self._scroll.viewport().width() - 32) // 210)
        for i, station in enumerate(self._filtered):
            card = _StationCard(station, self._manager)
            card.play_clicked.connect(
                lambda url=station.url, name=station.name, sid=station.id:
                self._play_station(url, name, sid))
            card.station_changed.connect(self.reload)
            row = i // cols
            col = i % cols
            self._grid.addWidget(card, row, col, Qt.AlignTop)

    def _play_station(self, url, name, station_id):
        self._manager.mark_played(station_id)
        self.station_selected.emit(url, name)

    def _add_station(self):
        dialog = RadioDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data["name"] or not data["url"]:
                QMessageBox.warning(self, "Datos incompletos",
                                    "Por favor, ingresa nombre y URL.")
                return
            existing = self._manager.find_by_url(data["url"])
            if existing:
                QMessageBox.warning(
                    self, "URL duplicada",
                    f"Ya existe la emisora '{existing.name}' con esta URL.")
                return
            self._manager.add(**data)
            self.reload()

    def _edit_station(self, station):
        dialog = RadioDialog(
            self, station.name, station.url, station.image_path,
            station.tags, station.homepage, station.country, station.codec)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data["name"] or not data["url"]:
                return
            self._manager.update(station.id, **data)
            self.reload()

    def _delete_station(self, station):
        reply = QMessageBox.question(
            self, "Eliminar emisora",
            f"¿Eliminar '{station.name}'?",
            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self._manager.remove(station.id)
            self.reload()


class _StationCard(QFrame):
    play_clicked = Signal()
    station_changed = Signal()

    def __init__(self, station, manager: RadioManager, parent=None):
        super().__init__(parent)
        self._station = station
        self._manager = manager
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
                border: 1px solid rgba(143,183,255,0.28);
            }
            QFrame[active="true"] {
                background: rgba(255,255,255,0.10);
                border: 1px solid rgba(143,183,255,0.40);
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
                pix = pix.scaled(180, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                img_label.setPixmap(pix)
            else:
                img_label.setPixmap(
                    get_sidebar_icon("radio_speaker", size=56))
                img_label.setStyleSheet(
                    "QLabel { background: rgba(255,255,255,0.035);"
                    "  border-radius: 8px; }")
        else:
            img_label.setPixmap(
                get_sidebar_icon("radio_speaker", size=56))
            img_label.setStyleSheet(
                "QLabel { background: rgba(255,255,255,0.035);"
                "  border-radius: 8px; }")
        layout.addWidget(img_label, alignment=Qt.AlignCenter)

        # Name
        name = station.name[:25] + "…" if len(station.name) > 25 else station.name
        name_lbl = QLabel(name)
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.84); font-size: 12px;"
            "  font-weight: 550; background: transparent; }")
        name_lbl.setWordWrap(False)
        layout.addWidget(name_lbl)

        # URL domain
        domain = _extract_domain(station.url)
        url_lbl = QLabel(domain[:32])
        url_lbl.setAlignment(Qt.AlignCenter)
        url_lbl.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.38); font-size: 9px;"
            "  background: transparent; }")
        layout.addWidget(url_lbl)

        # Badge row
        badge_row = QHBoxLayout()
        badge_row.setSpacing(4)
        badge_row.setAlignment(Qt.AlignCenter)
        stream_badge = QLabel("STREAM")
        stream_badge.setStyleSheet(
            "QLabel { color: rgba(143,183,255,0.80); font-size: 8px; font-weight: 600;"
            "  background: rgba(143,183,255,0.12); border-radius: 4px;"
            "  padding: 1px 5px; }")
        badge_row.addWidget(stream_badge)
        if station.favorite:
            fav_badge = QLabel("★")
            fav_badge.setStyleSheet(
                "QLabel { color: rgba(255,220,80,0.88); font-size: 10px;"
                "  background: transparent; }")
            badge_row.addWidget(fav_badge)
        layout.addLayout(badge_row)

        # Play button
        play_btn = QPushButton("▶ Reproducir")
        play_btn.setFlat(True)
        play_btn.setStyleSheet(
            "QPushButton { color: rgba(143,183,255,0.85); font-size: 11px;"
            "  font-weight: 550; background: transparent; border-radius: 8px;"
            "  padding: 4px; }"
            "QPushButton:hover { background: rgba(143,183,255,0.12); }")
        play_btn.clicked.connect(self.play_clicked.emit)
        layout.addWidget(play_btn)

        # Tooltip
        tooltip = f"{station.name}\n{station.url}"
        if station.country:
            tooltip += f"\n{station.country}"
        if station.codec:
            tooltip += f" · {station.codec}"
        self.setToolTip(tooltip)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.play_clicked.emit()

    def _on_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: rgba(18,20,28,0.98);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 12px;
                padding: 6px 4px;
                color: rgba(255,255,255,0.88);
            }
            QMenu::item {
                padding: 7px 32px 7px 16px;
                border-radius: 8px;
            }
            QMenu::item:selected {
                background: rgba(143,183,255,0.16);
                color: rgba(255,255,255,1.00);
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255,255,255,0.08);
                margin: 4px 8px;
            }
        """)

        play = menu.addAction("▶ Reproducir")
        edit = menu.addAction("✏️ Editar emisora")
        dup = menu.addAction("📋 Duplicar emisora")
        menu.addSeparator()
        copy = menu.addAction("🔗 Copiar URL")
        browse = menu.addAction("🌐 Abrir en navegador")
        menu.addSeparator()
        fav_text = "★ Quitar favorita" if self._station.favorite else "☆ Marcar favorita"
        fav = menu.addAction(fav_text)
        menu.addSeparator()
        delete = menu.addAction("🗑️ Eliminar emisora")

        action = menu.exec(self.mapToGlobal(pos))
        if action == play:
            self.play_clicked.emit()
        elif action == edit:
            w = self.window()
            while w and not isinstance(w, QWidget):
                w = w.parentWidget()
            if isinstance(w, RadioWidget):
                w._edit_station(self._station)
        elif action == dup:
            self._manager.duplicate(self._station.id)
            self.station_changed.emit()
        elif action == copy:
            QApplication.clipboard().setText(self._station.url)
        elif action == browse:
            QDesktopServices.openUrl(QUrl(self._station.url))
        elif action == fav:
            self._manager.toggle_favorite(self._station.id)
            self.station_changed.emit()
        elif action == delete:
            reply = QMessageBox.question(
                self, "Eliminar emisora",
                f"¿Eliminar '{self._station.name}'?",
                QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self._manager.remove(self._station.id)
                self.station_changed.emit()


class RadioDialog(QDialog):
    def __init__(self, parent=None, name: str = "", url: str = "",
                 image_path: str = "", tags: list[str] | None = None,
                 homepage: str = "", country: str = "", codec: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Añadir emisora" if not name else "Editar emisora")
        self.setMinimumWidth(440)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog { background: rgba(16,18,24,0.98); border-radius: 14px; }
            QLabel { color: rgba(255,255,255,0.68); font-size: 12px; }
            QLineEdit {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 8px; padding: 8px 12px;
                color: rgba(255,255,255,0.90); font-size: 13px;
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
        self._name_edit.setPlaceholderText("Ej: BBC Radio 1")
        form.addRow("Nombre:", self._name_edit)

        self._url_edit = QLineEdit(url)
        self._url_edit.setPlaceholderText("https://ejemplo.com/stream.mp3")
        form.addRow("URL del stream:", self._url_edit)

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

        self._homepage_edit = QLineEdit(homepage)
        self._homepage_edit.setPlaceholderText("https://... (opcional)")
        form.addRow("Página web:", self._homepage_edit)

        self._country_edit = QLineEdit(country)
        self._country_edit.setPlaceholderText("Ej: Reino Unido (opcional)")
        form.addRow("País:", self._country_edit)

        self._tags_edit = QLineEdit(", ".join(tags) if tags else "")
        self._tags_edit.setPlaceholderText("rock, indie, noticias (opcional)")
        form.addRow("Tags:", self._tags_edit)

        self._codec_edit = QLineEdit(codec)
        self._codec_edit.setPlaceholderText("Ej: MP3 320kbps (opcional)")
        form.addRow("Codec:", self._codec_edit)

        layout.addLayout(form)

        help_lbl = QLabel(
            "Formatos soportados: streams directos, .m3u, .m3u8, .pls\n"
            "Si pegas una URL sin http:// se agregará automáticamente.")
        help_lbl.setStyleSheet("color: rgba(255,255,255,0.32); font-size: 10px;")
        help_lbl.setWordWrap(True)
        layout.addWidget(help_lbl)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.setStyleSheet(
            "QPushButton { padding: 7px 18px; border-radius: 8px; }")
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _pick_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar imagen", os.path.expanduser("~"),
            "Imágenes (*.png *.jpg *.jpeg *.webp *.svg)")
        if path:
            self._image_path = path
            self._image_label.setText(os.path.basename(path))

    def _validate_and_accept(self):
        name = self._name_edit.text().strip()
        url = self._url_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Falta nombre", "Ingresa un nombre para la emisora.")
            self._name_edit.setFocus()
            return
        if not url:
            QMessageBox.warning(self, "Falta URL", "Ingresa la URL del stream.")
            self._url_edit.setFocus()
            return
        if not url.startswith(("http://", "https://")):
            reply = QMessageBox.question(
                self, "URL sin esquema",
                "La URL no comienza con http:// o https://\n\n"
                "¿Deseas agregar http:// automáticamente?",
                QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self._url_edit.setText("http://" + url)
            else:
                self._url_edit.setFocus()
                return
        self.accept()

    def get_data(self) -> dict:
        tags_text = self._tags_edit.text().strip()
        tags = [t.strip() for t in tags_text.split(",") if t.strip()] if tags_text else []
        return {
            "name": self._name_edit.text().strip(),
            "url": self._url_edit.text().strip(),
            "image_path": self._image_path,
            "tags": tags,
            "homepage": self._homepage_edit.text().strip(),
            "country": self._country_edit.text().strip(),
            "codec": self._codec_edit.text().strip(),
        }


def _extract_domain(url: str) -> str:
    m = re.search(r"https?://([^/:]+)", url)
    return m.group(1) if m else url[:32]
