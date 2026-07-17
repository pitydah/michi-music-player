from integrations.michi_ecosystem.config_planner import EcosystemConfigPlanner, PLAN_DEFINITIONS


class TestConfigPlanner:
    def test_plans_exist(self):
        assert "setup_mobile_sync" in PLAN_DEFINITIONS

    def test_create(self):
        planner = EcosystemConfigPlanner()
        assert planner is not None
