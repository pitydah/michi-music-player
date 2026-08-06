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
    from core.favorite_service import FavoriteService
    from core.library_mutation_service import LibraryMutationService
    from core.file_manager_service import FileManagerService

    cf = container.get("connection_factory")
    db = container.get("database")
    wm = container.get("worker_manager")
    eb = container.get("event_bus")

    sources_svc = LibrarySourcesService(cf)
    container.register("library_sources_service", sources_svc)
    canonical_query_service = LibraryQueryService(cf, library_sources_service=sources_svc)
    lqs = LibraryFilteredQueryService(canonical_query_service)
    container.register("library_query_service", lqs)
    container.register("library_filtered_query_service", lqs)
    container.register("collection_service", CollectionService(db=db, query_service=lqs))
    container.register("folder_tree_model", FolderTreeModel(sources_svc.root_paths()))
    favorite_service = FavoriteService(db=db, event_bus=eb)
    container.register("favorite_service", favorite_service)
    mutation_service = LibraryMutationService(
        db=db, event_bus=eb, favorite_service=favorite_service,
    )
    container.register("library_mutation_service", mutation_service)
    # UndoService restores DB values for persisted undo records via the
    # mutation service (P0: undo survives restarts when a record persists).
    undo_svc = container.get("undo_service")
    if undo_svc is not None:
        undo_svc.bind_db(db=db, mutation_service=mutation_service)
    # MetadataEditorService is THE metadata editing authority (Slice 8):
    # proposal -> preview -> confirm -> apply_batch -> readback -> undo, with
    # real DB (via LibraryMutationService), physical tag writer, EventBus,
    # ConfirmationService and UndoService injected.
    container.register(
        "metadata_editor_service",
        MetadataEditorService(
            db=db,
            mutation_service=mutation_service,
            event_bus=eb,
            confirmation_service=container.get("confirmation_service"),
            undo_service=container.get("undo_service"),
            worker_manager=wm,
        ),
    )
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
            favorite_service=favorite_service,
            file_manager_service=FileManagerService,
        ),
    )
    container.register("history_query_service", HistoryQueryService(cf))
    from core.search.models import SearchDomain
    from core.search.providers import (
        AlbumSearchRepository,
        ArtistSearchRepository,
        FolderSearchRepository,
        GenreSearchRepository,
        PlaylistSearchRepository,
        RadioSearchRepository,
        SearchProviderRegistry,
        SettingsSearchProvider,
        TrackSearchRepository,
    )

    search_registry = SearchProviderRegistry()
    search_registry.register(SearchDomain.TRACK, TrackSearchRepository(cf))
    search_registry.register(SearchDomain.ALBUM, AlbumSearchRepository(cf))
    search_registry.register(SearchDomain.ARTIST, ArtistSearchRepository(cf))
    search_registry.register(SearchDomain.PLAYLIST, PlaylistSearchRepository(cf))
    search_registry.register(SearchDomain.RADIO, RadioSearchRepository(cf))
    search_registry.register(SearchDomain.GENRE, GenreSearchRepository(cf))
    search_registry.register(SearchDomain.FOLDER, FolderSearchRepository(cf))
    settings_service = container.get("settings_service")
    if settings_service is not None:
        search_registry.register(
            SearchDomain.SETTINGS, SettingsSearchProvider(settings_service)
        )
    container.register("search_provider_registry", search_registry)
    container.register(
        "global_search_service",
        GlobalSearchService(
            connection_factory=cf,
            provider_registry=search_registry,
            query_executor=container.get("query_executor"),
            worker_manager=wm,
        ),
    )
    container.register("metadata_service", MetadataService(db=db))

    try:
        from library.genre_repository import GenreRepository
        from core.genre.genre_cleanup_service import GenreCleanupService
        genre_cleanup = GenreCleanupService(db=db, genre_repo=GenreRepository(db.conn))
        container.register("genre_cleanup_service", genre_cleanup)
    except Exception:
        logger.error("Failed to create genre_cleanup_service", exc_info=True)
        container.register("genre_cleanup_service", None)

    try:
        from core.library_doctor.repositories.scan_repository import (
            LibraryDoctorScanRepository,
        )
        scan_repo = LibraryDoctorScanRepository(db)
        container.register("library_doctor_scan_repository", scan_repo)
    except Exception:
        logger.error("Failed to create library_doctor_scan_repository", exc_info=True)
        scan_repo = None
        container.register("library_doctor_scan_repository", None)

    try:
        from core.library_doctor_service import LibraryDoctorService
        container.register(
            "library_doctor_service",
            LibraryDoctorService(
                db=db,
                scan_repository=scan_repo,
                worker_manager=wm,
                job_service=container.get("job_service"),
                mutation_service=container.get("library_mutation_service"),
                confirmation_service=container.get("confirmation_service"),
                undo_service=container.get("undo_service"),
                metadata_editor=container.get("metadata_editor_service"),
                genre_cleanup=container.get("genre_cleanup_service"),
                event_bus=eb,
            ),
        )
    except Exception:
        logger.error("Failed to create library_doctor_service", exc_info=True)
        container.register("library_doctor_service", None)

    try:
        from core.recognition_service import RecognitionService
        from recognition.provider_manager import ProviderManager
        recog = RecognitionService(provider_manager=ProviderManager(None))
        container.register("recognition_service", recog)
        sts = SmartTaggingService(worker_manager=wm, library_query_service=lqs,
                                   recognition_service=recog,
                                   metadata_editor=container.get(
                                       "metadata_editor_service"),
                                   confirmation_service=container.get(
                                       "confirmation_service"))
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
