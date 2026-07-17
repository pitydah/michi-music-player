from integrations.michi_ecosystem.ecosystem_actions import is_action_safe, is_action_confirmable


class TestEcosystemActions:
    def test_safe_actions(self):
        assert is_action_safe("diagnose_ecosystem") is True
        assert is_action_safe("unknown_action") is False

    def test_confirmable(self):
        assert is_action_confirmable("apply_config_plan") is True
