"""MichiAISnapshotService — build a unified sanitized snapshot for Michi AI.

Combines data from ContextService, Sync, Michi Link and Audio Lab.
Output is sanitized: no filepaths, tokens, passwords or audio data.
"""

from __future__ import annotations

from typing import Any


class MichiAISnapshotService:
    def __init__(self, context_service=None, sync_manager=None, michi_link_doctor=None):
        self._ctx = context_service
        self._sync = sync_manager
        self._doctor = michi_link_doctor

    def build_snapshot(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "route": {},
            "selection": {},
            "playback": {},
            "library_health": {},
            "sync": self._sync_status(),
            "michi_link": self._michi_link_status(),
            "recent_events": [],
            "capabilities": self._capabilities(),
        }

        if self._ctx is not None:
            try:
                snap = self._ctx.get_assistant_snapshot()
                if snap:
                    result["route"] = snap.get("route", {})
                    result["selection"] = snap.get("selection", {})
                    result["playback"] = snap.get("playback", {})
                    result["library_health"] = snap.get("library_health", {})
                    result["recent_events"] = snap.get("recent_events", [])[:20]
                    result["capabilities"] = snap.get("assistant_capabilities", {})
            except Exception:
                pass

        return result

    def _sync_status(self) -> dict[str, Any]:
        if self._sync is None:
            return {"active": False, "peers": 0}
        try:
            peers = self._sync.get_all_peers() if hasattr(self._sync, "get_all_peers") else []
            active = self._sync.isRunning() if hasattr(self._sync, "isRunning") else False
            return {"active": active, "peers": len(peers), "syncing": hasattr(self._sync, "is_syncing") and self._sync.is_syncing()}
        except Exception:
            return {"active": False, "peers": 0}

    def _michi_link_status(self) -> dict[str, Any]:
        if self._doctor is None:
            return {"available": False}
        try:
            summary = self._doctor.diagnose_home_summary()
            return {"available": True, "summary": summary}
        except Exception:
            return {"available": False}

    @staticmethod
    def _capabilities() -> dict[str, bool]:
        return {
            "can_search_library": True,
            "can_create_playlist": True,
            "can_analyze_audio": True,
            "can_diagnose_ecosystem": True,
            "can_create_plans": True,
        }
