#!/usr/bin/env python3
"""QML Performance probe — measures startup and route load times."""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    import psutil
except ImportError:
    psutil = None

STARTUP_STAGES = {}


def measure(label: str):
    STARTUP_STAGES[label] = time.time()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--routes", default="home,library,playlists,radio,settings,audio_lab")
    parser.add_argument("--all-routes", action="store_true")
    args = parser.parse_args()

    from ui_qml_bridge.qml_main import _get_app_version
    import platform

    measure("python_imports")

    try:
        from ui_qml_bridge.route_registry import ROUTES
    except Exception:
        ROUTES = {}

    routes_to_check = list(ROUTES.keys()) if args.all_routes else [r.strip() for r in args.routes.split(",")]

    measure("registry_loaded")

    results = {
        "app_version": _get_app_version(),
        "python": sys.version,
        "platform": platform.platform(),
        "startup_timings": {},
        "route_timings": {},
        "memory_mb": None,
    }

    for label, t in STARTUP_STAGES.items():
        results["startup_timings"][label] = round(t - STARTUP_STAGES.get("python_imports", t), 4)

    if psutil:
        try:
            proc = psutil.Process()
            results["memory_mb"] = round(proc.memory_info().rss / 1024 / 1024, 1)
        except Exception:
            pass

    # Measure RouteRegistry load
    for route in routes_to_check:
        start = time.time()
        info = ROUTES.get(route, {})
        elapsed = round((time.time() - start) * 1000, 2)
        results["route_timings"][route] = {
            "ms": elapsed,
            "status": info.get("status", "unknown"),
            "category": info.get("category", "unknown"),
        }

    results["routes_total"] = len(ROUTES)

    print(json.dumps(results, indent=2))
    (Path("/tmp/michi_qml_performance_probe.json")).write_text(json.dumps(results, indent=2))
    print("\nSaved to /tmp/michi_qml_performance_probe.json")


if __name__ == "__main__":
    main()
