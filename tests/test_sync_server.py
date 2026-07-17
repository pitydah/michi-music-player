from unittest.mock import MagicMock
from sync.sync_server import SyncServer


class TestSyncServer:
    def test_create(self):
        db = MagicMock()
        server = SyncServer(db=db)
        assert server is not None
