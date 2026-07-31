"""Playback composition — player, queue, track actions."""
from __future__ import annotations

import logging

from core.service_container import ServiceContainer

logger = logging.getLogger(__name__)


def build(container: ServiceContainer) -> None:
    from audio.player_service import PlayerService
    from core.queue_service import QueueService
    from core.notification_service import NotificationService
    from audio.player import GStreamerEngine

    eb = container.get("event_bus")
    persistence = container.get("runtime_persistence")
    engine = GStreamerEngine()
    ps = PlayerService(
        engine=engine,
        event_bus=eb,
        library_db=container.get("database"),
    )
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
        adapter = MPRISAdapter(player_service=ps, queue_service=qs)
        # CanQuit is only True when Quit() actually works. Wire the app quit
        # handler when a QGuiApplication is already running; otherwise CanQuit
        # stays False (honest no-op). Raise is left unwired (CanRaise=False)
        # because the QML window is not available at composition time.
        try:
            from PySide6.QtGui import QGuiApplication
            app = QGuiApplication.instance()
            if app is not None and hasattr(app, "quit"):
                adapter.set_quit_handler(app.quit)
        except Exception:
            logger.debug("MPRIS quit handler not wired", exc_info=True)
        container.register("mpris_adapter", adapter)
    except Exception:
        logger.error("Failed to create MPRISAdapter", exc_info=True)
        container.register("mpris_adapter", None)
