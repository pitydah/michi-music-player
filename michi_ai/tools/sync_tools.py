"""Michi AI Sync Tools — sync status and control."""

from __future__ import annotations

from michi_ai.tools.tool_result import ToolResult


def get_sync_status(sync_manager=None, **kwargs) -> ToolResult:
    if sync_manager is None:
        return ToolResult(ok=True, data={"active": False, "peers": 0, "syncing": False})
    try:
        peers = sync_manager.get_all_peers() if hasattr(sync_manager, "get_all_peers") else []
        active = sync_manager.isRunning() if hasattr(sync_manager, "isRunning") else False
        syncing = sync_manager.is_syncing() if hasattr(sync_manager, "is_syncing") else False
        return ToolResult(ok=True, data={"active": active, "peers": len(peers), "syncing": syncing})
    except Exception as e:
        return ToolResult(ok=False, code="ERROR", message=str(e))


def list_sync_peers(sync_manager=None, **kwargs) -> ToolResult:
    if sync_manager is None:
        return ToolResult(ok=True, data={"peers": []})
    try:
        peers = sync_manager.get_all_peers() if hasattr(sync_manager, "get_all_peers") else []
        safe = [{"alias": p.get("alias", ""), "device_type": p.get("device_type", "")} for p in peers]
        return ToolResult(ok=True, data={"peers": safe, "count": len(safe)})
    except Exception as e:
        return ToolResult(ok=False, code="ERROR", message=str(e))
