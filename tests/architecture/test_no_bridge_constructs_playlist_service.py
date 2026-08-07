"""Bridges must not construct services as fallback (ADR-003).

When an injected service is missing the bridge reports degraded mode
(INFRASTRUCTURE_UNAVAILABLE) instead of building the service itself.
"""
from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock

from ui_qml_bridge.playlists_bridge import PlaylistsBridge

BRIDGES_DIR = Path(__file__).resolve().parent.parent.parent / "ui_qml_bridge"

# Service/repository classes bridges used to construct as fallback.
FORBIDDEN_CONSTRUCTIONS = [
    r"PlaylistService\s*\(",
    r"HistoryQueryService\s*\(",
    r"LibraryDoctorScanRepository\s*\(",
    r"JobManager\s*\(",
    r"LRCLIBClient\s*\(",
]


def _bridge_files():
    return sorted(BRIDGES_DIR.glob("*.py"))


def test_no_bridge_constructs_services_as_fallback() -> None:
    offenders = []
    for path in _bridge_files():
        source = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_CONSTRUCTIONS:
            if re.search(pattern, source):
                offenders.append(f"{path.name}:{pattern}")
    assert offenders == [], (
        f"Bridges constructing services: {offenders}"
    )


def test_playlists_bridge_requires_injected_service() -> None:
    """Without an injected PlaylistService the bridge degrades explicitly."""
    bridge = PlaylistsBridge(db=MagicMock(), playlist_service=None)
    assert bridge._svc is None
    assert bridge.createPlaylist("X") == {
        "ok": False, "code": "INFRASTRUCTURE_UNAVAILABLE",
        "error": "SERVICE_UNAVAILABLE",
    }
    assert bridge._can() is False


def test_history_bridge_does_not_build_query_service() -> None:
    """HistoryBridge keeps history_query_service=None when not injected."""
    from ui_qml_bridge.history_bridge import HistoryBridge

    bridge = HistoryBridge(db=MagicMock())
    assert bridge._hqs is None
    assert bridge.fetchPage() == {"ok": False, "error": "NO_SERVICE"}
