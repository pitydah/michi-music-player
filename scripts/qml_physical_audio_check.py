#!/usr/bin/env python3
"""Physical audio check for QML — tests components that would enable audio.

Runs without display (offscreen). Verifies PlayerService, NowPlayingBridge,
PlaybackBridge, and cover loading work together.
Does NOT verify actual audio output (needs speakers).
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["QT_QPA_PLATFORM"] = "offscreen"

PASSED = []
FAILED = []


def check(name: str, ok: bool, detail: str = ""):
    if ok:
        PASSED.append(name)
        print(f"  ✓ {name}")
    else:
        FAILED.append(name)
        print(f"  ✗ {name}: {detail}")


def main():
    print("# QML Physical Audio Readiness Check\n")

    # 1. PlayerService creation
    print("## 1. PlayerService")
    try:
        from audio.player import GStreamerEngine
        engine = GStreamerEngine()
        from audio.player_service import PlayerService
        ps = PlayerService(engine)
        check("PlayerService created", True)
        check("PlayerService has play", hasattr(ps, 'play'), "no play method")
        check("PlayerService has pause", hasattr(ps, 'pause'), "no pause")
        check("PlayerService has stop", hasattr(ps, 'stop'), "no stop")
        check("PlayerService has seek", hasattr(ps, 'seek'), "no seek")
        check("PlayerService has set_volume", hasattr(ps, 'set_volume'), "no set_volume")
    except Exception as e:
        check(f"PlayerService init: {e}", False, str(e))

    # 2. NowPlayingBridge
    print("\n## 2. NowPlayingBridge")
    try:
        from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
        npb = NowPlayingBridge()
        check("NowPlayingBridge created", True)
        check("has trackTitle", hasattr(npb, 'trackTitle'), "no trackTitle")
        check("has trackArtist", hasattr(npb, 'trackArtist'), "no trackArtist")
        check("has position", hasattr(npb, 'position'), "no position")
        check("has trackDuration", hasattr(npb, 'trackDuration'), "no trackDuration")
        check("has position", hasattr(npb, 'position'), "no position")
    except Exception as e:
        check("NowPlayingBridge init failed", False, str(e))

    # 3. PlaybackBridge
    print("\n## 3. PlaybackBridge")
    try:
        from ui_qml_bridge.playback_bridge import PlaybackBridge
        from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
        npb = NowPlayingBridge()
        pb = PlaybackBridge(nowplaying_bridge=npb)
        check("PlaybackBridge created", True)
        check("has playPause", hasattr(pb, 'playPause'), "no playPause")
        check("has next", hasattr(pb, 'next'), "no next")
        check("has previous", hasattr(pb, 'previous'), "no previous")
    except Exception as e:
        check("PlaybackBridge init failed", False, str(e))

    # 4. Cover Bridge
    print("\n## 4. CoverBridge")
    try:
        from ui_qml_bridge.cover_bridge import CoverBridge
        cb = CoverBridge()
        check("CoverBridge created", True)
    except Exception as e:
        check("CoverBridge init failed", False, str(e))

    # 5. QML main module importable
    print("\n## 5. QML entry point")
    try:
        from ui_qml_bridge.qml_main import _get_app_version, _create_services
        ver = _get_app_version()
        check(f"App version: {ver}", True)
        svc = _create_services()
        check("Services created", True)
        if svc.player_service:
            check("PlayerService available", True)
        else:
            check("PlayerService available", False, "NOT created (may need display)")
    except Exception as e:
        check("QML entry point failed", False, str(e))

    # 6. Routes that imply audio
    print("\n## 6. Audio-capable routes")
    from ui_qml_bridge.route_registry import ROUTES
    qml_dir = Path(__file__).resolve().parent.parent / "ui_qml"
    for route, info in ROUTES.items():
        if info.get("source"):
            source = info["source"].lstrip("..").lstrip("/")
            qml_path = qml_dir / source
            exists = qml_path.exists()
            check(f"Route '{route}' page exists", exists, f"missing at {qml_path}")

    # Summary
    print(f"\n## Summary")
    print(f"**Passed:** {len(PASSED)}")
    print(f"**Failed:** {len(FAILED)}")
    print(f"**Audio output:** NOT VERIFIED (needs display)")
    print(f"**Seek/Next/Prev:** NOT VERIFIED (needs runtime)")

    return 0 if not FAILED else 1


if __name__ == "__main__":
    sys.exit(main())
