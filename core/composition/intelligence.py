"""Intelligence composition — Michi AI, mix/recommendation, action registry."""
from __future__ import annotations

import logging

from core.service_container import ServiceContainer

logger = logging.getLogger(__name__)


def build(container: ServiceContainer) -> None:
    from ui_qml_bridge.action_registry import ActionRegistry
    ar = ActionRegistry(container=container)
    container.register("action_registry", ar)
    search_registry = container.get("search_provider_registry")
    if search_registry is not None:
        from core.search.models import SearchDomain
        from core.search.providers import ActionSearchProvider

        search_registry.register(SearchDomain.ACTION, ActionSearchProvider(ar))
    try:
        from recommendation.smart_mix_service import SmartMixService
        from recommendation.recommendation_service import RecommendationService
        from core.mix_service import MixService
        from core.mix_query_service import MixQueryService
        db = container.get("database")
        pls = container.get("playlist_service")
        lqs = container.get("library_query_service")
        eb = container.get("event_bus")
        sms = SmartMixService(db)
        mqs = RecommendationService(db)
        queries = MixQueryService(db)
        mix_svc = MixService(db=db, recommendation_service=mqs,
                             smart_mix_service=sms,
                             library_query_service=lqs,
                             playlist_service=pls,
                             event_bus=eb,
                             mix_query_service=queries)
        container.register("mix_query_service", queries)
        container.register("mix_service", mix_svc)
    except Exception:
        logger.error("Failed to create mix services", exc_info=True)
        container.register("mix_query_service", None)
        container.register("mix_service", None)

    try:
        nav_svc = container.get("navigation_service")
        from core.assistant_initializer import create_assistant_composition
        comp = create_assistant_composition(
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
            navigation_service=nav_svc,
            lyrics_service=container.get("lyrics_service"),
            connection_service=container.get("connection_service"),
            home_audio_service=container.get("home_audio_service"),
            library_doctor_service=container.get("library_doctor_service"),
            track_action_service=container.get("track_action_service"),
            library_query_service=container.get("library_query_service"),
            device_registry=container.get("device_registry"),
            global_search_service=container.get("global_search_service"),
            metadata_editor_service=container.get("metadata_editor_service"),
        )
        container.register("michi_ai_service", comp.core_service)

        from michi_ai.recommender import set_library_provider
        lqs = container.get("library_query_service")
        if lqs:
            def _provider():
                try:
                    tracks = lqs.fetch_tracks(limit=1000)
                    return [
                        {"artist": t.get("artist", ""), "album": t.get("album", ""),
                         "title": t.get("title", ""), "genre": t.get("genre", "")}
                        for t in tracks
                    ]
                except Exception:
                    return []
            set_library_provider(_provider)
    except Exception as e:
        logger.error("Michi AI composition failed: %s", e)
