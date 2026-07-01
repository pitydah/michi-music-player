"""MichiAIContextBridge — connect external services to ContextService.

Bridges SyncManager, Michi Link services, Audio Lab, and tool execution
into the central ContextService event system. No UI dependency.
"""

from __future__ import annotations

import logging

from michi_ai.context.ai_event_mapper import map_event

logger = logging.getLogger("michi_ai.context_bridge")


class MichiAIContextBridge:
    def __init__(self, context_service=None):
        self._ctx = context_service

    def connect_sync_manager(self, sync_manager) -> None:
        if sync_manager is None:
            return
        signals = [
            ("sync_started", self._on_sync_started),
            ("sync_stopped", self._on_sync_stopped),
            ("client_connected", self._on_client_connected),
            ("peer_found", self._on_peer_found),
            ("peer_lost", self._on_peer_lost),
            ("error_occurred", self._on_sync_error),
        ]
        for signal_name, handler in signals:
            sig = getattr(sync_manager, signal_name, None)
            if sig is not None:
                try:
                    sig.connect(handler)
                except Exception:
                    logger.warning("Could not connect Sync signal: %s", signal_name)

    def _record(self, event_type: str, payload: dict | None = None) -> None:
        if self._ctx is None:
            return
        try:
            self._ctx.record_event(map_event(event_type), payload or {})
        except Exception:
            logger.debug("Failed to record event: %s", event_type)

    def _on_sync_started(self, port: int) -> None:
        self._record("sync_started", {"port": port})

    def _on_sync_stopped(self) -> None:
        self._record("sync_stopped")

    def _on_client_connected(self, alias: str) -> None:
        self._record("client_connected", {"alias": alias})

    def _on_peer_found(self, alias: str, ip: str) -> None:
        self._record("peer_found", {"alias": alias, "ip": ip})

    def _on_peer_lost(self, alias: str) -> None:
        self._record("peer_lost", {"alias": alias})

    def _on_sync_error(self, msg: str) -> None:
        self._record("sync_error", {"message": msg[:200]})

    def record_tool_result(self, tool_name: str, success: bool, payload: dict | None = None) -> None:
        event = "michi_ai_tool_executed" if success else "michi_ai_tool_failed"
        self._record(event, {"tool": tool_name, **(payload or {})})

    def record_plan_created(self, plan) -> None:
        self._record("michi_ai_plan_created", {"plan_id": getattr(plan, "plan_id", ""), "title": getattr(plan, "title", "")})

    def record_plan_applied(self, plan, result) -> None:
        self._record("michi_ai_plan_applied", {"plan_id": getattr(plan, "plan_id", ""), "success": getattr(result, "ok", False)})

    def record_micro_server_result(self, action: str, result) -> None:
        event = f"micro_server_{action}"
        ok = getattr(result, "ok", False) if not isinstance(result, dict) else result.get("ok", False)
        self._record(event, {"action": action, "ok": ok})

    def record_audio_lab_result(self, action: str, result) -> None:
        event = f"audio_lab_{action}"
        self._record(event, {"action": action})
