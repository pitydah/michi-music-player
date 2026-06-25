"""TrackRefTableModel — adapts list[TrackRef] to QStandardItemModel for QTableView."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel, QBrush, QColor

from sources.base_source import TrackRef


class TrackRefTableModel(QStandardItemModel):
    COL_TRACK = 0
    COL_TITLE = 1
    COL_ARTIST = 2
    COL_ALBUM = 3
    COL_YEAR = 4
    COL_GENRE = 5
    COL_DURATION = 6
    COL_URI = 7

    def __init__(self, parent=None):
        super().__init__(0, 8, parent)
        self.setHorizontalHeaderLabels(
            ["Nº pista", "Título", "Artista", "Álbum",
             "Año", "Género", "Duración", "Ruta"])

    def populate(self, items: list[TrackRef]):
        self.removeRows(0, self.rowCount())
        for item in items:
            # Track number
            tr = QStandardItem()
            tr.setEditable(False)
            tr.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            tr.setForeground(QBrush(QColor("rgba(255,255,255,0.72)")))
            tn = self._parse_track_number(item.track_number)
            if tn is not None:
                tr.setText(str(tn))
                tr.setData(tn, Qt.UserRole)
            else:
                tr.setText("—")

            # Title
            t = QStandardItem(item.title or "Sin título")
            t.setEditable(False)
            t.setToolTip(item.uri)
            t.setData(item, Qt.UserRole)

            a = QStandardItem(item.artist)
            a.setEditable(False)
            al = QStandardItem(item.album)
            al.setEditable(False)

            # Year: store as int for numeric sorting
            y = QStandardItem()
            y.setEditable(False)
            y.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            y.setForeground(QBrush(QColor("#8e8e93")))
            if item.year:
                y.setText(str(item.year))
                y.setData(item.year, Qt.UserRole)
            else:
                y.setText("—")

            g = QStandardItem(item.genre or "—")
            g.setEditable(False)

            # Duration: store formatted text but sort by raw seconds
            d = QStandardItem()
            d.setEditable(False)
            d.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            d.setForeground(QBrush(QColor("#8e8e93")))
            if item.duration:
                d.setText(self._fmt_duration(item.duration))
                d.setData(item.duration, Qt.UserRole)
            else:
                d.setText("—")

            uri = QStandardItem(item.uri)
            uri.setEditable(False)
            self.appendRow([tr, t, a, al, y, g, d, uri])

    def get_trackref(self, row: int) -> TrackRef | None:
        idx = self.index(row, self.COL_TITLE)
        return self.data(idx, Qt.UserRole)

    @staticmethod
    def _parse_track_number(value) -> int | None:
        if not value and value != 0:
            return None
        text = str(value).strip()
        if "/" in text:
            text = text.split("/", 1)[0].strip()
        try:
            return int(text)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _fmt_duration(seconds: float) -> str:
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m}:{s:02d}"
