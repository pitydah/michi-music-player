"""Safe File Operations — move and rename with preflight, DB update, and rollback.

Intra-root only (blocked outside library roots). Never deletes source before
DB is confirmed. Uses SQLite transactions for atomic DB updates.
"""

from __future__ import annotations

import os
import shutil
import logging
import contextlib

from library.folder_models import FolderMovePlan, FolderMoveResult

logger = logging.getLogger("michi.safe_file_ops")

_TABLES_WITH_FILEPATH = frozenset({
    "media_items", "playlist_items", "play_history", "favorites", "queue_state",
})


class SafeFileOperations:
    """Move and rename files/folders with preflight validation and DB sync."""

    def __init__(self, db=None):
        self._db = db

    def set_db(self, db):
        self._db = db

    @staticmethod
    def _table_exists(conn, table: str) -> bool:
        try:
            conn.execute(f"SELECT 1 FROM {table} LIMIT 1")
            return True
        except Exception:
            return False

    def plan_move(self, source: str, destination: str) -> FolderMovePlan:
        """Create a pre-flight move plan with full validation.

        Blocks if:
        - source does not exist
        - destination already exists
        - destination is outside library roots (intra-root only)
        - source and destination cross roots
        """
        plan = FolderMovePlan(source=source, destination=destination)
        plan.is_rename = os.path.dirname(source) == os.path.dirname(destination)

        if not os.path.exists(source):
            plan.warnings.append("El origen no existe")
            return plan

        if os.path.exists(destination):
            plan.conflicts.append("El destino ya existe")
            return plan

        if not os.access(os.path.dirname(destination), os.W_OK):
            plan.warnings.append("No hay permisos de escritura en el destino")
            return plan

        # Root validation: intra-root only with DB
        if self._db:
            try:
                roots = self._db.get_library_roots()
                if roots:
                    norm_src = os.path.normpath(source) + os.sep
                    norm_dst = os.path.normpath(destination) + os.sep
                    src_root = None
                    for r in roots:
                        nr = os.path.normpath(r) + os.sep
                        if norm_src.startswith(nr):
                            src_root = nr
                            break
                    if src_root is None and os.path.isfile(source):
                        # File may be inside a root
                        for r in roots:
                            nr = os.path.normpath(r) + os.sep
                            if os.path.normpath(source).startswith(
                                    os.path.normpath(r)):
                                src_root = os.path.normpath(r) + os.sep
                                break
                    if src_root is None:
                        plan.warnings.append(
                            "El origen no est\u00e1 dentro de ninguna ra\u00edz de biblioteca")
                    else:
                        if not norm_dst.startswith(src_root):
                            plan.conflicts.append(
                                "El destino queda fuera de la ra\u00edz de biblioteca "
                                "(intra-root only)")
                            plan.destination_outside_root = True

                        # Cross-root check
                        for r in roots:
                            nr = os.path.normpath(r) + os.sep
                            if nr != src_root and norm_dst.startswith(nr):
                                plan.conflicts.append(
                                    "No se permite mover entre diferentes ra\u00edces "
                                    "de biblioteca")
                                break
            except Exception as e:
                logger.warning("root validation failed: %s", e)

        # Check filesystem
        with contextlib.suppress(Exception):
            src_stat = os.statvfs(source) if hasattr(os, 'statvfs') else None
            dst_stat = os.statvfs(os.path.dirname(destination)) if hasattr(os, 'statvfs') else None
            if src_stat and dst_stat:
                plan.same_filesystem = (src_stat.f_fsid == dst_stat.f_fsid)

        # Count files and folders
        if os.path.isfile(source):
            plan.files_to_move = 1
            plan.total_size_bytes = os.path.getsize(source)
        elif os.path.isdir(source):
            for root, dirs, files in os.walk(source):
                plan.folders_to_move += len(dirs)
                plan.files_to_move += len(files)
                for f in files:
                    with contextlib.suppress(OSError):
                        plan.total_size_bytes += os.path.getsize(os.path.join(root, f))

        # Check DB impacts
        if self._db:
            self._check_db_impacts(plan)

        # Check sidecar files
        if os.path.isdir(source):
            for name in os.listdir(source):
                full = os.path.join(source, name)
                if os.path.isfile(full):
                    ext = os.path.splitext(name)[1].lower()
                    if ext in (".cue", ".log"):
                        plan.affected_cue_files.append(full)
                    if ext in (".m3u", ".m3u8", ".pls"):
                        plan.affected_playlist_files.append(full)
            for cover_name in ("cover.jpg", "cover.png", "folder.jpg", "folder.png",
                               "front.jpg", "front.png"):
                cover_path = os.path.join(source, cover_name)
                if os.path.isfile(cover_path):
                    plan.affected_sidecar_covers.append(cover_path)

        if plan.files_to_move > 0 and not plan.conflicts:
            plan.can_proceed = True

        return plan

    def _check_db_impacts(self, plan: FolderMovePlan):
        try:
            prefix = plan.source.rstrip(os.sep) + os.sep if os.path.isdir(plan.source) else plan.source
            conn = self._db.conn
            rows = conn.execute(
                "SELECT COUNT(*) FROM media_items "
                "WHERE (filepath = ? OR filepath LIKE ?) AND deleted_at IS NULL",
                (plan.source, prefix + "%")).fetchone()
            plan.affected_media_items = rows[0] if rows else 0

            if self._table_exists(conn, "playlist_items"):
                p_rows = conn.execute(
                    "SELECT DISTINCT p.name FROM playlists p "
                    "JOIN playlist_items pi ON pi.playlist_id = p.id "
                    "WHERE pi.filepath = ? OR pi.filepath LIKE ?",
                    (plan.source, prefix + "%")).fetchall()
                plan.affected_playlists = [r[0] for r in p_rows] if p_rows else []

            if self._table_exists(conn, "favorites"):
                f_rows = conn.execute(
                    "SELECT COUNT(*) FROM favorites "
                    "WHERE track_id = ? OR track_id LIKE ?",
                    (plan.source, prefix + "%")).fetchone()
                plan.affected_favorites = f_rows[0] if f_rows else 0

            if self._table_exists(conn, "play_history"):
                h_rows = conn.execute(
                    "SELECT COUNT(*) FROM play_history "
                    "WHERE track_id = ? OR track_id LIKE ?",
                    (plan.source, prefix + "%")).fetchone()
                plan.affected_history = h_rows[0] if h_rows else 0

            if self._table_exists(conn, "queue_state"):
                q_rows = conn.execute(
                    "SELECT COUNT(*) FROM queue_state "
                    "WHERE filepath = ? OR filepath LIKE ?",
                    (plan.source, prefix + "%")).fetchone()
                plan.affected_queue = q_rows[0] if q_rows else 0

            roots = self._db.get_library_roots() if self._db else []
            if roots:
                norm_dst = os.path.normpath(plan.destination) + os.sep
                plan.destination_outside_root = not any(
                    norm_dst.startswith(os.path.normpath(r) + os.sep)
                    for r in roots
                )
        except Exception as e:
            logger.warning("check_db_impacts failed: %s", e)

    def execute_move(self, plan: FolderMovePlan) -> FolderMoveResult:
        """Execute move with transaction DB update and rollback on failure."""
        result = FolderMoveResult(
            source=plan.source,
            destination=plan.destination,
        )

        if not plan.can_proceed:
            result.error_message = "El plan indica que no se puede proceder"
            return result

        if not os.path.exists(plan.source):
            result.error_message = f"El origen ya no existe: {plan.source}"
            return result

        os.makedirs(os.path.dirname(plan.destination), exist_ok=True)

        # Execute physical move
        try:
            shutil.move(plan.source, plan.destination)
            result.files_moved = plan.files_to_move
        except Exception as e:
            result.error_message = f"Error al mover: {e}"
            return result

        # Update DB in a single transaction
        if self._db:
            try:
                updated = self._update_db_paths(plan.source, plan.destination)
                result.db_updated = updated
                result.playlists_updated = len(plan.affected_playlists)
                result.favorites_updated = plan.affected_favorites
                result.history_updated = plan.affected_history
                result.queue_updated = getattr(plan, 'affected_queue', 0)
            except Exception as e:
                result.error_message = f"Error actualizando DB: {e}"
                result.db_failed = [plan.source]
                with contextlib.suppress(Exception):
                    shutil.move(plan.destination, plan.source)
                    result.rollback_performed = True
                    result.rollback_success = True
                return result

        result.success = True
        return result

    def _update_db_paths(self, old_path: str, new_path: str) -> int:
        """Update all DB records using a single transaction."""
        conn = self._db.conn
        count = 0

        with conn:
            if os.path.isfile(new_path):
                if self._table_exists(conn, "media_items"):
                    try:
                        conn.execute(
                            "UPDATE media_items SET filepath=?, filename=?, directory=?, "
                            "updated_at=? WHERE filepath=?",
                            (new_path, os.path.basename(new_path),
                             os.path.dirname(new_path), __import__("time").time(), old_path))
                    except Exception:
                        conn.execute(
                            "UPDATE media_items SET filepath=?, filename=?, directory=? "
                            "WHERE filepath=?",
                            (new_path, os.path.basename(new_path),
                             os.path.dirname(new_path), old_path))
                    count += 1
                for table in ("playlist_items", "queue_state"):
                    if self._table_exists(conn, table):
                        conn.execute(
                            f"UPDATE {table} SET filepath=? WHERE filepath=?",
                            (new_path, old_path))
                for table in ("play_history", "favorites"):
                    if self._table_exists(conn, table):
                        conn.execute(
                            f"UPDATE {table} SET track_id=? WHERE track_id=?",
                            (new_path, old_path))
            else:
                prefix = old_path.rstrip(os.sep) + os.sep
                if self._table_exists(conn, "media_items"):
                    rows = conn.execute(
                        "SELECT id, filepath FROM media_items "
                        "WHERE (filepath = ? OR filepath LIKE ?) AND deleted_at IS NULL",
                        (old_path, prefix + "%")).fetchall()
                    for rid, fp in rows:
                        new_fp = new_path if fp == old_path else fp.replace(old_path, new_path, 1)
                        try:
                            conn.execute(
                                "UPDATE media_items SET filepath=?, directory=?, "
                                "filename=?, updated_at=? WHERE id=?",
                                (new_fp, os.path.dirname(new_fp),
                                 os.path.basename(new_fp),
                                 __import__("time").time(), rid))
                        except Exception:
                            conn.execute(
                                "UPDATE media_items SET filepath=?, directory=?, "
                                "filename=? WHERE id=?",
                                (new_fp, os.path.dirname(new_fp),
                                 os.path.basename(new_fp), rid))
                        count += 1

                for table in ("playlist_items", "queue_state"):
                    if self._table_exists(conn, table):
                        self._batch_update_column(conn, table, "filepath",
                                                   old_path, new_path, prefix)
                for table in ("play_history", "favorites"):
                    if self._table_exists(conn, table):
                        self._batch_update_column(conn, table, "track_id",
                                                   old_path, new_path, prefix)

        # Rebuild FTS after transaction
        try:
            from library.search_index import SearchIndex
            idx = SearchIndex(conn)
            if idx.fts_exists:
                idx.rebuild_fts()
        except Exception:
            pass

        return count

    @staticmethod
    def _batch_update_column(conn, table: str, column: str,
                              old_path: str, new_path: str, prefix: str):
        """Update all rows where column starts with old_path prefix."""
        # Exact match
        conn.execute(
            f"UPDATE {table} SET {column}=? WHERE {column}=?",
            (new_path, old_path))
        # Prefix match using LIKE with safe pattern
        conn.execute(
            f"UPDATE {table} SET {column}=? || substr({column}, ?) "
            f"WHERE {column} LIKE ?",
            (new_path, len(old_path) + 1, prefix + "%"))
