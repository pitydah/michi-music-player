"""Smoke the INSTALLED wheel with productive QML instantiation (V4 §22CU).

- QML is read from the installed package (never repository source);
- every productive component in the required list must COMPILE and
  INSTANTIATE from the installed tree;
- context-dependent components use minimal fake QObjects;
- any Qt warning/error raised while instantiating fails the smoke.

Run with `python -I` from a directory outside the repository so no
repository file leaks into the import path.
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import (  # noqa: E402  # noqa: E402
    Property,
    QObject,
    QtMsgType,
    Signal,
    qInstallMessageHandler,
)
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlComponent, QQmlEngine  # noqa: E402

import michi  # noqa: E402

_QML_WARNINGS: list[str] = []
_CURRENT: list[str] = [""]


def _handler(msg_type, context, message):
    if msg_type in (
        QtMsgType.QtWarningMsg,
        QtMsgType.QtCriticalMsg,
        QtMsgType.QtFatalMsg,
    ):
        _QML_WARNINGS.append(f"[{_CURRENT[0]}] {message}")


def _changed(self=None):
    return None


class _Signal(QObject):
    changed = Signal()


def _obj(props: dict) -> QObject:
    """QObject con properties QML-facing (lectura) a partir de un dict."""

    class _Fake(QObject):
        pass

    fake = _Fake()
    for name, value in props.items():
        setattr(
            type(fake), name, Property(type(value), (lambda v: lambda self: v)(value))
        )
    return fake


class _Library(QObject):
    """Fake mínimo del LibraryBridge: cubre los bindings iniciales de las
    vistas productivas del smoke. Una sola clase con todas las properties
    en un bloque (los type de Shiboken se construyen con el namespace)."""

    changed = Signal()

    def __init__(self):
        super().__init__()

    libraryTrackCount = Property(int, lambda self: 0, notify=changed)
    fileCount = Property(int, lambda self: 0, notify=changed)
    albumCount = Property(int, lambda self: 0, notify=changed)
    artistCount = Property(int, lambda self: 0, notify=changed)
    genreCount = Property(int, lambda self: 0, notify=changed)
    searchActive = Property(bool, lambda self: False, notify=changed)
    searchQuery = Property(str, lambda self: "", notify=changed)
    searchTotalCount = Property(int, lambda self: 0, notify=changed)
    searchTrackCount = Property(int, lambda self: 0, notify=changed)
    searchAlbumCount = Property(int, lambda self: 0, notify=changed)
    searchArtistCount = Property(int, lambda self: 0, notify=changed)
    searchGenreCount = Property(int, lambda self: 0, notify=changed)
    scanStatus = Property(str, lambda self: "", notify=changed)
    scanProcessed = Property(int, lambda self: 0, notify=changed)
    scanTotal = Property(int, lambda self: 0, notify=changed)
    scanCurrentPath = Property(str, lambda self: "", notify=changed)
    hasDiagnostic = Property(bool, lambda self: False, notify=changed)
    diagnosticMessage = Property(str, lambda self: "", notify=changed)
    genreFilterActive = Property(bool, lambda self: False, notify=changed)
    selectedGenreName = Property(str, lambda self: "", notify=changed)
    canQueueTracks = Property(bool, lambda self: True, notify=changed)
    canAddTracksToPlaylists = Property(bool, lambda self: True, notify=changed)
    selectedAlbumKey = Property(str, lambda self: "", notify=changed)
    selectedArtistKey = Property(str, lambda self: "", notify=changed)
    artistName = Property(str, lambda self: "Artist", notify=changed)
    artistAlbumCount = Property(int, lambda self: 0, notify=changed)
    artistTrackCount = Property(int, lambda self: 0, notify=changed)
    artistAlbums = Property(list, lambda self: [], notify=changed)
    albumTitle = Property(str, lambda self: "Album", notify=changed)
    albumArtist = Property(str, lambda self: "", notify=changed)
    albumArtwork = Property(str, lambda self: "", notify=changed)
    albumTechnicalSummary = Property(str, lambda self: "", notify=changed)
    albumGenre = Property(str, lambda self: "", notify=changed)
    albumFacts = Property("QVariantMap", lambda self: {}, notify=changed)
    configuredSourceCount = Property(int, lambda self: 1, notify=changed)
    sourceOperationError = Property(str, lambda self: "", notify=changed)
    libraryMode = Property(str, lambda self: "songs", notify=changed)
    albumMode = Property(str, lambda self: "grid", notify=changed)
    songRows = Property(list, lambda self: [], notify=changed)
    albumTracks = Property(list, lambda self: [], notify=changed)
    artistTracks = Property(list, lambda self: [], notify=changed)
    favoriteTrackRows = Property(list, lambda self: [], notify=changed)
    historyTrackRows = Property(list, lambda self: [], notify=changed)
    recentlyAddedTrackRows = Property(list, lambda self: [], notify=changed)
    albums = Property(list, lambda self: [], notify=changed)
    artists = Property(list, lambda self: [], notify=changed)
    genres = Property(list, lambda self: [], notify=changed)
    favoriteTrackIds = Property(list, lambda self: [], notify=changed)
    favoritePaths = Property(list, lambda self: [], notify=changed)
    trackSortColumn = Property(str, lambda self: "", notify=changed)
    trackSortDescending = Property(bool, lambda self: False, notify=changed)
    hasConfiguredSources = Property(bool, lambda self: True, notify=changed)
    hasScannableSources = Property(bool, lambda self: False, notify=changed)


class _Playback(QObject):
    changed = Signal()
    status = Property(str, lambda self: "stopped", notify=changed)
    currentPath = Property(str, lambda self: "", notify=changed)
    hasPrevious = Property(bool, lambda self: False, notify=changed)
    hasNext = Property(bool, lambda self: False, notify=changed)


class _Playlists(QObject):
    changed = Signal()
    playlists = Property(list, lambda self: [], notify=changed)
    searchPlaylistCount = Property(int, lambda self: 0, notify=changed)


class _Enrichment(QObject):
    changed = Signal()
    onlineEnabled = Property(bool, lambda self: False, notify=changed)
    enrichmentJobState = Property(str, lambda self: "IDLE", notify=changed)
    artistArtworkPath = Property(str, lambda self: "", notify=changed)
    albumArtworkPath = Property(str, lambda self: "", notify=changed)
    state = Property(str, lambda self: "IDLE", notify=changed)
    stateMessage = Property(str, lambda self: "", notify=changed)
    busy = Property(bool, lambda self: False, notify=changed)
    activeKind = Property(str, lambda self: "", notify=changed)
    artistKnowledge = Property("QVariantMap", lambda self: {}, notify=changed)
    artistHasKnowledge = Property(bool, lambda self: False, notify=changed)
    artistAttributions = Property(list, lambda self: [], notify=changed)
    albumKnowledge = Property("QVariantMap", lambda self: {}, notify=changed)
    albumHasKnowledge = Property(bool, lambda self: False, notify=changed)
    albumAttributions = Property(list, lambda self: [], notify=changed)
    reviewOpen = Property(bool, lambda self: False, notify=changed)
    reviewKind = Property(str, lambda self: "", notify=changed)
    reviewLoading = Property(bool, lambda self: False, notify=changed)
    reviewError = Property(str, lambda self: "", notify=changed)
    artistCandidates = Property(list, lambda self: [], notify=changed)
    albumArtwork = Property(str, lambda self: "", notify=changed)
    albumArtist = Property(str, lambda self: "", notify=changed)
    albumTechnicalSummary = Property(str, lambda self: "", notify=changed)
    albumGenre = Property(str, lambda self: "", notify=changed)
    sourceOperationError = Property(str, lambda self: "", notify=changed)
    scanCurrentPath = Property(str, lambda self: "", notify=changed)
    libraryMode = Property(str, lambda self: "songs", notify=changed)
    albumMode = Property(str, lambda self: "grid", notify=changed)
    timelineGrouping = Property(str, lambda self: "decade", notify=changed)
    sourceState = Property(str, lambda self: "idle", notify=changed)
    canOpenArtistPortrait = Property(bool, lambda self: False, notify=changed)
    searchActive = Property(bool, lambda self: False, notify=changed)


_INSTANTIATED: list = []


def _instantiate(engine, qml_root, relative: str) -> bool:
    _CURRENT[0] = relative
    path = qml_root / relative
    component = QQmlComponent(engine, str(path))
    if component.status() != QQmlComponent.Ready:
        raise RuntimeError(
            f"{relative}: compile failed: "
            f"{'; '.join(e.toString() for e in component.errors())}"
        )
    root = component.create()
    if root is None:
        raise RuntimeError(f"{relative}: could not instantiate")
    _INSTANTIATED.append((root, component))
    return True


def _teardown():
    """Destrucción ordenada: roots primero (engine vivo), luego engines."""
    for root, component in reversed(_INSTANTIATED):
        try:
            root.deleteLater()
        except RuntimeError:
            pass
        del component
    from PySide6.QtCore import QCoreApplication

    for _ in range(6):
        QCoreApplication.processEvents()
    _INSTANTIATED.clear()


def main() -> int:
    app = QGuiApplication.instance() or QGuiApplication([])
    qml_root = Path(michi.__file__).resolve().parent / "presentation" / "qml"

    library = _Library()
    playback = _Playback()
    playlists = _Playlists()
    enrichment = _Enrichment()

    required = (
        "views/LibraryView.qml",
        "primitives/MichiMaterial.qml",
        "controls/MichiMenu.qml",
        "controls/MichiScrollBar.qml",
        "enrichment/EnrichmentStatusBar.qml",
        "enrichment/EnrichmentKnowledgeCard.qml",
        "enrichment/ReviewMatchesDialog.qml",
        "views/LibraryHeader.qml",
        "views/LibraryToolbar.qml",
        "views/ArtistDetailView.qml",
        "views/AlbumDetailView.qml",
        "patterns/SearchOverlay.qml",
    )
    missing = [relative for relative in required if not (qml_root / relative).is_file()]
    if missing:
        raise RuntimeError(f"wheel is missing resources: {missing}")

    qInstallMessageHandler(_handler)
    try:
        # Sin contexto (compilación + instanciación puras).
        for relative in (
            "controls/MichiMenu.qml",
            "controls/MichiScrollBar.qml",
            "primitives/MichiMaterial.qml",
        ):
            engine = QQmlEngine()
            engine.addImportPath(str(qml_root))
            _instantiate(engine, qml_root, relative)
            engine.deleteLater()

        # Context-dependent: fakes mínimos en el contexto del engine.
        engine = QQmlEngine()
        engine.addImportPath(str(qml_root))
        ctx = engine.rootContext()
        ctx.setContextProperty("library", library)
        ctx.setContextProperty("playback", playback)
        ctx.setContextProperty("playlists", playlists)
        ctx.setContextProperty("enrichment", enrichment)
        ctx.setContextProperty("navigation", _obj({}))
        ctx.setContextProperty("queue", _obj({}))
        ctx.setContextProperty("settingsBridge", _obj({}))
        ctx.setContextProperty("playbackSession", _obj({}))
        ctx.setContextProperty("window", _obj({}))
        for relative in (
            "enrichment/EnrichmentStatusBar.qml",
            "enrichment/EnrichmentKnowledgeCard.qml",
            "enrichment/ReviewMatchesDialog.qml",
            "views/LibraryHeader.qml",
            "views/LibraryToolbar.qml",
            "views/ArtistDetailView.qml",
            "views/AlbumDetailView.qml",
            "patterns/SearchOverlay.qml",
        ):
            _instantiate(engine, qml_root, relative)
            app.processEvents()
        _teardown()
        engine.deleteLater()
        for _ in range(6):
            app.processEvents()
    finally:
        # El handler queda instalado hasta el exit: los warnings del
        # teardown final del proceso se absorben (stderr limpio) y no
        # alteran el PASS.
        pass

    if _QML_WARNINGS:
        print("Installed-wheel QML smoke raised warnings:")
        for warning in _QML_WARNINGS[:10]:
            print(f"  {warning}")
        return 1
    print(
        f"Installed-wheel productive QML smoke PASS ({len(required)} "
        "components from the installed package)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
