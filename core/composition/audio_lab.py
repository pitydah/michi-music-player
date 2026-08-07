"""Audio Lab composition — diagnostics, conversion, analysis."""
from __future__ import annotations

import logging

from core.service_container import ServiceContainer

logger = logging.getLogger("michi.composition.audio_lab")


def build(container: ServiceContainer) -> None:
    wm = container.get("worker_manager")
    db = container.get("database")

    from core.audio_lab.audio_lab_service import AudioLabService
    als = AudioLabService(db=db, worker_manager=wm,
                          job_service=container.get("job_service"))
    if hasattr(als, 'setup') and callable(als.setup):
        try:
            als.setup()
        except Exception as e:
            logger.error("AudioLab setup failed: %s", e)
    container.register("audio_lab_service", als)

    try:
        from core.diagnostics_service import DiagnosticsService
        ps = container.get("playback_service")
        ds = DiagnosticsService(db=db, audio_diagnostics=True,
                                player_service=ps, worker_manager=wm)
        container.register("diagnostics_service", ds)
    except Exception:
        container.register("diagnostics_service", None)
    try:
        from core.audio_lab.cd_ripper_service import CDRipperService
        crs = CDRipperService()
        container.register("cd_ripper_service", crs)
    except Exception:
        container.register("cd_ripper_service", None)
