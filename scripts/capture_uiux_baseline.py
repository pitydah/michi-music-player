#!/usr/bin/env python3
"""Capture UI/UX baseline screenshots for the 10 main pages.

Requires: ImageMagick (import), xdotool.
Usage: python scripts/capture_uiux_baseline.py
"""

import os
import subprocess
import sys
import time

APP_PID: int | None = None
WINDOW_NAME = "Michi Music Player"
OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs",
    "uiux",
    "screenshots",
    "baseline-post-x10",
)

PAGES: list[dict[str, str]] = [
    {"route": "home", "label": "home"},
    {"route": "library", "label": "library"},
    {"route": "nowplaying", "label": "nowplaying"},
    {"route": "queue", "label": "queue"},
    {"route": "playlists", "label": "playlists"},
    {"route": "mix", "label": "mix"},
    {"route": "settings", "label": "settings"},
    {"route": "devices", "label": "devices"},
    {"route": "connections", "label": "connections"},
    {"route": "eq", "label": "eq"},
]


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _find_window() -> str | None:
    result = subprocess.run(
        ["xdotool", "search", "--name", WINDOW_NAME],
        capture_output=True, text=True, timeout=5,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip().split("\n")[0]
    return None


def _navigate(route: str) -> None:
    subprocess.run(
        ["xdotool", "key", "ctrl+k"],
        check=True, timeout=5,
    )
    time.sleep(0.3)
    subprocess.run(
        ["xdotool", "type", route],
        check=True, timeout=5,
    )
    time.sleep(0.2)
    subprocess.run(
        ["xdotool", "key", "Return"],
        check=True, timeout=5,
    )
    time.sleep(1.0)


def _capture(path: str) -> None:
    subprocess.run(
        ["import", "-window", "root", path],
        check=True, capture_output=True, timeout=30,
    )


def _window_size() -> tuple[int, int] | None:
    wid = _find_window()
    if not wid:
        return None
    result = subprocess.run(
        ["xdotool", "getwindowgeometry", wid],
        capture_output=True, text=True, timeout=5,
    )
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("Geometry:"):
            parts = line.split()
            if len(parts) > 1:
                dims = parts[1]
                w, h = dims.split("x")
                return int(w), int(h)
    return None


def _resize(w: int, h: int) -> None:
    wid = _find_window()
    if not wid:
        return
    subprocess.run(
        ["xdotool", "windowsize", wid, str(w), str(h)],
        check=True, timeout=5,
    )
    time.sleep(0.5)


def _set_sidebar(expanded: bool) -> None:
    subprocess.run(
        ["xdotool", "key", "ctrl+\\"],
        check=True, timeout=5,
    )
    time.sleep(0.4)


def main() -> int:
    _ensure_dir(OUTPUT_DIR)

    print(f"Output directory: {OUTPUT_DIR}")
    print("Waiting for Michi Music Player window...")

    timeout = 30
    deadline = time.monotonic() + timeout
    wid = None
    while time.monotonic() < deadline:
        wid = _find_window()
        if wid:
            break
        time.sleep(1)

    if not wid:
        print("ERROR: Could not find Michi Music Player window", file=sys.stderr)
        return 1

    print(f"Found window ID: {wid}")

    _resize(1920, 1080)
    time.sleep(1)

    use_sidebar = True
    current_size = _window_size()
    if current_size:
        print(f"Current window size: {current_size[0]}x{current_size[1]}")
        area = current_size[0] * current_size[1]
        if area < 1_500_000:
            use_sidebar = False
            print("Window too small — skipping sidebar toggle")

    for page in PAGES:
        route = page["route"]
        label = page["label"]
        collapsed_path = os.path.join(OUTPUT_DIR, f"{label}_sidebar_collapsed.png")
        expanded_path = os.path.join(OUTPUT_DIR, f"{label}_sidebar_expanded.png")

        _navigate(route)

        if use_sidebar and not os.path.exists(collapsed_path):
            _set_sidebar(expanded=False)
            time.sleep(0.5)
            _capture(collapsed_path)
            print(f"  Captured (collapsed): {collapsed_path}")
        elif os.path.exists(collapsed_path):
            print(f"  Skipped (exists): {collapsed_path}")

        if use_sidebar and not os.path.exists(expanded_path):
            _set_sidebar(expanded=True)
            time.sleep(0.5)
            _capture(expanded_path)
            print(f"  Captured (expanded): {expanded_path}")
        elif os.path.exists(expanded_path):
            print(f"  Skipped (exists): {expanded_path}")

        if not use_sidebar and not os.path.exists(collapsed_path):
            _capture(collapsed_path)
            print(f"  Captured: {collapsed_path}")

    print("Done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
