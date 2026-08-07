"""Shared fixtures for the Mix bridge tests (Fase Mix contract).

The bridge runs generation through a REAL inline DurableJobService
(no WorkerManager → the handler completes synchronously inside
``start_job``, mirroring the async signal flow) so tests exercise the
durable-job path end to end: job → MixService port → bridge state.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from core.jobs.handlers import make_mix_generate_handler
from core.jobs.job_service import DurableJobService
from ui_qml_bridge.mix_bridge import MixBridge


def default_tracks(strategy: str, count: int = 5) -> list[dict]:
    return [
        {"track_id": i, "id": i, "title": f"{strategy} {i}",
         "artist": "Artist A", "album": "Album B", "duration": 200,
         "reason": "Razon"}
        for i in range(1, count + 1)
    ]


def make_mix_service(outcomes: dict | None = None,
                     default_track_count: int = 5) -> MagicMock:
    """MixService double whose generate() returns canonical outcomes.

    ``outcomes`` maps strategy → result dict (or None for no-match
    outcomes).  Unlisted strategies produce COMPLETED_WITH_TRACKS.
    """
    svc = MagicMock()

    def _generate(strategy="daily", seed=None, limit=30, ctx=None):
        result = (outcomes or {}).get(strategy)
        if result is None:
            result = {
                "ok": True, "status": "COMPLETED_WITH_TRACKS",
                "message": "Mix generado", "strategy": strategy,
                "mix_id": f"query:{strategy}",
                "tracks": default_tracks(strategy, count=default_track_count),
                "count": default_track_count,
            }
        return dict(result)

    svc.generate.side_effect = _generate
    return svc


def make_bridge(mix_svc, tmp_path, **kwargs) -> tuple[MixBridge, DurableJobService]:
    job_svc = DurableJobService(db_path=str(tmp_path / "jobs.db"))
    job_svc.register_handler("mix_generate", make_mix_generate_handler(mix_svc))
    defaults = dict(
        mix_service=mix_svc,
        job_service=job_svc,
        playback_service=MagicMock(),
        queue_service=MagicMock(),
        playlist_service=MagicMock(),
    )
    defaults.update(kwargs)
    return MixBridge(**defaults), job_svc


@pytest.fixture
def job_service(tmp_path):
    return DurableJobService(db_path=str(tmp_path / "jobs.db"))
