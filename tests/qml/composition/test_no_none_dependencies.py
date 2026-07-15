
from core.results import OperationResult, OperationError, ValidationResult, JobResult
import pytest
pytestmark = [pytest.mark.qml_module("worker_manager")]


class TestOperationResultNoNone:
    def test_default_ok(self):
        r = OperationResult()
        assert r.ok is True

    def test_default_code_empty_string(self):
        r = OperationResult()
        assert r.code == ""

    def test_default_message_empty_string(self):
        r = OperationResult()
        assert r.message == ""

    def test_default_details_is_dict(self):
        r = OperationResult()
        assert isinstance(r.details, dict)

    def test_default_warnings_is_list(self):
        r = OperationResult()
        assert isinstance(r.warnings, list)

    def test_default_affected_ids_is_list(self):
        r = OperationResult()
        assert isinstance(r.affected_ids, list)


class TestValidationResult:
    def test_default_valid_true(self):
        v = ValidationResult()
        assert v.valid is True

    def test_default_errors_empty(self):
        v = ValidationResult()
        assert v.errors == []

    def test_default_warnings_empty(self):
        v = ValidationResult()
        assert v.warnings == []


class TestJobResult:
    def test_default_ok_true(self):
        j = JobResult()
        assert j.ok is True

    def test_default_progress_zero(self):
        j = JobResult()
        assert j.progress == 0.0

    def test_default_errors_empty(self):
        j = JobResult()
        assert j.errors == []


class TestOperationError:
    def test_ok_is_false(self):
        e = OperationError()
        assert e.ok is False

    def test_is_operation_result(self):
        e = OperationError()
        assert isinstance(e, OperationResult)
