"""PR #231 FINAL REVIEW SEAL — functional contract gates for the seven
open review threads (Codex). Every thread proved VALID against the code
before this file was written; each gate here pins the fixed contract.

P1-01 Songs → Playlist: the add-to-playlist intent is TrackId-FIRST (the
      A1 context host routes stable TrackIds through the Bridge; the path
      stays a factual location and never decides membership).
P1-02 Songs Properties action: the A1 context host provides the real
      consumer (LibraryContextActionHost → TrackPropertiesView). The
      SongsView FILE keeps the fail-closed default (canInspect: false) so
      a bare instance without the host never shows a dead action; the
      LibraryContentHost instance enables it only because the consumer is
      real.
P1-03 Add to New Playlist: no consumer exists repo-wide → the menu item
      must be hidden (no dead UI).
P1-04 Toolbar search placeholders must be qsTr-wrapped (localization).
P1-05 Source operation error chip: visible, inside the toolbar, on its own
      layout row — never overlapped by tabs/search/scan/enrich.
P1-06 Zoom 82/100/122 %: buttons update the SAME persistent preference
      authority the ComboBox uses (gallery/flow/vinyl by album mode) —
      single source of truth, survives reload and sibling preference edits.
P1-07 Artist portrait prefetch: bounded (queue <= 12, inflight <= 2) AND
      fair — every visible artist is eventually attempted, no duplicates,
      cached portraits never hit the network, Online OFF → zero work.
"""

import json
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import (  # noqa: F401
    Q_ARG,
    Property,
    QMetaObject,
    QObject,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest

QML_DIR = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"
EPSILON = 1.0


@pytest.fixture(scope="module")
def qapp():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    yield app


def _process(rounds=6):
    from PySide6.QtCore import QCoreApplication

    for _ in range(rounds):
        QCoreApplication.processEvents()


def _qml_source(relative_path):
    return (QML_DIR / relative_path).read_text(encoding="utf-8")


def _find_by_property(root, prop, value):
    """QQuickItem.childItems() traversal: ListView delegates are reachable
    through the visual tree but NOT through QObject.findChildren()."""
    from PySide6.QtQuick import QQuickItem

    def visit(item):
        try:
            if item.property(prop) == value:
                return item
        except RuntimeError:
            pass
        for child in item.childItems():
            found = visit(child)
            if found is not None:
                return found
        return None

    stack = [root] if isinstance(root, QQuickItem) else list(root.childItems())
    for item in stack:
        found = visit(item)
        if found is not None:
            return found
    return None


def _wait_for_property(root, prop, value, rounds=24):
    """ListView instantiates delegates lazily (and only after real
    frames); wait with a real event-loop spin until the delegate
    materializes."""
    for _ in range(rounds):
        found = _find_by_property(root, prop, value)
        if found is not None:
            return found
        QTest.qWait(50)
    return None


# ---------------------------------------------------------------------------
# Fake QML surfaces (minimal, honest: only properties the toolbar/view reads)
# ---------------------------------------------------------------------------


class _FakeLibrary(QObject):
    changed = Signal()

    def __init__(self, rows=None):
        super().__init__()
        self._rows = rows or []
        self._error = ""

    # Toolbar / ContentHost surfaces
    fileCount = Property(int, lambda self: 0)
    libraryTrackCount = Property(int, lambda self: 0)
    albumCount = Property(int, lambda self: 0)
    scanActive = Property(bool, lambda self: False)
    scanStatus = Property(str, lambda self: "")
    configuredSourceCount = Property(int, lambda self: 1)
    searchActive = Property(bool, lambda self: False)
    searchTotalCount = Property(int, lambda self: 0)
    searchQuery = Property(str, lambda self: "")
    scanProcessed = Property(int, lambda self: 0)
    scanTotal = Property(int, lambda self: 0)
    scanProgress = Property(float, lambda self: 0.0)
    scanCurrentPath = Property(str, lambda self: "")
    hasConfiguredSources = Property(bool, lambda self: True)
    hasScannableSources = Property(bool, lambda self: False)
    # Songs surface
    songRows = Property("QVariantList", lambda self: self._rows, notify=changed)
    favoriteTrackIds = Property("QVariantList", lambda self: [])
    favoritePaths = Property("QVariantList", lambda self: [])
    canQueueTracks = Property(bool, lambda self: True)
    canAddTracksToPlaylists = Property(bool, lambda self: True)
    trackSortColumn = Property(str, lambda self: "")
    trackSortDescending = Property(bool, lambda self: False)

    sourceOperationError = Property(str, lambda self: self._error, notify=changed)

    def __init__(self, rows=None):
        super().__init__()
        self._rows = rows or []
        self._error = ""
        self.playlist_target_calls: list = []

    @Slot(list)
    def request_tracks_playlist_target(self, track_ids):
        self.playlist_target_calls.append(list(track_ids))

    def set_error(self, text):
        self._error = text
        self.changed.emit()


class _FakeEnrichment(QObject):
    changed = Signal()
    onlineEnabled = Property(bool, lambda self: False, notify=changed)
    enrichmentJobState = Property(str, lambda self: "IDLE", notify=changed)
    enrichmentJobProcessed = Property(int, lambda self: 0, notify=changed)
    enrichmentJobTotal = Property(int, lambda self: 0, notify=changed)


class _FakePlayback(QObject):
    currentPath = Property(str, lambda self: "")


class _FakePlaylists(QObject):
    playlists = Property("QVariantList", lambda self: [])


class _FakeSettings(QObject):
    changed = Signal()
    _raw = ""

    def __init__(self, raw=""):
        super().__init__()
        self._raw = raw
        self.saved = []

    libraryViews = Property(str, lambda self: self._raw, notify=changed)

    @Slot(str)
    def set_library_views(self, raw):
        self._raw = raw
        self.saved.append(raw)
        self.changed.emit()


def _track_row(track_id, path, title="Song"):
    return {
        "trackId": track_id,
        "path": path,
        "title": title,
        "displayName": title,
        "artist": "Artist",
        "artistKey": "artist",
        "album": "Album",
        "albumKey": "album",
        "durationMs": 120000,
        "artworkPath": "",
        "formatKey": "flac",
        "formatLabel": "FLAC",
        "codec": "flac",
        "container": "flac",
        "dsdRate": "",
        "sampleRateHz": 44100,
        "bitDepth": 16,
        "bitrateBps": 800000,
        "channels": 2,
        "fileSize": 1000,
        "genre": "",
        "composer": "",
        "year": 2020,
        "unavailable": False,
    }


_KEEP = []


def _mount(qml_file, library=None, settings=None, width=1440, height=900):
    view = QQuickView()
    view.engine().addImportPath(str(QML_DIR))
    ctx = view.rootContext()
    library_obj = library if library is not None else _FakeLibrary()
    enrichment = _FakeEnrichment()
    playback = _FakePlayback()
    playlists = _FakePlaylists()
    ctx.setContextProperty("library", library_obj)
    ctx.setContextProperty("enrichment", enrichment)
    ctx.setContextProperty("playback", playback)
    ctx.setContextProperty("playlists", playlists)
    if settings is not None:
        ctx.setContextProperty("settingsBridge", settings)
    _KEEP.extend((library_obj, enrichment, playback, playlists))
    view.setSource(QUrl.fromLocalFile(str(QML_DIR / qml_file)))
    assert view.status() == QQuickView.Ready, [e.toString() for e in view.errors()]
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(width, height)
    view.show()
    QTest.qWait(40)
    return view


def _no_overlap(a, b):
    if a is None or b is None:
        return True
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (
        ax + aw <= bx + EPSILON
        or bx + bw <= ax + EPSILON
        or (ay + ah <= by + EPSILON or by + bh <= ay + EPSILON)
    )


def _geometry(obj):
    return obj.x(), obj.y(), obj.width(), obj.height()


# ===========================================================================
# P1-01 — Songs → Playlist transports TrackId-first (A1 context host)
# ===========================================================================


def test_table_playlist_signal_carries_track_id_and_path(qapp):
    """Contract of the wire: MichiTrackTable.addToPlaylistRequested carries
    (trackId, path); the delegate forwards trackId + modelData.path; SongsView
    routes the STABLE TrackId into the Bridge targeting seam
    (request_tracks_playlist_target) while the path remains factual."""
    table = _qml_source("media/MichiTrackTable.qml")
    songs = _qml_source("views/SongsView.qml")

    assert re.search(
        r"signal addToPlaylistRequested\(string trackId, string path\)", table
    ), "la señal de la tabla debe transportar trackId Y path"
    assert re.search(
        r"onAddToPlaylistRequested:\s*root\.addToPlaylistRequested\(\s*"
        r"trackId, modelData\.path\)",
        table,
    ), "el delegate debe reenviar el path factual del modelData"
    assert re.search(
        r"onAddToPlaylistRequested:\s*\(trackId, path\)\s*=>\s*"
        r"library\.request_tracks_playlist_target\(\[trackId\]\)",
        songs,
    ), "SongsView debe rutear el TrackId estable al seam de targeting"
    # El path nunca decide membership en el flujo nuevo.
    assert "addTargetPath = path" not in songs, (
        "el flujo A1 no alimenta el targeting legacy por path"
    )
    # TrackId nunca se degrada: activación/favoritos/cola siguen por trackId.
    assert (
        "onTrackActivated: (trackId, path, index) =>"
        " library.activate_track_by_id(trackId)" in songs
    )
    assert (
        "onFavoriteRequested: trackId => library.toggle_favorite_by_id(trackId)"
        in songs
    )


def test_songs_add_to_playlist_runtime_routes_stable_track_id(qapp):
    """Runtime: pressing Add to Playlist on a catalog-backed row (stable
    TrackId UUID + factual path) must invoke the Bridge targeting seam with
    the TrackId — never the path (membership identity)."""
    row = _track_row("uuid-123", "/music/a.flac")
    library = _FakeLibrary(rows=[row])
    library.playlist_target_calls = []
    view = _mount("views/SongsView.qml", library=library)
    root = view.rootObject()

    rows = root.property("rows") or []
    assert len(rows) == 1, f"filas en la tabla (vio {len(rows)})"
    track_row = _wait_for_property(root, "trackId", "uuid-123")
    assert track_row is not None, "delegate TrackRow instanciado"
    assert track_row.property("filePath") == "/music/a.flac"

    mo = track_row.metaObject()
    idx = mo.indexOfMethod("addToPlaylistRequested()")
    assert idx >= 0
    mo.method(idx).invoke(track_row)
    _process()

    assert library.playlist_target_calls == [["uuid-123"]], (
        "el seam recibe el TrackId estable, nunca el path"
    )
    # El targeting legacy por path ya no se alimenta desde Songs.
    assert root.property("addTargetPath") == "", (
        "addTargetPath debe permanecer vacío en el flujo A1"
    )
    view.close()


# ===========================================================================
# P1-02 — Properties action must not exist without an inspector surface
# ===========================================================================


def test_songs_properties_action_disabled_until_inspector_exists(qapp):
    """The SongsView FILE stays fail-closed (canInspect: false): a bare
    instance without the A1 context host never offers a dead Properties
    action. LibraryContentHost enables it only because the consumer
    (context host → TrackPropertiesView) is real — see the A1 runtime
    seal."""
    row = _track_row("uuid-1", "/music/a.flac")
    view = _mount("views/SongsView.qml", library=_FakeLibrary(rows=[row]))
    root = view.rootObject()
    assert root.property("canInspect") is False, (
        "el archivo SongsView no ofrece Properties sin consumer (A1 host)"
    )
    track_row = _wait_for_property(root, "trackId", "uuid-1")
    assert track_row is not None
    assert track_row.property("showInspector") is False
    view.close()


# ===========================================================================
# P1-03 — Add to New Playlist hidden while no consumer exists
# ===========================================================================


def test_add_to_new_playlist_item_hidden_without_consumer():
    """Repo-wide there is no consumer for new_playlist_target_requested /
    request_new_playlist_for_tracks wiring, so the menu item must be gated
    behind a capability that nothing enables (no dead UI)."""
    menu = _qml_source("media/TrackContextMenu.qml")
    assert re.search(r"property bool canAddToNewPlaylist: false", menu), (
        "capacidad desactivada por defecto"
    )
    assert re.search(
        r"visible: root\.canAddToPlaylist && root\.canAddToNewPlaylist",
        menu,
    ), "el item Add to New Playlist debe requerir la capacidad"
    # Ningún surface productivo la activa hoy (no hay consumer).
    for qml_file in Path(QML_DIR).rglob("*.qml"):
        src = qml_file.read_text(encoding="utf-8", errors="ignore")
        assert "canAddToNewPlaylist: true" not in src, (
            f"{qml_file.name} activa una acción sin consumer"
        )


# ===========================================================================
# P1-04 — Toolbar search placeholders translated
# ===========================================================================


def test_toolbar_search_placeholders_are_translated():
    toolbar = _qml_source("views/LibraryToolbar.qml")
    match = re.search(r"function searchPlaceholder\(\) \{(.*?)\n    \}", toolbar, re.S)
    assert match, "searchPlaceholder() presente"
    body = match.group(1)
    returns = re.findall(r"return (.+)$", body, re.M)
    assert returns, "hay returns en searchPlaceholder"
    for statement in returns:
        assert statement.strip().startswith("qsTr("), (
            f"placeholder sin qsTr: {statement.strip()!r}"
        )


# ===========================================================================
# P1-05 — Source operation error chip: own layout row, never overlapped
# ===========================================================================


def test_source_error_chip_visible_inside_toolbar_no_overlap(qapp):
    """With a real error present the chip must be visible, inside the toolbar
    bounds and NOT overlapped by LibraryTabs/Search/Scan/Enrich at any of the
    four canonical widths."""
    for width in (1920, 1440, 1200, 900):
        library = _FakeLibrary()
        view = _mount(
            "views/LibraryToolbar.qml", library=library, width=width, height=400
        )
        root = view.rootObject()
        # El rootObject ES el MichiGlassSurface del toolbar.
        toolbar = root
        assert toolbar.property("objectName") == "libraryToolbar"

        library.set_error("Test source error")
        QTest.qWait(20)

        chip = root.findChild(QObject, "librarySourceErrorChip")
        if chip is None:
            chip = _find_by_property(root, "objectName", "librarySourceErrorChip")
        assert chip is not None, f"{width}: chip presente"
        assert chip.property("visible") is True, f"{width}: chip visible"
        assert chip.property("text") == "Test source error"

        cg = _geometry(chip)
        tg = _geometry(toolbar)
        assert cg[0] >= 0 and cg[1] >= 0, f"{width}: chip dentro (x/y)"
        assert cg[0] + cg[2] <= tg[0] + tg[2] + EPSILON, f"{width}: dentro ancho"
        assert cg[1] + cg[3] <= tg[1] + tg[3] + EPSILON, f"{width}: dentro alto"

        for name, object_name in (
            ("tabs", "libraryTabs"),
            ("search", "resizableLibrarySearchPane"),
            ("scan", "libraryScanSplitButton"),
            ("enrich", "libraryEnrichButton"),
        ):
            other = root.findChild(QObject, object_name)
            if other is None or not other.property("visible"):
                continue
            og = _geometry(other)
            assert not _overlap_rects(cg, og), (
                f"{width}: chip NO se solapa con {name} (chip {cg} vs {name} {og})"
            )
        view.close()


def _overlap_rects(a, b):
    """True when a and b share area (used when both must be disjoint)."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay)


def test_source_error_chip_is_a_layout_row_not_a_floating_sibling(qapp):
    """The chip must live INSIDE toolbarContent's ColumnLayout (own row) —
    declared before the navigation grid, not anchored over sibling controls."""
    toolbar = _qml_source("views/LibraryToolbar.qml")
    content_start = toolbar.index("ColumnLayout {")
    chip_idx = toolbar.index("librarySourceErrorChip")
    grid_idx = toolbar.index("libraryNavigationGrid")
    assert chip_idx > content_start, "chip dentro del ColumnLayout"
    assert chip_idx < grid_idx, "chip declarado ANTES del navigation grid"


# ===========================================================================
# P1-06 — Zoom buttons update the persistent preference authority
# ===========================================================================


def _default_prefs_json():
    return json.dumps(
        {
            "activeMode": "grid",
            "sortMode": "title",
            "sortDescending": False,
            "filterMode": "all",
            "gallery": {
                "artworkSize": "medium",
                "spacing": "balanced",
                "metadataLevel": "standard",
                "precisionMetadata": False,
                "quickActions": True,
                "inspector": True,
            },
            "flow": {
                "coverSize": "standard",
                "visibleAlbums": "auto",
                "depth": "standard",
                "ambientColor": True,
                "metadataLevel": "standard",
            },
            "vinyl": {
                "sleeveSize": "standard",
                "spacing": "standard",
                "reveal": "standard",
                "metadataLevel": "standard",
                "artworkLabel": True,
                "inspector": True,
            },
            "chronology": {
                "grouping": "decade",
                "direction": "newest",
                "density": "standard",
                "metadataLevel": "standard",
                "showPeriodDensity": False,
            },
            "editorial": {
                "heroVisible": True,
                "informationRichness": "standard",
                "cachedEnrichmentVisible": True,
                "archiveLayout": "list",
            },
            "studioList": {
                "density": "standard",
                "artworkSize": "small",
                "metadataLevel": "standard",
                "precisionMetadata": True,
                "inspector": True,
                "artistColumn": True,
                "yearColumn": True,
                "tracksColumn": True,
                "durationColumn": True,
                "formatColumn": True,
            },
        }
    )


def _zoom(view_root, value):
    ok = QMetaObject.invokeMethod(
        view_root, "requestAlbumZoom", Q_ARG("QVariant", float(value))
    )
    assert ok, "requestAlbumZoom invocable"
    QTest.qWait(20)


def _album_mode(view_root, mode):
    ok = QMetaObject.invokeMethod(
        view_root, "requestAlbumMode", Q_ARG("QVariant", mode)
    )
    assert ok, f"requestAlbumMode({mode}) invocable"
    QTest.qWait(20)


def test_zoom_buttons_update_persistent_preference_authority(qapp):
    """82/100/122 % must write the SAME preference the ComboBox reads
    (gallery.artworkSize in grid mode) — the persisted JSON is the single
    source of truth; albumZoom is only its projection. A sibling gallery
    preference change must NOT revert the zoom, and a fresh view must
    restore it."""
    settings = _FakeSettings(_default_prefs_json())
    view = _mount("views/LibraryView.qml", settings=settings)
    root = view.rootObject()
    root.setProperty("currentTab", "albums")
    _process()
    assert root.property("albumMode") == "grid"
    assert abs(root.property("albumZoom") - 1.0) < 1e-6

    # zoom-out → 82 %
    _zoom(root, 0.82)
    assert abs(root.property("albumZoom") - 0.82) < 1e-6
    prefs = json.loads(settings._raw)
    assert prefs["gallery"]["artworkSize"] == "small"
    # 100 %
    _zoom(root, 1.0)
    assert abs(root.property("albumZoom") - 1.0) < 1e-6
    assert json.loads(settings._raw)["gallery"]["artworkSize"] == "medium"
    # 122 %
    _zoom(root, 1.22)
    assert abs(root.property("albumZoom") - 1.22) < 1e-6
    assert json.loads(settings._raw)["gallery"]["artworkSize"] == "large"

    # Volver a 82 % y cambiar OTRA opción de gallery: el zoom NO revierte.
    _zoom(root, 0.82)
    ok = QMetaObject.invokeMethod(
        root,
        "updateViewPreference",
        Q_ARG("QVariant", "gallery"),
        Q_ARG("QVariant", "spacing"),
        Q_ARG("QVariant", "relaxed"),
    )
    assert ok
    QTest.qWait(20)
    assert abs(root.property("albumZoom") - 0.82) < 1e-6, (
        "cambio de otra opción de gallery no puede revertir el zoom"
    )
    prefs = json.loads(settings._raw)
    assert prefs["gallery"]["spacing"] == "relaxed"
    assert prefs["gallery"]["artworkSize"] == "small"
    view.close()

    # Reload: un view nuevo con la MISMA preferencia persiste el zoom.
    view2 = _mount("views/LibraryView.qml", settings=settings)
    root2 = view2.rootObject()
    root2.setProperty("currentTab", "albums")
    _process()
    assert abs(root2.property("albumZoom") - 0.82) < 1e-6, (
        "tras recrear la vista el zoom se restaura desde la preferencia"
    )
    view2.close()


def test_zoom_respects_album_mode_preference_authority(qapp):
    """En cover mode la autoridad es flow.coverSize (small/standard/large):
    el botón 82 % persiste 'small' en flow, no en gallery."""
    settings = _FakeSettings(_default_prefs_json())
    view = _mount("views/LibraryView.qml", settings=settings)
    root = view.rootObject()
    root.setProperty("currentTab", "albums")
    _process()
    _album_mode(root, "cover")
    assert abs(root.property("albumZoom") - 1.0) < 1e-6
    _zoom(root, 0.82)
    assert abs(root.property("albumZoom") - 0.82) < 1e-6
    prefs = json.loads(settings._raw)
    assert prefs["flow"]["coverSize"] == "small"
    assert prefs["gallery"]["artworkSize"] == "medium", "grid authority intacta"
    view.close()


# ===========================================================================
# P1-07 — Portrait prefetch: bounded AND fair
# ===========================================================================


class _HoldingCoordinator:
    """Wraps the real coordinator and parks every enrich_artist call so the
    bridge stays mid-flight while the test inspects queue/inflight."""

    def __init__(self, inner):
        self.inner = inner
        self.artist_calls = []

    def __getattr__(self, name):
        return getattr(self.inner, name)

    def enrich_artist(self, artist, albums, tracks, on_state=None):
        self.artist_calls.append((artist.key, on_state))


def _prefetch_gate_fixture(online=True):
    from enrichment_presentation_fakes import make_bridge
    from test_m6_9_presentation_bridge import _populate_artist

    bridge, service, _, repo, store, coordinator, _ = make_bridge(online=online)
    holding = _HoldingCoordinator(coordinator)
    bridge._coordinator = holding
    return bridge, service, repo, store, holding, _populate_artist


def _release_inflight(bridge, rounds=80):
    from michi.application.enrichment_coordinator import EnrichmentOperationState

    for _ in range(rounds):
        inflight = list(bridge._portrait_prefetch_inflight)
        if not inflight and not bridge._portrait_prefetch_queue:
            break
        for key in inflight:
            bridge._relay.portrait_event_received.emit(
                SimpleNamespace(
                    state=EnrichmentOperationState.READY, local_entity_key=key
                )
            )
        _process(4)
    else:
        raise AssertionError("prefetch queue/inflight never drained")


def test_portrait_prefetch_eventually_covers_all_visible_artists(qapp):
    """20 visible artists fed in repeated batches: every eligible key is
    eventually attempted, no duplicates, queue <= 12, inflight <= 2,
    cached portrait resolved without any enrich call (no network)."""
    from dataclasses import replace

    from michi.domain.enrichment import (
        EnrichmentAssetRecord,
        EnrichmentEntityKind,
    )

    bridge, service, repo, store, holding, populate = _prefetch_gate_fixture(
        online=True
    )
    keys = [f"visible-{index}" for index in range(20)]
    for index, key in enumerate(keys):
        populate(service, key, f"Artist {index}", f"mb-{index}")

    # Último artista con portada ya cacheada (perfil + asset) → cache hit.
    cached_key = keys[19]
    profile = service.get_artist_knowledge(cached_key)
    assert profile is not None
    store.store(
        EnrichmentAssetRecord(
            asset_id="art-cache",
            entity_kind=EnrichmentEntityKind.ARTIST,
            external_entity_id="mb-19",
            mime_type="image/jpeg",
            provider="wikimedia-commons",
        ),
        b"portrait",
    )
    repo.save_artist_profile(replace(profile, artwork_asset_id="art-cache"))

    max_queue = 0
    max_inflight = 0

    def sample():
        nonlocal max_queue, max_inflight
        max_queue = max(max_queue, len(bridge._portrait_prefetch_queue))
        max_inflight = max(max_inflight, len(bridge._portrait_prefetch_inflight))

    for _ in range(4):
        bridge.prefetch_artist_portraits(keys)
        sample()
        _release_inflight(bridge)
        sample()

    attempted = set(bridge._portrait_prefetch_attempted)
    portraits = bridge.property("artistPortraits") or {}
    missing = {key for key in keys if key not in attempted and key not in portraits}
    assert not missing, (
        "todo artista visible es intentado (network) o resuelto (cache); "
        f"faltan: {sorted(missing)}"
    )
    # El cacheado no es elegible de red: nunca en attempted.
    assert cached_key not in attempted
    called_keys = [key for key, _ in holding.artist_calls]
    assert len(called_keys) == len(set(called_keys)), "sin requests duplicados"
    assert cached_key not in called_keys, "portada cacheada resuelta sin trabajo de red"
    portraits = bridge.property("artistPortraits") or {}
    assert portraits.get(cached_key, "").endswith("art-cache")
    assert max_queue <= 12, f"queue bounded <= 12 (vio {max_queue})"
    assert max_inflight <= 2, f"inflight bounded <= 2 (vio {max_inflight})"


def test_portrait_prefetch_offline_does_zero_work(qapp):
    """Online OFF → el batch no intenta ningún artista (cero red, cero
    coordinator work, nada en cola ni inflight)."""
    bridge, _, _, _, holding, _ = _prefetch_gate_fixture(online=False)
    keys = [f"visible-{index}" for index in range(20)]
    bridge.prefetch_artist_portraits(keys)
    _process(6)
    assert holding.artist_calls == []
    assert bridge._portrait_prefetch_queue == []
    assert bridge._portrait_prefetch_inflight == set()
    assert bridge._portrait_prefetch_attempted == set()
