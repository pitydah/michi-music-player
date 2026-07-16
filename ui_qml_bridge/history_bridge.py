"""HistoryBridge — QML-facing play history with full CRUD, pagination, filters,
export via JobService, retention, statistics, and integration with ActionRegistry,
NavigationBridge, PageStateStore, CapabilityBridge, AccessibilityBridge.
No direct SQL from bridge — delegates to HistoryQueryService.
"""
from __future__ import annotations

import json
import os

from PySide6.QtCore import QObject, Signal, Property, Slot
import logging

from core.history_query_service import HistoryQueryService
from ui_qml.models.HistoryListModel import HistoryListModel

logger = logging.getLogger("michi.history")

_PAGE_SIZE = 100


class HistoryBridge(QObject):
    dataChanged = Signal()
    exportProgress = Signal(str, int)
    retentionApplied = Signal(int)

    def __init__(self, db=None, history_query_service=None, query_executor=None,
                 playback_service=None, action_registry=None,
                 navigation_bridge=None, page_state_store=None,
                 capability_bridge=None, accessibility_bridge=None,
                 notification_bridge=None, job_bridge=None, parent=None):
        super().__init__(parent)
        assert db is not None, "HistoryBridge: db is REQUIRED"
        self._db = db
        self._hqs = history_query_service or HistoryQueryService(db=db)
        self._qe = query_executor
        self._playback_svc = playback_service
        self._action_registry = action_registry
        self._navigation = navigation_bridge
        self._page_state = page_state_store
        self._capability = capability_bridge
        self._accessibility = accessibility_bridge
        self._notifications = notification_bridge
        self._job_bridge = job_bridge
        self._model = HistoryListModel(db=db, history_query_service=self._hqs,
                                       query_executor=query_executor, parent=self)

    @Property("QVariant", notify=dataChanged)
    def historyModel(self):
        return self._model

    @Property(int, notify=dataChanged)
    def historyCount(self):
        return self._model.totalCount

    @Property("QVariant", notify=dataChanged)
    def historyQueryService(self):
        return self._hqs

    @Property("QVariant", notify=dataChanged)
    def playbackBridge(self):
        return getattr(self, '_playback_bridge', None)

    def setPlaybackBridge(self, bridge):
        self._playback_bridge = bridge

    def _notify(self, text: str, kind: str = "info"):
        if self._notifications:
            self._notifications.showMessage(text, kind=kind)

    @Slot(result=dict)
    def refresh(self):
        self._model.refresh()
        self.dataChanged.emit()
        return {"ok": True, "count": self.historyCount}

    @Slot(int, int, str, str, str, str, result=dict)
    def fetchPage(self, offset: int = 0, limit: int = _PAGE_SIZE,
                  artist: str = "", album: str = "",
                  device: str = "", search: str = ""):
        if not self._hqs:
            return {"ok": False, "error": "NO_SERVICE"}
        try:
            items = self._hqs.fetch_history_with_event_ids(
                offset=offset, limit=limit,
                artist=artist, album=album,
                device=device, search=search,
            )
            total = self._hqs.count_history(artist=artist, album=album,
                                            device=device, search=search)
            return {"ok": True, "items": items, "total": total, "offset": offset, "limit": limit}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def removeHistoryItem(self, track_id: str):
        result = self._hqs.remove_history_item(track_id) if self._hqs else {"ok": False, "error": "NO_SERVICE"}
        if result.get("ok"):
            self.refresh()
        return result

    @Slot(str, result=dict)
    def removeHistoryEvent(self, event_id: str):
        if not self._hqs:
            return {"ok": False, "error": "NO_SERVICE"}
        try:
            result = self._hqs.remove_event_by_id(int(event_id))
            if result.get("ok"):
                self.refresh()
            return result
        except (ValueError, TypeError):
            return {"ok": False, "error": "INVALID_ID"}

    @Slot(result=dict)
    def clearHistory(self):
        if not self._hqs:
            return {"ok": False, "error": "NO_SERVICE"}
        result = self._hqs.clear_history()
        if result.get("ok"):
            self.refresh()
            self._notify("Historial borrado", "info")
        return result

    @Slot(str, str, str, str, result=dict)
    def clearFiltered(self, artist: str = "", album: str = "",
                      device: str = "", search: str = ""):
        if not self._hqs:
            return {"ok": False, "error": "NO_SERVICE"}
        try:
            items = self._hqs.fetch_history_with_event_ids(0, 999999, artist, album, device, search)
            ids = [str(i.get("event_id", 0)) for i in items if i.get("event_id")]
            removed = 0
            for eid in ids:
                r = self._hqs.remove_event_by_id(int(eid))
                if r.get("ok"):
                    removed += 1
            self.refresh()
            return {"ok": True, "removed": removed}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, str, result=dict)
    def exportHistory(self, filepath: str, fmt: str = "json",
                      artist: str = "", album: str = "",
                      device: str = "", search: str = ""):
        if not self._hqs:
            return {"ok": False, "error": "NO_SERVICE"}
        if self._job_bridge and hasattr(self._job_bridge, '_add_job'):
            def _export():
                result = self._hqs.export_history(
                    filepath, fmt, artist=artist, album=album,
                    device=device, search=search,
                )
                if not result.get("ok"):
                    raise RuntimeError(result.get("message", "Export failed"))
                return result
            self._job_bridge._add_job("history_export", f"Exportando historial a {fmt}", _export)
            return {"ok": True, "async": True}
        return self._hqs.export_history(filepath, fmt, artist=artist, album=album,
                                        device=device, search=search)

    @Slot(str, str, result=dict)
    def cancelExport(self, export_id: str, filepath: str = ""):
        if filepath and os.path.exists(filepath):
            import contextlib
            with contextlib.suppress(Exception):
                os.remove(filepath)
        return {"ok": True, "cancelled": True}

    @Slot(str, result=dict)
    def playEntry(self, track_id: str):
        return self.playHistoryItem(track_id)

    @Slot(str, result=dict)
    def playHistoryItem(self, track_id: str):
        if self._playback_svc and hasattr(self._playback_svc, 'play'):
            try:
                tid = int(track_id) if track_id.isdigit() else track_id
                return self._playback_svc.play(tid)
            except Exception as e:
                return {"ok": False, "error": str(e)}
        if self._action_registry:
            return self._action_registry.execute("track_play_now")
        return {"ok": False, "error": "NO_PLAYBACK"}

    @Slot(str, result=dict)
    def applyRetention(self, config_json: str):
        if not self._hqs:
            return {"ok": False, "error": "NO_SERVICE"}
        try:
            config = json.loads(config_json) if config_json else {}
            max_age_days = config.get("max_age_days", 365)
            result = self._hqs.apply_retention(max_age_days=max_age_days)
            if result.get("ok"):
                self.refresh()
                self.retentionApplied.emit(result.get("deleted_count", 0))
            return result
        except (json.JSONDecodeError, Exception) as e:
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def getStatistics(self):
        if self._hqs:
            return self._hqs.get_statistics()
        return {"ok": False, "error": "NO_SERVICE"}

    @Slot(bool, result=dict)
    def setHistoryEnabled(self, enabled: bool):
        if self._hqs:
            return self._hqs.set_history_enabled(enabled)
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    @Slot(int, result=dict)
    def setHistoryLimit(self, limit: int):
        if self._hqs:
            return self._hqs.set_history_limit(limit)
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    @Slot(result=dict)
    def historyScore(self) -> dict:
        score = 0
        if self._hqs:
            score += 30
        if self._model:
            score += 20
        if self._action_registry:
            score += 15
        if self._job_bridge:
            score += 15
        if self._notifications:
            score += 10
        return {
            "score": min(100, score),
            "has_service": self._hqs is not None,
            "has_model": self._model is not None,
            "has_action_registry": self._action_registry is not None,
            "has_job_bridge": self._job_bridge is not None,
        }
