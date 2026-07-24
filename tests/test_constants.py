from integrations.michi_ecosystem.constants import STATUS_OK, SYNC_DISABLED


class TestConstants:
    def test_ok(self):
        assert STATUS_OK == "ok"

    def test_sync_disabled(self):
        assert SYNC_DISABLED == "SYNC_DISABLED"
