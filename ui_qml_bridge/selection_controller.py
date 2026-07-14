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

    def _mutate(self):
        self._generation += 1
        self.selectionChanged.emit()
        self.countChanged.emit()
        self.generationChanged.emit()

    @Slot("QVariantList")
    def replace(self, ids: list):
        self._selected_ids = list(ids)
        self._anchor = ids[0] if ids else -1
        self._current = ids[-1] if ids else -1
        self._mutate()

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
        self._mutate()

    @Slot(int)
    def add(self, item_id: int):
        if item_id not in self._selected_ids:
            self._selected_ids = list(self._selected_ids) + [item_id]
            if self._anchor < 0:
                self._anchor = item_id
            self._current = item_id
            self._mutate()

    @Slot(int)
    def remove(self, item_id: int):
        if item_id in self._selected_ids:
            new_list = list(self._selected_ids)
            new_list.remove(item_id)
            self._selected_ids = new_list
            self._mutate()

    @Slot(int, int)
    def selectRangeByRows(self, from_row: int, to_row: int, all_ids: list = None):
        if all_ids is None:
            self._selected_ids = list(range(min(from_row, to_row), max(from_row, to_row) + 1))
        else:
            low = min(from_row, to_row)
            high = max(from_row, to_row)
            self._selected_ids = [all_ids[i] for i in range(low, high + 1) if i < len(all_ids)]
        self._current = self._selected_ids[-1] if self._selected_ids else -1
        self._mutate()

    @Slot(list)
    def selectAllLoaded(self, all_ids: list):
        self._selected_ids = list(all_ids)
        self._anchor = all_ids[0] if all_ids else -1
        self._current = all_ids[-1] if all_ids else -1
        self._mutate()

    @Slot(list)
    def selectAllFiltered(self, filtered_ids: list):
        self._selected_ids = list(filtered_ids)
        self._anchor = filtered_ids[0] if filtered_ids else -1
        self._current = filtered_ids[-1] if filtered_ids else -1
        self._mutate()

    @Slot(list)
    def invertLoaded(self, all_ids: list):
        current_set = set(self._selected_ids)
        self._selected_ids = [i for i in all_ids if i not in current_set]
        self._mutate()

    @Slot()
    def clear(self):
        self._selected_ids = []
        self._anchor = -1
        self._current = -1
        self._mutate()

    @Slot(int, result=bool)
    def contains(self, item_id: int) -> bool:
        return item_id in self._selected_ids

    @Slot(result=dict)
    def restore(self):
        return {
            "ok": True,
            "selected_ids": list(self._selected_ids),
            "anchor": self._anchor,
            "current": self._current,
            "generation": self._generation,
            "count": len(self._selected_ids),
        }
