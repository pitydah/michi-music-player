from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot

from ui_qml.models.HistoryListModel import HistoryListModel


class HistoryBridge(QObject):
    dataChanged = Signal()

    def __init__(self, db=None, history_query_service=None, query_executor=None,
                 playback_service=None, action_registry=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._hqs = history_query_service
        self._qe = query_executor
        self._playback_svc = playback_service
        self._action_registry = action_registry
        self._model = HistoryListModel(db=db, history_query_service=history_query_service,
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

    @Slot(result=dict)
    def refresh(self):
        self._model.refresh()
        self.dataChanged.emit()
        return {"ok": True, "count": self.historyCount}

    @Slot(str, result=dict)
    def removeHistoryItem(self, track_id: str):
        if self._hqs:
            result = self._hqs.remove_history_item(track_id)
            self.refresh()
            return result
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            self._db.conn.execute("DELETE FROM play_history WHERE track_id=?", (track_id,))
            self._db.conn.commit()
            self.refresh()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def removeHistoryEvent(self, event_id: str):
        if self._hqs and hasattr(self._hqs, 'remove_event_by_id'):
            try:
                result = self._hqs.remove_event_by_id(int(event_id))
                self.refresh()
                return result
            except (ValueError, TypeError):
                return {"ok": False, "error": "INVALID_ID"}
        return {"ok": False, "error": "NO_SERVICE"}

    @Slot(result=dict)
    def clearHistory(self):
        if self._hqs:
            result = self._hqs.clear_history()
            self.refresh()
            return result
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            self._db.conn.execute("DELETE FROM play_history")
            self._db.conn.commit()
            self.refresh()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, str, result=dict)
    def exportHistory(self, filepath: str, fmt: str = "json"):
        if self._hqs and hasattr(self._hqs, 'export_history'):
            return self._hqs.export_history(filepath, fmt)
        if not filepath:
            return {"ok": False, "error": "EMPTY_PATH"}
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            import json
            rows = self._db.conn.execute(
                "SELECT h.id, h.track_id, h.played_at, h.device, "
                "m.title, m.artist, m.album "
                "FROM play_history h "
                "LEFT JOIN media_items m ON h.track_id = m.filepath "
                "ORDER BY h.played_at DESC"
            ).fetchall()
            items = [
                {"event_id": r[0], "track_id": r[1], "played_at": r[2],
                 "device": r[3], "title": r[4] or "", "artist": r[5] or "",
                 "album": r[6] or ""}
                for r in rows
            ]
            with open(filepath, "w") as f:
                json.dump(items, f, indent=2)
            return {"ok": True, "count": len(items), "format": fmt}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, str, result=dict)
    def cancelExport(self, export_id: str, filepath: str = ""):
        import os
        import contextlib
        if filepath and os.path.exists(filepath):
            with contextlib.suppress(Exception):
                os.remove(filepath)
        return {"ok": True, "cancelled": True}

    @Slot(str, result=dict)
    def playHistoryItem(self, track_id: str):
        if self._playback_svc and hasattr(self._playback_svc, 'play'):
            return self._playback_svc.play(int(track_id) if track_id.isdigit() else track_id)
        if self._action_registry:
            return self._action_registry.execute("track_play_now")
        return {"ok": False, "error": "NO_PLAYBACK"}

    @Slot(str, result=dict)
    def applyRetention(self, config_json: str):
        if self._hqs and hasattr(self._hqs, 'apply_retention'):
            import json
            try:
                config = json.loads(config_json) if config_json else {}
                max_age_days = config.get("max_age_days", 365)
                result = self._hqs.apply_retention(max_age_days=max_age_days)
                self.refresh()
                return result
            except (json.JSONDecodeError, Exception):
                result = self._hqs.apply_retention(max_age_days=365)
                self.refresh()
                return result
        return {"ok": False, "error": "NO_SERVICE"}

    @Slot(result=dict)
    def getStatistics(self):
        if self._hqs and hasattr(self._hqs, 'get_statistics'):
            return self._hqs.get_statistics()
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            total = self._db.conn.execute("SELECT COUNT(*) FROM play_history").fetchone()[0] or 0
            return {"ok": True, "total_plays": total}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(bool, result=dict)
    def setHistoryEnabled(self, enabled: bool):
        if self._hqs:
            return self._hqs.set_history_enabled(enabled)
        return {"ok": True}

    @Slot(int, result=dict)
    def setHistoryLimit(self, limit: int):
        if self._hqs:
            return self._hqs.set_history_limit(limit)
        return {"ok": True}
