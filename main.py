#!/usr/bin/python3
"""Michi Music Player — delegates to michi.app_launcher.launch()."""

import sys

if "--diagnostics" in sys.argv:
    from core.service_container import ServiceContainer
    sc = ServiceContainer()
    print("=== Diagnostics ===")
    print(f"Python: {sys.version}")
    print(f"Platform: {sys.platform}")
    try:
        from PySide6.QtCore import qVersion
        print(f"Qt: {qVersion()}")
    except ImportError:
        print("Qt: NOT AVAILABLE")
    try:
        import gi
        gi.require_version("Gst", "1.0")
        from gi.repository import Gst
        Gst.init(None)
        print("GStreamer: AVAILABLE")
    except Exception:
        print("GStreamer: NOT AVAILABLE")
    sys.exit(0)

from michi.app_launcher import launch

# Presentation preview harness — demo fixtures only load when this flag is
# passed explicitly. Never active in normal runtime.
PRESENTATION_PREVIEW = "--presentation-preview" in sys.argv

if __name__ == "__main__":
    sys.exit(launch())
