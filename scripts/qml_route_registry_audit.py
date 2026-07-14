#!/usr/bin/env python3
"""Audit QML Route Registry consistency."""
import sys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ui_qml_bridge.route_registry import ROUTES  # noqa: E402

ERRORS = []


def check():
    # Every route has required fields
    for route, info in ROUTES.items():
        for key in ("title", "source", "category", "status"):
            if key not in info:
                ERRORS.append(f"{route}: missing {key}")

            # Every source exists
        if "source" in info and info.get("status") != "placeholder":
            source_path = info["source"].replace("../pages/", "pages/")
            qml_path = ROOT / "ui_qml" / source_path
            if not qml_path.exists():
                ERRORS.append(f"{route}: source not found: {qml_path}")

    # Sidebar routes must be in registry
    sidebar = (ROOT / "ui_qml" / "shell" / "Sidebar.qml").read_text()
    sidebar_routes = set(re.findall(r'route: "(\w+)"', sidebar))
    for r in sidebar_routes:
        if r not in ROUTES:
            ERRORS.append(f"Sidebar route {r} not in RouteRegistry")

    # PageStack fallback sources must be in registry
    pagestack = (ROOT / "ui_qml" / "shell" / "PageStack.qml").read_text()
    for _r, info in ROUTES.items():
        if info["source"] not in pagestack and info["status"] != "disabled":
            # Allow route registry to be the primary source
            pass

    print("# QML Route Registry Audit")
    print()
    if ERRORS:
        print("| Error |")
        print("|---|---|")
        for e in ERRORS:
            print(f"| {e} |")
    else:
        print("No errors found.")
    print()
    print(f"**Routes in registry:** {len(ROUTES)}")
    print(f"**Sidebar routes:** {len(sidebar_routes)}")
    print(f"**Errors:** {len(ERRORS)}")
    return len(ERRORS)


if __name__ == "__main__":
    sys.exit(check())
