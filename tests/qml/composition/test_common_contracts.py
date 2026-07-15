
from core.results import OperationResult, OperationError, ValidationResult, JobResult
import pytest
pytestmark = [pytest.mark.qml_module("worker_manager")]


class TestOperationResultContract:
    def test_has_ok_field(self):
        r = OperationResult()
        assert hasattr(r, 'ok')

    def test_has_code_field(self):
        r = OperationResult()
        assert hasattr(r, 'code')

    def test_has_message_field(self):
        r = OperationResult()
        assert hasattr(r, 'message')

    def test_has_details_field(self):
        r = OperationResult()
        assert hasattr(r, 'details')

    def test_has_recoverable_field(self):
        r = OperationResult()
        assert hasattr(r, 'recoverable')

    def test_has_retryable_field(self):
        r = OperationResult()
        assert hasattr(r, 'retryable')

    def test_has_requires_confirmation_field(self):
        r = OperationResult()
        assert hasattr(r, 'requires_confirmation')

    def test_has_job_id_field(self):
        r = OperationResult()
        assert hasattr(r, 'job_id')

    def test_has_affected_ids_field(self):
        r = OperationResult()
        assert hasattr(r, 'affected_ids')

    def test_has_warnings_field(self):
        r = OperationResult()
        assert hasattr(r, 'warnings')


class TestValidationResultContract:
    def test_has_valid_field(self):
        v = ValidationResult()
        assert hasattr(v, 'valid')

    def test_has_errors_field(self):
        v = ValidationResult()
        assert hasattr(v, 'errors')

    def test_has_warnings_field(self):
        v = ValidationResult()
        assert hasattr(v, 'warnings')


class TestJobResultContract:
    def test_has_ok_field(self):
        j = JobResult()
        assert hasattr(j, 'ok')

    def test_has_job_id_field(self):
        j = JobResult()
        assert hasattr(j, 'job_id')

    def test_has_progress_field(self):
        j = JobResult()
        assert hasattr(j, 'progress')

    def test_has_results_field(self):
        j = JobResult()
        assert hasattr(j, 'results')

    def test_has_errors_field(self):
        j = JobResult()
        assert hasattr(j, 'errors')


class TestOperationErrorContract:
    def test_is_operation_result(self):
        e = OperationError()
        assert isinstance(e, OperationResult)

    def test_ok_defaults_false(self):
        e = OperationError()
        assert e.ok is False

    def test_recoverable_defaults_false(self):
        e = OperationError()
        assert e.recoverable is False
