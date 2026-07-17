from unittest.mock import MagicMock
from sync.sync_manager import SyncManager


class TestSyncService:
    def test_create(self):
        db = MagicMock()
        mgr = SyncManager(db=db)
        assert mgr._active is False

    def test_signals_exist(self):
        db = MagicMock()
        mgr = SyncManager(db=db)
        assert mgr.sync_started is not None
