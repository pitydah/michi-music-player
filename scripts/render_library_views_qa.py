"""Render the six premium Library views at the required review frames."""

# QML context properties intentionally follow the public camelCase contract.
# ruff: noqa: N802, N815

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickWindow

ROOT = Path(__file__).resolve().parents[1]
QML = ROOT / "src/michi/presentation/qml"
MODES = {
    "gallery": "grid",
    "album-flow": "cover",
    "listening-wall": "vinyl",
    "chronology": "timeline",
    "editorial": "magazine",
    "studio-list": "list",
}
FRAMES = (
    (900, 900, "compact"),
    (1440, 900, "normal"),
    (1920, 1080, "wide"),
    (1440, 900, "selected-and-focus"),
    (1440, 900, "view-options-open"),
)


def album_rows(count: int = 72) -> list[dict]:
    palettes = (
        ("#1D4561", "#163548", "#09141E", "#62B5D7"),
        ("#67402E", "#462A25", "#170D0D", "#D78B62"),
        ("#3D315C", "#29213E", "#0E0A16", "#A88BD5"),
    )
    rows = []
    for index in range(count):
        dominant, secondary, backplane, accent = palettes[index % len(palettes)]
        year = 1958 + index % 68
        rows.append(
            {
                "key": f"qa::{index}",
                "title": f"Nocturne Archive {index + 1:02d}",
                "artist": f"Michi Ensemble {index % 11 + 1}",
                "year": year,
                "decade": f"{year // 10 * 10}s",
                "trackCount": 7 + index % 8,
                "durationMs": 2_100_000 + index * 1_300,
                "discCount": 2 if index % 9 == 0 else 1,
                "genres": ["Electronic", "Ambient"] if index % 3 == 0 else ["Jazz"],
                "composers": [],
                "hasArtwork": False,
                "artworkPath": "",
                "technicalState": "mixed" if index % 5 == 0 else "homogeneous",
                "technicalSummary": "FLAC · 24-bit · 96 kHz",
                "codecs": ["FLAC"],
                "maxSampleRateHz": 96_000,
                "maxBitDepth": 24,
                "maxChannels": 2,
                "containsDsd": False,
                "containsHighResolution": index % 4 == 0,
                "isFavorite": index % 8 == 0,
                "isRecentlyAdded": index < 6,
                "artworkPalette": {
                    "colors": [dominant, secondary, backplane],
                    "dominant": dominant,
                    "secondary": secondary,
                    "backplane": backplane,
                    "accentSafe": accent,
                    "luminance": 0.18,
                    "warmth": 0.0,
                },
            }
        )
    return rows


class QaLibrary(QObject):
    library_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._albums = album_rows()

    @Property(list, notify=library_changed)
    def albums(self):
        return self._albums

    @Property(list, notify=library_changed)
    def timelineAlbums(self):
        return sorted(self._albums, key=lambda row: (-row["year"], row["title"]))

    fileCount = Property(int, lambda self: 864, notify=library_changed)
    albumCount = Property(int, lambda self: len(self._albums), notify=library_changed)
    artistCount = Property(int, lambda self: 11, notify=library_changed)
    currentDir = Property(str, lambda self: "/qa/music", notify=library_changed)
    selectedAlbumKey = Property(str, lambda self: "", notify=library_changed)
    selectedArtistKey = Property(str, lambda self: "", notify=library_changed)
    searchActive = Property(bool, lambda self: False, notify=library_changed)
    searchQuery = Property(str, lambda self: "", notify=library_changed)
    searchAlbumCount = Property(
        int, lambda self: len(self._albums), notify=library_changed
    )
    searchTotalCount = Property(
        int, lambda self: len(self._albums), notify=library_changed
    )
    scanStatus = Property(str, lambda self: "", notify=library_changed)
    scanProcessed = Property(int, lambda self: 0, notify=library_changed)
    scanTotal = Property(int, lambda self: 0, notify=library_changed)
    favoritePaths = Property(list, lambda self: [], notify=library_changed)

    @Slot(str)
    def search(self, _query):
        return None

    @Slot()
    def clear_search(self):
        return None

    @Slot(str)
    def scan(self, _path):
        return None

    @Slot(str)
    def select_album(self, _key):
        return None

    @Slot(str)
    def play_album(self, _key):
        return None


class QaEnrichment(QObject):
    revision = Property(int, lambda self: 0)

    @Slot(str, int, result="QVariantMap")
    def album(self, key, _revision):
        return {
            "albumKey": key,
            "hasCachedKnowledge": True,
            "knowledge": {"label": "Michi Editions", "releaseYear": 2024},
        }


def render(output: Path) -> list[dict]:
    app = QGuiApplication.instance() or QGuiApplication([])
    library = QaLibrary()
    enrichment = QaEnrichment()
    results = []
    for view_name, mode in MODES.items():
        for width, height, state in FRAMES:
            engine = QQmlEngine()
            engine.addImportPath(str(QML))
            engine.rootContext().setContextProperty("library", library)
            engine.rootContext().setContextProperty("libraryEnrichment", enrichment)
            component = QQmlComponent(
                engine, QUrl.fromLocalFile(str(QML / "views/LibraryView.qml"))
            )
            errors = "; ".join(error.toString() for error in component.errors())
            if component.status() != QQmlComponent.Ready:
                raise RuntimeError(errors)
            root = component.create()
            if root is None:
                raise RuntimeError(errors or "LibraryView could not instantiate")
            window = QQuickWindow()
            window.setGeometry(0, 0, width, height)
            root.setParentItem(window.contentItem())
            root.setProperty("width", width)
            root.setProperty("height", height)
            root.setProperty("currentTab", "albums")
            root.setProperty("albumMode", mode)
            window.show()
            for _ in range(8):
                app.processEvents()

            if state == "selected-and-focus":
                active = root.findChild(
                    QObject,
                    {
                        "grid": "albumGridView",
                        "cover": "albumCoverView",
                        "vinyl": "albumVinylView",
                        "timeline": "albumTimelineView",
                        "magazine": "albumMagazineView",
                        "list": "albumListView",
                    }[mode],
                )
                if active is not None:
                    active.setFocus(True)
            elif state == "view-options-open":
                popup = root.findChild(QObject, "libraryViewOptionsPopup")
                if popup is None:
                    raise RuntimeError("View Options popup not found")
                popup.setProperty("visible", True)
            for _ in range(6):
                app.processEvents()

            target = output / f"{view_name}--{width}x{height}--{state}.png"
            image = window.grabWindow()
            if image.isNull() or not image.save(str(target)):
                raise RuntimeError(f"could not save {target}")
            results.append(
                {
                    "view": view_name,
                    "width": width,
                    "height": height,
                    "state": state,
                    "file": target.name,
                }
            )
            window.close()
            root.deleteLater()
            window.deleteLater()
            engine.deleteLater()
            app.processEvents()
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    args.output.mkdir(parents=True, exist_ok=True)
    frames = render(args.output)
    (args.output / "index.json").write_text(
        json.dumps({"schemaVersion": 1, "frames": frames}, indent=2) + "\n",
        encoding="utf-8",
    )
    if len(frames) != len(MODES) * len(FRAMES):
        raise RuntimeError("incomplete visual QA matrix")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
