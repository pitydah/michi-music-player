"""Playback composition — player, queue, track actions."""
from __future__ import annotations

from core.service_container import ServiceContainer, ServicePriority


def build(container: ServiceContainer) -> None:
    from audio.player_service import PlayerService
    from core.queue_service import QueueService
    from core.track_action_service import TrackActionService
    from core.notification_service import NotificationService
    from audio.player import GStreamerEngine

    eb = container.get("event_bus")
    qs = QueueService(event_bus=eb)
    ts = TrackActionService()
    engine = GStreamerEngine()
    ps = PlayerService(engine=engine, event_bus=eb)
    ns = NotificationService(event_bus=eb)

    container.register("queue_service", qs)
    container.register("track_action_service", ts)
    container.register("playback_service", ps)
    container.register("notification_service", ns)
