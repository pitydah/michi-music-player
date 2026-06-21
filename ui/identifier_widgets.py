"""Identifier Widgets — premium glass cards for the music identifier dashboard."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
)


class _GlassCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(
            "QFrame#idCard { background: rgba(255,255,255,0.035);"
            "  border: 1px solid rgba(255,255,255,0.065);"
            "  border-radius: 18px; }"
            "QLabel { background: transparent; }")
        self.setObjectName("idCard")


class _GlassButton(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setStyleSheet(
            "QPushButton { color: rgba(255,255,255,0.78); font-size: 11px;"
            "  font-weight: 600; background: rgba(255,255,255,0.06);"
            "  border: 1px solid rgba(255,255,255,0.09);"
            "  border-radius: 10px; padding: 7px 14px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.11);"
            "  border: 1px solid rgba(255,255,255,0.15); }")
        self.setCursor(Qt.PointingHandCursor)


class _PrimaryButton(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setStyleSheet(
            "QPushButton { color: #fff; font-size: 12px; font-weight: 740;"
            "  background: rgba(70,145,255,0.22);"
            "  border: 1px solid rgba(90,165,255,0.42);"
            "  border-radius: 12px; padding: 9px 18px; }"
            "QPushButton:hover { background: rgba(90,165,255,0.32);"
            "  border: 1px solid rgba(120,190,255,0.56); }")
        self.setCursor(Qt.PointingHandCursor)


class StatusPill(QLabel):
    STATES = {
        "listening": ("rgba(52,199,89,0.88)", "#34C759"),
        "paused": ("rgba(255,255,255,0.52)", "rgba(255,255,255,0.12)"),
        "processing": ("rgba(175,82,250,0.88)", "#AF52FA"),
        "identified": ("rgba(52,199,89,0.88)", "#34C759"),
        "no_match": ("rgba(255,255,255,0.42)", "rgba(255,255,255,0.12)"),
        "error": ("rgba(255,69,58,0.88)", "#FF453A"),
        "idle": ("rgba(255,255,255,0.42)", "rgba(255,255,255,0.12)"),
    }
    LABELS = {
        "idle": "Inactivo", "listening": "Escuchando",
        "paused": "Pausado", "processing": "Identificando",
        "identified": "Detectado", "error": "Error",
        "no_match": "Sin coincidencia",
    }

    def __init__(self, text: str = "", state: str = "idle"):
        super().__init__(text)
        self._state = state
        self._refresh()

    def set_state(self, state: str):
        self._state = state
        self._refresh()

    def _refresh(self):
        c, bg = self.STATES.get(self._state, self.STATES["idle"])
        label = self.LABELS.get(self._state, self._state)
        self.setText(label)
        self.setStyleSheet(
            f"font-size: 11px; font-weight: 700; color: {c};"
            f"background: rgba(255,255,255,0.04);"
            f"border: 1px solid rgba(255,255,255,0.07);"
            f"border-radius: 9px; padding: 5px 11px;")


class DetectionResultCard(QFrame):
    play_requested = Signal(dict)
    search_requested = Signal(dict)
    delete_requested = Signal(dict)

    def __init__(self, track: dict):
        super().__init__()
        self._track = track
        self.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.035);"
            "  border: 1px solid rgba(255,255,255,0.06);"
            "  border-radius: 14px; }"
            "QFrame:hover { background: rgba(255,255,255,0.055);"
            "  border: 1px solid rgba(255,255,255,0.10); }"
            "QLabel { background: transparent; }")
        self.setCursor(Qt.ArrowCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(12)

        # Info column
        info = QVBoxLayout()
        info.setSpacing(2)

        title_text = track.get("title", "Sin titulo")
        artist_text = track.get("artist", "")
        line1 = f"{title_text} — {artist_text}" if artist_text else title_text
        t = QLabel(line1[:60])
        t.setStyleSheet(
            "font-size: 13px; font-weight: 650; color: rgba(255,255,255,0.85);")
        info.addWidget(t)

        parts = []
        source = track.get("source", "") or track.get("source_label", "")
        provider = track.get("provider", "")
        match_status = track.get("match_status", "")
        if source:
            parts.append(_source_label(source))
        if provider:
            parts.append(provider)
        if match_status == "matched":
            parts.append("En biblioteca")
        line2 = " \u00b7 ".join(parts)
        s = QLabel(line2)
        s.setStyleSheet("font-size: 11px; color: rgba(255,255,255,0.42);")
        info.addWidget(s)

        lay.addLayout(info, 1)

        # Actions
        if track.get("matched_filepath") or track.get("matched_library_id"):
            play_btn = _GlassButton("Reproducir")
            play_btn.clicked.connect(lambda: self.play_requested.emit(track))
            lay.addWidget(play_btn)

        search_btn = _GlassButton("Buscar")
        search_btn.clicked.connect(lambda: self.search_requested.emit(track))
        lay.addWidget(search_btn)

        del_btn = _GlassButton("X")
        del_btn.setFixedWidth(32)
        del_btn.setStyleSheet(del_btn.styleSheet() + (
            "QPushButton:hover { color: #FF453A; }"))
        del_btn.clicked.connect(lambda: self.delete_requested.emit(track))
        lay.addWidget(del_btn)


class EmptyState(QWidget):
    def __init__(self, title: str, subtitle: str = ""):
        super().__init__()
        self.setStyleSheet("background: transparent;")
        el = QVBoxLayout(self)
        el.setAlignment(Qt.AlignCenter)
        el.setContentsMargins(24, 32, 24, 32)
        el.setSpacing(6)

        t = QLabel(title)
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet(
            "font-size: 14px; font-weight: 600; color: rgba(255,255,255,0.48);")
        el.addWidget(t)

        if subtitle:
            s = QLabel(subtitle)
            s.setAlignment(Qt.AlignCenter)
            s.setWordWrap(True)
            s.setStyleSheet(
                "font-size: 11px; color: rgba(255,255,255,0.32);")
            el.addWidget(s)


def _source_label(source: str) -> str:
    return {
        "radio": "Radio", "navidrome": "Navidrome",
        "jellyfin": "Jellyfin", "remote_stream": "Stream",
        "local_file": "Archivo local", "manual": "Manual",
    }.get(source, source or "Desconocido")
