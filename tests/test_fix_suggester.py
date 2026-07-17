from integrations.michi_ecosystem.fix_suggester import suggest_fix, ISSUE_FIXES


class TestFixSuggester:
    def test_issue_fixes_exist(self):
        assert "MICRO_NOT_CONFIGURED" in ISSUE_FIXES

    def test_suggest_fix(self):
        fix = suggest_fix({"MICRO_NOT_CONFIGURED": {"status": "error"}})
        assert fix is not None
