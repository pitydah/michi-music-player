"""CapabilityBridge — exposes backend capabilities to QML.

Based on BridgeFactory._capabilities + real service availability.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property


class CapabilityBridge(QObject):
    dataChanged = Signal()

    def __init__(self, factory=None, parent=None):
        super().__init__(parent)
        self._factory = factory
        self._caps: dict[str, bool] = {}

    def refresh(self):
        if not self._factory:
            return
        caps = dict(self._factory.capabilities)
        # Add computed capabilities
        svc = self._factory._services if hasattr(self._factory, '_services') else None
        caps["has_fts5"] = self._check_fts5(svc)
        caps["has_radio"] = svc and svc.has("radio_manager")
        caps["has_sync"] = svc and svc.has("sync_manager")
        caps["has_home_audio"] = svc and svc.has("home_audio_controller")
        caps["has_snapcast"] = svc and svc.has("snapcast_controller")
        caps["has_disc_service"] = svc and svc.has("disc_service")
        caps["has_smart_tagging"] = svc and svc.has("smart_tagging_service")
        caps["has_metadata_writer"] = self._check_metadata_writer(svc)
        self._caps = caps
        self.dataChanged.emit()

    @Property("QVariantMap", notify=dataChanged)
    def capabilities(self):
        return dict(self._caps)

    def has(self, name: str) -> bool:
        return self._caps.get(name, False)

    def _check_fts5(self, svc) -> bool:
        if not svc or not svc.db:
            return False
        try:
            row = svc.db.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='virtual_table' AND name='media_fts'"
            ).fetchone()
            return row is not None
        except Exception:
            return False

    def _check_metadata_writer(self, svc) -> bool:
        import importlib.util
        return importlib.util.find_spec("mutagen") is not None
