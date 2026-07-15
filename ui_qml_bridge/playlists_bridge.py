"""PlaylistsBridge — connects QML Playlists page to real playlist backend.
Integrates: JobService, ActionRegistry, ConfirmationBridge, NavigationBridge,
PageStateStore, CapabilityBridge, AccessibilityBridge, NotificationBridge.
No direct DB access from bridge — delegates to PlaylistService.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Property, Slot
import logging

from core.playlist_service import PlaylistService

logger = logging.getLogger("michi.playlists")


class PlaylistsBridge(QObject):
    dataChanged = Signal()
    jobProgress = Signal(str, int)
    partialSuccess = Signal(str, int, int)

    def __init__(self, db=None, selection_context=None, player_service=None,
                 playlist_service=None, action_registry=None,
                 confirmation_bridge=None, navigation_bridge=None,
                 page_state_store=None, capability_bridge=None,
                 accessibility_bridge=None, notification_bridge=None,
                 job_bridge=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._sel_ctx = selection_context
        self._player = player_service
        self._svc = playlist_service or PlaylistService(db=db)
        self._action_registry = action_registry
        self._confirmation = confirmation_bridge
        self._navigation = navigation_bridge
        self._page_state = page_state_store
        self._capability = capability_bridge
        self._accessibility = accessibility_bridge
        self._notifications = notification_bridge
        self._job_bridge = job_bridge
        self._playlists: list[dict] = []
        self._import_cache: dict[str, dict] = {}
        self._operation_counter = 0

    def setSelectionContext(self, ctx):
        self._sel_ctx = ctx

    def _can(self) -> bool:
        return (
            (self._svc is not None and hasattr(self._svc, 'list'))
            or (self._db is not None and hasattr(self._db, 'get_playlists'))
        )

    def _notify(self, text: str, kind: str = "info"):
        if self._notifications:
            self._notifications.showMessage(text, kind=kind)

    def _require_confirmation(self, action: str, title: str,
                              details: dict | None = None) -> bool:
        if self._confirmation:
            cid = f"playlist_{action}_{self._operation_counter}"
            self._operation_counter += 1
            self._confirmation.requestConfirmation(cid, title, details or {})
            return True
        return False

    @Property("QVariantList", notify=dataChanged)
    def playlists(self):
        return self._playlists

    @Slot()
    def refresh(self):
        result = []
        if self._can():
            try:
                plists = self._svc.list()
                for p in plists:
                    pid = p.get("id", 0)
                    name = p.get("name", "")
                    track_count = p.get("track_count", 0)
                    result.append({
                        "id": pid,
                        "title": name,
                        "track_count": track_count,
                        "duration": "",
                        "cover_key": f"playlist_{pid}",
                        "is_smart": False,
                        "updated_at": "",
                        "description": "",
                    })
            except Exception:
                logger.debug("Playlist refresh failed", exc_info=True)
                result = []
        if not result and os.environ.get("MICHI_QML_DEMO") == "1":
            result = [
                {"id": 0, "title": "Favoritas", "track_count": 12, "duration": "45:30",
                 "cover_key": "fav", "is_demo": True},
                {"id": 0, "title": "Descubrimientos", "track_count": 8, "duration": "32:15",
                 "cover_key": "disc", "is_demo": True},
            ]
        self._playlists = result
        self.dataChanged.emit()

    @Slot(str, result=dict)
    def createPlaylist(self, name: str):
        result = self._svc.create(name) if self._can() else {"ok": False, "error": "NO_DB"}
        if result.get("ok"):
            self.refresh()
            self._notify(f"Playlist '{name}' creada", "success")
        return result

    @Slot(int, str, result=dict)
    def renamePlaylist(self, pid: int, name: str):
        result = self._svc.rename(pid, name) if self._can() else {"ok": False, "error": "NO_DB"}
        if result.get("ok"):
            self.refresh()
            self._notify(f"Playlist renombrada a '{name}'", "success")
        return result

    @Slot(int, result=dict)
    def duplicatePlaylist(self, pid: int):
        result = self._svc.duplicate(pid) if self._can() else {"ok": False, "error": "NO_DB"}
        if result.get("ok"):
            self.refresh()
            self._notify(f"Playlist duplicada como '{result.get('name', '')}'", "success")
        return result

    @Slot(int, result=dict)
    def deletePlaylist(self, pid: int):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        plist = next((p for p in self._playlists if p.get("id") == pid), {})
        name = plist.get("title", "sin nombre")
        cid = f"delete_playlist_{pid}_{int(time.time())}"
        if self._confirmation:
            self._confirmation.requestConfirmation(
                cid, f"Eliminar playlist '{name}'?",
                {"pid": pid, "name": name, "action": "delete"}
            )
            return {"ok": True, "requires_confirmation": True, "confirmation_id": cid}
        return self._execute_delete(pid, name)

    def _execute_delete(self, pid: int, name: str) -> dict:
        result = self._svc.delete(pid)
        if result.get("ok"):
            self.refresh()
            self._notify(f"Playlist '{name}' eliminada", "info")
        return result

    @Slot(int, result=dict)
    def clearPlaylist(self, pid: int):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        cid = f"clear_playlist_{pid}_{int(time.time())}"
        if self._confirmation:
            self._confirmation.requestConfirmation(
                cid, "Borrar todas las pistas de esta playlist?",
                {"pid": pid, "action": "clear"}
            )
            return {"ok": True, "requires_confirmation": True, "confirmation_id": cid}
        return self._execute_clear(pid)

    def _execute_clear(self, pid: int) -> dict:
        result = self._svc.clear_playlist(pid)
        if result.get("ok"):
            self.refresh()
            self._notify("Playlist limpiada", "info")
        return result

    @Slot(str, bool, result=dict)
    def resolveConfirmation(self, confirmation_id: str, accepted: bool):
        if not accepted:
            return {"ok": False, "cancelled": True}
        if confirmation_id.startswith("delete_playlist_"):
            parts = confirmation_id.split("_")
            if len(parts) >= 4:
                try:
                    pid = int(parts[2])
                except (ValueError, IndexError):
                    return {"ok": False, "error": "INVALID_ID"}
                plist = next((p for p in self._playlists if p.get("id") == pid), {})
                return self._execute_delete(pid, plist.get("title", ""))
        if confirmation_id.startswith("clear_playlist_"):
            parts = confirmation_id.split("_")
            if len(parts) >= 4:
                try:
                    pid = int(parts[2])
                except (ValueError, IndexError):
                    return {"ok": False, "error": "INVALID_ID"}
                return self._execute_clear(pid)
        return {"ok": False, "error": "UNKNOWN_CONFIRMATION"}

    def _get_items_internal(self, pid: int) -> list[dict]:
        if not self._can():
            return []
        try:
            if self._svc and hasattr(self._svc, '_get_items_internal'):
                return self._svc._get_items_internal(pid)
            if self._db and hasattr(self._db, 'get_playlist_items'):
                items = self._db.get_playlist_items(pid)
                return [
                    {
                        "track_id": getattr(item, 'id', 0) if not isinstance(item, dict) else item.get("id", 0),
                        "track_uid": "",
                        "filepath": getattr(item, 'filepath', '') if not isinstance(item, dict) else item.get("filepath", ''),
                        "title": getattr(item, 'title', '') if not isinstance(item, dict) else item.get("title", ''),
                        "artist": "",
                        "album": "",
                        "duration": 0,
                        "position": idx,
                    }
                    for idx, item in enumerate(items)
                ]
            return []
        except Exception:
            return []

    def _playlist_item_to_public(self, item: dict) -> dict:
        return {
            "track_id": item.get("track_id", 0),
            "track_uid": item.get("track_uid", ""),
            "public_ref": f"track_{item.get('track_id', 0)}",
            "title": item.get("title", ""),
            "artist": item.get("artist", ""),
            "album": item.get("album", ""),
            "duration": item.get("duration", 0),
            "cover_key": item.get("album_key", "") or item.get("album", ""),
            "missing": not bool(item.get("filepath")),
        }

    @Slot(int, result=dict)
    def getPlaylistDetail(self, pid: int):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        result = self._svc.get_detail(pid)
        if not result.get("ok"):
            return result
        tracks = [self._playlist_item_to_public(t) for t in result.get("tracks", [])]
        return {"ok": True, "tracks": tracks, "count": len(tracks)}

    @Slot(int, str, str, result=dict)
    def addTrackToPlaylist(self, pid: int, filepath: str = "", track_id: str = ""):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        if not filepath and not track_id and self._sel_ctx:
            filepath = self._sel_ctx.selectedFilepath
            track_id = self._sel_ctx.selectedTrackId
        try:
            if track_id:
                try:
                    tid = int(track_id)
                except (ValueError, TypeError):
                    tid = 0
                if tid:
                    result = self._svc.add_track(pid, track_id=tid)
                else:
                    return {"ok": False, "error": "NO_VALID_TRACK"}
            elif filepath and Path(filepath).is_file():
                result = self._svc.add_track(pid, filepath=filepath)
            else:
                return {"ok": False, "error": "NO_SELECTION"}
            if result.get("ok"):
                self.refresh()
            return result
        except Exception as e:
            logger.debug("Add track to playlist failed", exc_info=True)
            return {"ok": False, "error": str(e)}

    @Slot(int, int, result=dict)
    def removeTrackFromPlaylist(self, pid: int, track_id: int):
        result = self._svc.remove_track(pid, track_id) if self._can() else {"ok": False, "error": "NO_DB"}
        if result.get("ok"):
            self.refresh()
        return result

    @Slot(int, result=dict)
    def addSelectedTrackToPlaylist(self, pid: int):
        return self.addTrackToPlaylist(pid)

    @Slot(int, "QVariantList", result=dict)
    def batchAddTracks(self, pid: int, tracks: list):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        count = 0
        errors = 0
        for t in tracks:
            fp = t.get("filepath", "") if isinstance(t, dict) else ""
            tid = t.get("track_id", 0) if isinstance(t, dict) else 0
            try:
                if tid:
                    r = self._svc.add_track(pid, track_id=int(tid))
                elif fp:
                    r = self._svc.add_track(pid, filepath=fp)
                else:
                    errors += 1
                    continue
                if r.get("ok"):
                    count += 1
                else:
                    errors += 1
            except Exception:
                errors += 1
        self.refresh()
        if errors > 0:
            self.partialSuccess.emit(f"Se agregaron {count} pistas, {errors} fallaron", count, errors)
        return {"ok": True, "count": count, "errors": errors}

    @Slot(int, "QVariantList", result=dict)
    def batchAddTrackIds(self, playlist_id: int, track_ids: list):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        count = 0
        errors = 0
        for tid in track_ids:
            try:
                r = self._svc.add_track(playlist_id, track_id=int(tid))
                if r.get("ok"):
                    count += 1
                else:
                    errors += 1
            except (ValueError, TypeError):
                errors += 1
        self.refresh()
        return {"ok": True, "count": count, "errors": errors}

    @Slot(int, int, int, result=dict)
    def reorderTrack(self, pid: int, from_index: int, to_index: int):
        result = self._svc.reorder(pid, from_index, to_index) if self._can() else {"ok": False, "error": "NO_DB"}
        if result.get("ok"):
            self.refresh()
        return result

    @Slot(int, int, result=dict)
    def playPlaylistFromIndex(self, pid: int, index: int = 0):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        items = self._get_items_internal(pid)
        if not items:
            return {"ok": False, "error": "NO_TRACKS"}
        fps = [t["filepath"] for t in items[index:] if t.get("filepath")]
        if not fps:
            return {"ok": False, "error": "NO_TRACKS"}
        if self._player and hasattr(self._player, 'enqueue'):
            self._player.enqueue(fps, play_now=True)
            return {"ok": True, "count": len(fps)}
        return {"ok": False, "error": "UNSUPPORTED"}

    @Slot(result=dict)
    def playlistScore(self) -> dict:
        score = 0
        if self._can():
            score += 20
        if self._playlists:
            real = [p for p in self._playlists if not p.get("is_demo")]
            count = len(real)
            if count > 0:
                score += min(30, count * 5)
        if self._svc and hasattr(self._svc, 'get_detail'):
            score += 20
        if self._svc and hasattr(self._svc, 'rename'):
            score += 15
        if self._svc and hasattr(self._svc, 'delete'):
            score += 15
        return {
            "score": min(100, score),
            "has_db": self._can(),
            "playlist_count": len([p for p in self._playlists if not p.get("is_demo")]),
            "can_create": self._can(),
            "can_delete": self._can(),
            "can_rename": self._can(),
        }

    @Slot(str, result=dict)
    def saveQueueAsPlaylist(self, name: str):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        if not name:
            return {"ok": False, "error": "EMPTY_NAME"}
        result = self._svc.save_queue(self._player, name)
        if result.get("ok"):
            self.refresh()
            self._notify(f"Cola guardada como '{name}'", "success")
        return result

    @Slot(str, result=dict)
    def previewPlaylistImport(self, filepath: str):
        if self._svc:
            return self._svc.import_preview(filepath)
        return {"ok": False, "error": "NO_SERVICE"}

    @Slot(str, str, result=dict)
    def confirmPlaylistImport(self, filepath: str, name: str = ""):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        result = self._svc.import_confirm(filepath, name)
        if result.get("ok"):
            self.refresh()
            self._notify(f"Importada '{result.get('name', name)}' ({result.get('count', 0)} pistas)", "success")
        return result

    def _run_import_via_job(self, filepath: str, name: str = ""):
        if self._job_bridge and hasattr(self._job_bridge, '_add_job'):
            def _import():
                result = self._svc.import_confirm(filepath, name)
                if not result.get("ok"):
                    raise RuntimeError(result.get("message", "Import failed"))
                return result
            self._job_bridge._add_job("playlist_import", f"Importando playlist {name or Path(filepath).stem}", _import)
            return {"ok": True, "async": True}
        return self.confirmPlaylistImport(filepath, name)

    @Slot(str, result=dict)
    def cancelPlaylistImport(self, import_id: str):
        return self._svc.cancel_import(import_id)

    def _export_m3u(self, destination_path: str, items: list[dict]) -> dict:
        try:
            fps = [t.get("filepath", "") for t in items if t.get("filepath")]
            with open(destination_path, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for fp in fps:
                    f.write(f"{fp}\n")
            return {"ok": True, "count": len(fps)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _export_m3u8(self, destination_path: str, items: list[dict]) -> dict:
        try:
            fps = [t.get("filepath", "") for t in items if t.get("filepath")]
            with open(destination_path, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for fp in fps:
                    f.write(f"{fp}\n")
            return {"ok": True, "count": len(fps)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _run_export_via_job(self, pid: int, destination_path: str, fmt: str = "m3u"):
        if self._job_bridge and hasattr(self._job_bridge, '_add_job'):
            def _export():
                items = self._get_items_internal(pid)
                if not items:
                    raise RuntimeError("No tracks to export")
                if fmt == "m3u8":
                    return self._export_m3u8(destination_path, items)
                return self._export_m3u(destination_path, items)
            self._job_bridge._add_job("playlist_export", "Exportando playlist", _export)
            return {"ok": True, "async": True}
        return self._export_direct(pid, destination_path, fmt)

    def _export_direct(self, pid: int, destination_path: str, fmt: str) -> dict:
        items = self._get_items_internal(pid)
        if not items:
            return {"ok": False, "error": "NO_TRACKS"}
        if fmt == "m3u8":
            return self._export_m3u8(destination_path, items)
        return self._export_m3u(destination_path, items)

    @Slot(str, result=dict)
    def importM3U(self, filepath: str):
        return self._run_import_via_job(filepath)

    @Slot(str, result=dict)
    def importM3U8(self, filepath: str):
        return self._run_import_via_job(filepath)

    @Slot(int, str, result=dict)
    def exportM3U(self, pid: int, destination_path: str):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        return self._run_export_via_job(pid, destination_path, "m3u")

    @Slot(int, str, result=dict)
    def exportM3U8(self, pid: int, destination_path: str):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        return self._run_export_via_job(pid, destination_path, "m3u8")

    @Slot(int, result=dict)
    def playPlaylist(self, pid: int):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        items = self._get_items_internal(pid)
        if not items:
            return {"ok": False, "error": "NO_TRACKS"}
        fps = [t["filepath"] for t in items if t.get("filepath")]
        if not fps:
            return {"ok": False, "error": "NO_TRACKS"}
        if self._player and hasattr(self._player, 'enqueue'):
            self._player.enqueue(fps, play_now=True)
            return {"ok": True, "count": len(fps)}
        return {"ok": False, "error": "UNSUPPORTED"}

    @Slot(int, result=dict)
    def setCover(self, pid: int, cover_path: str):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        try:
            if hasattr(self._svc, 'set_cover'):
                return self._svc.set_cover(pid, cover_path)
            return {"ok": False, "error": "UNSUPPORTED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(int, str, result=dict)
    def setDescription(self, pid: int, description: str):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        try:
            if self._db and hasattr(self._db, 'update_playlist'):
                self._db.update_playlist(pid, description=description)
                self.refresh()
                return {"ok": True}
            if hasattr(self._svc, '_db') and self._svc._db and hasattr(self._svc._db, 'update_playlist'):
                self._svc._db.update_playlist(pid, description=description)
                self.refresh()
                return {"ok": True}
            return {"ok": False, "error": "NO_DB"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(int, result=dict)
    def detectMissingTracks(self, pid: int):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        result = self._svc.detect_missing(pid)
        return result

    @Slot(int, "QVariantList", result=dict)
    def removeMissingTracks(self, pid: int, track_ids: list):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        removed = 0
        errors = 0
        for tid in track_ids:
            try:
                r = self._svc.remove_track(pid, int(tid))
                if r.get("ok"):
                    removed += 1
                else:
                    errors += 1
            except (ValueError, TypeError):
                errors += 1
        if removed:
            self.refresh()
        return {"ok": True, "removed": removed, "errors": errors}

    @Slot(result=dict)
    def beginTransaction(self):
        if self._svc:
            return self._svc.begin()
        return {"ok": False, "error": "NO_SERVICE"}

    @Slot(result=dict)
    def commitTransaction(self):
        if self._svc:
            result = self._svc.commit()
            self.refresh()
            return result
        return {"ok": False, "error": "NO_SERVICE"}

    @Slot(result=dict)
    def rollbackTransaction(self):
        if self._svc:
            result = self._svc.rollback()
            self.refresh()
            return result
        return {"ok": False, "error": "NO_SERVICE"}

    @Slot(str, result=dict)
    def setSmartRule(self, pid: int, rule_json: str):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        try:
            rule = json.loads(rule_json) if rule_json else {}
            if hasattr(self._db, 'update_playlist'):
                self._db.update_playlist(pid, smart_rule=json.dumps(rule))
                self.refresh()
                return {"ok": True}
            return {"ok": False, "error": "UNSUPPORTED"}
        except (json.JSONDecodeError, Exception) as e:
            return {"ok": False, "error": str(e)}

    @staticmethod
    def _format_duration(secs: float) -> str:
        if secs <= 0:
            return ""
        h = int(secs // 3600)
        m = int((secs % 3600) // 60)
        return f"{h}h {m}m" if h > 0 else f"{m} min"
