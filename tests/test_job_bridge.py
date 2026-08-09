from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.job_bridge import JobBridge, TITLE_BY_TYPE

pytestmark = pytest.mark.isolation


class TestJobBridge:
    def test_create(self):
        bridge = JobBridge(worker_manager=MagicMock(), db=MagicMock())
        assert bridge is not None

    def test_title_by_type_includes_analysis(self):
        """TITLE_BY_TYPE maps 'analysis' to 'Análisis técnico' (spec 3.2)."""
        assert "analysis" in TITLE_BY_TYPE
        assert TITLE_BY_TYPE["analysis"] == "Análisis técnico"

    def test_analysis_job_maps_to_qml_title(self):
        from core.jobs.job_service import DurableJobService

        svc = DurableJobService(db_path=":memory:")
        bridge = JobBridge(job_service=svc)
        jid = svc.create_job("analysis", owner="test")
        jobs = bridge.jobs
        analysis_job = next(j for j in jobs if j["job_id"] == jid)
        assert analysis_job["title"] == "Análisis técnico"
