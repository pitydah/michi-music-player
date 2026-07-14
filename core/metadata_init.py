"""Metadata service initialization for ServiceContainer.

Creates MetadataService with all required dependencies.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.metadata.init")


def create_metadata_service(registry) -> object:
    from core.metadata_service import MetadataService

    library_repo = _resolve_library_repo(registry)
    settings = registry.get("settings_service") if registry else None
    jobs = registry.get("job_service") if registry else None

    svc = MetadataService(
        library_repo=library_repo,
        settings_service=settings,
        job_service=jobs,
    )
    logger.info("MetadataService created (library=%s, settings=%s, jobs=%s)",
                library_repo is not None, settings is not None, jobs is not None)
    return svc


def _resolve_library_repo(registry):
    if registry is None:
        return None
    qs = registry.get("library_query_service")
    ms = registry.get("library_mutation_service")
    if qs is None and ms is None:
        return None

    class _LibraryRepo:
        def get_track(self, track_id: int):
            if qs is not None:
                return qs.get_track(track_id)
            return None

        def update_metadata(self, track_id: int, data: dict):
            if ms is not None:
                ms.update_metadata(track_id, data)

    return _LibraryRepo()
