"""Audio Lab composition — diagnostics, conversion, analysis."""
from __future__ import annotations

from core.service_container import ServiceContainer, ServicePriority


def build(container: ServiceContainer) -> None:
    wm = container.get("worker_manager")

    try:
        from core.audio_lab.audio_lab_service import AudioLabService
        container.register("audio_lab_service", AudioLabService(worker_manager=wm))
    except Exception:
        container.register("audio_lab_service", None)

    try:
        from core.diagnostics_service import DiagnosticsService
        db = container.get("database")
        ps = container.get("playback_service")
        ds = DiagnosticsService(db=db, audio_diagnostics=True,
                                player_service=ps, worker_manager=wm)
        container.register("diagnostics_service", ds)
    except Exception:
        container.register("diagnostics_service", None)
