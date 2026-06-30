"""MediaItemTableModel — premium model for Biblioteca > Canciones.

Uses MediaItem directly, not TrackRef. Supports sorting, tooltips,
and optional columns for technical metadata.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex

from library.media_item import MediaItem

_COL_FAV = 0
_COL_STATUS = 1
_COL_TITLE = 2
_COL_ARTIST = 3
_COL_ALBUM = 4
_COL_YEAR = 5
_COL_GENRE = 6
_COL_DURATION = 7
_COL_FORMAT = 8
_COL_QUALITY = 9
_COL_FILEPATH = 10

_BASE_COLUMNS = [
    ("", 28),            # fav star
    ("", 24),            # status badge
    ("Título", 220),
    ("Artista", 200),
    ("Álbum", 200),
    ("Año", 56),
    ("Género", 120),
    ("Duración", 70),
    ("Formato", 64),
    ("Calidad", 120),
    ("Ruta", 200),
]

_OPTIONAL_COLUMNS = {
    "bitrate": ("Bitrate", 80),
    "sample_rate": ("Sample Rate", 90),
    "bit_depth": ("Bit Depth", 72),
    "channels": ("Canales", 64),
    "bpm": ("BPM", 56),
    "key": ("Tonalidad", 64),
    "play_count": ("Reproducciones", 80),
    "last_played": ("Últ. Reproducción", 120),
    "rating": ("Rating", 56),
    "size": ("Tamaño", 80),
    "created_at": ("Agregado", 120),
    "last_scanned": ("Últ. Escaneo", 120),
    "track_uid": ("Track UID", 180),
}

ItemDataRole = Qt.ItemDataRole


class MediaItemTableModel(QAbstractTableModel):
    """Table model for MediaItem-based song library.

    Supports:
    - Base columns (fav, status, title, artist, album, year, genre, duration, format, quality, path)
    - Optional columns (bitrate, sample_rate, bit_depth, channels, bpm, key, etc.)
    - Numeric sorting, tooltips, status data
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[MediaItem] = []
        self._optional_cols: list[str] = []
        self._status_cache: dict[int, dict] = {}
        self._fav_set: set[int] = set()

    # ── Column management ──

    @property
    def base_column_count(self) -> int:
        return len(_BASE_COLUMNS)

    def set_optional_columns(self, cols: list[str]):
        valid = [c for c in cols if c in _OPTIONAL_COLUMNS]
        self._optional_cols = valid

    def get_optional_columns(self) -> list[str]:
        return list(self._optional_cols)

    def column_widths(self) -> list[int]:
        widths = [w for _, w in _BASE_COLUMNS]
        for c in self._optional_cols:
            _, w = _OPTIONAL_COLUMNS[c]
            widths.append(w)
        return widths

    # ── Data management ──

    def populate(self, items: list[MediaItem], fav_ids: set[int] | None = None,
                 status_cache: dict[int, dict] | None = None):
        self.beginResetModel()
        self._items = list(items)
        self._fav_set = set(fav_ids or [])
        self._status_cache = dict(status_cache or {})
        self.endResetModel()

    def item_at(self, row: int) -> MediaItem | None:
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def items_at(self, rows: list[int]) -> list[MediaItem]:
        return [self._items[r] for r in rows if 0 <= r < len(self._items)]

    def all_items(self) -> list[MediaItem]:
        return list(self._items)

    # ── QAbstractTableModel protocol ──

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._items) if not parent.isValid() else 0

    def columnCount(self, parent=QModelIndex()) -> int:
        return self.base_column_count + len(self._optional_cols) if not parent.isValid() else 0

    def headerData(self, section, orientation, role=ItemDataRole.DisplayRole):
        if orientation != Qt.Horizontal or role != ItemDataRole.DisplayRole:
            return None
        if section < self.base_column_count:
            return _BASE_COLUMNS[section][0]
        opt_idx = section - self.base_column_count
        if opt_idx < len(self._optional_cols):
            col_key = self._optional_cols[opt_idx]
            return _OPTIONAL_COLUMNS[col_key][0]
        return None

    def _col_key(self, section: int) -> str | None:
        if section < self.base_column_count:
            return None  # base columns handled directly
        opt_idx = section - self.base_column_count
        if opt_idx < len(self._optional_cols):
            return self._optional_cols[opt_idx]
        return None

    def data(self, index, role=ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        item = self._items[index.row()]
        col = index.column()
        item_id = getattr(item, 'id', 0)

        if role == ItemDataRole.ToolTipRole:
            return self._tooltip(item, col)

        if role == ItemDataRole.DisplayRole:
            return self._display(item, col)

        if role == ItemDataRole.UserRole:
            return item

        if role == Qt.TextAlignmentRole:
            if col in (_COL_YEAR, _COL_DURATION):
                return Qt.AlignCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        return None

    def _display(self, item: MediaItem, col: int) -> str:
        if col == _COL_FAV:
            return "★" if getattr(item, 'id', 0) in self._fav_set else ""
        if col == _COL_TITLE:
            return item.title or item.filename or ""
        if col == _COL_ARTIST:
            return item.artist or ""
        if col == _COL_ALBUM:
            return item.album or ""
        if col == _COL_YEAR:
            return str(item.year) if item.year else ""
        if col == _COL_GENRE:
            return item.genre or ""
        if col == _COL_DURATION:
            return self._fmt_duration(item.duration)
        if col == _COL_FORMAT:
            return (item.ext or "").lstrip(".").upper()
        if col == _COL_FILEPATH:
            return item.filepath or ""
        if col == _COL_QUALITY:
            st = self._status_cache.get(item_id(item), {})
            return st.get("quality_label", "")
        if col == _COL_STATUS:
            st = self._status_cache.get(item_id(item), {})
            badges = st.get("badges", [])
            return " | ".join(badges) if badges else ""
        # Optional columns
        col_key = self._col_key(col)
        if col_key:
            return self._opt_display(item, col_key)
        return ""

    def _opt_display(self, item: MediaItem, key: str) -> str:
        val = getattr(item, key, None)
        if val is None:
            return ""
        if key == "size":
            return _fmt_size(val)
        if key == "duration":
            return self._fmt_duration(val)
        if key in ("sample_rate",):
            return f"{val // 1000}kHz" if val else ""
        if key in ("bitrate",):
            return f"{val // 1000}k" if val else ""
        if key == "bit_depth":
            return f"{val}bit" if val else ""
        return str(val)

    def _tooltip(self, item: MediaItem, col: int) -> str:
        lines = [item.title or item.filename or "?"]
        if item.artist:
            lines.append(f"Artista: {item.artist}")
        if item.album:
            lines.append(f"Álbum: {item.album}")
        tech = []
        if item.sample_rate:
            tech.append(f"{item.sample_rate // 1000}kHz")
        if item.bit_depth:
            tech.append(f"{item.bit_depth}bit")
        if item.channels:
            tech.append(f"{item.channels}ch")
        if item.bitrate:
            tech.append(f"{item.bitrate // 1000}kbps")
        if tech:
            lines.append(" | ".join(tech))
        if item.filepath:
            lines.append(f"\n{item.filepath}")
        return "\n".join(lines)

    @staticmethod
    def _fmt_duration(seconds: float) -> str:
        if not seconds or seconds <= 0:
            return ""
        s = int(seconds)
        h, m = divmod(s, 3600)
        m, s = divmod(m, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    # ── Sorting ──

    def sort(self, column, order=Qt.AscendingOrder):
        self.layoutAboutToBeChanged.emit()
        reverse = order == Qt.DescendingOrder

        def _sort_key(item: MediaItem) -> Any:
            if column == _COL_TITLE:
                return (item.title or item.filename or "").lower()
            if column == _COL_ARTIST:
                return (item.artist or "").lower()
            if column == _COL_ALBUM:
                return (item.album or "").lower()
            if column == _COL_YEAR:
                return item.year or 0
            if column == _COL_GENRE:
                return (item.genre or "").lower()
            if column == _COL_DURATION:
                return item.duration or 0
            if column == _COL_FORMAT:
                return (item.ext or "").lower()
            if column == _COL_FILEPATH:
                return (item.filepath or "").lower()
            col_key = self._col_key(column)
            if col_key:
                val = getattr(item, col_key, None)
                if val is None:
                    return ""
                if col_key in ("sample_rate", "bitrate", "bit_depth", "channels", "bpm",
                              "play_count", "rating", "size", "year", "duration"):
                    return val
                return str(val).lower()
            return ""

        self._items.sort(key=_sort_key, reverse=reverse)
        self.layoutChanged.emit()


def item_id(item: MediaItem) -> int:
    return getattr(item, 'id', 0)


def _fmt_size(bytes_val) -> str:
    if not bytes_val:
        return ""
    b = int(bytes_val)
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f}{unit}"
        b /= 1024
    return f"{b:.1f}TB"
