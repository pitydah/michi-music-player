"""DeviceSyncService — application facade for audio-only device sync.

Fase Sync (P0 stabilization, falso éxito #8): the facade owns NO parallel
system. Everything canonical is injected:

    DeviceRegistry → DeviceDiscoveryAdapters → DeviceProfileResolver →
    DeviceSyncPlanner → TranscodePlanner → DurableJobService →
    TransferAdapter → VerificationService → SyncHistoryRepository

No own threads (no ``threading.Lock``), no parallel ``_jobs`` dict, no
internal job counter, no in-memory history, no own trust store, no direct
subprocess (external tools go through ProcessController) and no
brand-name protocol detection (brands only contribute profiles).

Transfers are DURABLE jobs: ``sync_to_device`` creates a
``device_sync`` job (owner ``device:<id>``) and ``create_transfer_job``
creates a ``device_transfer`` job; progress and cancellation flow through
the job context. History is persisted by SyncHistoryRepository in the
app database (migration 10).

The QML-facing surface (discover / pair / get_job / cancel_job /
list_jobs / get_history / ...) is preserved so DevicesBridge keeps its
stable slots and shapes.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any, Callable

from core.device_sync.discovery import DiscoveryComposite
from core.device_sync.history import SyncHistoryRepository
from core.device_sync.identity import resolve_identity
from core.device_sync.models import (
    AUDIO_EXTENSIONS,
    AUDIO_PLAYLIST_EXTENSIONS,
    DeviceCapabilities,
    DeviceIdentity,
    DeviceInfo,
    DeviceProtocol,
    PairedDevice,
    StorageInfo,
    SyncDirection,
    SyncErrorCode,
    SyncHistoryEntry,
    SyncPlanItem,
    TransferJob,
    TransferStatus,
    format_size,
    is_audio_file,
    is_playlist_file,
    safe_filename,
)
from core.device_sync.planning import DeviceSyncPlanner
from core.device_sync.profile_resolver import DeviceProfileResolver
from core.device_sync.transcode_planning import TranscodePlanner
from core.device_sync.transfer import TransferAdapter
from core.device_sync.verification import VerificationService
from core.jobs.job_service import JobState

logger = logging.getLogger("michi.device_sync")

TRANSFER_CHUNK_SIZE = 65536

# Legacy re-exports: existing tests import these from core.device_sync_service.
__all__ = [
    "AUDIO_EXTENSIONS",
    "AUDIO_PLAYLIST_EXTENSIONS",
    "TRANSFER_CHUNK_SIZE",
    "DeviceProtocol",
    "SyncDirection",
    "TransferStatus",
    "DeviceIdentity",
    "DeviceCapabilities",
    "StorageInfo",
    "TransferJob",
    "SyncHistoryEntry",
    "PairedDevice",
    "DeviceSyncService",
    "SyncErrorCode",
]


def _format_size(bytes_val: int) -> str:
    return format_size(bytes_val)


def _safe_filename(name: str, max_len: int = 255) -> str:
    return safe_filename(name, max_len)


def _is_audio_file(path: str) -> bool:
    return is_audio_file(path)


def _is_playlist_file(path: str) -> bool:
    return is_playlist_file(path)


def _parse_direction(value: str) -> SyncDirection:
    try:
        return SyncDirection(value)
    except ValueError:
        return SyncDirection.TO_DEVICE


_STATE_TO_TRANSFER = {
    JobState.QUEUED: TransferStatus.QUEUED,
    JobState.RUNNING: TransferStatus.TRANSFERRING,
    JobState.PAUSING: TransferStatus.QUEUED,
    JobState.PAUSED: TransferStatus.QUEUED,
    JobState.CANCELLING: TransferStatus.TRANSFERRING,
    JobState.CANCELLED: TransferStatus.CANCELLED,
    JobState.SUCCEEDED: TransferStatus.COMPLETED,
    JobState.PARTIAL_SUCCESS: TransferStatus.COMPLETED,
    JobState.FAILED: TransferStatus.FAILED,
    JobState.INTERRUPTED: TransferStatus.FAILED,
}


class DeviceSyncService:
    def __init__(
        self,
        *,
        device_registry=None,
        discovery_adapters=None,
        profile_resolver: DeviceProfileResolver | None = None,
        sync_planner: DeviceSyncPlanner | None = None,
        transcode_planner: TranscodePlanner | None = None,
        job_service=None,
        transfer_adapter: TransferAdapter | None = None,
        verification_service: VerificationService | None = None,
        history_repository: SyncHistoryRepository | None = None,
        event_bus=None,
        process_controller=None,
    ):
        self._registry = device_registry
        self._adapters = discovery_adapters or []
        self._resolver = profile_resolver
        self._planner = sync_planner
        self._transcode_planner = transcode_planner
        self._job_service = job_service
        self._transfer = transfer_adapter
        self._verifier = verification_service
        self._history_repository = history_repository
        self._event_bus = event_bus
        self._process_controller = process_controller

        self._discovered: dict[str, DeviceIdentity] = {}
        self._on_progress: Callable[[TransferJob], None] | None = None

    @property
    def device_registry(self):
        """Public read port: the injected DeviceRegistry (single instance)."""
        return self._registry

    # ── Internal helpers ──

    def _composite(self) -> DiscoveryComposite:
        if isinstance(self._adapters, DiscoveryComposite):
            return self._adapters
        return DiscoveryComposite(self._adapters)

    def _emit(self, event: str, data: Any = None):
        if self._event_bus is not None:
            try:
                self._event_bus.publish(event, data)
            except Exception:  # noqa: BLE001
                logger.debug("Event publish %s failed", event, exc_info=True)

    def _registry_key(self, identity: DeviceIdentity) -> str:
        return (
            f"{identity.protocol.value}:"
            f"{identity.serial or identity.mount_point}"
        )

    def _resolve_device_info(self, device_id: str) -> DeviceInfo | None:
        """Resolve a device by stable serial / mount point / registry key.

        Resolution order: discovery cache → paired registry → live
        discovery adapters → mount probe. Never fabricates a device.
        """
        if not device_id:
            return None
        for identity in self._discovered.values():
            if (
                identity.serial == device_id
                or identity.mount_point == device_id
                or self._registry_key(identity) == device_id
            ):
                return self._info_from_identity(identity)
        paired = self._paired_identities()
        for identity in paired:
            if (
                identity.serial == device_id
                or identity.mount_point == device_id
                or self._registry_key(identity) == device_id
            ):
                return self._info_from_identity(identity)
        for info in self._composite().discover():
            info = resolve_identity(info, self._registry)
            if (
                info.serial == device_id
                or info.mount_point == device_id
                or self._registry_key(self._identity_from_info(info)) == device_id
            ):
                return info
        info = self._composite().probe(device_id)
        if info is not None:
            return resolve_identity(info, self._registry)
        return None

    def _info_from_identity(self, identity: DeviceIdentity) -> DeviceInfo:
        return DeviceInfo(
            protocol=identity.protocol,
            label=identity.label,
            mount_point=identity.mount_point,
            vendor=identity.vendor,
            model=identity.model,
            serial=identity.serial,
            identity_source=identity.identity_source,
            identity_unstable=identity.identity_unstable,
            music_directory="Music",
            capabilities=[],
        )

    def _caps_for_device(self, device: DeviceInfo) -> DeviceCapabilities:
        """Profile caps narrowed by adapter-declared formats (real MTP)."""
        caps = self.resolve_capabilities(self._identity_from_info(device))
        if device.declared_formats:
            caps.supported_formats = set(device.declared_formats)
        return caps

    def _music_root(self, device: DeviceInfo) -> str:
        if device.mount_point and device.mount_point != device.music_directory:
            return os.path.join(device.mount_point, device.music_directory)
        return device.music_directory or "Music"

    def _job_view(self, job: Any) -> TransferJob:
        if job is None:
            return TransferJob()
        payload = getattr(job, "payload", {}) or {}
        direction = _parse_direction(payload.get("direction", "to_device"))
        state = getattr(job, "state", JobState.QUEUED)
        errors = getattr(job, "errors", None) or []
        error = errors[-1] if errors else ""
        started_at = _parse_ts(getattr(job, "startedAt", ""))
        finished_at = _parse_ts(getattr(job, "finishedAt", ""))
        return TransferJob(
            job_id=getattr(job, "id", ""),
            source_path=str(payload.get("source_path", "") or ""),
            dest_path=str(payload.get("dest_path", "") or ""),
            direction=direction,
            status=_STATE_TO_TRANSFER.get(state, TransferStatus.QUEUED),
            total_bytes=int(getattr(job, "total", 0) or 0),
            transferred_bytes=int(getattr(job, "current", 0) or 0),
            error=error,
            started_at=started_at,
            finished_at=finished_at,
            cancelled=state in (JobState.CANCELLING, JobState.CANCELLED),
        )

    def _device_domain_jobs(self) -> list[dict]:
        """Job-service dicts for jobs owned by the device domain only."""
        if self._job_service is None:
            return []
        return [
            j for j in self._job_service.list_jobs()
            if str(j.get("owner", "")).startswith("device:")
        ]

    def shutdown(self):
        self._discovered.clear()

    # ── Event callbacks (legacy transfer progress) ──

    def set_on_progress(self, cb: Callable[[TransferJob], None] | None):
        self._on_progress = cb

    # ── Discovery ──

    def discover(self) -> list[DeviceIdentity]:
        self._discovered.clear()
        results: list[DeviceIdentity] = []
        for info in self._composite().discover():
            info = resolve_identity(info, self._registry)
            identity = self._identity_from_info(info)
            results.append(identity)
            key = f"{identity.protocol.value}:{identity.serial or identity.mount_point}"
            self._discovered[key] = identity
        return results

    @staticmethod
    def _identity_from_info(info: DeviceInfo) -> DeviceIdentity:
        return DeviceIdentity(
            protocol=info.protocol,
            vendor=info.vendor,
            model=info.model,
            serial=info.serial,
            label=info.label,
            mount_point=info.mount_point,
            identity_source=info.identity_source,
            identity_unstable=info.identity_unstable,
        )

    def _probe_mount(self, mount_path: str) -> DeviceIdentity | None:
        info = self._composite().probe(mount_path)
        if info is None:
            return None
        return self._identity_from_info(resolve_identity(info, self._registry))

    def get_discovered(self) -> list[DeviceIdentity]:
        return list(self._discovered.values())

    def identify(self, mount_point: str) -> DeviceIdentity | None:
        for dev in self._discovered.values():
            if dev.mount_point == mount_point:
                return dev
        for identity in self._paired_identities():
            if identity.mount_point == mount_point:
                return identity
        return self._probe_mount(mount_point)

    # ── Profile resolution ──

    def resolve_capabilities(self, identity: DeviceIdentity) -> DeviceCapabilities:
        if self._resolver is None:
            return DeviceCapabilities()
        return self._resolver.resolve_capabilities(identity)

    def get_profile(self, key: str) -> dict:
        identity = self._resolve_identity_by_key(key)
        if identity is None or self._resolver is None:
            return {}
        profile = self._resolver.resolve_profile(identity)
        return {
            "profile_id": profile.profile_id,
            "name": profile.name,
            "protocol": profile.protocol,
            "vendor": profile.vendor,
            "supports_pairing": profile.supports_pairing,
            "supports_authorization": profile.supports_authorization,
            "supports_trust": profile.supports_trust,
            "supports_playlists": profile.supports_playlists,
            "supports_transcode": profile.supports_transcode,
            "music_directory": profile.music_directory,
            "supported_formats": sorted(profile.supported_formats),
            "transcode_target": profile.transcode_target,
        }

    def _resolve_identity_by_key(self, key: str) -> DeviceIdentity | None:
        for identity in self._discovered.values():
            if self._registry_key(identity) == key:
                return identity
        for identity in self._paired_identities():
            if self._registry_key(identity) == key or identity.serial == key:
                return identity
        return None

    # ── Storage ──

    def get_storage(self, mount_point: str) -> StorageInfo:
        try:
            st = os.statvfs(mount_point)
            return StorageInfo(
                total_bytes=st.f_frsize * st.f_blocks,
                free_bytes=st.f_frsize * st.f_bfree,
                used_bytes=st.f_frsize * (st.f_blocks - st.f_bfree),
                label=Path(mount_point).name,
            )
        except OSError:
            return StorageInfo()

    def free_space(self, mount_point: str) -> dict:
        info = self.get_storage(mount_point)
        if info.total_bytes <= 0:
            return {"ok": False, "error": "STORAGE_UNAVAILABLE"}
        return {"ok": True, "free_bytes": info.free_bytes,
                "total_bytes": info.total_bytes,
                "free_gb": round(info.free_bytes / (1024**3), 1)}

    def list_music(self, mount_point: str, music_dir: str = "Music") -> list[dict]:
        results = []
        base = Path(mount_point) / music_dir
        if not base.is_dir():
            base = Path(mount_point)
        try:
            for f in base.rglob("*"):
                if f.is_file() and _is_audio_file(str(f)):
                    rel = f.relative_to(mount_point)
                    results.append({
                        "path": str(f), "relative": str(rel), "name": f.name,
                        "size": f.stat().st_size,
                    })
        except PermissionError:
            pass
        return results

    # ── Pairing & trust (canonical DeviceRegistry, injected) ──

    def _paired_identities(self) -> list[DeviceIdentity]:
        if self._registry is None:
            return []
        identities = []
        for device in self._registry.list_all():
            identity = DeviceIdentity(
                protocol=_parse_protocol(getattr(device, "protocol", "")),
                vendor=getattr(device, "vendor", "") or "",
                model=getattr(device, "device_model", "") or "",
                serial=getattr(device, "serial", "") or "",
                label=getattr(device, "name", "") or "",
                mount_point=getattr(device, "mount_point", "") or "",
            )
            if identity.serial or identity.mount_point:
                identities.append(identity)
        return identities

    def pair(self, identity: DeviceIdentity) -> dict:
        if self._registry is None:
            return {"ok": False, "error": "REGISTRY_UNAVAILABLE"}
        key = self._registry_key(identity)
        if self._registry.get(key) is not None:
            return {"ok": False, "error": "ALREADY_PAIRED"}
        self._registry.register(
            key,
            name=identity.label or identity.model or identity.serial or "Device",
            device_type=identity.protocol.value,
            device_model=identity.model,
        )
        self._registry.update(
            key,
            vendor=identity.vendor,
            serial=identity.serial,
            mount_point=identity.mount_point,
            protocol=identity.protocol.value,
            authorized=False,
            trusted=False,
        )
        self._emit("device.paired", {"key": key, "label": identity.label})
        return {"ok": True, "key": key, "label": identity.label}

    def unpair(self, key: str) -> dict:
        if self._registry is None:
            return {"ok": False, "error": "REGISTRY_UNAVAILABLE"}
        if self._registry.get(key) is None:
            return {"ok": False, "error": "NOT_PAIRED"}
        self._registry.remove(key)
        self._emit("device.unpaired", {"key": key})
        return {"ok": True}

    def get_paired(self) -> list[dict]:
        if self._registry is None:
            return []
        results = []
        for device in self._registry.list_all():
            results.append({
                "key": device.device_id,
                "label": device.name,
                "vendor": getattr(device, "vendor", "") or "",
                "model": device.device_model,
                "protocol": getattr(device, "protocol", "") or device.device_type,
                "authorized": bool(getattr(device, "authorized", False)),
                "trusted": bool(getattr(device, "trusted", False)),
                "paired_at": _parse_ts(device.paired_at),
                "last_contact": _parse_ts(device.last_seen),
                "mount_point": getattr(device, "mount_point", "") or "",
            })
        return results

    def is_paired(self, key: str) -> bool:
        if self._registry is None:
            return False
        return self._registry.get(key) is not None

    def authorize(self, key: str) -> dict:
        return self._set_paired_flag(key, "authorized", True, "device.authorized")

    def unauthorize(self, key: str) -> dict:
        return self._set_paired_flag(key, "authorized", False, "device.unauthorized")

    def trust(self, key: str) -> dict:
        return self._set_paired_flag(key, "trusted", True, "device.trusted")

    def untrust(self, key: str) -> dict:
        return self._set_paired_flag(key, "trusted", False, "device.untrusted")

    def _set_paired_flag(self, key: str, flag: str, value: bool, event: str) -> dict:
        if self._registry is None:
            return {"ok": False, "error": "REGISTRY_UNAVAILABLE"}
        if self._registry.get(key) is None:
            return {"ok": False, "error": "NOT_PAIRED"}
        self._registry.update(key, **{flag: value})
        self._emit(event, {"key": key})
        return {"ok": True}

    # ── Durable transfer jobs (device_transfer) ──

    def create_transfer_job(self, source_path: str, dest_path: str,
                            direction: SyncDirection = SyncDirection.TO_DEVICE) -> TransferJob | None:
        if self._job_service is None:
            return None
        try:
            total = Path(source_path).stat().st_size
        except OSError:
            total = 0
        job_id = self._job_service.create_job(
            "device_transfer",
            owner="device:transfer",
            payload={
                "source_path": source_path,
                "dest_path": dest_path,
                "direction": direction.value,
                "total_bytes": total,
            },
            total=total,
            cancellable=True,
            pausable=False,
            retryable=True,
        )
        return self.get_job(job_id)

    def execute_job(self, job_id: str) -> dict:
        if self._job_service is None:
            return {"ok": False, "error": "JOB_SERVICE_UNAVAILABLE"}
        if self._job_service.get_job(job_id) is None:
            return {"ok": False, "error": "NOT_FOUND"}
        if not self._job_service.start_job(job_id):
            return self._job_outcome(job_id)
        return self._job_outcome(job_id)

    def _job_outcome(self, job_id: str) -> dict:
        job = self._job_service.get_job(job_id)
        if job is None:
            return {"ok": False, "error": "NOT_FOUND"}
        if job.state in (JobState.SUCCEEDED, JobState.PARTIAL_SUCCESS):
            return {"ok": True, "job_id": job_id, "status": job.state.value,
                    "total_bytes": job.total}
        if job.state in (JobState.FAILED, JobState.INTERRUPTED, JobState.CANCELLED):
            error = (job.errors[-1] if job.errors else "") or job.state.value
            return {"ok": False, "job_id": job_id, "status": job.state.value,
                    "error": error}
        return {"ok": True, "job_id": job_id, "status": job.state.value}

    def get_job(self, job_id: str) -> TransferJob | None:
        if self._job_service is None:
            return None
        return self._job_view(self._job_service.get_job(job_id))

    def list_jobs(self, status_filter: TransferStatus | None = None) -> list[TransferJob]:
        views = [self._job_view(self._job_service.get_job(j["id"]))
                 for j in self._device_domain_jobs()]
        if status_filter:
            return [j for j in views if j.status == status_filter]
        return views

    def list_sync_jobs(self, device_id: str = "") -> list[dict]:
        jobs = self._device_domain_jobs()
        if device_id:
            jobs = [j for j in jobs if j.get("owner") == f"device:{device_id}"]
        return jobs

    def cancel_job(self, job_id: str) -> dict:
        if self._job_service is None:
            return {"ok": False, "error": "JOB_SERVICE_UNAVAILABLE"}
        ok = self._job_service.cancel_job(job_id)
        if not ok:
            return {"ok": False, "error": "NOT_FOUND_OR_TERMINAL"}
        return {"ok": True}

    def retry_job(self, job_id: str) -> dict:
        if self._job_service is None:
            return {"ok": False, "error": "JOB_SERVICE_UNAVAILABLE"}
        ok = self._job_service.retry_job(job_id)
        if not ok:
            return {"ok": False, "error": "NOT_RETRYABLE"}
        return {"ok": True}

    def cancel_sync(self, job_id: str = "") -> dict:
        """Scoped cancellation — never cancels jobs outside the device domain."""
        if self._job_service is None:
            return {"ok": False, "error": "JOB_SERVICE_UNAVAILABLE"}
        if job_id:
            return self.cancel_job(job_id)
        cancelled = 0
        for j in self._device_domain_jobs():
            if self._job_service.cancel_job(j["id"]):
                cancelled += 1
        return {"ok": True, "cancelled": cancelled}

    def partial_success(self, job_id: str) -> dict:
        job = self._job_service.get_job(job_id) if self._job_service else None
        if job is None:
            return {"ok": False, "error": "NOT_FOUND"}
        result = job.result or {}
        completed = int(result.get("transferred", 0) or 0)
        failed = int(result.get("failed", 0) or 0)
        total = int(result.get("total", 0) or 0)
        return {"ok": True, "completed": completed, "failed": failed,
                "total": total}

    # ── Canonical sync entry point (durable device_sync job) ──

    def sync_to_device(self, device_id: str, track_ids: list[str],
                       playlist_name: str = "") -> dict:
        if self._job_service is None:
            return {"ok": False, "error": "JOB_SERVICE_UNAVAILABLE"}
        if not device_id:
            return {"ok": False, "error": "DEVICE_ID_REQUIRED"}
        if not track_ids:
            return {"ok": False, "error": "NO_TRACKS_SELECTED"}
        job_id = self._job_service.create_job(
            "device_sync",
            owner=f"device:{device_id}",
            payload={
                "device_id": device_id,
                "track_ids": list(track_ids),
                "playlist_name": playlist_name or "",
            },
            cancellable=True,
            pausable=False,
            retryable=True,
        )
        self._job_service.start_job(job_id)
        job = self._job_service.get_job(job_id)
        status = job.state.value if job is not None else "QUEUED"
        return {"ok": True, "job_id": job_id, "status": status}

    # ── Planning (real, via DeviceSyncPlanner) ──

    def plan_sync(self, device_key: str, track_ids_or_path: Any) -> dict:
        device = self._resolve_device_info(device_key)
        if device is None:
            return {"ok": False, "error": "DEVICE_NOT_FOUND",
                    "code": "DEVICE_NOT_FOUND"}
        track_paths = self._resolve_track_paths(track_ids_or_path)
        if not track_paths:
            return {"ok": False, "error": "NO_TRACKS_SELECTED",
                    "code": "NO_TRACKS_SELECTED"}
        if self._planner is None:
            return {"ok": False, "error": "PLANNER_UNAVAILABLE",
                    "code": "PLANNER_UNAVAILABLE"}
        caps = self._caps_for_device(device)
        plan = self._planner.plan(device, track_paths, caps,
                                  music_root=self._music_root(device))
        if plan.error_code:
            return {"ok": False, "error": plan.error_code,
                    "code": plan.error_code, "message": plan.error}
        return {"ok": True, "plan": self._planner.preview(plan),
                "device_id": device.serial or device.mount_point}

    def estimate_sync(self, device_key: str, track_ids_or_path: Any) -> dict:
        result = self.plan_sync(device_key, track_ids_or_path)
        if not result.get("ok"):
            return result
        plan = result["plan"]
        return {"ok": True, "estimate": {
            "total_files": plan.get("total_files", 0),
            "total_bytes": plan.get("total_size", 0),
            "free_bytes": plan.get("free_space", 0),
            "can_fit": plan.get("can_fit", False),
        }}

    def sync_plan(self, device_key: str, track_ids_or_path: Any = None) -> dict:
        result = self.plan_sync(device_key, track_ids_or_path)
        if not result.get("ok"):
            return {"ok": True, "device_key": device_key, "plan": {
                "total_tracks": 0, "total_size_mb": 0, "new_tracks": 0,
                "existing_tracks": 0, "skipped_tracks": 0,
                "error": result.get("error", ""),
            }}
        plan = result["plan"]
        return {"ok": True, "device_key": device_key, "plan": {
            "total_tracks": plan.get("total_files", 0),
            "total_size_mb": round((plan.get("total_size", 0) or 0) / (1024**2), 1),
            "new_tracks": plan.get("total_files", 0),
            "existing_tracks": 0,
            "skipped_tracks": 0,
            "can_fit": plan.get("can_fit", False),
            "track_ids": track_ids_or_path,
        }}

    def _resolve_track_paths(self, track_ids_or_path: Any) -> list[str]:
        if isinstance(track_ids_or_path, (list, tuple)):
            return [str(t) for t in track_ids_or_path]
        value = str(track_ids_or_path or "")
        if not value:
            return []
        path = Path(value)
        if path.is_file() and _is_audio_file(value):
            return [value]
        if path.is_dir():
            return [
                str(f) for f in path.rglob("*")
                if f.is_file() and _is_audio_file(str(f))
            ]
        return []

    def start_sync(self, device_key: str = "", plan: dict | None = None) -> dict:
        if plan and plan.get("track_ids"):
            return self.sync_to_device(
                str(device_key or plan.get("device_key", "")),
                list(plan["track_ids"]),
                str(plan.get("playlist_name", "") or ""),
            )
        return {"ok": True, "message": "No active plan", "job_id": ""}

    # ── Canonical pipeline runners (invoked by the job handlers) ──

    def run_device_sync(self, device_id: str, track_ids: list[str],
                        playlist_name: str = "", ctx=None) -> dict:
        """plan → space → formats → transfer → verify → playlist → history → event."""
        device = self._resolve_device_info(device_id)
        if device is None:
            return {"ok": False, "error_code": SyncErrorCode.DEVICE_NOT_FOUND.value,
                    "error": "DEVICE_NOT_FOUND"}
        if self._transfer is None:
            return {"ok": False, "error_code": SyncErrorCode.TRANSFER_FAILED.value,
                    "error": "TransferAdapter unavailable"}
        if self._planner is None or self._verifier is None:
            return {"ok": False, "error_code": SyncErrorCode.TRANSFER_FAILED.value,
                    "error": "Sync pipeline unavailable"}

        # Device presence check BEFORE planning: a vanished mount must not
        # be misreported as insufficient space.
        if device.mount_point and not Path(device.mount_point).is_dir():
            self._record_history(device, "", TransferStatus.FAILED,
                                 0, 0, "DEVICE_DISCONNECTED", "")
            self._emit("device_sync.failed", {
                "device_id": device_id,
                "error_code": SyncErrorCode.DEVICE_DISCONNECTED.value})
            return {"ok": False,
                    "error_code": SyncErrorCode.DEVICE_DISCONNECTED.value,
                    "error": "DEVICE_DISCONNECTED"}

        caps = self._caps_for_device(device)
        music_root = self._music_root(device)
        track_paths = self._resolve_track_paths(track_ids)
        if not track_paths:
            return {"ok": False,
                    "error_code": SyncErrorCode.NO_TRACKS.value,
                    "error": "NO_TRACKS_SELECTED"}
        plan = self._planner.plan(device, track_paths, caps,
                                  music_root=music_root)
        if plan.error_code:
            self._record_history(device, "", TransferStatus.FAILED,
                                 0, 0, plan.error, "")
            return {"ok": False, "error_code": plan.error_code,
                    "error": plan.error}

        self._emit("device_sync.started", {
            "device_id": device_id, "total": len(plan.items)})

        transferred = 0
        failed = 0
        bytes_done = 0
        total = plan.total_bytes or 1
        playlist_entries: list[str] = []
        for index, item in enumerate(plan.items):
            if ctx is not None:
                ctx.token.raise_if_cancelled()
                ctx.report_progress(
                    index / len(plan.items),
                    f"Transfiriendo {Path(item.source).name}",
                )
            outcome = self._transfer.transfer(
                item, ctx=ctx,
                progress_cb=self._progress_cb(item, ctx, total, bytes_done),
                device_mount=device.mount_point or music_root,
            )
            if outcome.status == TransferStatus.CANCELLED.value:
                self._record_history(device, "", TransferStatus.CANCELLED,
                                     item.size_bytes, outcome.bytes_transferred,
                                     "CANCELLED", "")
                self._emit("device_sync.cancelled", {
                    "device_id": device_id, "job_id": ""})
                return {"ok": False, "status": "CANCELLED",
                        "error_code": SyncErrorCode.CANCELLED.value,
                        "error": "Sync cancelled"}
            if not outcome.ok:
                failed += 1
                if outcome.error_code == SyncErrorCode.DEVICE_DISCONNECTED.value:
                    self._record_history(device, "", TransferStatus.FAILED,
                                         item.size_bytes,
                                         outcome.bytes_transferred,
                                         outcome.error, "")
                    self._emit("device_sync.failed", {
                        "device_id": device_id,
                        "error_code": outcome.error_code})
                    return {"ok": False,
                            "error_code": SyncErrorCode.DEVICE_DISCONNECTED.value,
                            "error": outcome.error}
                self._record_history(device, "", TransferStatus.FAILED,
                                     item.size_bytes, outcome.bytes_transferred,
                                     outcome.error, "")
                self._emit("device_sync.failed", {
                    "device_id": device_id,
                    "error_code": SyncErrorCode.TRANSFER_FAILED.value})
                return {"ok": False,
                        "error_code": SyncErrorCode.TRANSFER_FAILED.value,
                        "error": outcome.error}
            verification = self._verifier.verify(item.source, item.dest)
            if not verification.ok:
                self._record_history(device, "", TransferStatus.FAILED,
                                     item.size_bytes, outcome.bytes_transferred,
                                     "VERIFICATION_MISMATCH", "")
                self._emit("device_sync.failed", {
                    "device_id": device_id,
                    "error_code": SyncErrorCode.VERIFICATION_MISMATCH.value})
                return {"ok": False,
                        "error_code": SyncErrorCode.VERIFICATION_MISMATCH.value,
                        "error": "VERIFICATION_MISMATCH"}
            transferred += 1
            bytes_done += item.size_bytes
            playlist_entries.append(item.dest)

        if ctx is not None:
            ctx.report_progress(0.95, "Generando playlist")

        playlist_path = ""
        if playlist_entries and caps.supports_playlists:
            result = self.render_playlist(
                os.path.join(music_root, _playlist_name(playlist_name)),
                [_relative_to_root(e, music_root) for e in playlist_entries],
            )
            if result.get("ok"):
                playlist_path = result["path"]

        self._record_history(device, "", TransferStatus.COMPLETED,
                             bytes_done, bytes_done, "", playlist_path)
        self._emit("device_sync.completed", {
            "device_id": device_id,
            "transferred": transferred,
            "failed": failed,
            "total_bytes": bytes_done,
            "playlist_path": playlist_path,
        })
        return {
            "ok": True,
            "device_id": device_id,
            "transferred": transferred,
            "failed": failed,
            "skipped": len(plan.items) - transferred - failed,
            "total": len(plan.items),
            "total_bytes": bytes_done,
            "playlist_path": playlist_path,
        }

    def run_transfer_file(self, source_path: str, dest_path: str,
                          ctx=None) -> dict:
        if self._transfer is None:
            return {"ok": False, "error_code": SyncErrorCode.TRANSFER_FAILED.value,
                    "error": "TransferAdapter unavailable"}
        if self._verifier is None:
            return {"ok": False, "error_code": SyncErrorCode.TRANSFER_FAILED.value,
                    "error": "Verification unavailable"}
        try:
            size = Path(source_path).stat().st_size
        except OSError as exc:
            self._record_history(None, dest_path, TransferStatus.FAILED,
                                 0, 0, str(exc), "")
            return {"ok": False, "error_code": SyncErrorCode.TRANSFER_FAILED.value,
                    "error": str(exc)}
        item = SyncPlanItem(source=source_path, dest=dest_path,
                            action="copy", size_bytes=size)
        outcome = self._transfer.transfer(
            item, ctx=ctx,
            progress_cb=self._progress_cb(item, ctx, size, 0),
        )
        if outcome.status == TransferStatus.CANCELLED.value:
            return {"ok": False, "status": "CANCELLED",
                    "error_code": SyncErrorCode.CANCELLED.value,
                    "error": "Transfer cancelled"}
        if not outcome.ok:
            return {"ok": False, "error_code": outcome.error_code,
                    "error": outcome.error}
        verification = self._verifier.verify(source_path, dest_path)
        if not verification.ok:
            return {"ok": False,
                    "error_code": SyncErrorCode.VERIFICATION_MISMATCH.value,
                    "error": "VERIFICATION_MISMATCH"}
        self._record_history(None, dest_path, TransferStatus.COMPLETED,
                             size, outcome.bytes_transferred, "", "")
        return {"ok": True, "source_path": source_path, "dest_path": dest_path,
                "total_bytes": outcome.bytes_transferred}

    def _progress_cb(self, item: SyncPlanItem, ctx, total: int, offset: int):
        import contextlib

        def on_progress(current: int, _total: int):
            if self._on_progress is not None:
                view = TransferJob(
                    job_id="", source_path=item.source, dest_path=item.dest,
                    status=TransferStatus.TRANSFERRING,
                    total_bytes=item.size_bytes,
                    transferred_bytes=current,
                )
                with contextlib.suppress(Exception):
                    self._on_progress(view)
            if ctx is not None and hasattr(ctx, "progress_cb"):
                with contextlib.suppress(Exception):
                    ctx.progress_cb(offset + current, total)

        return on_progress

    def _record_history(self, device: DeviceInfo | None, dest_path: str,
                        status: TransferStatus, total: int, transferred: int,
                        error: str, playlist_path: str):
        if self._history_repository is None:
            return
        label = ""
        device_id = ""
        if device is not None:
            label = device.label
            device_id = device.serial or device.mount_point
        elif dest_path:
            label = Path(dest_path).parts[0] if Path(dest_path).parts else ""
        self._history_repository.add({
            "job_id": "",
            "device_id": device_id,
            "device_label": label,
            "direction": "to_device",
            "status": status.value,
            "total_bytes": total,
            "transferred_bytes": transferred,
            "error": error,
            "playlist_path": playlist_path,
            "timestamp": time.time(),
        })

    # ── History (persisted, repository injected) ──

    def get_history(self, limit: int = 20) -> list[dict]:
        if self._history_repository is None:
            return []
        return self._history_repository.list(limit=limit)

    def clear_history(self) -> dict:
        if self._history_repository is None:
            return {"ok": False, "error": "HISTORY_UNAVAILABLE"}
        return self._history_repository.clear()

    def last_errors(self, limit: int = 10) -> list[dict]:
        if self._history_repository is None:
            return []
        return self._history_repository.last_errors(limit=limit)

    # ── Playlists ──

    def list_playlists(self, mount_point: str) -> list[dict]:
        results = []
        base = Path(mount_point)
        try:
            for f in base.rglob("*"):
                if f.is_file() and _is_playlist_file(str(f)):
                    results.append({
                        "path": str(f), "name": f.name,
                        "size": f.stat().st_size,
                    })
        except PermissionError:
            pass
        return results

    def render_playlist(self, playlist_path: str, tracks: list[str]) -> dict:
        try:
            dst = Path(playlist_path)
            dst.parent.mkdir(parents=True, exist_ok=True)
            lines = ["#EXTM3U\n"]
            for t in tracks:
                lines.append(f"{t}\n")
            dst.write_text("".join(lines), encoding="utf-8")
            return {"ok": True, "path": str(dst), "count": len(tracks)}
        except OSError as e:
            return {"ok": False, "error": str(e)}

    # ── Legacy policy surface ──

    def formats(self) -> list[str]:
        return [".flac", ".mp3", ".wav", ".ogg", ".opus", ".m4a", ".aiff"]

    def profiles(self) -> list[dict]:
        return [
            {"id": "lossless", "name": "Lossless", "format": "flac", "bitrate": 0},
            {"id": "high", "name": "High Quality", "format": "mp3", "bitrate": 320},
            {"id": "medium", "name": "Medium", "format": "mp3", "bitrate": 192},
        ]

    def selection(self, device_key: str) -> dict:
        return {"ok": True, "device_key": device_key, "selected": []}

    def transcode_policy(self, policy: str = "copy") -> dict:
        return {"ok": True, "policy": policy}

    def get_transcode_policy(self, device_key: str) -> str:
        return "copy"

    def naming_policy(self, policy: str = "keep") -> dict:
        return {"ok": True, "policy": policy}

    def set_naming_pattern(self, device_key: str, pattern: str) -> dict:
        return {"ok": True, "pattern": pattern}

    def collision_policy(self, policy: str = "skip") -> dict:
        return {"ok": True, "policy": policy}

    def set_collision_strategy(self, device_key: str, strategy: str) -> dict:
        return {"ok": True, "strategy": strategy}

    def size_estimate(self, device_key: str, track_count: int) -> dict:
        return {"ok": True, "estimated_mb": track_count * 10}

    def get_device_detail(self, device_key: str) -> dict:
        identity = self._resolve_identity_by_key(device_key)
        if identity is None:
            return {"ok": False, "error": "NOT_FOUND"}
        caps = self.resolve_capabilities(identity)
        return {
            "ok": True,
            "key": device_key,
            "label": identity.label,
            "vendor": identity.vendor,
            "model": identity.model,
            "protocol": identity.protocol.value,
            "serial": identity.serial,
            "mount_point": identity.mount_point,
            "supports_playlists": caps.supports_playlists,
            "music_directory": caps.music_directory,
        }

    def eject(self, mount_point: str) -> dict:
        """Unmount through the controlled process port (never subprocess)."""
        if self._process_controller is None:
            return {"ok": False, "error": "PROCESS_CONTROLLER_UNAVAILABLE"}
        proc = self._process_controller.spawn_sync(
            "umount", [mount_point],
        )
        if proc is None:
            return {"ok": False, "error": "UMOUNT_SPAWN_FAILED"}
        deadline = time.monotonic() + 5.0
        while proc.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        self._process_controller.cleanup_sync(proc.pid)
        if proc.poll() == 0:
            return {"ok": True, "message": f"Unmounted {mount_point}"}
        return {"ok": False, "error": f"umount exit {proc.poll()}"}


def _parse_ts(value: Any) -> float:
    if not value:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        try:
            return time.mktime(time.strptime(str(value), "%Y-%m-%dT%H:%M:%S"))
        except (TypeError, ValueError):
            return 0.0


def _parse_protocol(value: str) -> DeviceProtocol:
    for proto in DeviceProtocol:
        if proto.value == value:
            return proto
    return DeviceProtocol.UNKNOWN


def _playlist_name(playlist_name: str) -> str:
    name = safe_filename(playlist_name or "Michi Sync")
    if not name.lower().endswith(".m3u"):
        name += ".m3u"
    return name


def _relative_to_root(path: str, root: str) -> str:
    try:
        return os.path.relpath(path, root)
    except ValueError:
        return path
