"""Jobs snapshot section — durable job service state."""

from __future__ import annotations

from typing import Any


class JobsSectionProvider:
    section_key = "jobs"

    def build(self, context) -> dict[str, Any]:
        jobs = context.services.get("job_service")
        if jobs is None:
            return {
                "available": False,
                "reason": "job_service_missing",
                "active": 0,
                "queued": 0,
                "total": 0,
            }
        try:
            total = 0
            queued = 0
            active = 0
            if hasattr(jobs, "list_jobs"):
                all_jobs = jobs.list_jobs() or []
                total = len(all_jobs)
                for job in all_jobs:
                    state = getattr(job, "state", None)
                    label = getattr(state, "value", None) or str(state or "")
                    if label in ("queued", "pending"):
                        queued += 1
                    elif label in ("running", "started"):
                        active += 1
            return {
                "available": True,
                "total": total,
                "active": active,
                "queued": queued,
            }
        except Exception as exc:
            return {
                "available": False,
                "reason": "job_readback_failed",
                "error": str(exc)[:200],
                "active": 0,
                "queued": 0,
                "total": 0,
            }
