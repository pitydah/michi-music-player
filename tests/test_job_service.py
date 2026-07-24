from core.jobs.job_service import DurableJobService, JobState


class TestJobService:
    def test_create(self):
        svc = DurableJobService(db_path=":memory:")
        assert svc is not None

    def test_state_enum(self):
        assert JobState.QUEUED.value == "QUEUED"
        assert JobState.SUCCEEDED.value == "SUCCEEDED"
