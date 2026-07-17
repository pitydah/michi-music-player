from integrations.michi_ecosystem.fix_suggester import get_fix_for_issue, ISSUE_FIXES


class TestFixSuggester:
    def test_issue_fixes_exist(self):
        assert "MICRO_NOT_CONFIGURED" in ISSUE_FIXES

    def test_get_fix(self):
        fix = get_fix_for_issue("MICRO_NOT_CONFIGURED")
        assert fix is not None
        assert "problem" in fix
