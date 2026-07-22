"""Library composition — query, sources, search, playlists, history."""
from __future__ import annotations

from core.service_container import ServiceContainer


def build(container: ServiceContainer) -> None:
    from core.library.library_query_service import LibraryQueryService
    from core.library.library_filtered_query_service import LibraryFilteredQueryService
    from core.library_sources_service import LibrarySourcesService
    from core.metadata_editor_service import MetadataEditorService
    from core.library_service import LibraryService
    from core.playlist_service import PlaylistService
    from core.history_query_service import HistoryQueryService
    from core.global_search_service import GlobalSearchService
    from core.metadata_service import MetadataService
    from core.smart_tagging_service import SmartTaggingService
    from core.track_action_service import TrackActionService

    cf = container.get("connection_factory")
    db = container.get("database")
    wm = container.get("worker_manager")

    canonical_query_service = LibraryQueryService(cf)
    lqs = LibraryFilteredQueryService(canonical_query_service)
    container.register("library_query_service", lqs)
    container.register("library_sources_service", LibrarySourcesService(cf))
    container.register("library_mutation_service", MetadataEditorService(db=db))
    container.register("metadata_editor_service", MetadataEditorService(db=db))
    container.register("library_service", LibraryService(db=db, worker_manager=wm, library_query_service=lqs))
    playlist_service = PlaylistService(cf)
    container.register("playlist_service", playlist_service)
    container.register(
        "track_action_service",
        TrackActionService(
            query_service=lqs,
            queue_service=container.require("queue_service"),
            playlist_service=playlist_service,
            db=db,
        ),
    )
    container.register("history_query_service", HistoryQueryService(cf))
    container.register("global_search_service", GlobalSearchService(cf.db_path))
    container.register("metadata_service", MetadataService())

    try:
        from core.library_doctor_service import LibraryDoctorService
        container.register("library_doctor_service", LibraryDoctorService(db))
    except Exception:
        container.register("library_doctor_service", None)

    try:
        sts = SmartTaggingService(worker_manager=wm, library_query_service=lqs)
        container.register("smart_tagging_service", sts)
    except Exception:
        container.register("smart_tagging_service", None)
