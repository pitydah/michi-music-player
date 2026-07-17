from integrations.michi_ecosystem.ecosystem_fix_suggester import EcosystemFixSuggester


class TestEcosystemFixSuggester:
    def test_suggest(self):
        suggester = EcosystemFixSuggester()
        fix = suggester.suggest_fix({"NO_PAIRED_DEVICES": {"status": "error"}})
        assert fix is not None
