"""SyncPlanner — real sync plan generation with space calculation, preview, progress."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger("michi.sync.planner")


@dataclass
class SyncOperation:
    source: str = ""
    dest: str = ""
    size: int = 0  # bytes
    action: str = "copy"  # copy, update, delete, skip
    reason: str = ""


@dataclass
class SyncPlan:
    operations: list[SyncOperation] = field(default_factory=list)
    total_size: int = 0
    total_files: int = 0
    free_space: int = 0
    needed_space: int = 0
    can_fit: bool = False
    transcode_policy: str = ""


class SyncPlanner:
    def __init__(self, transcode_service=None):
        self._transcode = transcode_service

    def build_plan(self, source_files: list[str], dest_root: str,
                   transcode_policy: str = "", existing_files: list[str] | None = None
                   ) -> list[SyncOperation]:
        existing = set(existing_files or [])
        operations = []

        for src in source_files:
            if not os.path.isfile(src):
                continue
            rel = os.path.basename(src)
            _ext = os.path.splitext(src)[1]
            size = os.path.getsize(src)

            # Determine destination path (possibly transcoded)
            dest_name = rel
            if transcode_policy and self._transcode:
                needs = self._transcode.needs_transcode(src, transcode_policy)
                if needs:
                    dest_name = os.path.splitext(rel)[0] + ".flac"  # default transcode output
                    size = int(size * 0.6)  # estimated (FLAC compression ~60%)

            dest = os.path.join(dest_root, dest_name)
            action = "update" if dest in existing else "copy"

            if dest in existing and abs(os.path.getsize(dest) - size) < 1024:
                action = "skip"
                reason = "Same file"
            else:
                reason = "New" if action == "copy" else "Updated"

            operations.append(SyncOperation(
                source=src, dest=dest, size=size, action=action, reason=reason,
            ))

        return operations

    def calculate_plan(self, operations: list[SyncOperation],
                       dest_root: str) -> SyncPlan:
        total_size = sum(op.size for op in operations if op.action != "skip")
        total_files = sum(1 for op in operations if op.action != "skip")
        free_space = self._get_free_space(dest_root)
        needed_space = total_size
        can_fit = free_space >= needed_space if free_space > 0 else True

        return SyncPlan(
            operations=operations,
            total_size=total_size,
            total_files=total_files,
            free_space=free_space,
            needed_space=needed_space,
            can_fit=can_fit,
        )

    def preview(self, plan: SyncPlan) -> dict:
        return {
            "ok": True,
            "total_files": plan.total_files,
            "total_size": plan.total_size,
            "free_space": plan.free_space,
            "needed_space": plan.needed_space,
            "can_fit": plan.can_fit,
            "by_action": {
                "copy": sum(1 for op in plan.operations if op.action == "copy"),
                "update": sum(1 for op in plan.operations if op.action == "update"),
                "skip": sum(1 for op in plan.operations if op.action == "skip"),
                "delete": sum(1 for op in plan.operations if op.action == "delete"),
            },
        }

    def _get_free_space(self, path: str) -> int:
        try:
            import shutil
            usage = shutil.disk_usage(path)
            return usage.free
        except Exception:
            return 0
