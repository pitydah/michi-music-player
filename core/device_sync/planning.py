"""DeviceSyncPlanner — real sync planning with space validation and estimates.

Plan flow (mandatory, Fase Sync):
    select tracks → space validation → format compatibility →
    copy/transcode decision → REAL estimate (source file sizes, device
    free space — no fixed multipliers) → plan items.

A plan with insufficient space returns ``error_code=SPACE_INSUFFICIENT``
and NO items: nothing is transferred partially.
"""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from core.device_sync.models import (
    DeviceCapabilities,
    DeviceInfo,
    SyncErrorCode,
    DeviceSyncPlan,
    SyncPlanItem,
    safe_filename,
)
from core.device_sync.transcode_planning import TranscodePlanner

logger = logging.getLogger("michi.device_sync.planner")


class DeviceSyncPlanner:
    def __init__(self, transcode_planner: TranscodePlanner | None = None):
        self._transcode = transcode_planner or TranscodePlanner()

    def plan(
        self,
        device: DeviceInfo,
        track_paths: list[str],
        caps: DeviceCapabilities,
        music_root: str = "",
    ) -> DeviceSyncPlan:
        plan = DeviceSyncPlan(device_id=device.serial or device.mount_point)
        music_root = music_root or device.music_directory or "Music"

        items: list[SyncPlanItem] = []
        for source in track_paths:
            if not source or not os.path.isfile(source):
                continue
            size = os.path.getsize(source)
            if size <= 0:
                continue
            name = safe_filename(Path(source).name)
            dest = os.path.join(music_root, name)
            decision = self._transcode.decide(source, caps)
            if decision.needs_transcode and not decision.possible:
                plan.error_code = SyncErrorCode.FORMAT_UNSUPPORTED.value
                plan.error = (
                    f"FORMAT_UNSUPPORTED: {Path(source).name} cannot be "
                    f"transcoded for this device")
                return plan
            if decision.needs_transcode:
                base = os.path.splitext(name)[0]
                dest = os.path.join(music_root, base + decision.target_ext)
                items.append(SyncPlanItem(
                    source=source, dest=dest, action="transcode",
                    size_bytes=size, target_ext=decision.target_ext,
                    transcode_profile=decision.profile_id,
                    reason=decision.reason,
                ))
            else:
                items.append(SyncPlanItem(
                    source=source, dest=dest, action="copy",
                    size_bytes=size, reason="Format compatible",
                ))

        if not items:
            plan.error_code = SyncErrorCode.PLAN_EMPTY.value
            plan.error = "No syncable audio tracks in selection"
            return plan

        needed = sum(item.size_bytes for item in items)
        free = self._free_bytes(device, music_root)
        plan.items = items
        plan.total_bytes = needed
        plan.free_bytes = free
        plan.needed_bytes = needed
        plan.can_fit = free >= needed
        if not plan.can_fit:
            plan.error_code = SyncErrorCode.SPACE_INSUFFICIENT.value
            plan.error = (
                f"SPACE_INSUFFICIENT: need {needed} bytes, "
                f"device has {free} bytes free")
            plan.items = []
        return plan

    def preview(self, plan: DeviceSyncPlan) -> dict:
        by_action: dict[str, int] = {}
        for item in plan.items:
            by_action[item.action] = by_action.get(item.action, 0) + 1
        return {
            "device_id": plan.device_id,
            "total_files": len(plan.items),
            "total_size": plan.total_bytes,
            "free_space": plan.free_bytes,
            "needed_space": plan.needed_bytes,
            "can_fit": plan.can_fit,
            "by_action": by_action,
        }

    @staticmethod
    def _free_bytes(device: DeviceInfo, music_root: str) -> int:
        if device.free_bytes > 0:
            return device.free_bytes
        probe = music_root if os.path.isdir(music_root) else device.mount_point
        if probe and os.path.isdir(probe):
            try:
                return shutil.disk_usage(probe).free
            except OSError:
                return 0
        return 0
