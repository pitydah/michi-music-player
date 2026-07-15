"""31-band graphic equalizer — stub. Real EQ is in QML EqualizerPage."""
from __future__ import annotations

from PySide6.QtCore import Signal


def _db_to_y(db: float, h: int) -> int:
    ratio = (db + 12.0) / 24.0
    return int((1.0 - ratio) * (h - 1))


def _y_to_db(y: int, h: int) -> float:
    ratio = 1.0 - (y / max(h - 1, 1))
    return round((ratio * 24.0 - 12.0) * 10) / 10.0


class BandSlider:
    value_changed = Signal(float)
    def __init__(self, freq_label: str = "", parent=None):
        self._value = 0.0

    def set_value(self, db: float):
        self._value = db

    def value(self) -> float:
        return self._value


class GraphicEqWidget:
    def __init__(self, parent=None):
        self._bands = [0.0] * 31

    def set_bands(self, bands: list[float]):
        self._bands = list(bands)

    def get_bands(self) -> list[float]:
        return list(self._bands)
