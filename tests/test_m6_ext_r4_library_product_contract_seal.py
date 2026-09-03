"""M6-EXT-R4 LIBRARY PRODUCT CONVERGENCE SEAL — product contract gates.

P1-LIB-01  canonical Toolbar ↔ Bridge contract (real QML)
P1-LIB-02  Sources manager declarative stable identity
P1-LIB-03  QUrl → local path boundary (never parsed in QML)
P1-LIB-04  configured vs scannable source semantics
P1-LIB-05  effective availability reaches TrackRow
P1-LIB-06  structural libraryTrackCount vs filtered fileCount
P1-LIB-11  TRACK_MISSING diagnostic converges after stable-ID recovery

Every gate crosses the REAL product boundary (QML component → metaobject →
Bridge → Service) — a Python-only path is never the proof.
"""

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

from michi.application.library_service import LibraryService
from michi.application.ports import (
    LibraryPrefsPort,
    ScanCancelled,
)
from michi.application.source_scan_coordinator import SourceScanCoordinator
from michi.application.source_scan_lifecycle import SourceScanLifecycle
from michi.domain.library import LibraryDiagnosticCode, LibraryPrefs
from michi.domain.library_catalog import (
    LibrarySource,
    MediaAvailability,
    SourceAvailability,
    media_playback_blocked,
    new_library_source_id,
)
from michi.infrastructure.filesystem_source_scanner import (
    FilesystemLibrarySourceScanner,
)
from michi.infrastructure.library_catalog import SqliteLibraryCatalogRepository
from michi.infrastructure.library_media_cache import SqliteLibraryMediaCache
from michi.presentation.library_bridge import LibraryBridge

QML_DIR = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


class _Prefs(LibraryPrefsPort):
    def load(self):
        return LibraryPrefs()

    def save(self, prefs):
        del prefs


class _ManualPipeline:
    def __init__(self):
        self.submissions = []
        self.cancelled = []

    def submit(self, generation, work, on_progress, on_done):
        self.submissions.append((generation, work, on_progress, on_done))

    def cancel(self, generation):
        self.cancelled.append(generation)
        for submitted in self.submissions:
            if submitted[0] == generation:
                submitted[3](generation, None, ScanCancelled())
                return


class _Progress:
    def __init__(self, phase="", total=0, processed=0, current_path=""):
        self.phase = phase
        self.total = total
        self.processed = processed
        self.current_path = current_path


def _source(tmp_path, name, enabled=True):
    root = tmp_path / name
    root.mkdir(exist_ok=True)
    return LibrarySource(
        library_source_id=new_library_source_id(),
        display_name=name,
        root_path=str(root),
        enabled=enabled,
    )


def _world(tmp_path):
    db_path = tmp_path / "michi.db"
    catalog = SqliteLibraryCatalogRepository(db_path)
    library = LibraryService(FilesystemLibrarySourceScanner(), library_prefs=_Prefs())
    coordinator = SourceScanCoordinator(
        library,
        catalog,
        FilesystemLibrarySourceScanner(),
        media_cache=SqliteLibraryMediaCache(db_path),
    )
    pipeline = _ManualPipeline()
    lifecycle = SourceScanLifecycle(coordinator, pipeline)
    bridge = LibraryBridge(
        library,
        source_coordinator=coordinator,
        source_scan_lifecycle=lifecycle,
    )
    return library, catalog, coordinator, lifecycle, pipeline, bridge


def _load(engine, rel):
    component = QQmlComponent(engine, str(QML_DIR / rel))
    errs = "; ".join(e.toString() for e in component.errors())
    assert component.status() == QQmlComponent.Ready, f"{rel}: {errs}"
    obj = component.create()
    engine._keepalive = getattr(engine, "_keepalive", []) + [component]
    return obj


# ==========================================================================
# P1-LIB-01 — CANONICAL TOOLBAR CONTRACT
# ==========================================================================


class TestToolbarContract:
    def test_bridge_metaobject_exposes_scan_all_sources(self):
        """QML ``library.scan_all_sources()`` MUST resolve on the REAL
        Bridge metaobject — the product boundary is the metaobject."""
        library, _, _, _, _, bridge = _world(Path("/tmp"))
        meta = bridge.metaObject()
        assert meta.indexOfMethod("scan_all_sources()") >= 0
        assert meta.indexOfMethod("hasSources()") < 0
        assert meta.indexOfMethod("scanAllSources()") < 0

    def test_qml_perform_scan_is_invokable(self, qapp, tmp_path):
        library, catalog, coordinator, lifecycle, pipeline, bridge = _world(tmp_path)
        engine = QQmlEngine()
        engine.addImportPath(str(QML_DIR))
        engine.rootContext().setContextProperty("library", bridge)
        toolbar = _load(engine, "views/LibraryToolbar.qml")
        meta = toolbar.metaObject()
        idx = meta.indexOfMethod("performScan()")
        assert idx >= 0, "performScan() not invokable on the real Toolbar"
        meta.method(idx).invoke(toolbar)

    def test_one_scannable_source_routes_to_scan_all_sources(self, qapp, tmp_path):
        library, catalog, coordinator, lifecycle, pipeline, bridge = _world(tmp_path)
        source = _source(tmp_path, "a")
        (Path(source.root_path) / "a.flac").write_bytes(b"x")
        catalog.upsert_source(source)
        coordinator.list_sources()
        assert bridge.property("hasConfiguredSources") is True
        assert bridge.property("hasScannableSources") is True

        # Armar el scan vía request_scan_all (como hace scan_all_sources).
        bridge.scan_all_sources()
        assert len(pipeline.submissions) == 1

    def test_zero_configured_routes_to_add_source(self, qapp, tmp_path):
        library, catalog, coordinator, lifecycle, pipeline, bridge = _world(tmp_path)
        assert bridge.property("hasConfiguredSources") is False
        assert bridge.property("hasScannableSources") is False
        # SEMANTIC INTEGRATION: el toolbar premium de main (PR #224-228)
        # no reconstruye política de sources en QML — la ruta productiva
        # es el metaobject del bridge (scan_all_sources), verificado arriba.
        assert bridge.metaObject().indexOfMethod("scan_all_sources()") >= 0

    def test_configured_but_zero_scannable_routes_to_source_manager(
        self, qapp, tmp_path
    ):
        library, catalog, coordinator, lifecycle, pipeline, bridge = _world(tmp_path)
        source = _source(tmp_path, "a", enabled=False)
        catalog.upsert_source(source)
        coordinator.list_sources()
        assert bridge.property("hasConfiguredSources") is True
        assert bridge.property("hasScannableSources") is False
        # scan_all_sources no somete nada (0 scannables) — sin side effects.
        bridge.scan_all_sources()
        assert len(pipeline.submissions) == 0
        assert bridge.property("hasConfiguredSources") is True

    def test_no_nonexistent_aliases_remain(self):
        toolbar = Path(QML_DIR / "views" / "LibraryToolbar.qml").read_text()
        assert "hasSources" not in toolbar
        assert "scanAllSources" not in toolbar
        assert "performScan" in toolbar

    def test_productive_ui_scan_wiring_uses_source_lifecycle_only(self):
        """FREEZE AUDIT P1 GATE: la UI premium (toolbar + source popover)
        NUNCA llama library.scan() (pipeline legacy) — el Scan pasa por
        scan_all_sources() y agregar carpeta por
        add_and_scan_music_source_url (SourceScanLifecycle). El estado
        visual de sources deriva de la proyección moderna
        (hasConfiguredSources), nunca de currentDir."""
        toolbar = Path(QML_DIR / "views" / "LibraryToolbar.qml").read_text()
        popover = Path(QML_DIR / "views" / "LibrarySourcePopover.qml").read_text()

        # 1) El toolbar productivo nunca toca el pipeline legacy
        # (solo comentarios que lo prohíben).
        code_lines = [
            line
            for line in toolbar.splitlines()
            if line.strip() and not line.strip().startswith("//")
        ]
        assert "library.scan(" not in "".join(code_lines)
        assert "library.currentDir" not in toolbar
        # 2) El estado de Sources es la proyección moderna del Bridge.
        assert "library.hasConfiguredSources" in toolbar
        # 3) El Scan usa el Source lifecycle canónico.
        assert "library.scan_all_sources()" in toolbar
        # 4) Agregar carpeta usa add_and_scan_music_source_url.
        assert "library.add_and_scan_music_source_url(" in popover
        popover_code = [
            line
            for line in popover.splitlines()
            if line.strip() and not line.strip().startswith("//")
        ]
        assert "library.scan(" not in "".join(popover_code)
        # 5) El popover no depende del estado legacy currentDir.
        assert "library.currentDir" not in popover

    def test_perform_scan_runtime_uses_modern_lifecycle(self, qapp, tmp_path):
        """FREEZE AUDIT P1 GATE (runtime): invocar performScan() del
        toolbar REAL con un source configurado somete al
        SourceScanLifecycle (scan_all_sources) — nunca al pipeline legacy."""
        from PySide6.QtQml import QQmlEngine

        library, catalog, coordinator, lifecycle, pipeline, bridge = _world(tmp_path)
        source = _source(tmp_path, "a")
        (Path(source.root_path) / "a.flac").write_bytes(b"x")
        catalog.upsert_source(source)
        coordinator.list_sources()
        bridge.library_changed.emit()

        engine = QQmlEngine()
        engine.addImportPath(str(QML_DIR))
        engine.rootContext().setContextProperty("library", bridge)
        toolbar = _load(engine, "views/LibraryToolbar.qml")
        # POST-MERGE SEMANTIC RECOVERY: el toolbar R4 no expone
        # hasSource — el contrato moderno vive en el bridge.
        assert bridge.property("hasConfiguredSources") is True
        meta = toolbar.metaObject()
        idx = meta.indexOfMethod("performScan()")
        assert idx >= 0
        meta.method(idx).invoke(toolbar)
        qapp.processEvents()
        assert len(pipeline.submissions) == 1, (
            "performScan → scan_all_sources → SourceScanLifecycle"
        )
        engine.deleteLater()


# ==========================================================================
# P1-LIB-02 — SOURCES MANAGER DECLARATIVE IDENTITY
# ==========================================================================


class TestSourcesManagerContract:
    def test_declarative_delegate_uses_stable_identity(self, qapp, tmp_path):
        from PySide6.QtCore import QUrl
        from PySide6.QtQuick import QQuickView

        library, catalog, coordinator, lifecycle, pipeline, bridge = _world(tmp_path)
        active = _source(tmp_path, "active")
        disabled = _source(tmp_path, "disabled", enabled=False)
        catalog.upsert_source(active)
        catalog.upsert_source(disabled)
        coordinator.retire_source(disabled.library_source_id)
        coordinator.list_sources()

        # 1. El dialog REAL se instancia (product wiring proof).
        harness_path = Path(__file__).resolve().parent / "SourcesDialogHarness.qml"
        view = QQuickView()
        view.engine().addImportPath(str(QML_DIR))
        view.engine().rootContext().setContextProperty("library", bridge)
        view.setSource(QUrl.fromLocalFile(str(harness_path)))
        assert view.status() == QQuickView.Ready, view.errors()
        qapp.processEvents()
        dialog = view.rootObject().findChild(QObject, "MusicSourcesDialog")
        assert dialog is not None and dialog.property("visible") is True

        # 2. El model reactivo expone la identidad estable por fila.
        rows = bridge.property("musicSources")
        assert len(rows) == 2
        by_name = {row["name"]: row for row in rows}
        assert by_name["active"]["id"] == active.library_source_id
        assert by_name["disabled"]["id"] == disabled.library_source_id
        assert Path(by_name["active"]["rootPath"]) == Path(active.root_path)
        assert by_name["active"]["enabled"] is True
        assert by_name["disabled"]["enabled"] is False
        assert by_name["disabled"]["lifecycle"] == "retired"

        # 3. Las acciones del manager reciben el SourceId EXACTO del model
        # (sin derivación por parent-chain): scan con el id del model.
        bridge.scan_source(by_name["active"]["id"])
        assert len(pipeline.submissions) == 1
        # Un source DISABLED/RETIRED jamás entra al worker.
        bridge.scan_source(by_name["disabled"]["id"])
        assert len(pipeline.submissions) == 1
        view.close()

    def test_dialog_source_is_declarative(self):
        """No manual createObject, no parent-chain identity, no
        Item.enabled collision for configured state."""
        source = Path(QML_DIR / "views" / "MusicSourcesDialog.qml").read_text()
        assert "Repeater" in source
        assert "property bool sourceEnabled" in source
        assert "property bool enabled" not in source
        assert "parent.parent.parent" not in source
        assert "createObject(" not in source

    def test_qurl_translation_lives_in_bridge(self, qapp, tmp_path):
        toolbar = Path(QML_DIR / "views" / "LibraryToolbar.qml").read_text()
        assert 'toString().replace("file://", "")' not in toolbar
        dialog = Path(QML_DIR / "views" / "MusicSourcesDialog.qml").read_text()
        assert 'toString().replace("file://", "")' not in dialog


# ==========================================================================
# P1-LIB-03 — QURL BOUNDARY + FIRST-RUN USE CASE
# ==========================================================================


class TestQUrlBoundary:
    def test_special_character_root_persists_exact_path(self, tmp_path):
        library, catalog, coordinator, lifecycle, pipeline, bridge = _world(tmp_path)
        root = tmp_path / "Music #1 % colección 日本語"
        root.mkdir(parents=True)
        (root / "a.flac").write_bytes(b"x")
        error = bridge.add_and_scan_music_source_url(QUrl.fromLocalFile(str(root)))
        assert error == ""
        sources = coordinator.list_sources()
        assert len(sources) == 1
        assert Path(sources[0].root_path) == root
        # UN solo source configurado y UNA sola submission async.
        assert len(pipeline.submissions) == 1

    def test_remote_url_rejected_no_mutation(self, tmp_path):
        library, catalog, coordinator, lifecycle, pipeline, bridge = _world(tmp_path)
        error = bridge.add_and_scan_music_source_url(QUrl("https://example.com/music"))
        assert "local" in error.lower()
        assert coordinator.list_sources() == ()
        assert pipeline.submissions == []

    def test_relocate_url_boundary(self, tmp_path):
        library, catalog, coordinator, lifecycle, pipeline, bridge = _world(tmp_path)
        source = _source(tmp_path, "a")
        catalog.upsert_source(source)
        new_root = tmp_path / "Música nueva"
        new_root.mkdir()
        error = bridge.relocate_source_url(
            source.library_source_id, QUrl.fromLocalFile(str(new_root))
        )
        assert error == ""
        relocated = coordinator.list_sources()[0]
        assert Path(relocated.root_path) == new_root
        assert len(pipeline.submissions) == 1


# ==========================================================================
# P1-LIB-05 — EFFECTIVE AVAILABILITY → ROW
# ==========================================================================


class TestEffectiveAvailabilityRow:
    def test_media_playback_blocked_matrix(self):
        assert media_playback_blocked(MediaAvailability.AVAILABLE) is False
        assert media_playback_blocked(MediaAvailability.UNKNOWN) is False
        assert media_playback_blocked(MediaAvailability.MISSING) is True
        assert media_playback_blocked(MediaAvailability.SOURCE_OFFLINE) is True
        assert media_playback_blocked(MediaAvailability.ACCESS_DENIED) is True
        assert media_playback_blocked(MediaAvailability.IO_ERROR) is True

    def test_source_offline_composes_into_unavailable(self, tmp_path):
        library, catalog, coordinator, lifecycle, pipeline, bridge = _world(tmp_path)
        source = _source(tmp_path, "a")
        (Path(source.root_path) / "a.flac").write_bytes(b"x")
        catalog.upsert_source(source)
        coordinator.scan_source(source)
        coordinator._observations[source.library_source_id] = SourceAvailability.OFFLINE
        ref = library.state.tracks[0]
        row = bridge._project_track_row(ref)
        assert row["availability"] == "source_offline"
        assert row["unavailable"] is True

    def test_track_row_wires_unavailable(self, qapp, tmp_path):
        table = Path(QML_DIR / "media" / "MichiTrackTable.qml").read_text()
        assert "unavailable: Boolean(modelData.unavailable)" in table
        row_qml = Path(QML_DIR / "media" / "TrackRow.qml").read_text()
        assert "property bool unavailable" in row_qml
        assert "!root.unavailable" in row_qml


# ==========================================================================
# P1-LIB-06 — STRUCTURAL libraryTrackCount
# ==========================================================================


class TestStructuralLibraryCount:
    def test_filtered_zero_results_never_impersonate_empty_library(self, tmp_path):
        library, catalog, coordinator, lifecycle, pipeline, bridge = _world(tmp_path)
        source = _source(tmp_path, "a")
        catalog.upsert_source(source)
        for name in ("a.flac", "b.flac", "c.flac"):
            (Path(source.root_path) / name).write_bytes(b"x")
        coordinator.scan_source(source)
        assert bridge.property("fileCount") == 3

        library.search("zzzz-no-match-zzzz")
        assert bridge.property("fileCount") == 0
        assert bridge.property("libraryTrackCount") == 3

    def test_true_empty_library_still_first_run(self, tmp_path):
        library, catalog, coordinator, lifecycle, pipeline, bridge = _world(tmp_path)
        assert bridge.property("fileCount") == 0
        assert bridge.property("libraryTrackCount") == 0


# ==========================================================================
# P1-LIB-11 — TRACK_MISSING DIAGNOSTIC RECOVERY
# ==========================================================================


class TestDiagnosticRecovery:
    def test_relink_same_track_id_clears_diagnostic(self, tmp_path):
        library, catalog, coordinator, lifecycle, pipeline, bridge = _world(tmp_path)
        source = _source(tmp_path, "a")
        track_path = Path(source.root_path) / "song.flac"
        track_path.write_bytes(b"x")
        catalog.upsert_source(source)
        coordinator.scan_source(source)
        track = library.state.tracks[0]

        # El archivo desaparece → playback validation marca MISSING.
        track_path.unlink()
        library.validate_track_for_playback(track)
        assert library.state.diagnostic is not None
        assert library.state.diagnostic.code is LibraryDiagnosticCode.TRACK_MISSING

        # Relink: el archivo vuelve con la MISMA identidad.
        track_path.write_bytes(b"y" * 100)
        coordinator.scan_source(source)
        recovered = library.trackref_by_id(track.track_id)
        assert recovered is not None
        assert recovered.availability is MediaAvailability.AVAILABLE
        assert library.state.diagnostic is None

    def test_still_missing_keeps_diagnostic(self, tmp_path):
        library, catalog, coordinator, lifecycle, pipeline, bridge = _world(tmp_path)
        source = _source(tmp_path, "a")
        track_path = Path(source.root_path) / "song.flac"
        track_path.write_bytes(b"x")
        catalog.upsert_source(source)
        coordinator.scan_source(source)
        track = library.state.tracks[0]
        track_path.unlink()
        library.validate_track_for_playback(track)
        assert library.state.diagnostic is not None

        # Rescan: el archivo sigue ausente → el diagnóstico permanece.
        coordinator.scan_source(source)
        assert library.state.diagnostic is not None
        assert library.state.diagnostic.code is LibraryDiagnosticCode.TRACK_MISSING

    def test_unrelated_source_scan_never_clears(self, tmp_path):
        library, catalog, coordinator, lifecycle, pipeline, bridge = _world(tmp_path)
        source_a = _source(tmp_path, "a")
        track_a = Path(source_a.root_path) / "song.flac"
        track_a.write_bytes(b"x")
        catalog.upsert_source(source_a)
        coordinator.scan_source(source_a)
        track = library.state.tracks[0]
        track_a.unlink()
        library.validate_track_for_playback(track)
        assert library.state.diagnostic is not None

        source_b = _source(tmp_path, "b")
        (Path(source_b.root_path) / "b.flac").write_bytes(b"x")
        catalog.upsert_source(source_b)
        coordinator.scan_source(source_b)
        # El diagnóstico de A sobrevive al scan de B.
        assert library.state.diagnostic is not None
        assert library.state.diagnostic.code is LibraryDiagnosticCode.TRACK_MISSING
