"""Composition-level queue progression reconciliation tests."""
from __future__ import annotations

from core.composition.playback import build
from core.service_container import ServiceContainer


def test_playback_composition_reconciles_backend_progress() -> None:
    container = ServiceContainer()
    build(container)
    queue = container.require("queue_service")
    player = container.require("playback_service")
    queue.replace([
        {"filepath": "/a.flac", "title": "A"},
        {"filepath": "/b.flac", "title": "B"},
    ])

    player.queue_progressed.emit(
        1, "/b.flac", "gapless", queue.revision
    )

    assert queue.current_index == 1
    assert queue.get_current()["title"] == "B"


def test_playback_composition_rejects_stale_progress() -> None:
    container = ServiceContainer()
    build(container)
    queue = container.require("queue_service")
    player = container.require("playback_service")
    queue.replace([
        {"filepath": "/a.flac"},
        {"filepath": "/b.flac"},
    ])

    player.queue_progressed.emit(
        1, "/b.flac", "gapless", queue.revision - 1
    )

    assert queue.current_index == 0
