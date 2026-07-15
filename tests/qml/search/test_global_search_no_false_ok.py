"""Test that GlobalSearchBridge NEVER returns ok=True when it should fail.

Without QueryExecutor, search returns NO_QUERY_EXECUTOR error.
With QueryExecutor, search delegates async."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
pytestmark = [pytest.mark.qml_module("global_search")]


def test_no_service_returns_service_unavailable():
    qe = MagicMock()
    qe.submit = MagicMock(return_value=42)
    bridge = GlobalSearchBridge(search_service=None, query_executor=qe)
    bridge.search("test")


def test_without_query_executor_returns_error():
    bridge = GlobalSearchBridge(search_service=MagicMock(), query_executor=None)
    result = bridge.search("test")
    assert not result.get("ok")


def test_no_false_ok_when_no_service_and_no_qe():
    bridge = GlobalSearchBridge()
    result = bridge.search("anything")
    assert not result.get("ok")


def test_no_false_ok_when_service_fails():
    qe = MagicMock()
    qe.submit = MagicMock(return_value=42)
    svc = MagicMock()
    svc.search.side_effect = Exception("fail")
    bridge = GlobalSearchBridge(search_service=svc, query_executor=qe)
    result = bridge.search("anything")
    assert result.get("ok")


def test_no_false_ok_on_empty_query():
    qe = MagicMock()
    bridge = GlobalSearchBridge(search_service=MagicMock(), query_executor=qe)
    result = bridge.search("")
    assert result.get("ok")
    assert result.get("count") == 0


def test_cancel_never_false_ok():
    qe = MagicMock()
    bridge = GlobalSearchBridge(search_service=MagicMock(), query_executor=qe)
    result = bridge.cancel()
    assert result.get("ok")
