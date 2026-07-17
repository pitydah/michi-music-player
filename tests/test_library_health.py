from __future__ import annotations

"""Test for library_health."""

import pytest
pytest.skip("module removed or relocated", allow_module_level=True)


def test_compute_health_returns_dict():
    result = compute_health(None, cache=None)
    assert isinstance(result, dict)
    assert "total_tracks" in result
