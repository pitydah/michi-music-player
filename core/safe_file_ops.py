"""Safe File Operations — move and rename with preflight, DB update, and rollback.

Intra-root only. Never deletes source files before DB is confirmed.
"""

from __future__ import annotations

import os
import shutil
import logging
from typing import Any

from library.folder_models import FolderMovePlan, FolderMoveResult

logger = logging.getLogger("michi.safe_file_ops")


class SafeFileOperations:
    """Move and rename files/folders with preflight validation and DB sync."""

    def __init__(self, db=None):
        self._db = db

    def set_db(self, db):
        self._db = db

    def plan_move(self, source: str, destination: str) -> FolderMovePlan:
        """Create a pre-flight move plan with all checks."""
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

        # Check filesystem
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
                    try:
                        plan.total_size_bytes += os.path.getsize(os.path.join(root, f))
                    except OSError:
                        pass

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

            # Sidecar covers
            for cover_name in ("cover.jpg", "cover.png", "folder.jpg", "folder.png",
                               "front.jpg", "front.png"):
                cover_path = os.path.join(source, cover_name)
                if os.path.isfile(cover_path):
                    plan.affected_sidecar_covers.append(cover_path)

        # Final validation
        if plan.files_to_move > 0:
            plan.can_proceed = True

        return plan

    def _check_db_impacts(self, plan: FolderMovePlan):
        """Check how many DB records would be affected."""
        try:
            prefix = plan.source + os.sep if os.path.isdir(plan.source) else plan.source
            rows = self._db.conn.execute(
                "SELECT COUNT(*) FROM media_items "
                "WHERE (filepath = ? OR filepath LIKE ?) AND deleted_at IS NULL",
                (plan.source, prefix + "%")).fetchone()
            plan.affected_media_items = rows[0] if rows else 0

            # Playlists that reference these files
            p_rows = self._db.conn.execute(
                "SELECT DISTINCT p.name FROM playlists p "
                "JOIN playlist_items pi ON pi.playlist_id = p.id "
                "WHERE pi.filepath = ? OR pi.filepath LIKE ?",
                (plan.source, prefix + "%")).fetchall()
            plan.affected_playlists = [r[0] for r in p_rows] if p_rows else []

            # Favorites
            f_rows = self._db.conn.execute(
                "SELECT COUNT(*) FROM favorites "
                "WHERE track_id = ? OR track_id LIKE ?",
                (plan.source, prefix + "%")).fetchone()
            plan.affected_favorites = f_rows[0] if f_rows else 0

            # History
            h_rows = self._db.conn.execute(
                "SELECT COUNT(*) FROM play_history "
                "WHERE track_id = ? OR track_id LIKE ?",
                (plan.source, prefix + "%")).fetchone()
            plan.affected_history = h_rows[0] if h_rows else 0

            # Check if destination is outside known roots
            if self._db:
                roots = self._db.get_library_roots()
                if roots:
                    norm_dst = os.path.normpath(plan.destination) + os.sep
                    plan.destination_outside_root = not any(
                        norm_dst.startswith(os.path.normpath(r) + os.sep)
                        for r in roots
                    )
        except Exception as e:
            logger.warning("check_db_impacts failed: %s", e)

    def execute_move(self, plan: FolderMovePlan) -> FolderMoveResult:
        """Execute a move operation with DB update and rollback capability."""
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

        # Preflight: ensure parent of destination exists
        os.makedirs(os.path.dirname(plan.destination), exist_ok=True)

        # Execute physical move
        try:
            shutil.move(plan.source, plan.destination)
            result.files_moved = plan.files_to_move
        except Exception as e:
            result.error_message = f"Error al mover: {e}"
            return result

        # Update DB if connected
        if self._db:
            try:
                updated = self._update_db_paths(plan.source, plan.destination)
                result.db_updated = updated
                result.playlists_updated = len(plan.affected_playlists)
            except Exception as e:
                result.error_message = f"Error actualizando DB: {e}"
                result.db_failed = [plan.source]
                # Rollback
                try:
                    shutil.move(plan.destination, plan.source)
                    result.rollback_performed = True
                    result.rollback_success = True
                except Exception as rb_e:
                    logger.critical("Rollback failed: %s. Files may be at %s",
                                    rb_e, plan.destination)
                    result.rollback_success = False
                return result

        result.success = True
        return result

    def _update_db_paths(self, old_path: str, new_path: str) -> int:
        """Update all DB records referencing old_path to new_path."""
        count = 0

        if os.path.isfile(new_path):
            # Single file
            self._db.conn.execute(
                "UPDATE media_items SET filepath=?, filename=?, directory=?, "
                "updated_at=? WHERE filepath=?",
                (new_path, os.path.basename(new_path),
                 os.path.dirname(new_path), __import__("time").time(), old_path))
            self._db.conn.execute(
                "UPDATE playlist_items SET filepath=? WHERE filepath=?",
                (new_path, old_path))
            self._db.conn.execute(
                "UPDATE play_history SET track_id=? WHERE track_id=?",
                (new_path, old_path))
            self._db.conn.execute(
                "UPDATE favorites SET track_id=? WHERE track_id=?",
                (new_path, old_path))
            self._db.conn.execute(
                "UPDATE queue_state SET filepath=? WHERE filepath=?",
                (new_path, old_path))
            count += 1
        else:
            prefix = old_path + os.sep
            new_prefix = new_path + os.sep

            # Media items
            rows = self._db.conn.execute(
                "SELECT id, filepath, directory, filename FROM media_items "
                "WHERE (filepath = ? OR filepath LIKE ?) AND deleted_at IS NULL",
                (old_path, prefix + "%")).fetchall()
            for row in rows:
                rid, fp, _dir, fname = row
                if fp == old_path:
                    new_fp = new_path
                    new_dir = os.path.dirname(new_path)
                else:
                    new_fp = fp.replace(old_path, new_path, 1)
                    new_dir = os.path.dirname(new_fp)
                self._db.conn.execute(
                    "UPDATE media_items SET filepath=?, directory=?, "
                    "filename=?, updated_at=? WHERE id=?",
                    (new_fp, new_dir, os.path.basename(new_fp),
                     __import__("time").time(), rid))
                count += 1

            # Playlist items
            self._db.conn.execute(
                "UPDATE playlist_items SET filepath=? WHERE filepath=?",
                (new_path, old_path))
            p_rows = self._db.conn.execute(
                "SELECT id, filepath FROM playlist_items "
                "WHERE filepath LIKE ?", (prefix + "%",)).fetchall()
            for pr in p_rows:
                new_pfp = pr[1].replace(old_path, new_path, 1)
                self._db.conn.execute(
                    "UPDATE playlist_items SET filepath=? WHERE id=?",
                    (new_pfp, pr[0]))

            # Play history
            self._db.conn.execute(
                "UPDATE play_history SET track_id=? WHERE track_id=?",
                (new_path, old_path))
            h_rows = self._db.conn.execute(
                "SELECT id, track_id FROM play_history "
                "WHERE track_id LIKE ?", (prefix + "%",)).fetchall()
            for hr in h_rows:
                new_hid = hr[1].replace(old_path, new_path, 1)
                self._db.conn.execute(
                    "UPDATE play_history SET track_id=? WHERE id=?",
                    (new_hid, hr[0]))

            # Favorites
            self._db.conn.execute(
                "UPDATE favorites SET track_id=? WHERE track_id=?",
                (new_path, old_path))
            fav_rows = self._db.conn.execute(
                "SELECT rowid, track_id FROM favorites "
                "WHERE track_id LIKE ?", (prefix + "%",)).fetchall()
            for fr in fav_rows:
                new_fid = fr[1].replace(old_path, new_path, 1)
                self._db.conn.execute(
                    "UPDATE favorites SET track_id=? WHERE rowid=?",
                    (new_fid, fr[0]))

            # Queue state
            self._db.conn.execute(
                "UPDATE queue_state SET filepath=? WHERE filepath=?",
                (new_path, old_path))
            q_rows = self._db.conn.execute(
                "SELECT id, filepath FROM queue_state "
                "WHERE filepath LIKE ?", (prefix + "%",)).fetchall()
            for qr in q_rows:
                new_qfp = qr[1].replace(old_path, new_path, 1)
                self._db.conn.execute(
                    "UPDATE queue_state SET filepath=? WHERE id=?",
                    (new_qfp, qr[0]))

        self._db.conn.commit()

        # Rebuild FTS
        try:
            from library.search_index import SearchIndex
            idx = SearchIndex(self._db.conn)
            if idx.fts_exists:
                idx.rebuild_fts()
        except Exception:
            pass

        return count
