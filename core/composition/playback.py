"""Playback composition — player, queue, track actions."""
from __future__ import annotations

from core.service_container import ServiceContainer


def build(container: ServiceContainer) -> None:
    from audio.player_service import PlayerService
    from core.queue_service import QueueService
    from core.notification_service import NotificationService
    from audio.player import GStreamerEngine

    eb = container.get("event_bus")
    persistence = container.get("runtime_persistence")
    engine = GStreamerEngine()
    ps = PlayerService(engine=engine, event_bus=eb)
    qs = QueueService(
        player_service=ps,
        event_bus=eb,
        runtime_persistence=persistence,
    )
    ps.queue_progressed.connect(qs.reconcile_backend_progress)
    ns = NotificationService(event_bus=eb)

    container.register("queue_service", qs)
    container.register("playback_service", ps)
    container.register("notification_service", ns)

    try:
        from adapters.mpris import MPRISAdapter
        container.register(
            "mpris_adapter",
            MPRISAdapter(player_service=ps, queue_service=qs),
        )
    except Exception:
        container.register("mpris_adapter", None)
