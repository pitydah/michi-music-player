from integrations.michi_ecosystem.ecosystem_fix_suggester import EcosystemFixSuggester


class TestEcosystemFixSuggester:
    def test_suggest(self):
        suggester = EcosystemFixSuggester()
        fix = suggester.suggest("NO_PAIRED_DEVICES")
        assert fix is not None
        assert "problem" in fix
