"""Music Identifier View — control panel + detected tracks history."""

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QFrame,
)


class MusicIdentifierView(QWidget):
    toggle_requested = Signal(bool)
    clear_requested = Signal()
    track_selected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._enabled = False
        self._status = "idle"

        main = QVBoxLayout(self)
        main.setContentsMargins(32, 24, 32, 24)
        main.setSpacing(16)

        # ── Block 1: Control card ──
        card1 = QFrame()
        card1.setStyleSheet("""
            QFrame {
                background: rgba(255,255,255,0.055);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 18px;
                padding: 22px;
            }
        """)
        c1 = QVBoxLayout(card1)
        c1.setContentsMargins(22, 18, 22, 18)
        c1.setSpacing(10)

        title_lbl = QLabel("Identificador musical")
        title_lbl.setStyleSheet(
            "font-size:17px;font-weight:650;color:rgba(245,245,247,0.92);"
            "background:transparent;border:none;")
        c1.addWidget(title_lbl)

        desc = QLabel(
            "Detecta canciones que suenan en radio, streaming o reproducción "
            "local y guarda un historial para revisarlas después.")
        desc.setWordWrap(True)
        desc.setStyleSheet(
            "font-size:12px;color:rgba(245,245,247,0.56);"
            "background:transparent;border:none;")
        c1.addWidget(desc)

        c1.addSpacing(8)

        # Button + status row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self._toggle_btn = QPushButton("Activar identificador")
        self._toggle_btn.setFixedHeight(36)
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_btn.clicked.connect(self._on_toggle)
        self._toggle_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,122,0,0.12);
                border: 1px solid rgba(255,122,0,0.25);
                border-radius: 10px;
                padding: 0 18px;
                color: #FF7A00;
                font-size: 13px;
                font-weight: 550;
            }
            QPushButton:hover {
                background: rgba(255,122,0,0.20);
                border-color: rgba(255,122,0,0.4);
            }
        """)
        btn_row.addWidget(self._toggle_btn)

        self._status_label = QLabel("Inactivo")
        self._status_label.setStyleSheet(
            "font-size:12px;color:rgba(245,245,247,0.40);"
            "background:transparent;border:none;")
        btn_row.addWidget(self._status_label)
        btn_row.addStretch()
        c1.addLayout(btn_row)

        self._status_message = QLabel("")
        self._status_message.setStyleSheet(
            "font-size:11px;color:rgba(245,245,247,0.35);"
            "background:transparent;border:none;")
        c1.addWidget(self._status_message)

        main.addWidget(card1)

        # ── Block 2: History card ──
        card2 = QFrame()
        card2.setStyleSheet("""
            QFrame {
                background: rgba(255,255,255,0.055);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 18px;
                padding: 22px;
            }
        """)
        c2 = QVBoxLayout(card2)
        c2.setContentsMargins(22, 18, 22, 18)
        c2.setSpacing(10)

        hist_title = QLabel("Canciones detectadas")
        hist_title.setStyleSheet(
            "font-size:17px;font-weight:650;color:rgba(245,245,247,0.92);"
            "background:transparent;border:none;")
        c2.addWidget(hist_title)

        hist_desc = QLabel(
            "Las canciones identificadas aparecerán aquí con hora, "
            "fuente y proveedor.")
        hist_desc.setWordWrap(True)
        hist_desc.setStyleSheet(
            "font-size:12px;color:rgba(245,245,247,0.56);"
            "background:transparent;border:none;")
        c2.addWidget(hist_desc)

        c2.addSpacing(4)

        self._list = QListWidget()
        self._list.setFrameShape(QFrame.NoFrame)
        self._list.setStyleSheet("""
            QListWidget {
                background: transparent; border: none;
            }
            QListWidget::item {
                padding: 10px 14px;
                border-bottom: 1px solid rgba(255,255,255,0.05);
                border-radius: 8px;
                margin: 1px 4px;
            }
            QListWidget::item:hover {
                background: rgba(255,255,255,0.04);
            }
        """)
        self._list.doubleClicked.connect(self._on_item_dbl)
        c2.addWidget(self._list, stretch=1)

        self._empty_label = QLabel("Aún no hay canciones detectadas.")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet(
            "font-size:13px;color:rgba(245,245,247,0.35);"
            "background:transparent;border:none;")
        c2.addWidget(self._empty_label)

        # Clear button
        btn_row2 = QHBoxLayout()
        btn_row2.addStretch()
        clear_btn = QPushButton("Limpiar historial")
        clear_btn.setFlat(True)
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet(
            "QPushButton { color:rgba(245,245,247,0.4);font-size:12px; }"
            "QPushButton:hover { color:#FF3C48; }")
        clear_btn.clicked.connect(self.clear_requested.emit)
        btn_row2.addWidget(clear_btn)
        c2.addLayout(btn_row2)

        main.addWidget(card2, stretch=1)

    def _on_toggle(self):
        self._enabled = not self._enabled
        self.toggle_requested.emit(self._enabled)

    def _on_item_dbl(self, item):
        data = item.data(Qt.UserRole)
        if data:
            self.track_selected.emit(data)

    # ── Public API ──

    def set_identifier_state(self, state: str):
        self._status = state
        labels = {
            "idle": "Inactivo",
            "listening": "Escuchando…",
            "processing": "Identificando…",
            "identified": "Canción detectada",
            "error": "Error",
        }
        colors = {
            "idle": "rgba(245,245,247,0.40)",
            "listening": "#FF7A00",
            "processing": "#DD007A",
            "identified": "#34c759",
            "error": "#FF3C48",
        }
        self._status_label.setText(labels.get(state, state))
        self._status_label.setStyleSheet(
            f"font-size:12px;color:{colors.get(state, colors['idle'])};"
            "background:transparent;border:none;")

    def set_identifier_enabled(self, enabled: bool):
        self._enabled = enabled
        if enabled:
            self._toggle_btn.setText("Desactivar identificador")
            self._toggle_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 #FF4D2E, stop:1 #DD007A
                    );
                    border: none;
                    border-radius: 10px;
                    padding: 0 18px;
                    color: #ffffff;
                    font-size: 13px;
                    font-weight: 550;
                }
                QPushButton:hover {
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 #FF6E4E, stop:1 #EE2288
                    );
                }
            """)
        else:
            self._toggle_btn.setText("Activar identificador")
            self._toggle_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255,122,0,0.12);
                    border: 1px solid rgba(255,122,0,0.25);
                    border-radius: 10px;
                    padding: 0 18px;
                    color: #FF7A00;
                    font-size: 13px;
                    font-weight: 550;
                }
                QPushButton:hover {
                    background: rgba(255,122,0,0.20);
                    border-color: rgba(255,122,0,0.4);
                }
            """)

    def set_status_message(self, text: str):
        self._status_message.setText(text)

    def set_detected_tracks(self, tracks: list[dict]):
        self._list.clear()
        if not tracks:
            self._empty_label.setVisible(True)
            return

        self._empty_label.setVisible(False)
        for t in tracks:
            dt = t.get("detected_at", 0)
            time_str = ""
            if dt:
                d = datetime.fromtimestamp(dt)
                time_str = d.strftime("%H:%M")

            title = t.get("title", "Sin título")
            artist = t.get("artist", "")
            source = t.get("source", "")
            provider = t.get("provider", "")

            line1 = f"{title} — {artist}" if artist else title
            line2_parts = []
            if time_str:
                line2_parts.append(time_str)
            if source:
                line2_parts.append(source)
            if provider:
                line2_parts.append(provider)
            line2 = " · ".join(line2_parts)

            item = QListWidgetItem()
            item.setData(Qt.UserRole, t)
            item.setSizeHint(item.sizeHint())
            self._list.addItem(item)

            w = QWidget()
            w.setStyleSheet("background:transparent;")
            l = QVBoxLayout(w)
            l.setContentsMargins(0, 0, 0, 0)
            l.setSpacing(2)

            l1 = QLabel(line1)
            l1.setStyleSheet(
                "font-size:13px;font-weight:550;color:rgba(245,245,247,0.85);"
                "background:transparent;border:none;")
            l.addWidget(l1)

            l2 = QLabel(line2)
            l2.setStyleSheet(
                "font-size:11px;color:rgba(245,245,247,0.45);"
                "background:transparent;border:none;")
            l.addWidget(l2)

            self._list.setItemWidget(item, w)
