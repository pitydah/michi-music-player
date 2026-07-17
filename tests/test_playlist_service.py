from unittest.mock import MagicMock
from core.playlist_service import PlaylistService, PlaylistTransaction


class TestPlaylistService:
    def test_create_without_db(self):
        svc = PlaylistService(db=None)
        assert svc._db is None

    def test_create_transaction(self):
        db = MagicMock()
        txn = PlaylistTransaction(db)
        txn.begin()
        txn.commit()
        db.conn.execute.assert_called_with("BEGIN")
        db.conn.commit.assert_called()
