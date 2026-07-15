from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal, Property, Slot

logger = logging.getLogger("michi.devices")

STATE_INITIALIZING = "INITIALIZING"
STATE_DISCOVERING = "DISCOVERING"
STATE_EMPTY = "EMPTY"
STATE_READY = "READY"
STATE_PAIRING = "PAIRING"
STATE_PLANNING = "PLANNING"
STATE_TRANSFERRING = "TRANSFERRING"
STATE_CANCELLING = "CANCELLING"
STATE_CANCELLED = "CANCELLED"
STATE_PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
STATE_FAILED = "FAILED"
STATE_DEFERRED_PHYSICAL = "DEFERRED_PHYSICAL"
STATE_METHOD_UNAVAILABLE = "METHOD_UNAVAILABLE"

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
        return {"ok": False, "error": "METHOD_UNAVAILABLE"}
    if isinstance(raw, str):
        return {"ok": False, "error": raw}
    return {"ok": False, "error": f"Unexpected result: {type(raw).__name__}"}


def _typed_error(code: str, message: str = "") -> dict:
    return {"ok": False, "error": code, "message": message or code}


def _method_unavailable(name: str = "") -> dict:
    return {"ok": False, "error": "METHOD_UNAVAILABLE", "message": name or "Method not available"}


def _require_confirm(action: str) -> dict:
    return {"ok": False, "error": "CONFIRMATION_REQUIRED", "action": action}


def _is_audio_extension(path: str) -> str | None:
    ext = os.path.splitext(path)[1].lower()
    if ext in _AUDIO_EXTS:
        return "audio"
    if ext in _VIDEO_EXTS:
        return "video"
    return None


class DevicesBridge(QObject):
    stateChanged = Signal()
    state = STATE_INITIALIZING
    errorMessage = ""

    def __init__(
        self,
        device_sync_service=None,
        job_service=None,
        action_registry=None,
        confirmation_service=None,
        navigation_bridge=None,
        capability_bridge=None,
        page_state_store=None,
        accessibility_bridge=None,
        parent=None,
        **kwargs,
    ):
        super().__init__(parent)
        self._dev_svc = device_sync_service or kwargs.get("device_sync_service") or kwargs.get("sync_manager")
        self._sync_mgr = self._dev_svc
        self._job_svc = job_service or kwargs.get("job_service")
        self._registry = action_registry or kwargs.get("action_registry")
        self._confirm_svc = confirmation_service or kwargs.get("confirmation_service")
        self._nav = navigation_bridge or kwargs.get("navigation_bridge")
        self._cap = capability_bridge or kwargs.get("capability_bridge")
        self._page_state = page_state_store or kwargs.get("page_state_store")
        self._access = accessibility_bridge or kwargs.get("accessibility_bridge")

        self._server_active = False
        self._server_port = 53318
        self._peers: list[dict] = []
        self._paired_devices: list[dict] = []
        self._discovered: list[dict] = []
        self._transfer_jobs: list[dict] = []
        self._transfer_history: list[dict] = []
        self._storage_info: list[dict] = []
        self._compatibility_info: list[dict] = []
        self._qr_code_data = ""
        self._bridge_available = True
        self._set_state()

    def _set_state(self):
        if self._error:
            self.state = STATE_FAILED
        elif self._server_active and (self._paired_devices or self._peers):
            self.state = STATE_READY
        elif self._server_active:
            self.state = STATE_EMPTY
        elif self._dev_svc:
            self.state = STATE_DISCOVERING
        else:
            self.state = STATE_INITIALIZING

    @property
    def _error(self):
        return bool(self.errorMessage)

    @Property(str, notify=stateChanged)
    def pageState(self):
        return self.state

    @Property(str, notify=stateChanged)
    def qrCodeData(self):
        return self._qr_code_data

    @Property(bool, notify=stateChanged)
    def bridgeAvailable(self):
        return self._bridge_available

    @Property(str, notify=stateChanged)
    def bridgeErrorMessage(self):
        return self.errorMessage

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
        return list(self._discovered)

    @Property("QVariantList", notify=stateChanged)
    def transferJobs(self):
        return list(self._transfer_jobs)

    @Property("QVariantList", notify=stateChanged)
    def transferHistory(self):
        return list(self._transfer_history)

    @Property("QVariantList", notify=stateChanged)
    def storageInfo(self):
        return list(self._storage_info)

    @Property("QVariantList", notify=stateChanged)
    def compatibilityInfo(self):
        return list(self._compatibility_info)

    @Property(bool, notify=stateChanged)
    def transferActive(self):
        return any(
            j.get("state") in ("transferring", "queued", "cancel_requested")
            for j in self._transfer_jobs
        )

    @Slot(str, result=str)
    def fileName(self, path: str) -> str:
        if not path:
            return ""
        return Path(path).name

    @Slot(result=dict)
    def discover(self):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            self.state = STATE_DISCOVERING
            self.stateChanged.emit()
            if hasattr(self._dev_svc, 'discover'):
                discovered = self._dev_svc.discover()
            else:
                discovered = getattr(self._dev_svc, 'get_discovered', lambda: [])()
            self._discovered = [
                {
                    "alias": getattr(d, 'alias', '') or getattr(d, 'name', '') or str(d),
                    "device": getattr(d, 'device', 'desktop') or getattr(d, 'protocol', '') or '',
                    "ip": getattr(d, 'ip', ''),
                    "port": getattr(d, 'port', 0),
                    "protocol": getattr(d, 'protocol', ''),
                    "serial": getattr(d, 'serial', ''),
                }
                for d in (discovered or [])
            ]
            self._set_state()
            self.stateChanged.emit()
            return {"ok": True, "count": len(self._discovered)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def startServer(self):
        if not self._dev_svc:
            return _typed_error("NO_SYNC_MANAGER")
        try:
            fn = getattr(self._dev_svc, 'start', None)
            if fn:
                raw = fn()
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
            logger.debug("startServer failed", exc_info=True)
            self._server_active = False
            self.stateChanged.emit()
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def stopServer(self):
        if not self._dev_svc:
            return _typed_error("NO_SYNC_MANAGER", "No se puede detener: no hay servicio disponible.")
        try:
            fn = getattr(self._dev_svc, 'stop', None)
            if fn:
                raw = fn()
                result = _normalise_result(raw)
            else:
                result = {"ok": True}
            self._server_active = not result.get("ok", True)
            self.stateChanged.emit()
            return result
        except Exception as e:
            logger.debug("stopServer failed", exc_info=True)
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def refresh(self):
        peers = []
        paired = []
        svc = self._dev_svc
        if svc:
            try:
                if hasattr(svc, 'get_all_peers'):
                    peers = svc.get_all_peers()
                else:
                    peers = getattr(svc, 'peers', [])
                if hasattr(svc, 'get_paired_devices'):
                    paired = svc.get_paired_devices()
                else:
                    paired = getattr(svc, 'get_paired', lambda: [])()
                self._server_active = getattr(svc, 'running', False) or getattr(svc, 'is_active', False) or self._server_active
            except Exception as e:
                logger.debug("refresh failed: %s", e)
        self._peers = peers
        self._paired_devices = paired
        self._set_state()
        self.stateChanged.emit()
        return {"ok": True, "peers": len(peers), "paired": len(paired)}

    @Slot(str, int, result=dict)
    def connectToPeer(self, ip: str, port: int):
        if not self._dev_svc:
            return _typed_error("NO_SYNC_MANAGER")
        try:
            fn = getattr(self._dev_svc, 'connect', None)
            if fn:
                raw = fn(ip, port)
                return _normalise_result(raw)
            return _typed_error("CONNECT_NOT_SUPPORTED", "La conexion directa a pares no esta soportada.")
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def identify(self, path_or_key: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            if hasattr(self._dev_svc, 'identify'):
                identity = self._dev_svc.identify(path_or_key)
                return {"ok": True, "identity": str(identity)}
            return _typed_error("IDENTIFY_NOT_SUPPORTED")
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def pairDevice(self, path_or_key: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            self.state = STATE_PAIRING
            self.stateChanged.emit()
            discovered = getattr(self._dev_svc, 'get_discovered', lambda: [])()
            for identity in discovered:
                key = f"{getattr(identity, 'protocol', 'unknown')}:{getattr(identity, 'serial', '')}"
                if key == path_or_key or getattr(identity, 'mount_point', '') == path_or_key:
                    result = self._dev_svc.pair(identity)
                    self.refresh()
                    return result
            if ":" in path_or_key:
                for identity in discovered:
                    key = f"{getattr(identity, 'protocol', 'unknown')}:{getattr(identity, 'serial', '')}"
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
    def authorizeDevice(self, key: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            return self._dev_svc.authorize(key)
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
    def profile(self, key: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            if hasattr(self._dev_svc, 'get_profile'):
                prof = self._dev_svc.get_profile(key)
                return {"ok": True, "profile": prof}
            return {"ok": True, "profile": {}}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def deviceDetailStorage(self, path: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            info = getattr(self._dev_svc, 'get_storage', lambda p: type('S', (), {'total_bytes': 0, 'free_bytes': 0, 'used_bytes': 0})())(path)
            self._storage_info = [{
                "mount_point": path,
                "total_bytes": info.total_bytes,
                "free_bytes": info.free_bytes,
                "used_bytes": info.used_bytes,
                "total_gb": round(info.total_bytes / (1024 ** 3), 2) if info.total_bytes else 0,
                "supported_formats": sorted(_AUDIO_EXTS),
            }]
            self.stateChanged.emit()
            return {"ok": True, "storage": self._storage_info}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def freeSpace(self, path: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            info = getattr(self._dev_svc, 'get_storage', lambda p: type('S', (), {'total_bytes': 0, 'free_bytes': 0, 'used_bytes': 0})())(path)
            return {"ok": True, "free_bytes": info.free_bytes, "total_bytes": info.total_bytes}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def supportedFormats(self, path: str):
        return {"ok": True, "formats": sorted(_AUDIO_EXTS)}

    @Slot(str, result=dict)
    def discoverDevices(self):
        return self.discover()

    @Slot(str, result=dict)
    def untrustDevice(self, key: str):
        return self.unpairDevice(key)

    @Slot(str, result=dict)
    def unauthorizeDevice(self, key: str):
        return self.unpairDevice(key)

    @Slot(str, result=dict)
    def deviceDetailCompatibility(self, path: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            identity = self._dev_svc.identify(path) if hasattr(self._dev_svc, 'identify') else None
            caps = self._dev_svc.resolve_capabilities(identity) if identity and hasattr(self._dev_svc, 'resolve_capabilities') else None
            self._compatibility_info = [{
                "protocol": getattr(identity, 'protocol', 'unknown').value if identity and hasattr(getattr(identity, 'protocol', ''), 'value') else (getattr(identity, 'protocol', 'unknown') if identity else "unknown"),
                "supported_formats": sorted(_AUDIO_EXTS),
                "unsupported_formats": sorted(_VIDEO_EXTS),
                "supports_pairing": getattr(caps, 'supports_pairing', False) if caps else False,
                "supports_playlists": getattr(caps, 'supports_playlists', False) if caps else False,
            }]
            self.stateChanged.emit()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def selection(self, selection_id: str):
        return {"ok": True, "selection_id": selection_id}

    @Slot(str, result=dict)
    def transcodePolicy(self, device_key: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            policy = getattr(self._dev_svc, 'get_transcode_policy', lambda k: "copy")(device_key)
            return {"ok": True, "policy": policy}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, str, result=dict)
    def naming(self, device_key: str, pattern: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            fn = getattr(self._dev_svc, 'set_naming_pattern', None)
            if fn:
                fn(device_key, pattern)
            return {"ok": True, "pattern": pattern}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, str, result=dict)
    def collision(self, device_key: str, strategy: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            fn = getattr(self._dev_svc, 'set_collision_strategy', None)
            if fn:
                fn(device_key, strategy)
            return {"ok": True, "strategy": strategy}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, str, result=dict)
    def syncPlan(self, device_key: str, playlist_or_path: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            self.state = STATE_PLANNING
            self.stateChanged.emit()
            fn = getattr(self._dev_svc, 'plan_sync', None)
            if fn:
                plan = fn(device_key, playlist_or_path)
                return {"ok": True, "plan": plan}
            return _typed_error("PLAN_NOT_SUPPORTED")
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, str, result=dict)
    def estimate(self, device_key: str, playlist_or_path: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            fn = getattr(self._dev_svc, 'estimate_sync', None)
            if fn:
                est = fn(device_key, playlist_or_path)
                return {"ok": True, "estimate": est}
            return {"ok": True, "estimate": {}}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, str, result=dict)
    def startTransfer(self, source: str, destination: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            audio_type = _is_audio_extension(source)
            if audio_type == "video":
                return _typed_error("VIDEO_NOT_SUPPORTED", "No se admiten archivos de video. Solo audio.")
            if audio_type is None:
                return _typed_error("UNSUPPORTED_FORMAT", "Formato de archivo no reconocido")
            self.state = STATE_TRANSFERRING
            self.stateChanged.emit()
            job = self._dev_svc.create_transfer_job(source, destination)
            result = self._dev_svc.execute_job(job.job_id) if hasattr(job, 'job_id') else self._dev_svc.execute_job(job)
            self._refresh_transfer_jobs()
            return result
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def startSync(self):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            fn = getattr(self._dev_svc, 'start_sync', None)
            if fn:
                result = fn()
                return _normalise_result(result)
            return _typed_error("SYNC_NOT_SUPPORTED")
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def transferProgress(self, job_id: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            job = getattr(self._dev_svc, 'get_job', lambda j: None)(job_id)
            if job:
                return {
                    "ok": True,
                    "job_id": getattr(job, 'job_id', job_id),
                    "transferred_bytes": getattr(job, 'transferred_bytes', 0),
                    "total_bytes": getattr(job, 'total_bytes', 0),
                    "status": getattr(job, 'status', ''),
                }
            return _typed_error("JOB_NOT_FOUND")
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def cancelTransfer(self, job_id: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        self.state = STATE_CANCELLING
        self.stateChanged.emit()
        result = self._dev_svc.cancel_job(job_id)
        self._refresh_transfer_jobs()
        return result

    @Slot(str, result=dict)
    def retryTransfer(self, job_id: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            job = self._dev_svc.get_job(job_id) if hasattr(self._dev_svc, 'get_job') else None
            if not job:
                return _typed_error("JOB_NOT_FOUND")
            src = getattr(job, 'source_path', '')
            dst = getattr(job, 'dest_path', '') or getattr(job, 'destination_path', '')
            if src and dst:
                new_job = self._dev_svc.create_transfer_job(src, dst)
                result = self._dev_svc.execute_job(getattr(new_job, 'job_id', new_job))
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
                return _typed_error("VIDEO_NOT_SUPPORTED", "No se admiten archivos de video.")
            if audio_type is None:
                return _typed_error("UNSUPPORTED_FORMAT", "Formato no soportado. Solo audio.")
            if not os.path.exists(path):
                return {"ok": True, "warning": "FILE_NOT_FOUND", "type": "audio", "transcode_policy": "copy"}
            return {"ok": True, "type": "audio", "transcode_policy": "copy"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def ejectDevice(self, mount_point: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        if not mount_point:
            return _typed_error("NO_MOUNT_POINT")
        try:
            fn = getattr(self._dev_svc, 'eject', None)
            if fn:
                return _normalise_result(fn(mount_point))
            return _typed_error("EJECT_NOT_SUPPORTED", "La expulsion no esta soportada por este servicio.")
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def history(self, device_key: str = ""):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            fn = getattr(self._dev_svc, 'get_history', lambda: [])
            hist = fn()
            self._transfer_history = list(hist)
            self.stateChanged.emit()
            return {"ok": True, "history": list(hist)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, str, result=dict)
    def listMusic(self, mount_point: str, music_dir: str = "Music"):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        try:
            fn = getattr(self._dev_svc, 'list_music', None)
            if fn:
                files = fn(mount_point, music_dir=music_dir)
                return {"ok": True, "files": files}
            return _typed_error("LIST_NOT_SUPPORTED")
        except Exception as e:
            return _typed_error(str(e))

    @Slot(str, result=dict)
    def loadDeviceDetail(self, device_key: str):
        if not self._dev_svc:
            return _typed_error("NO_DEVICE_SYNC_SERVICE")
        if not device_key:
            return _typed_error("NO_DEVICE_KEY")
        try:
            detail = {}
            fn = getattr(self._dev_svc, 'get_device_detail', None)
            if fn:
                raw = fn(device_key)
                if isinstance(raw, dict):
                    detail = raw
            return {"ok": True, "detail": detail}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(result=str)
    def getDeviceIcon(self, deviceType: str):
        icons = {
            "android": "smartphone",
            "iphone": "smartphone",
            "desktop": "desktop",
            "laptop": "laptop",
            "tablet": "tablet",
            "dedicated": "music_note",
            "hiby": "music_note",
            "fiio": "music_note",
            "sandisk": "sd_card",
            "ruizu": "music_note",
            "ums": "usb",
            "mtp": "smartphone",
            "michi": "devices",
            "generic": "folder",
        }
        return icons.get(deviceType.lower(), "devices")

    @Slot(result=str)
    def generateQRCode(self):
        from uuid import uuid4
        self._qr_code_data = f"michi://pair/{uuid4().hex[:12]}"
        self.stateChanged.emit()
        return self._qr_code_data

    @Slot(str, result=dict)
    def confirmDestructive(self, action: str):
        if action == "unpair":
            return {"ok": True, "confirmed": True, "action": "unpair"}
        if action == "clear_history":
            return {"ok": True, "confirmed": True, "action": "clear_history"}
        if action == "overwrite":
            return {"ok": True, "confirmed": True, "action": "overwrite"}
        if action == "replace":
            return {"ok": True, "confirmed": True, "action": "replace"}
        return _typed_error("UNKNOWN_ACTION", f"Accion destructiva desconocida: {action}")

    @Slot(str, result=dict)
    def retry(self, job_id: str):
        return self.retryTransfer(job_id)

    def _refresh_transfer_jobs(self):
        if not self._dev_svc:
            return
        try:
            fn = getattr(self._dev_svc, 'list_jobs', lambda: [])
            jobs = fn()
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
            hist_fn = getattr(self._dev_svc, 'get_history', lambda: [])
            self._transfer_history = list(hist_fn())
            self.stateChanged.emit()
        except Exception:
            pass
