from __future__ import annotations

"""Test for metadata_doctor."""

import pytest
pytest.skip("module removed or relocated", allow_module_level=True)


def test_suggest_normalizations_returns_list():
    result = suggest_normalizations(None)
    assert isinstance(result, list)
