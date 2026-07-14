from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from michi_ai.v2.core.models import (
    ConfirmationMode, ConfirmationRequest, ErrorCode, OperationResult,
    PlanStep,
)


class ConfirmationPolicyV2:
    DEFAULT_TTL_SECONDS = 120
    ALWAYS_CONFIRM_ACTIONS: frozenset[str] = frozenset({
        "delete", "remove", "clear", "overwrite", "repair", "transfer",
        "convert", "modify_metadata", "clean_history", "disconnect",
        "apply_plan", "start_conversion", "apply_library_repair",
        "start_device_sync", "apply_setting_change",
    })

    def __init__(self, mode: ConfirmationMode = ConfirmationMode.PER_DESTRUCTIVE_STEP, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self._mode = mode
        self._ttl_seconds = ttl_seconds
        self._issued: dict[str, ConfirmationRequest] = {}
        self._consumed: set[str] = set()

    @property
    def mode(self) -> ConfirmationMode:
        return self._mode

    def set_mode(self, mode: ConfirmationMode) -> None:
        self._mode = mode

    def requires_confirmation(self, step: PlanStep, plan_requires: bool = False) -> bool:
        if self._mode == ConfirmationMode.NONE:
            return False

        if self._mode == ConfirmationMode.ALWAYS:
            return True

        if plan_requires and self._mode in (ConfirmationMode.ONCE_PER_PLAN, ConfirmationMode.PER_DESTRUCTIVE_STEP):
            return True

        return step.tool in self.ALWAYS_CONFIRM_ACTIONS or any(
            keyword in step.tool for keyword in self.ALWAYS_CONFIRM_ACTIONS
        )

    def issue(self, plan_id: str, summary: str = "", affected_resources: tuple[str, ...] = (), risks: tuple[str, ...] = (), required_phrase: str = "", plan: Any | None = None) -> ConfirmationRequest:
        confirmation_id = uuid.uuid4().hex[:16]
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=self._ttl_seconds)).isoformat()
        request = ConfirmationRequest(
            confirmation_id=confirmation_id,
            plan_id=plan_id,
            summary=summary,
            affected_resources=affected_resources,
            risks=risks,
            expires_at=expires_at,
            required_phrase=required_phrase,
            plan=plan,
        )
        self._issued[confirmation_id] = request
        return request

    def validate(self, confirmation_id: str, plan_id: str) -> OperationResult[None]:
        request = self._issued.get(confirmation_id)
        if request is None:
            return OperationResult.failure(
                ErrorCode.CONFIRMATION_EXPIRED,
                "Confirmation request not found or already consumed",
            )

        if confirmation_id in self._consumed:
            return OperationResult.failure(
                ErrorCode.CONFIRMATION_EXPIRED,
                "Confirmation already used (single-use)",
            )

        if request.plan_id != plan_id:
            return OperationResult.failure(
                ErrorCode.CONFIRMATION_EXPIRED,
                "Confirmation does not match plan",
            )

        if request.expires_at:
            try:
                expires = datetime.fromisoformat(request.expires_at)
                if expires < datetime.now(timezone.utc):
                    self._consumed.add(confirmation_id)
                    return OperationResult.failure(
                        ErrorCode.CONFIRMATION_EXPIRED,
                        "Confirmation request has expired",
                    )
            except (ValueError, TypeError):
                pass

        self._consumed.add(confirmation_id)
        return OperationResult.success()

    def clean_expired(self) -> int:
        now = datetime.now(timezone.utc)
        expired = 0
        for cid, req in list(self._issued.items()):
            if req.expires_at:
                try:
                    expires = datetime.fromisoformat(req.expires_at)
                    if expires < now:
                        self._issued.pop(cid, None)
                        expired += 1
                except (ValueError, TypeError):
                    self._issued.pop(cid, None)
                    expired += 1
        return expired

    def pending_count(self) -> int:
        return len(self._issued) - len(self._consumed)

    def clear(self) -> None:
        self._issued.clear()
        self._consumed.clear()
