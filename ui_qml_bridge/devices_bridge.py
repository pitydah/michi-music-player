"""DevicesBridge — connects QML Sync/Devices page to real SyncManager.

Returns dict ok/error from all actions. Does not mark serverActive=true
if start() fails. Normalises result types: True, False, {"ok": true},
{"ok": false, ...}, exception.

Bridge accepts dependencies by constructor — no service construction inside.
Audio-only — explicitly exclude video, show message if video content found.
"""
from __future__ import annotations

import os

from PySide6.QtCore import QObject, Signal, Property, Slot
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sync.sync_manager import SyncManager

logger = logging.getLogger("michi.devices")

_STARTED_ERROR = "NO_SYNC_MANAGER"
_AUDIO_EXTS = frozenset({
    ".mp3", ".flac", ".wav", ".ogg", ".opus", ".m4a", ".aac",
    ".wma", ".dsf", ".dff", ".ape", ".aiff", ".alac",
})
_VIDEO_EXTS = frozenset({".mp4", ".avi", ".mkv", ".mov", ".webm", ".m4v", ".wmv"})


def _normalise_result(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, bool):
        return {"ok": raw}
    if raw is None:
        return {"ok": True}
    if isinstance(raw, str):
        return {"ok": False, "error": raw}
    return {"ok": False, "error": f"Unexpected result: {type(raw).__name__}"}


def _typed_error(code: str, message: str = "") -> dict:
    return {"ok": False, "error": code, "message": message or code}


def _is_audio_extension(path: str) -> str | None:
    """Returns 'audio', 'video', or None."""
    ext = os.path.splitext(path)[1].lower()
    if ext in _AUDIO_EXTS:
        return "audio"
    if ext in _VIDEO_EXTS:
        return "video"
    return None


class DevicesBridge(QObject):
    stateChanged = Signal()

    def __init__(
        self,
        sync_manager: SyncManager | None = None,
        device_sync_service=None,
        job_service=None,
        parent=None,
    ):
        super().__init__(parent)
        self._sync_mgr = sync_manager
        self._dev_svc = device_sync_service
        self._job_svc = job_service
        self._server_active = False
        self._server_port = 53318
        self._peers: list[dict] = []
        self._paired_devices: list[dict] = []
        self._discovered: list[dict] = []
        self._transfer_jobs: list[dict] = []
        self._transfer_history: list[dict] = []
        self._storage_info: list[dict] = []
        self._compatibility_info: list[dict] = []

    @Property(bool, notify=stateChanged)
    def serverActive(self):
        return self._server_active

    @Property(int, notify=stateChanged)
    def serverPort(self):
        return self._server_port

    @Property("QVariantList", notify=stateChanged)
    def peers(self):
        return self._peers

    @Property("QVariantList", notify=stateChanged)
    def pairedDevices(self):
        return self._paired_devices

    @Property("QVariantList", notify=stateChanged)
    def discovered(self):
        return self._discovered

    @Property("QVariantList", notify=stateChanged)
    def transferJobs(self):
        return self._transfer_jobs

    @Property("QVariantList", notify=stateChanged)
    def transferHistory(self):
        return self._transfer_history

    @Property("QVariantList", notify=stateChanged)
    def storageInfo(self):
        return self._storage_info

    @Property("QVariantList", notify=stateChanged)
    def compatibilityInfo(self):
        return self._compatibility_info

    @Property(bool, notify=stateChanged)
    def transferActive(self):
        return any(
            j.get("state") in ("transferring", "queued", "cancel_requested")
            for j in self._transfer_jobs
        )

    @Slot(result=dict)
    def startServer(self):
        if not self._sync_mgr:
            return _typed_error("NO_SYNC_MANAGER")
        try:
            if hasattr(self._sync_mgr, 'start'):
                raw = self._sync_mgr.start()
                result = _normalise_result(raw)
            else:
                result = {"ok": True}
            if result.get("ok"):
                self._server_active = True
            else:
                self._server_active = False
            self.stateChanged.emit()
            return result
        except Exception as e:
            logger.debug("SyncManager start failed", exc_info=True)
            self._server_active = False
            self.stateChanged.emit()
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def stopServer(self):
        if not self._sync_mgr:
            return _typed_error("NO_SYNC_MANAGER",
                                "No se puede detener: no hay SyncManager disponible.")
        try:
            if hasattr(self._sync_mgr, 'stop'):
                raw = self._sync_mgr.stop()
                result = _normalise_result(raw)
            else:
                result = {"ok": True}
            self._server_active = False
            self.stateChanged.emit()
            return result
        except Exception as e:
            logger.debug("SyncManager stop failed", exc_info=True)
            self.stateChanged.emit()
            return {"ok": False, "error": str(e)}

    def _refresh_paired_from_dev_svc(self):
        if not self._dev_svc:
            return []
        try:
            return [
                {
                    "alias": p.get("label", p.get("key", "")),
                    "device": p.get("protocol", "desktop"),
                }
                for p in (self._dev_svc.get_paired() if hasattr(self._dev_svc, 'get_paired') else [])
            ]
        except Exception:
            return []

    @Slot(result=dict)
    def refresh(self):
        peers = []
        paired = []
        if self._sync_mgr:
            try:
                if hasattr(self._sync_mgr, 'get_all_peers'):
                    all_peers = self._sync_mgr.get_all_peers()
                    for p in all_peers:
                        peers.append({
                            "alias": p.get("alias", "") if isinstance(p, dict) else getattr(p, 'alias', '') or str(p),
                            "device": p.get("device", "desktop") if isinstance(p, dict) else getattr(p, 'device', 'desktop'),
                            "ip": p.get("ip", "") if isinstance(p, dict) else getattr(p, 'ip', ''),
                            "port": p.get("port", 0) if isinstance(p, dict) else getattr(p, 'port', 0),
                        })
            except Exception as e:
                logger.debug("Sync peers refresh failed: %s", e)
            try:
                active_val = getattr(self._sync_mgr, 'is_active', False)
                self._server_active = active_val() if callable(active_val) else bool(active_val)
            except Exception:
                pass
            try:
                if hasattr(self._sync_mgr, 'get_paired_devices'):
                    all_paired = self._sync_mgr.get_paired_devices()
                    for p in all_paired:
                        paired.append({
                            "alias": p.get("alias", "") if isinstance(p, dict) else getattr(p, 'alias', '') or str(p),
                            "device": p.get("device", "desktop") if isinstance(p, dict) else getattr(p, 'device', 'desktop'),
                        })
            except Exception as e:
                logger.debug("Sync paired devices refresh failed: %s", e)
        dev_svc_paired = self._refresh_paired_from_dev_svc()
        if dev_svc_paired:
            paired.extend(dev_svc_paired)
        self._peers = peers
        self._paired_devices = paired
        self.stateChanged.emit()
        return {"ok": True, "peers": len(peers), "paired": len(paired)}

    @Slot(str, result=dict)
    def loadDeviceDetail(self, device_key: str):
        if not self._sync_mgr:
            return _typed_error("NO_SYNC_MANAGER")
        if not device_key:
            return _typed_error("NO_DEVICE_KEY")
        try:
            detail = {}
            if hasattr(self._sync_mgr, 'get_device_detail'):
                raw = self._sync_mgr.get_device_detail(device_key)
                if isinstance(raw, dict):
                    detail = raw
            return {"ok": True, "detail": detail}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def discoverDevices(self):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            if hasattr(self._dev_svc, 'discover'):
                discovered = self._dev_svc.discover()
            else:
                discovered = self._dev_svc.get_discovered() if hasattr(self._dev_svc, 'get_discovered') else []
            self._discovered = [
                {
                    "alias": getattr(d, 'alias', '') or getattr(d, 'name', '') or str(d),
                    "device": getattr(d, 'device', 'desktop') or getattr(d, 'protocol', '') or '',
                    "ip": getattr(d, 'ip', ''),
                    "port": getattr(d, 'port', 0),
                }
                for d in (discovered or [])
            ]
            self.stateChanged.emit()
            return {"ok": True, "count": len(self._discovered)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def pairDevice(self, path_or_key: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            discovered = self._dev_svc.get_discovered()
            for identity in discovered:
                key = f"{identity.protocol.value}:{identity.serial}"
                mount = getattr(identity, 'mount_point', '') or ''
                if key == path_or_key or mount == path_or_key:
                    result = self._dev_svc.pair(identity)
                    self.refresh()
                    return result
            if ":" in path_or_key:
                for identity in discovered:
                    key = f"{identity.protocol.value}:{identity.serial}"
                    if key == path_or_key:
                        result = self._dev_svc.pair(identity)
                        self.refresh()
                        return result
            return _typed_error("DEVICE_NOT_FOUND")
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def unpairDevice(self, key: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            return self._dev_svc.unpair(key)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def trustDevice(self, key: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            return self._dev_svc.trust(key)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def untrustDevice(self, key: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            return self._dev_svc.untrust(key)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def authorizeDevice(self, key: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            return self._dev_svc.authorize(key)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def unauthorizeDevice(self, key: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            return self._dev_svc.unauthorize(key)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def deviceDetailStorage(self, path: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            if hasattr(self._dev_svc, 'get_storage'):
                info = self._dev_svc.get_storage(path)
            else:
                info = type('StorageInfo', (), {'total_bytes': 0, 'free_bytes': 0, 'used_bytes': 0})()
            self._storage_info = [{
                "mount_point": path,
                "total_bytes": info.total_bytes,
                "free_bytes": info.free_bytes,
                "used_bytes": info.used_bytes,
                "total_gb": round(info.total_bytes / (1024 ** 3), 2) if info.total_bytes else 0,
                "supported_formats": sorted(_AUDIO_EXTS),
            }]
            self.stateChanged.emit()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def deviceDetailCompatibility(self, path: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            identity = self._dev_svc.identify(path)
            caps = self._dev_svc.resolve_capabilities(identity) if identity else None
            self._compatibility_info = [{
                "protocol": identity.protocol.value if identity else "unknown",
                "supported_formats": sorted(_AUDIO_EXTS),
                "unsupported_formats": sorted(_VIDEO_EXTS),
                "supports_pairing": caps.supports_pairing if caps else False,
                "supports_playlists": caps.supports_playlists if caps else False,
            }]
            self.stateChanged.emit()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, str, result=dict)
    def startTransfer(self, source: str, destination: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            audio_type = _is_audio_extension(source)
            if audio_type == "video":
                return _typed_error("VIDEO_NOT_SUPPORTED",
                                    "No se admiten archivos de video. Solo audio.")
            if audio_type is None:
                return _typed_error("UNSUPPORTED_FORMAT",
                                    "Formato de archivo no reconocido")
            job = self._dev_svc.create_transfer_job(source, destination)
            result = self._dev_svc.execute_job(job.job_id)
            self._refresh_transfer_jobs()
            return result
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def cancelTransfer(self, job_id: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            result = self._dev_svc.cancel_job(job_id)
            self._refresh_transfer_jobs()
            return result
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def retryTransfer(self, job_id: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            job = self._dev_svc.get_job(job_id)
            if not job:
                return _typed_error("JOB_NOT_FOUND")
            src = getattr(job, 'source_path', '')
            dst = getattr(job, 'dest_path', '') or getattr(job, 'destination_path', '')
            if src and dst:
                new_job = self._dev_svc.create_transfer_job(src, dst)
                result = self._dev_svc.execute_job(new_job.job_id)
                self._refresh_transfer_jobs()
                return result if isinstance(result, dict) else {"ok": True}
            return _typed_error("JOB_NO_SOURCE")
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def clearTransferHistory(self):
        if self._dev_svc and hasattr(self._dev_svc, 'clear_history'):
            self._dev_svc.clear_history()
        self._transfer_history = []
        self.stateChanged.emit()
        return {"ok": True}

    @Slot(str, result=dict)
    def validateAudioFile(self, path: str):
        try:
            audio_type = _is_audio_extension(path)
            if audio_type == "video":
                return _typed_error("VIDEO_NOT_SUPPORTED",
                                    "No se admiten archivos de video.")
            if audio_type is None:
                return _typed_error("UNSUPPORTED_FORMAT",
                                    "Formato no soportado. Solo audio.")
            if not os.path.exists(path):
                return {"ok": True, "warning": "FILE_NOT_FOUND",
                        "type": "audio", "transcode_policy": "copy"}
            return {
                "ok": True,
                "type": "audio",
                "transcode_policy": "copy",
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def ejectDevice(self, mount_point: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        if not mount_point:
            return _typed_error("NO_MOUNT_POINT")
        try:
            if hasattr(self._dev_svc, 'eject'):
                return _normalise_result(self._dev_svc.eject(mount_point))
            return _typed_error("EJECT_NOT_SUPPORTED",
                                "La expulsión no está soportada por este servicio.")
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _refresh_transfer_jobs(self):
        if not self._dev_svc:
            return
        try:
            jobs = self._dev_svc.list_jobs()
            self._transfer_jobs = []
            for j in jobs:
                src = getattr(j, 'source_path', '') or ''
                dst = getattr(j, 'dest_path', '') or getattr(j, 'destination_path', '') or ''
                status_val = getattr(j, 'status', '')
                status_str = status_val.value if hasattr(status_val, 'value') else str(status_val)
                direction_val = getattr(j, 'direction', '')
                direction_str = direction_val.value if hasattr(direction_val, 'value') else str(direction_val)
                self._transfer_jobs.append({
                    "job_id": getattr(j, 'job_id', '') or '',
                    "file_name": os.path.basename(src) or 'Unknown',
                    "source_path": src,
                    "destination_path": dst,
                    "total_bytes": getattr(j, 'total_bytes', 0) or 0,
                    "transferred_bytes": getattr(j, 'transferred_bytes', 0) or 0,
                    "status": status_str,
                    "state": status_str,
                    "direction": direction_str,
                })
            history = self._dev_svc.get_history() if hasattr(self._dev_svc, 'get_history') else []
            self._transfer_history = list(history)
            self.stateChanged.emit()
        except Exception:
            pass
