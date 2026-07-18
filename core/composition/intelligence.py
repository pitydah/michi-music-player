"""Intelligence composition — Michi AI and mix/recommendation services."""
from __future__ import annotations

from core.service_container import ServiceContainer, ServicePriority


def build(container: ServiceContainer) -> None:
    try:
        from recommendation.smart_mix_service import SmartMixService
        from recommendation.recommendation_service import RecommendationService
        from core.mix_service import MixService
        db = container.get("database")
        pls = container.get("playlist_service")
        lqs = container.get("library_query_service")
        eb = container.get("event_bus")
        sms = SmartMixService(db)
        mqs = RecommendationService(db)
        mix_svc = MixService(db=db, recommendation_service=mqs,
                             smart_mix_service=sms,
                             library_query_service=lqs,
                             playlist_service=pls,
                             event_bus=eb)
        container.register("mix_query_service", mqs)
        container.register("mix_service", mix_svc)
    except Exception:
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
        )
        container.register("michi_ai_service", comp.core_service)

        from michi_ai.recommender import set_library_provider
        db = container.get("database")
        if db:
            def _provider():
                try:
                    rows = db.execute(
                        "SELECT artist, album, title, genre FROM media WHERE kind='audio' LIMIT 1000"
                    ).fetchall()
                    return [{"artist": r[0] or "", "album": r[1] or "",
                             "title": r[2] or "", "genre": r[3] or ""} for r in rows]
                except Exception:
                    return []
            set_library_provider(_provider)
    except Exception as e:
        import logging
        logging.getLogger("michi.bootstrap.intelligence").warning(
            "Michi AI composition failed: %s", e)
