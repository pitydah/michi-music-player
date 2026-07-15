from __future__ import annotations

from core.result import OperationResult


class TestOperationResult:
    def test_default_ok(self):
        r = OperationResult()
        assert r.ok is True

    def test_default_code_empty(self):
        r = OperationResult()
        assert r.code == ""

    def test_default_data_empty_dict(self):
        r = OperationResult()
        assert r.data == {}

    def test_default_warnings_empty(self):
        r = OperationResult()
        assert r.warnings == []

    def test_default_partial_false(self):
        r = OperationResult()
        assert r.partial is False

    def test_default_retryable_false(self):
        r = OperationResult()
        assert r.retryable is False

    def test_to_dict_returns_all_fields(self):
        r = OperationResult(ok=False, code="ERR", message="fail", data={"x": 1}, warnings=["w"], partial=True, retryable=True)
        d = r.to_dict()
        assert d["ok"] is False
        assert d["code"] == "ERR"
        assert d["message"] == "fail"
        assert d["data"] == {"x": 1}
        assert d["warnings"] == ["w"]
        assert d["partial"] is True
        assert d["retryable"] is True

    def test_from_legacy_dict_basic(self):
        d = {"ok": False, "code": "E1", "message": "error", "warnings": ["warn"]}
        r = OperationResult.from_legacy_dict(d)
        assert r.ok is False
        assert r.code == "E1"
        assert r.message == "error"
        assert r.warnings == ["warn"]

    def test_from_legacy_dict_with_details(self):
        d = {"ok": False, "code": "E2", "details": {"file": "x"}, "recoverable": True}
        r = OperationResult.from_legacy_dict(d)
        assert r.data == {"file": "x"}
        assert r.partial is True

    def test_from_legacy_dict_missing_defaults(self):
        r = OperationResult.from_legacy_dict({})
        assert r.ok is True
        assert r.code == ""
        assert r.data == {}
        assert r.warnings == []
        assert r.partial is False
        assert r.retryable is False
