"""TrackRefTableModel — adapts list[TrackRef] to QStandardItemModel for QTableView."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel, QBrush, QColor

from sources.base_source import TrackRef


class TrackRefTableModel(QStandardItemModel):
    COL_TITLE = 0; COL_ARTIST = 1; COL_ALBUM = 2
    COL_YEAR = 3; COL_GENRE = 4; COL_DURATION = 5; COL_URI = 6

    def __init__(self, parent=None):
        super().__init__(0, 7, parent)
        self.setHorizontalHeaderLabels(
            ["Título", "Artista", "Álbum", "Año", "Género", "Duración", ""])

    def populate(self, items: list[TrackRef]):
        self.removeRows(0, self.rowCount())
        for item in items:
            t = QStandardItem(item.title or "Sin título")
            t.setEditable(False); t.setToolTip(item.uri)
            t.setData(item, Qt.UserRole)
            a = QStandardItem(item.artist); a.setEditable(False)
            al = QStandardItem(item.album); al.setEditable(False)

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

            g = QStandardItem(item.genre or "—"); g.setEditable(False)

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

            uri = QStandardItem(item.uri); uri.setEditable(False)
            self.appendRow([t, a, al, y, g, d, uri])

    def get_trackref(self, row: int) -> TrackRef | None:
        idx = self.index(row, self.COL_TITLE)
        return self.data(idx, Qt.UserRole)

    @staticmethod
    def _fmt_duration(seconds: float) -> str:
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m}:{s:02d}"
