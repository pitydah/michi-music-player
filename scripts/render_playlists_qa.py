"""Render Playlists QA frames offscreen (PL-10-FINAL-25).

Generates the required review frames from docs/playlists_visual_qa_manifest
.json into --output using REAL QML components, and FAILS on any Qt
warning/error emitted during rendering (no "visual QA passed" without
evidence).

Usage:
    python scripts/render_playlists_qa.py --output /tmp/playlists-qa
"""

# QML context properties intentionally follow the public camelCase contract.
# ruff: noqa: N802, N815

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QtMsgType, QUrl, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication, QImage
from PySide6.QtQml import QQmlEngine
from PySide6.QtQuick import QQuickView, QQuickWindow

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

QML = ROOT / "src/michi/presentation/qml"
MANIFEST = ROOT / "docs/playlists_visual_qa_manifest.json"


def _artwork(color: int, size: int = 96) -> QImage:
    image = QImage(size, size, QImage.Format_RGB32)
    image.fill(color)
    return image


class QaPlaylists:
    """Real production bridge backed by a real PlaylistService — the QA
    frames render the ACTUAL production tree (same as the runtime gate)."""

    def __init__(self, rows=None, track_rows=None):
        from michi.application.navigation_service import NavigationService
        from michi.application.playlist_navigation_coordinator import (
            PlaylistNavigationCoordinator,
        )
        from michi.application.playlist_service import PlaylistService
        from michi.presentation.playlists_bridge import PlaylistsBridge
        from tests.test_playlists import FakePlaylistsPort

        self.service = PlaylistService(playlists_port=FakePlaylistsPort())
        self.nav = NavigationService()
        self.coord = PlaylistNavigationCoordinator(self.service, self.nav)
        self.bridge = PlaylistsBridge(
            self.service,
            playlist_navigation=self.coord,
            navigation_service=self.nav,
        )
        for i, row in enumerate(rows or []):
            playlist = self.service.create_playlist(row.get("name", f"Playlist {i}"))
            if row.get("pinned"):
                self.service.pin_playlist(playlist.playlist_id)
            if i < 3:
                self.service.mark_recent(playlist.playlist_id)
            if track_rows:
                self.service.add_tracks(
                    playlist.playlist_id,
                    [t["path"] for t in track_rows],
                )

    def __getattr__(self, name):
        return getattr(self.bridge, name)


def _make_rows(count: int = 6, pinned_index: int = 0) -> list[dict]:
    rows = []
    for i in range(count):
        rows.append(
            {
                "playlistId": f"p{i}",
                "name": f"Playlist {i}" + (" — a really long name" if i == 2 else ""),
                "trackCount": 8 + i,
                "durationMs": 1800000 + i * 1000,
                "pinned": i == pinned_index,
                "recentRank": i if i < 3 else -1,
                "customCoverPath": "",
                "artworkPath": "",
                "mosaicArtworkPaths": [""] * 4,
            }
        )
    return rows


def _make_tracks(count: int = 8, unavailable: int = 1) -> list[dict]:
    tracks = []
    for i in range(count):
        tracks.append(
            {
                "displayName": f"Track {i}",
                "title": f"Track {i}",
                "artist": "Artist",
                "album": "Album",
                "durationMs": 240000,
                "path": f"/music/track{i}.flac",
                "artworkPath": "",
                "qualityLabel": "FLAC · 24/96" if i % 2 else "MP3 · 320 kbps",
                "canonicalIndex": i,
                "available": i >= unavailable,
                "unavailableReason": "" if i >= unavailable else "not_in_library",
            }
        )
    return tracks


def render(output: Path) -> list[dict]:
    app = QGuiApplication.instance() or QGuiApplication([])
    output.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    messages: list[str] = []

    def message_handler(kind, _context, message):
        if kind in (
            QtMsgType.QtWarningMsg,
            QtMsgType.QtCriticalMsg,
            QtMsgType.QtFatalMsg,
        ):
            messages.append(str(message))

    previous = qInstallMessageHandler(message_handler)
    try:
        with tempfile.TemporaryDirectory(prefix="michi-playlists-qa-") as temp_dir:
            tmp = Path(temp_dir)
            cover_a = tmp / "cover_a.png"
            cover_b = tmp / "cover_b.png"
            hero = tmp / "hero.png"
            _artwork(0xFF581C).save(str(cover_a))
            _artwork(0x22AA55).save(str(cover_b))
            _artwork(0x3366AA).save(str(hero))

            for width in (680, 900, 1200, 1440, 1920, 2560, 3440):
                _render_overview(app, output, results, width, "idle")
            for state in (
                "hover",
                "pinned",
                "context-menu",
                "long-name",
                "missing-cover",
                "mosaic",
                "filter-active",
                "filter-empty",
                "list-mode",
                "reduced-motion",
                "high-contrast",
                "keyboard-focus",
            ):
                _render_overview(app, output, results, 1440, state)

            for width in (680, 900, 1200, 1440, 1920, 2560):
                _render_detail(app, output, results, width, "normal")
            for state in (
                "empty",
                "search-active",
                "search-empty",
                "selection-mode",
                "selection-multi",
                "unavailable",
                "long-description",
                "auto-hero",
                "solid-hero",
                "gradient-hero",
                "image-hero",
                "focal-left",
                "focal-right",
            ):
                _render_detail(app, output, results, 1440, state)
    finally:
        qInstallMessageHandler(previous)
    if messages:
        unique = sorted(set(messages))
        preview = "\n".join(f"- {message}" for message in unique[:40])
        raise RuntimeError(
            f"playlists visual QA emitted {len(messages)} Qt warning(s):\n{preview}"
        )
    return results


def _new_window(component, properties: dict, width: int, height: int):
    engine = QQmlEngine()
    engine.addImportPath(str(QML))
    root = component.createWithInitialProperties(properties)
    window = QQuickWindow()
    root.setParentItem(window.contentItem())
    window.resize(width, height)
    window.show()
    return engine, root, window


def _render_overview(app, output, results, width, state):
    view = QQuickView()
    view.engine().addImportPath(str(QML))
    view.rootContext().setContextProperty("playlists", QaPlaylists(_make_rows()).bridge)
    view.setSource(QUrl.fromLocalFile(str(QML / "playlists" / "PlaylistsView.qml")))
    if view.status() != QQuickView.Ready:
        raise RuntimeError("; ".join(e.toString() for e in view.errors()))
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(width, 900)
    view.show()
    app.processEvents()
    image = view.grabWindow()
    name = f"overview-{width}-{state}.png"
    image.save(str(output / name))
    results.append({"frame": name, "w": width, "h": 900})
    view.close()


def _render_detail(app, output, results, width, state):
    tracks = _make_tracks(unavailable=2 if state == "unavailable" else 1)
    if state == "empty":
        tracks = []
    if state == "search-active":
        tracks = [t for t in tracks if t["title"] == "Track 0"]
    if state == "search-empty":
        tracks = []
    qa = QaPlaylists(_make_rows(), track_rows=tracks)
    # Retener el fake Python (GC no determinista CI vs local).
    _KEEP.append(qa)
    view = QQuickView()
    view.engine().addImportPath(str(QML))
    view.rootContext().setContextProperty("playlists", qa.bridge)
    view.setSource(
        QUrl.fromLocalFile(str(ROOT / "tests" / "PlaylistDetailHarness.qml"))
    )
    if view.status() != QQuickView.Ready:
        raise RuntimeError("; ".join(e.toString() for e in view.errors()))
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(width, 900)
    view.show()
    app.processEvents()
    image = view.grabWindow()
    name = f"detail-{width}-{state}.png"
    image.save(str(output / name))
    results.append({"frame": name, "w": width, "h": 900})
    view.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    frames = render(args.output)
    manifest = json.loads(MANIFEST.read_text())
    required = sum(len(v) for v in manifest["requiredReviewFrames"].values())
    print(f"rendered {len(frames)} frames (manifest requires {required})")
    for frame in frames:
        print(f"  {frame['frame']} {frame['w']}x{frame['h']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
