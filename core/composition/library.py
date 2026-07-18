"""Library composition — query, sources, search, playlists, history."""
from __future__ import annotations

from core.service_container import ServiceContainer, ServicePriority


def build(container: ServiceContainer) -> None:
    from core.library.library_query_service import LibraryQueryService
    from core.library_sources_service import LibrarySourcesService
    from core.metadata_editor_service import MetadataEditorService
    from core.library_service import LibraryService
    from core.playlist_service import PlaylistService
    from core.history_query_service import HistoryQueryService
    from core.global_search_service import GlobalSearchService
    from core.metadata_service import MetadataService
    from core.smart_tagging_service import SmartTaggingService
    from core.metadata_service import MetadataService

    cf = container.get("connection_factory")
    db = container.get("database")
    wm = container.get("worker_manager")

    lqs = LibraryQueryService(cf)
    container.register("library_query_service", lqs)
    container.register("library_sources_service", LibrarySourcesService(cf))
    container.register("library_mutation_service", MetadataEditorService(db=db))
    container.register("library_service", LibraryService(db=db, worker_manager=wm, library_query_service=lqs))
    container.register("playlist_service", PlaylistService(cf))
    container.register("history_query_service", HistoryQueryService(cf))
    container.register("global_search_service", GlobalSearchService(cf))
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
