from unittest.mock import MagicMock
from core.jobs.job_service import JobService, JobState


class TestJobService:
    def test_create(self):
        svc = JobService(db=MagicMock())
        assert svc is not None

    def test_state_enum(self):
        assert JobState.QUEUED.value == "QUEUED"
        assert JobState.SUCCEEDED.value == "SUCCEEDED"
