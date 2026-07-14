"""DevicesBridge — connects QML Sync/Devices page to real SyncManager.

Returns dict ok/error from all actions. Does not mark serverActive=true
if start() fails. Normalises result types: True, False, {"ok": true},
{"ok": false, ...}, exception.
"""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Property, Slot
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sync.sync_manager import SyncManager

logger = logging.getLogger("michi.devices")

_STARTED_ERROR = "NO_SYNC_MANAGER"

AUDIO_EXTENSIONS = frozenset({
    ".mp3", ".flac", ".wav", ".wv", ".ogg", ".opus", ".m4a", ".aac",
    ".wma", ".dsf", ".dff", ".ape", ".aiff", ".aif", ".mpc",
})
VIDEO_EXTENSIONS = frozenset({
    ".mp4", ".avi", ".mkv", ".mov", ".webm", ".m4v", ".wmv", ".flv",
})


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


class DevicesBridge(QObject):
    stateChanged = Signal()

    def __init__(self, sync_manager: SyncManager | None = None, parent=None,
                 device_sync_service=None, job_service=None):
        super().__init__(parent)
        self._sync_mgr = sync_manager
        self._device_sync_svc = device_sync_service
        self._job_svc = job_service
        self._server_active = False
        self._server_port = 53318
        self._peers: list[dict] = []
        self._paired_devices: list[dict] = []
        self._discovered: list[dict] = []
        self._storage_info: list[dict] = []
        self._compatibility_info: list[dict] = []
        self._transfer_jobs: list[dict] = []
        self._transfer_history: list[dict] = []

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
        if self._device_sync_svc:
            try:
                svc_paired = self._device_sync_svc.get_paired()
                for p in svc_paired:
                    if not any(d.get("alias", "") == p.get("label", "") for d in paired):
                        paired.append({
                            "alias": p.get("label", ""),
                            "device": p.get("protocol", "dedicated"),
                            "vendor": p.get("vendor", ""),
                            "model": p.get("model", ""),
                        })
            except Exception as e:
                logger.debug("Device sync paired refresh failed: %s", e)
        self._peers = peers
        self._paired_devices = paired
        self.stateChanged.emit()
        return {"ok": True, "peers": len(peers), "paired": len(paired)}

    @Property("QVariantList", notify=stateChanged)
    def discovered(self):
        return list(self._discovered)

    @Property("QVariantList", notify=stateChanged)
    def storageInfo(self):
        return list(self._storage_info)

    @Property("QVariantList", notify=stateChanged)
    def compatibilityInfo(self):
        return list(self._compatibility_info)

    @Property("QVariantList", notify=stateChanged)
    def transferJobs(self):
        return list(self._transfer_jobs)

    @Property("QVariantList", notify=stateChanged)
    def transferHistory(self):
        return list(self._transfer_history)

    @Slot(result=dict)
    def discoverDevices(self):
        if not self._device_sync_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE", "Servicio de dispositivos no disponible")
        try:
            discovered = self._device_sync_svc.discover()
            self._discovered = [
                {"mount_point": d.mount_point, "vendor": d.vendor, "model": d.model,
                 "label": d.label or Path(d.mount_point).name, "protocol": d.protocol.value}
                for d in discovered
            ]
            self.stateChanged.emit()
            return {"ok": True, "count": len(self._discovered)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def pairDevice(self, mount_point: str):
        if not self._device_sync_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE", "Servicio de dispositivos no disponible")
        identity = self._device_sync_svc.identify(mount_point)
        if not identity:
            return {"ok": False, "error": "NOT_FOUND", "message": "Dispositivo no encontrado"}
        result = self._device_sync_svc.pair(identity)
        self.refresh()
        return result

    @Slot(str, result=dict)
    def unpairDevice(self, key: str):
        if not self._device_sync_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        result = self._device_sync_svc.unpair(key)
        self.refresh()
        return result

    @Slot(str, result=dict)
    def trustDevice(self, key: str):
        if not self._device_sync_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        return self._device_sync_svc.trust(key)

    @Slot(str, result=dict)
    def deviceDetailStorage(self, mount_point: str):
        if not self._device_sync_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            info = self._device_sync_svc.get_storage(mount_point)
            self._storage_info = [{
                "mount_point": mount_point,
                "total_bytes": info.total_bytes,
                "free_bytes": info.free_bytes,
                "used_bytes": info.used_bytes,
                "label": info.label,
                "total_gb": info.total_bytes / 1073741824 if info.total_bytes else 0,
            }]
            self.stateChanged.emit()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def deviceDetailCompatibility(self, mount_point: str):
        if not self._device_sync_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        identity = self._device_sync_svc.identify(mount_point)
        if not identity:
            return {"ok": False, "error": "NOT_FOUND"}
        caps = self._device_sync_svc.resolve_capabilities(identity)
        self._compatibility_info = [{
            "mount_point": mount_point,
            "supports_pairing": caps.supports_pairing,
            "supports_playlists": caps.supports_playlists,
            "supports_authorization": caps.supports_authorization,
            "supported_formats": sorted(caps.supported_formats),
            "music_directory": caps.music_directory,
        }]
        self.stateChanged.emit()
        return {"ok": True}

    @Slot(str, str, result=dict)
    def startTransfer(self, src: str, dst: str):
        if not self._device_sync_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        ext = Path(src).suffix.lower()
        if ext in VIDEO_EXTENSIONS:
            return {"ok": False, "error": "VIDEO_NOT_SUPPORTED"}
        if ext not in AUDIO_EXTENSIONS:
            return {"ok": False, "error": "UNSUPPORTED_FORMAT"}
        if not os.path.isfile(src):
            return {"ok": False, "error": "FILE_NOT_FOUND"}
        try:
            job = self._device_sync_svc.create_transfer_job(src, dst)
            result = self._device_sync_svc.execute_job(job.job_id)
            self._refresh_transfer_jobs()
            return result
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def cancelTransfer(self, job_id: str):
        if not self._device_sync_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        result = self._device_sync_svc.cancel_job(job_id)
        self._refresh_transfer_jobs()
        return result

    @Slot(str, result=dict)
    def retryTransfer(self, job_id: str):
        if not self._device_sync_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        result = self._device_sync_svc.retry_job(job_id)
        self._refresh_transfer_jobs()
        return result

    @Slot(str, result=dict)
    def validateAudioFile(self, path: str):
        ext = Path(path).suffix.lower()
        if ext in VIDEO_EXTENSIONS:
            return {"ok": False, "error": "VIDEO_NOT_SUPPORTED",
                    "message": "Solo se admiten archivos de audio"}
        if ext not in AUDIO_EXTENSIONS:
            return {"ok": False, "error": "UNSUPPORTED_FORMAT",
                    "message": f"Formato '{ext}' no soportado"}
        if not os.path.isfile(path):
            return {"ok": False, "error": "FILE_NOT_FOUND"}
        transcode_policy = "copy" if ext == ".flac" else "transcode_if_needed"
        return {"ok": True, "format": ext.lstrip('.'), "transcode_policy": transcode_policy}

    @Slot(result=dict)
    def clearTransferHistory(self):
        if self._device_sync_svc:
            self._device_sync_svc.clear_history()
        self._transfer_history = []
        self.stateChanged.emit()
        return {"ok": True}

    def _refresh_transfer_jobs(self):
        if self._device_sync_svc:
            self._transfer_jobs = [
                {"job_id": j.job_id, "source_path": j.source_path, "dest_path": j.dest_path,
                 "status": j.status.value, "total_bytes": j.total_bytes,
                 "transferred_bytes": j.transferred_bytes, "error": j.error}
                for j in self._device_sync_svc.list_jobs()
            ]
            self._transfer_history = self._device_sync_svc.get_history()
        self.stateChanged.emit()
