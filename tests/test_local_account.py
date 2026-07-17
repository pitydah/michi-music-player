from sync.local_account import LocalAccountManager, _hash_password


class TestLocalAccount:
    def test_hash_password(self):
        dk_hex, salt_hex = _hash_password("testpass")
        assert len(dk_hex) > 0
        assert len(salt_hex) > 0

    def test_create_manager(self):
        mgr = LocalAccountManager()
        assert mgr is not None
