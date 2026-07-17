from __future__ import annotations

import pytest


@pytest.mark.xfail(reason="module removed or relocated", strict=False)
class TestLegacy:
    def test_placeholder(self):
        pass
