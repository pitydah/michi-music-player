"""Intelligence composition — recommendations, mix generation and actions."""
from __future__ import annotations

import logging

from core.service_container import ServiceContainer

logger = logging.getLogger(__name__)


def build(container: ServiceContainer) -> None:
    from ui_qml_bridge.action_registry import ActionRegistry

    action_registry = ActionRegistry()
    container.register("action_registry", action_registry)

    try:
        from core.mix_query_service import MixQueryService
        from core.mix_service import MixService
        from recommendation.recommendation_service import RecommendationService
        from recommendation.smart_mix_service import SmartMixService

        db = container.require("database")
        connection_factory = container.require("connection_factory")
        playlist_service = container.get("playlist_service")
        library_query_service = container.get("library_query_service")
        event_bus = container.get("event_bus")

        mix_query_service = MixQueryService(
            db=db,
            connection_factory=connection_factory,
        )
        recommendation_service = RecommendationService(db)
        smart_mix_service = SmartMixService(db)
        mix_service = MixService(
            db=db,
            recommendation_service=recommendation_service,
            smart_mix_service=smart_mix_service,
            mix_query_service=mix_query_service,
            library_query_service=library_query_service,
            playlist_service=playlist_service,
            event_bus=event_bus,
        )

        # These are distinct contracts. RecommendationService must never be
        # registered under mix_query_service: the QML bridge expects catalog
        # methods such as favorites(), recent() and high_quality().
        container.register("mix_query_service", mix_query_service)
        container.register("recommendation_service", recommendation_service)
        container.register("mix_service", mix_service)
    except Exception:
        logger.error("Failed to create mix services", exc_info=True)
        container.register("mix_query_service", None)
        container.register("recommendation_service", None)
        container.register("mix_service", None)

    try:
        navigation_service = container.get("navigation_service")
        from core.assistant_initializer import create_assistant_composition

        composition = create_assistant_composition(
            metadata_service=container.get("metadata_service"),
            queue_service=container.get("queue_service"),
            playlist_service=container.get("playlist_service"),
            confirmation_service=container.get("confirmation_service"),
            job_service=container.get("job_service"),
            settings_service=container.get("settings_service"),
            player_service=container.get("playback_service"),
            library_db=container.get("database"),
            audio_lab_service=container.get("audio_lab_service"),
            sync_manager=container.get("device_sync_service"),
            diagnostics_service=container.get("diagnostics_service"),
            mix_service=container.get("mix_service"),
            navigation_service=navigation_service,
            lyrics_service=container.get("lyrics_service"),
            connection_service=container.get("connection_service"),
            home_audio_service=container.get("home_audio_service"),
            library_doctor_service=container.get("library_doctor_service"),
            track_action_service=container.get("track_action_service"),
            library_query_service=container.get("library_query_service"),
        )
        container.register("michi_ai_service", composition.core_service)

        from michi_ai.recommender import set_library_provider

        library_query_service = container.get("library_query_service")
        if library_query_service:

            def _provider() -> list[dict[str, str]]:
                try:
                    tracks = library_query_service.fetch_tracks(limit=1000)
                    return [
                        {
                            "artist": track.get("artist", ""),
                            "album": track.get("album", ""),
                            "title": track.get("title", ""),
                            "genre": track.get("genre", ""),
                        }
                        for track in tracks
                    ]
                except Exception:
                    logger.debug("AI library provider failed", exc_info=True)
                    return []

            set_library_provider(_provider)
    except Exception as exc:
        logger.error(
            "Michi AI composition failed: %s",
            exc,
            exc_info=True,
        )
