"""Artist match dialog — let the user select the correct TheAudioDB match."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QWidget,
)
from PySide6.QtCore import Qt, Signal

from integrations.theaudiodb.models import ArtistExternalInfo


class ArtistMatchDialog(QDialog):
    artist_chosen = Signal(object)  # ArtistExternalInfo | None = skip
    skip_requested = Signal()

    def __init__(self, artist_name: str, candidates: list[ArtistExternalInfo],
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Seleccionar artista: {artist_name}")
        self.setMinimumSize(460, 400)
        self.setModal(True)
        self.setStyleSheet(
            "QDialog { background: #0d1116; }"
            "QLabel { background: transparent; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        title = QLabel(f"Coincidencias para \"{artist_name}\"")
        title.setStyleSheet(
            "font-size: 16px; font-weight: 700; color: rgba(255,255,255,0.88);")
        layout.addWidget(title)

        sub = QLabel(
            "Selecciona el artista correcto de TheAudioDB o ignora la info externa.")
        sub.setStyleSheet("font-size: 11px; color: rgba(255,255,255,0.48);")
        sub.setWordWrap(True)
        layout.addWidget(sub)
        layout.addSpacing(6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        cl = QVBoxLayout(container)
        cl.setSpacing(8)

        for c in candidates:
            card = _CandidateCard(c)
            card.chosen.connect(lambda info=c: self._on_choose(info))
            cl.addWidget(card)

        cl.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

        # Skip button
        btns = QHBoxLayout()
        btns.addStretch()
        skip_btn = QPushButton("No usar info externa")
        skip_btn.setStyleSheet(
            "QPushButton { color: rgba(255,255,255,0.52); font-size: 12px;"
            "  background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.07);"
            "  border-radius: 10px; padding: 8px 18px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.08); }")
        skip_btn.setCursor(Qt.PointingHandCursor)
        skip_btn.clicked.connect(self._on_skip)
        btns.addWidget(skip_btn)
        layout.addLayout(btns)

    def _on_choose(self, info: ArtistExternalInfo):
        self.artist_chosen.emit(info)
        self.accept()

    def _on_skip(self):
        self.skip_requested.emit()
        self.reject()


class _CandidateCard(QFrame):
    chosen = Signal()

    def __init__(self, info: ArtistExternalInfo):
        super().__init__()
        self._info = info
        self.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.035);"
            "  border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; }"
            "QFrame:hover { background: rgba(255,255,255,0.06);"
            "  border: 1px solid rgba(255,255,255,0.11); }")
        self.setCursor(Qt.PointingHandCursor)

        h = QHBoxLayout(self)
        h.setContentsMargins(12, 10, 12, 10)
        h.setSpacing(12)

        # Thumb
        thumb = QLabel()
        thumb.setFixedSize(56, 56)
        thumb.setStyleSheet(
            "background: rgba(255,255,255,0.04); border-radius: 10px;"
            "border: 1px solid rgba(255,255,255,0.06);")
        thumb.setAlignment(Qt.AlignCenter)
        h.addWidget(thumb)

        # Info
        v = QVBoxLayout()
        v.setSpacing(2)
        name = QLabel(info.name or "Sin nombre")
        name.setStyleSheet(
            "font-size: 13px; font-weight: 700; color: rgba(255,255,255,0.88);")
        v.addWidget(name)

        details = []
        if info.genre:
            details.append(info.genre)
        if info.country:
            details.append(info.country)
        if info.formed_year:
            details.append(str(info.formed_year))
        if details:
            det = QLabel(" \u00b7 ".join(details))
            det.setStyleSheet(
                "font-size: 11px; color: rgba(255,255,255,0.42);")
            v.addWidget(det)

        if info.biography_preferred:
            bio = QLabel(info.biography_preferred[:120] + (
                "\u2026" if len(info.biography_preferred) > 120 else ""))
            bio.setStyleSheet(
                "font-size: 10.5px; color: rgba(255,255,255,0.38);")
            bio.setWordWrap(True)
            v.addWidget(bio)

        h.addLayout(v, 1)
        h.addStretch()

        btn = QPushButton("Usar este")
        btn.setFixedSize(90, 32)
        btn.setStyleSheet(
            "QPushButton { color: #FFFFFF; font-size: 11px; font-weight: 600;"
            "  background: rgba(70,145,255,0.20);"
            "  border: 1px solid rgba(90,165,255,0.35);"
            "  border-radius: 8px; }"
            "QPushButton:hover { background: rgba(90,165,255,0.30); }")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self.chosen.emit)
        h.addWidget(btn)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.chosen.emit()
        super().mousePressEvent(event)
