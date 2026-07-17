from __future__ import annotations

import pytest


@pytest.mark.xfail(reason="AIAssistantService removed", strict=False)
class TestLegacy:
    def test_placeholder(self):
        pass
