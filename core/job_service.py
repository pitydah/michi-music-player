"""JobService — re-exports DurableJobService as canonical job service."""
from __future__ import annotations

from core.jobs.job_service import DurableJobService, DurableJob, JobState, TERMINAL_STATES  # noqa: F401

JobService = DurableJobService
