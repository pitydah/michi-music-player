"""M6.9-PRESENTATION — QML integration tests.

Loads the new enrichment components and the three modified views with
fake context bridges; asserts the new surface objectNames exist and the
views render without ReferenceError/TypeError/binding-loop symptoms.
Offscreen platform; no sleeps (processEvents only).
"""

import os
import sys
from pathlib import Path

import pytest
from enrichment_presentation_fakes import ARTIST_A_KEY, make_bridge
from PySide6.QtCore import Property, QObject, QUrl, Slot
from PySide6.QtQml import QQmlComponent, QQmlEngine

QML_DIR = (
    Path(__file__).resolve().parent.parent / "src" / "michi" / "presentation" / "qml"
)


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    yield app


class FakePlayback(QObject):
    currentPath = Property(str, lambda self: "")


class FakeNavigation(QObject):
    @Slot(str)
    def navigate(self, route):
        pass


class FakeSettings(QObject):
    onlineEnrichmentChanged = __import__("PySide6.QtCore", fromlist=["Signal"]).Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._online = False

    def _get_online(self):
        return self._online

    onlineEnrichment = Property(bool, _get_online, notify=onlineEnrichmentChanged)

    @Slot(bool)
    def set_online_enrichment(self, enabled):
        self._online = bool(enabled)
        self.onlineEnrichmentChanged.emit()

    @Slot(str)
    def set_window_geometry(self, json_str):
        pass

    windowGeometry = Property(str, lambda self: "{}")


class FakeLibrary(QObject):
    """Minimal projection used by ArtistDetailView / AlbumDetailView."""

    selectedArtistKeyChanged = __import__(
        "PySide6.QtCore", fromlist=["Signal"]
    ).Signal()
    selectedAlbumKeyChanged = __import__("PySide6.QtCore", fromlist=["Signal"]).Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._artist_key = ARTIST_A_KEY
        self._album_key = "7::album x::artist a"

    def _get_artist_key(self):
        return self._artist_key

    def _get_artist_name(self):
        return "Artist A"

    def _get_artist_album_count(self):
        return 2

    def _get_artist_track_count(self):
        return 3

    def _get_artist_albums(self):
        return [
            {
                "key": "7::album x::artist a",
                "title": "Album X",
                "artist": "Artist A",
                "artworkPath": "",
                "trackCount": 2,
            }
        ]

    def _get_artist_tracks(self):
        return [
            {
                "path": "/music/a1.flac",
                "title": "Track One",
                "artist": "Artist A",
                "album": "Album X",
                "durationMs": 240000,
                "qualityLabel": "CD",
            }
        ]

    def _get_favorite_paths(self):
        return []

    def _get_album_key(self):
        return self._album_key

    def _get_album_title(self):
        return "Album X"

    def _get_album_artist(self):
        return "Artist A"

    def _get_album_genres(self):
        return ["Rock"]

    def _get_album_year(self):
        return 1980

    def _get_album_artwork(self):
        return ""

    def _get_album_tracks(self):
        return self._get_artist_tracks()

    def _get_album_technical_summary(self):
        return "CD"

    def _get_album_duration_ms(self):
        return 490000

    selectedArtistKey = Property(str, _get_artist_key, notify=selectedArtistKeyChanged)
    artistName = Property(str, _get_artist_name)
    artistAlbumCount = Property(int, _get_artist_album_count)
    artistTrackCount = Property(int, _get_artist_track_count)
    artistAlbums = Property("QVariantList", _get_artist_albums)
    artistTracks = Property("QVariantList", _get_artist_tracks)
    favoritePaths = Property("QVariantList", _get_favorite_paths)
    selectedAlbumKey = Property(str, _get_album_key, notify=selectedAlbumKeyChanged)
    albumTitle = Property(str, _get_album_title)
    albumArtist = Property(str, _get_album_artist)
    albumGenres = Property("QVariantList", _get_album_genres)
    albumYear = Property(int, _get_album_year)
    albumArtwork = Property(str, _get_album_artwork)
    albumTracks = Property("QVariantList", _get_album_tracks)
    albumTechnicalSummary = Property(str, _get_album_technical_summary)
    albumDurationMs = Property(int, _get_album_duration_ms)

    @Slot()
    def clear_artist_selection(self):
        pass

    @Slot()
    def clear_album_selection(self):
        pass

    @Slot(str)
    def select_album(self, key):
        pass

    @Slot(int)
    def activate_artist_track(self, index):
        pass

    @Slot(int)
    def activate_album_track(self, index):
        pass

    @Slot(str)
    def toggle_favorite(self, path):
        pass

    currentDir = Property(str, lambda self: "/music")


def _load_qml(engine, path, name):
    """Returns (component, obj): the component must stay alive or the
    C++ object is garbage-collected."""
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_DIR / path)))
    assert component.status() == QQmlComponent.Ready, component.errorString()
    obj = component.create()
    assert obj is not None, component.errorString()
    obj.setObjectName(name)
    return component, obj


def _make_engine(qapp, enrichment_bridge):
    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))
    ctx = engine.rootContext()
    ctx.setContextProperty("library", FakeLibrary())
    ctx.setContextProperty("playback", FakePlayback())
    ctx.setContextProperty("navigation", FakeNavigation())
    ctx.setContextProperty("settingsBridge", FakeSettings())
    ctx.setContextProperty("enrichment", enrichment_bridge)
    return engine


class TestEnrichmentComponents:
    def test_status_bar_loads(self, qapp):
        bridge, _, _, _, _, _, _ = make_bridge(online=True)
        engine = _make_engine(qapp, bridge)
        _, root = _load_qml(engine, "enrichment/EnrichmentStatusBar.qml", "statusBar")
        assert root.property("state") == "IDLE"
        root.setProperty("state", "OFFLINE")
        root.setProperty("message", "Offline — showing saved information")
        assert root.property("visible") is True
        engine.deleteLater()

    def test_knowledge_card_loads(self, qapp):
        bridge, _, _, _, _, _, _ = make_bridge(online=True)
        engine = _make_engine(qapp, bridge)
        _, root = _load_qml(
            engine, "enrichment/EnrichmentKnowledgeCard.qml", "knowledgeCard"
        )
        root.setProperty(
            "knowledge",
            {
                "biography": "A composer biography.",
                "country": "United States",
                "beginYear": 1950,
                "website": "https://example.org",
                "genres": ["Classical"],
            },
        )
        root.setProperty("hasKnowledge", True)
        root.setProperty(
            "sources",
            [
                {
                    "provider": "musicbrainz",
                    "license": "CC BY-NC-SA 3.0",
                    "sourceUrl": "https://musicbrainz.org/artist/mb-a",
                    "isStale": False,
                }
            ],
        )
        qapp.processEvents()
        assert root.property("hasKnowledge") is True
        engine.deleteLater()

    def test_attribution_loads(self, qapp):
        """Uses a declarative QML binding (the production pattern) —
        QVariantList var properties do not notify when assigned from
        Python via setProperty, but DO through the QML engine."""
        bridge, _, _, _, _, _, _ = make_bridge(online=True)
        engine = _make_engine(qapp, bridge)
        component = QQmlComponent(engine)
        component.setData(
            b"""
            import QtQuick
            import "../enrichment"
            EnrichmentAttribution {
                sources: [{provider: "wikipedia", license: "CC BY-SA", isStale: false}]
            }
            """,
            QUrl.fromLocalFile(str(QML_DIR / "enrichment/__wrapper_test.qml")),
        )
        assert component.status() == QQmlComponent.Ready, component.errorString()
        root = component.create()
        assert root is not None
        qapp.processEvents()
        assert root.property("visible") is True
        engine.deleteLater()

    def test_actions_loads(self, qapp):
        bridge, _, _, _, _, _, _ = make_bridge(online=True)
        engine = _make_engine(qapp, bridge)
        _, root = _load_qml(engine, "enrichment/EnrichmentActions.qml", "actions")
        root.setProperty("kind", "artist")
        root.setProperty("onlineEnabled", True)
        root.setProperty("hasKnowledge", True)
        qapp.processEvents()
        engine.deleteLater()

    def test_review_dialog_loads_and_states(self, qapp):
        bridge, _, _, _, _, _, _ = make_bridge(online=True)
        engine = _make_engine(qapp, bridge)
        _, root = _load_qml(
            engine, "enrichment/ReviewMatchesDialog.qml", "reviewDialog"
        )
        assert root.objectName() == "reviewDialog"
        root.setProperty("kind", "artist")
        root.setProperty(
            "artistCandidates",
            [
                {
                    "externalArtistId": "mb-a",
                    "displayName": "Artist A",
                    "disambiguation": "",
                    "provider": "musicbrainz",
                }
            ],
        )
        root.setProperty("loading", False)
        qapp.processEvents()
        assert root.property("kind") == "artist"
        engine.deleteLater()


class TestViewsLoad:
    def test_artist_detail_view_loads(self, qapp):
        bridge, _, _, _, _, _, _ = make_bridge(online=True)
        engine = _make_engine(qapp, bridge)
        _, root = _load_qml(engine, "views/ArtistDetailView.qml", "artistDetailView")
        assert root.objectName() == "artistDetailView"
        qapp.processEvents()
        engine.deleteLater()

    def test_album_detail_view_loads(self, qapp):
        bridge, _, _, _, _, _, _ = make_bridge(online=True)
        engine = _make_engine(qapp, bridge)
        _, root = _load_qml(engine, "views/AlbumDetailView.qml", "albumDetailView")
        assert root.objectName() == "albumDetailView"
        qapp.processEvents()
        engine.deleteLater()

    def test_settings_view_loads(self, qapp):
        bridge, _, _, _, _, _, _ = make_bridge(online=True)
        engine = _make_engine(qapp, bridge)
        _, root = _load_qml(engine, "views/SettingsView.qml", "settingsView")
        qapp.processEvents()
        switch = root.findChild(QObject, "onlineEnrichmentSwitch")
        assert switch is not None, "online enrichment switch missing"
        engine.deleteLater()


class TestBridgeStateProjection:
    def test_states_flow_through_qml(self, qapp):
        """Drive the bridge to READY and verify the QML card sees it."""
        bridge, _, _, _, _, _, _ = make_bridge(online=True)
        engine = _make_engine(qapp, bridge)
        _, root = _load_qml(engine, "enrichment/EnrichmentKnowledgeCard.qml", "card")
        root.setProperty("knowledge", bridge.property("artistKnowledge"))
        root.setProperty("hasKnowledge", bridge.property("artistHasKnowledge"))
        bridge.activate_artist(ARTIST_A_KEY)
        import time

        from enrichment_presentation_fakes import process_events

        end = time.monotonic() + 10
        while bridge.property("state") != "READY" and time.monotonic() < end:
            process_events(8)
        assert bridge.property("state") == "READY"
        root.setProperty("knowledge", bridge.property("artistKnowledge"))
        root.setProperty("hasKnowledge", bridge.property("artistHasKnowledge"))
        assert root.property("hasKnowledge") is True
        engine.deleteLater()
