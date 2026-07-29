"""Library composition — query, sources, search, playlists, history."""
from __future__ import annotations

import logging

from core.service_container import ServiceContainer

logger = logging.getLogger(__name__)


def build(container: ServiceContainer) -> None:
    from core.library.library_query_service import LibraryQueryService
    from core.library.library_filtered_query_service import LibraryFilteredQueryService
    from core.library.collection_service import CollectionService
    from library.folder_tree_model import FolderTreeModel
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

    sources_svc = LibrarySourcesService(cf)
    container.register("library_sources_service", sources_svc)
    canonical_query_service = LibraryQueryService(cf, library_sources_service=sources_svc)
    lqs = LibraryFilteredQueryService(canonical_query_service)
    container.register("library_query_service", lqs)
    container.register("library_filtered_query_service", lqs)
    container.register("collection_service", CollectionService(db=db, query_service=lqs))
    container.register("folder_tree_model", FolderTreeModel(sources_svc.root_paths()))
    container.register("library_mutation_service", MetadataEditorService(db=db))
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
        logger.error("Failed to create library_doctor_service", exc_info=True)
        container.register("library_doctor_service", None)

    try:
        from core.recognition_service import RecognitionService
        from recognition.provider_manager import ProviderManager
        recog = RecognitionService(provider_manager=ProviderManager(None))
        container.register("recognition_service", recog)
        sts = SmartTaggingService(worker_manager=wm, library_query_service=lqs,
                                   recognition_service=recog)
        container.register("smart_tagging_service", sts)
    except Exception:
        logger.error("Failed to create smart_tagging_service", exc_info=True)
        container.register("smart_tagging_service", None)

    try:
        from core.library.artwork_resolver import CoverArtService
        container.register("artwork_service", CoverArtService(db=db))
    except Exception:
        logger.error("Failed to create artwork_service", exc_info=True)
        container.register("artwork_service", None)

    try:
        from core.songs_service import SongsService
        container.register("songs_service", SongsService(db=db, library_query_service=lqs))
    except Exception:
        logger.error("Failed to create songs_service", exc_info=True)
        container.register("songs_service", None)

    try:
        from core.track_service import TrackService
        container.register("track_service", TrackService(db=db))
    except Exception:
        logger.error("Failed to create track_service", exc_info=True)
        container.register("track_service", None)

    try:
        from core.genres_service import GenresService
        container.register("genres_service", GenresService(db=db))
    except Exception:
        logger.error("Failed to create genres_service", exc_info=True)
        container.register("genres_service", None)

    try:
        from core.folder_service import FolderService
        container.register("folder_service", FolderService(db=db, worker_manager=wm))
    except Exception:
        logger.error("Failed to create folder_service", exc_info=True)
        container.register("folder_service", None)
