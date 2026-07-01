"""GenreStatsPanel — detailed stats panel for a genre, embedded in detail views."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QGridLayout, QLabel, QFrame

from ui.central.central_styles import card_title_qss

_TEXT2 = "rgba(255,255,255,0.78)"
_TEXT3 = "rgba(255,255,255,0.62)"


def _format_dur(secs: float) -> str:
    if secs <= 0:
        return ""
    s = int(secs)
    h = s // 3600
    m = (s % 3600) // 60
    return f"{h} h {m} min" if h > 0 else f"{m} min"


class GenreStatsPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("genreStatsPanel")
        self.setStyleSheet(
            "QFrame#genreStatsPanel { background: rgba(255,255,255,0.03);"
            "border: 1px solid rgba(255,255,255,0.045); border-radius: 14px; }"
            "QLabel { background: transparent; border: none; }")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(18, 14, 18, 14)
        self._layout.setSpacing(4)

    def set_stats(self, g: dict):
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        hdr = QLabel("Estadísticas")
        hdr.setStyleSheet(card_title_qss())
        self._layout.addWidget(hdr)

        rows = [
            ("Canciones", str(g.get("track_count", 0))),
            ("Álbumes", str(g.get("album_count", 0))),
            ("Artistas", str(g.get("artist_count", 0))),
            ("Duración", _format_dur(g.get("duration_total", 0)) or "—"),
            ("Calidad", g.get("dominant_quality", "—")),
            ("Lossless", str(g.get("lossless_count", 0))),
            ("Lossy", str(g.get("lossy_count", 0))),
            ("Hi-Res", str(g.get("hires_count", 0))),
            ("Sin metadata", str(g.get("missing_metadata_count", 0))),
            ("Reproducciones", str(g.get("play_count", 0))),
        ]

        grid = QGridLayout()
        grid.setSpacing(3)
        for ri, (label, val) in enumerate(rows):
            kl = QLabel(label)
            kl.setStyleSheet(f"color: {_TEXT3}; font-size: 11px;")
            vl = QLabel(val)
            vl.setStyleSheet(f"color: {_TEXT2}; font-size: 11px; font-weight: 600;")
            grid.addWidget(kl, ri, 0, Qt.AlignTop)
            grid.addWidget(vl, ri, 1, Qt.AlignTop)
        self._layout.addLayout(grid)
