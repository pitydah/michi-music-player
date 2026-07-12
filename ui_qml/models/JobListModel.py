"""JobListModel — wraps JobBridge.jobs as QAbstractListModel for QML views."""
from __future__ import annotations

from PySide6.QtCore import Qt, QAbstractListModel, QModelIndex, Signal


class JobListModel(QAbstractListModel):
    JobIdRole = Qt.UserRole + 1
    TypeRole = Qt.UserRole + 2
    TitleRole = Qt.UserRole + 3
    StateRole = Qt.UserRole + 4
    ProgressRole = Qt.UserRole + 5
    MessageRole = Qt.UserRole + 6
    ErrorCodeRole = Qt.UserRole + 7
    CanCancelRole = Qt.UserRole + 8
    CanRetryRole = Qt.UserRole + 9
    DurationRole = Qt.UserRole + 10

    dataChanged = Signal()

    def __init__(self, job_bridge=None, parent=None):
        super().__init__(parent)
        self._bridge = job_bridge
        self._items: list[dict] = []

    def _owner(self) -> str:
        return "jobs"

    def roleNames(self):
        return {self.JobIdRole: b"jobId", self.TypeRole: b"type",
                self.TitleRole: b"title", self.StateRole: b"state",
                self.ProgressRole: b"progress", self.MessageRole: b"message",
                self.ErrorCodeRole: b"errorCode",
                self.CanCancelRole: b"canCancel", self.CanRetryRole: b"canRetry",
                self.DurationRole: b"duration"}

    def rowCount(self, parent=QModelIndex()):
        return len(self._items)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        mapping = {self.JobIdRole: "job_id", self.TypeRole: "type",
                   self.TitleRole: "title", self.StateRole: "state",
                   self.ProgressRole: "progress", self.MessageRole: "message",
                   self.ErrorCodeRole: "error_code",
                   self.CanCancelRole: "can_cancel", self.CanRetryRole: "can_retry",
                   self.DurationRole: "duration"}
        key = mapping.get(role, "")
        if key:
            return item.get(key, "")
        if role == Qt.DisplayRole:
            return item.get("title", "")
        return None

    def refresh(self):
        if not self._bridge:
            return
        new = getattr(self._bridge, 'jobs', [])
        self.beginResetModel()
        self._items = list(new)
        self.endResetModel()
