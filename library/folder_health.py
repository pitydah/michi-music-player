"""Folder health analysis — assess folder structure, indexing, and metadata status.

Pure analysis service, no Qt imports. Operates on FolderEntry lists and DB queries.
"""

from __future__ import annotations

import os
import logging
from typing import Any

from library.folder_index import (
    list_folder_entries, list_audio_files, list_subfolders,
    classify_file, walk_audio_files,
)
from library.folder_models import (
    FolderEntry, FolderHealth, FolderProblem, FolderDbDiff,
    FolderActionRecommendation, classify_status,
)

logger = logging.getLogger("michi.folder_health")

_COVER_NAMES = frozenset({
    "cover.jpg", "cover.png", "folder.jpg", "folder.png",
    "front.jpg", "front.png", "album.jpg", "album.png",
    "art.jpg", "art.png", "portada.jpg", "portada.png",
})

_METADATA_FIELDS = frozenset({"title", "artist", "album"})


class FolderHealthService:
    """Analyze folder health by combining filesystem inspection with DB data."""

    def __init__(self, db=None, probe_audio: bool = False, deep: bool = False):
        self._db = db
        self._probe_audio = probe_audio
        self._deep = deep

    def set_db(self, db):
        self._db = db

    def analyze(self, path: str, recursive: bool = False,
                max_depth: int | None = 1) -> FolderHealth:
        """Run a full health analysis on a folder."""
        health = FolderHealth(path=path)

        if not path:
            health.score = 0
            health.status = classify_status(0)
            health.warnings.append("path_empty")
            return health

        norm_path = os.path.normpath(path)
        health.path = norm_path
        health.exists = os.path.exists(norm_path)

        if not health.exists:
            health.score = 0
            health.status = classify_status(0)
            health.warnings.append("path_not_found")
            return health

        health.readable = os.access(norm_path, os.R_OK)
        if not health.readable:
            health.score = 20
            health.status = classify_status(20)
            health.warnings.append("not_readable")
            return health

        # Determine library root status
        if self._db:
            try:
                roots = self._db.get_library_roots()
                health.is_library_root = norm_path in roots
                health.is_inside_library_root = any(
                    norm_path.startswith(r + os.sep) or norm_path == r
                    for r in roots
                )
            except Exception:
                pass

        # Gather entries
        entries = list_folder_entries(norm_path)
        health.total_entries = len(entries)

        if recursive and max_depth and max_depth > 1:
            from library.folder_index import walk_folder_entries
            deeper = walk_folder_entries(norm_path, max_depth=max_depth)
            entries = deeper

        self._analyze_entries(entries, health)
        self._detect_missing_cover(norm_path, health)
        self._compare_with_db(norm_path, health)

        # Compute score
        health.score = self._compute_score(health)
        health.status = classify_status(health.score)
        health.recommended_actions = self.build_recommendations(health)

        return health

    def analyze_entries(self, path: str, recursive: bool = False,
                        max_depth: int | None = 1) -> list[FolderEntry]:
        """Return analyzed FolderEntry list for a path."""
        entries = list_folder_entries(path)
        if recursive and max_depth and max_depth > 1:
            from library.folder_index import walk_folder_entries
            entries = walk_folder_entries(path, max_depth=max_depth)
        self._enrich_entries(entries)
        return entries

    def _analyze_entries(self, entries: list[FolderEntry], health: FolderHealth):
        """Fill health fields from an entry list."""
        formats = set()

        for e in entries:
            if e.kind == "folder":
                health.subfolder_count += 1
                continue

            if e.kind == "audio":
                health.audio_count += 1
                if e.db_id and e.is_indexed:
                    health.indexed_audio_count += 1
                else:
                    health.unindexed_audio_count += 1
                if e.ext:
                    formats.add(e.ext.lstrip(".").upper())
                if e.problems:
                    health.missing_metadata_count += 1
                continue

            if e.kind == "unsupported_audio":
                health.unsupported_audio_count += 1
                continue

        if len(formats) > 1:
            health.mixed_formats = True
        health.formats = sorted(formats)

    def detect_missing_metadata(self, entries: list[FolderEntry]) -> list[FolderProblem]:
        """Detect entries with missing metadata fields."""
        problems = []
        for e in entries:
            if e.kind != "audio":
                continue
            missing = []
            if not e.title:
                missing.append("title")
            if not e.artist:
                missing.append("artist")
            if not e.album:
                missing.append("album")
            if missing:
                problems.append(FolderProblem(
                    path=e.path,
                    problem_type="missing_metadata",
                    severity="warning",
                    description=f"Faltan campos: {', '.join(missing)}",
                    suggested_action="open_metadata_editor",
                    action_label="Editar metadata",
                ))
        return problems

    def detect_missing_cover(self, path: str, health: FolderHealth | None = None) -> bool:
        """Check if a folder has a cover image file. Updates health if provided."""
        has_cover = self._has_local_cover(path)
        if health is not None:
            health.missing_cover = not has_cover
        return has_cover

    def _has_local_cover(self, path: str) -> bool:
        try:
            for name in _COVER_NAMES:
                if os.path.isfile(os.path.join(path, name)):
                    return True
        except OSError:
            pass
        return False

    def detect_mixed_formats(self, entries: list[FolderEntry]) -> list[str]:
        """Return distinct audio formats found in entries."""
        formats = set()
        for e in entries:
            if e.kind == "audio" and e.ext:
                formats.add(e.ext.lstrip(".").upper())
        return sorted(formats)

    def _detect_missing_cover(self, path: str, health: FolderHealth):
        health.missing_cover = not self._has_local_cover(path)

    def _compare_with_db(self, path: str, health: FolderHealth):
        """Compare filesystem audio files with DB records under this folder."""
        if not self._db:
            return
        try:
            audio_files = set(list_audio_files(path))
            db_items = self._db.get_all_by_directory(path, exact=True)
            db_paths = {i.filepath for i in db_items}

            missing_from_db = audio_files - db_paths
            health.unindexed_audio_count = len(missing_from_db)

            # Count DB paths missing from filesystem
            stale_db = db_paths - audio_files
            health.missing_db_paths_count = len(stale_db)
        except Exception as e:
            logger.debug("compare_with_db failed for %s: %s", path, e)

    def _compute_score(self, health: FolderHealth) -> int:
        """Compute a 0-100 health score with penalties."""
        score = 100
        if not health.exists:
            return 0
        if not health.readable:
            return 20

        if health.audio_count > 0:
            ratio = health.indexed_audio_count / health.audio_count
            if ratio < 0.5:
                score -= 15
            elif ratio < 1.0:
                score -= 8

        if health.missing_metadata_count > 0 and health.audio_count > 0:
            penalty = min(15, health.missing_metadata_count * 3)
            score -= penalty

        if health.missing_cover and health.audio_count > 0:
            score -= 8

        if health.mixed_formats:
            score -= 6

        if health.unsupported_audio_count > 0:
            score -= 8

        if health.missing_db_paths_count > 0:
            penalty = min(20, health.missing_db_paths_count * 4)
            score -= penalty

        if health.permission_errors:
            score -= 30

        return max(0, min(100, score))

    def build_recommendations(self, health: FolderHealth) -> list[FolderActionRecommendation]:
        """Build actionable recommendations from health data."""
        recs = []

        if not health.is_library_root and not health.is_inside_library_root and health.exists:
            recs.append(FolderActionRecommendation(
                action="add_library_root",
                label="Agregar a biblioteca",
                severity="warning",
                priority=90,
                description="Esta carpeta no pertenece a tu biblioteca.",
                requires_confirmation=True,
            ))

        if health.unindexed_audio_count > 0:
            recs.append(FolderActionRecommendation(
                action="scan_folder",
                label="Escanear carpeta",
                severity="info",
                priority=80,
                description=f"{health.unindexed_audio_count} archivos sin indexar.",
                affected_count=health.unindexed_audio_count,
            ))

        if health.missing_metadata_count > 0:
            recs.append(FolderActionRecommendation(
                action="open_metadata_editor",
                label="Editar metadata",
                severity="warning",
                priority=70,
                description=f"{health.missing_metadata_count} archivos con metadata incompleta.",
                affected_count=health.missing_metadata_count,
            ))

        if health.missing_cover and health.audio_count > 0:
            recs.append(FolderActionRecommendation(
                action="find_cover",
                label="Buscar carátula",
                severity="info",
                priority=60,
                description="No se encontró carátula local en esta carpeta.",
            ))

        if health.mixed_formats:
            recs.append(FolderActionRecommendation(
                action="review_formats",
                label="Revisar formatos",
                severity="info",
                priority=50,
                description=f"Formatos mezclados: {', '.join(health.formats)}",
            ))

        if health.missing_db_paths_count > 0:
            recs.append(FolderActionRecommendation(
                action="cleanup_missing",
                label="Limpiar rutas faltantes",
                severity="warning",
                priority=85,
                description=f"{health.missing_db_paths_count} rutas en DB no existen en disco.",
                affected_count=health.missing_db_paths_count,
                requires_confirmation=True,
            ))

        if health.unsupported_audio_count > 0:
            recs.append(FolderActionRecommendation(
                action="convert_or_ignore",
                label="Convertir o ignorar",
                severity="warning",
                priority=40,
                description=f"{health.unsupported_audio_count} archivos no soportados.",
                affected_count=health.unsupported_audio_count,
            ))

        if health.permission_errors:
            recs.append(FolderActionRecommendation(
                action="open_in_file_manager",
                label="Abrir en gestor",
                severity="critical",
                priority=95,
                description="Errores de permisos al leer la carpeta.",
            ))

        recs.sort(key=lambda r: r.priority, reverse=True)
        return recs

    def _enrich_entries(self, entries: list[FolderEntry]):
        """Enrich entries with DB info if available."""
        if not self._db:
            return
        audio_entries = [e for e in entries if e.kind == "audio" and e.path]
        if not audio_entries:
            return
        try:
            paths = [e.path for e in audio_entries]
            placeholders = ",".join("?" * len(paths))
            rows = self._db.conn.execute(
                f"SELECT filepath, id, duration, COALESCE(title,'') as t, "
                f"COALESCE(artist,'') as a, COALESCE(album,'') as al "
                f"FROM media_items WHERE filepath IN ({placeholders}) "
                f"AND deleted_at IS NULL",
                paths
            ).fetchall()
            db_map = {r[0]: r for r in rows}
            for e in audio_entries:
                row = db_map.get(e.path)
                if row:
                    e.db_id = row[1]
                    e.is_indexed = True
                    e.duration = row[2] or 0.0
                    e.title = row[3]
                    e.artist = row[4]
                    e.album = row[5]
                    missing = []
                    if not e.title:
                        missing.append("title")
                    if not e.artist:
                        missing.append("artist")
                    if not e.album:
                        missing.append("album")
                    if missing:
                        e.status = "incomplete"
                        e.problems.append(f"missing_{','.join(missing)}")
                    else:
                        e.status = "ok"
                else:
                    e.is_indexed = False
                    e.status = "not_indexed"
        except Exception as exc:
            logger.debug("_enrich_entries failed: %s", exc)
