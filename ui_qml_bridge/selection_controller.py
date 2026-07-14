"""SelectionController — QObject adapted selection state with immutability guarantees.

selectedIds is always a new list on every mutation. Never mutates in place.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot


class SelectionController(QObject):
    selectionChanged = Signal()
    countChanged = Signal()
    generationChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_ids: list[int] = []
        self._anchor: int = -1
        self._current: int = -1
        self._generation: int = 0

    @Property("QVariantList", notify=selectionChanged)
    def selectedIds(self):
        return list(self._selected_ids)

    @Property(int, notify=countChanged)
    def count(self):
        return len(self._selected_ids)

    @Property(int, notify=selectionChanged)
    def anchor(self):
        return self._anchor

    @Property(int, notify=selectionChanged)
    def current(self):
        return self._current

    @Property(int, notify=generationChanged)
    def generation(self):
        return self._generation

    @Property(bool, notify=selectionChanged)
    def hasSelection(self):
        return len(self._selected_ids) > 0

    @Slot(int)
    def toggle(self, item_id: int):
        new_list = list(self._selected_ids)
        if item_id in new_list:
            idx = new_list.index(item_id)
            new_list.pop(idx)
        else:
            new_list.append(item_id)
            if self._anchor < 0:
                self._anchor = item_id
        self._current = item_id
        self._selected_ids = new_list
        self._generation += 1
        self.selectionChanged.emit()
        self.countChanged.emit()
        self.generationChanged.emit()

    @Slot(int)
    def range(self, item_id: int):
        if self._anchor < 0 or not self._selected_ids:
            self.toggle(item_id)
            return
        low = min(self._anchor, item_id)
        high = max(self._anchor, item_id)
        new_set = set(self._selected_ids)
        for i in range(low, high + 1):
            new_set.add(i)
        self._current = item_id
        self._selected_ids = sorted(new_set)
        self._generation += 1
        self.selectionChanged.emit()
        self.countChanged.emit()
        self.generationChanged.emit()

    @Slot()
    def selectAll(self):
        self._selected_ids = []
        self._generation += 1
        self.selectionChanged.emit()
        self.countChanged.emit()
        self.generationChanged.emit()

    def populate_all(self, ids: list[int]):
        self._selected_ids = list(ids)
        self._generation += 1
        self.selectionChanged.emit()
        self.countChanged.emit()
        self.generationChanged.emit()

    @Slot()
    def selectFiltered(self):
        pass

    @Slot()
    def clear(self):
        self._selected_ids = []
        self._anchor = -1
        self._current = -1
        self._generation += 1
        self.selectionChanged.emit()
        self.countChanged.emit()
        self.generationChanged.emit()

    @Slot(int, result=bool)
    def contains(self, item_id: int) -> bool:
        return item_id in self._selected_ids
