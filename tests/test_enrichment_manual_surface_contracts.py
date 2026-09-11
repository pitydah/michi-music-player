"""POST-R4 P9 (E2/E5) — enrichment manual surface contracts.

- EnrichmentInlineState.qml is DEAD (no productive consumer): negative
  gate — the file must not exist;
- visible strings of the manual match surface are translatable (no raw
  strings);
- the manual match rows are AUDITABLE: provider identity + external id
  are rendered (never an opaque name + button list).
"""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

QML = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"


@pytest.fixture(scope="module")
def qapp():
    """QGuiApplication module-scoped (los tests del dialog montan QML)."""
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    yield app


def _qml(rel):
    return (QML / rel).read_text(encoding="utf-8", errors="ignore")


DIALOG_RAW_STRINGS = (
    "Review artist match",
    "Review album match",
    "Use this match",
    "Searching…",
    "Cancel",
    "Search",
    "Search online databases to confirm who this artist is.",
)


class TestDeadComponentRemoved:
    def test_enrichment_inline_state_does_not_exist(self):
        assert not (QML / "enrichment" / "EnrichmentInlineState.qml").exists(), (
            "EnrichmentInlineState.qml no tiene consumidores productivos: "
            "componente muerto eliminado"
        )

    def test_no_view_references_inline_state(self):
        for view in (QML / "views").glob("*.qml"):
            src = view.read_text(encoding="utf-8", errors="ignore")
            assert "EnrichmentInlineState" not in src, view.name


class TestManualSurfaceI18n:
    @pytest.mark.parametrize("file", ["enrichment/ReviewMatchesDialog.qml"])
    def test_dialog_visible_strings_translated(self, file):
        import re

        src = _qml(file)
        for raw in DIALOG_RAW_STRINGS:
            # el string no debe aparecer FUERA de qsTr(...)
            matches = re.findall(r'qsTr\("' + re.escape(raw) + r'"\)', src)
            bare = re.findall(r'(?<!qsTr\()"' + re.escape(raw) + r'"', src)
            assert matches, f"el string debe estar traducido: {raw!r}"
            assert not bare, f"raw string sin qsTr: {raw!r}"
        assert src.count("qsTr(") >= 10

    def test_actions_visible_strings_translated(self):
        import re

        src = _qml("enrichment/EnrichmentActions.qml")
        for raw in ("Refresh", "Clear online info", "Reset match"):
            bare = re.findall(r'(?<!qsTr\()"' + re.escape(raw) + r'"', src)
            assert not bare, f"raw string sin qsTr: {raw!r}"
        assert src.count("qsTr(") >= 6


class TestAuditableCandidates:
    def test_artist_rows_render_provider_and_mbid(self):
        """El resultado manual no es opaco: el row muestra la identidad
        del provider y el MusicBrainz ID del candidato."""
        src = _qml("enrichment/ReviewMatchesDialog.qml")
        delegate = src[src.index("delegate: ItemDelegate") :]
        delegate = delegate[: delegate.index("/* keyboard")]
        assert "modelData.disambiguation" in delegate
        assert "modelData.provider" in delegate
        assert "externalArtistId" in delegate
        assert 'qsTr("MusicBrainz ID: %1")' in delegate

    def test_album_rows_render_credit_year_provider_and_id(self):
        src = _qml("enrichment/ReviewMatchesDialog.qml")
        delegate = src[src.index("delegate: ItemDelegate") :]
        delegate = delegate[: delegate.index("/* keyboard")]
        assert "modelData.artistCredit" in delegate
        assert "modelData.year" in delegate
        assert "externalReleaseGroupId" in delegate
        assert 'qsTr("MusicBrainz release-group: %1")' in delegate

    def test_candidates_carry_provider_identity(self):
        """El bridge emite el provider junto a cada candidato (la
        identidad de la fuente es parte del dato auditable)."""
        # los candidates views del coordinator ya llevan provider: gate
        # estructural sobre el mapeo del bridge.

        from michi.presentation.enrichment_bridge import EnrichmentBridge  # noqa: F401

        bridge_src = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "michi"
            / "presentation"
            / "enrichment_bridge.py"
        ).read_text(encoding="utf-8")
        assert '"provider": c.provider' in bridge_src, (
            "el candidato del review lleva su provider"
        )
        assert '"externalArtistId": c.external_artist_id' in bridge_src


class TestArtworkSourceDialog:
    """POST-R4 E2 (12.4): el image picker muestra los candidatos reales
    con preview + fuente; los strings visibles son traducibles."""

    def _load(self, local_path, external_path, current=""):

        from PySide6.QtQml import QQmlComponent, QQmlEngine

        from tests.test_m9_r1j_playlist_interactions import _process

        engine = QQmlEngine()
        engine.addImportPath(str(QML))
        comp = QQmlComponent(
            engine, str(QML / "enrichment" / "ArtworkSourceDialog.qml")
        )
        assert comp.status() == QQmlComponent.Ready, [
            e.toString() for e in comp.errors()
        ]
        obj = comp.create()
        assert obj is not None
        engine._held = comp
        obj.setProperty("localPath", local_path)
        obj.setProperty("externalPath", external_path)
        obj.setProperty("currentSource", current)
        _process()
        return engine, obj

    def _all_texts(self, obj):
        from PySide6.QtCore import QObject

        texts = []
        for child in obj.findChildren(QObject):
            try:
                t = child.property("text")
                if isinstance(t, str) and t:
                    texts.append(t)
            except RuntimeError:
                continue
        return texts

    def test_both_candidates_rendered(self, qapp):
        engine, obj = self._load("/local/folder.jpg", "/managed/external.jpg")
        try:
            texts = self._all_texts(obj)
            joined = " | ".join(texts)
            assert "Cover Art Archive" in joined, texts
            assert "Local artwork" in joined, texts
            assert obj.property("objectName") == "artworkSourceDialog"
        finally:
            obj.deleteLater()
            engine.deleteLater()

    def test_current_external_is_marked(self, qapp):
        from PySide6.QtCore import QObject

        engine, obj = self._load(
            "/local/folder.jpg", "/managed/external.jpg", "external"
        )
        try:
            # el marcador "In use" existe para la elección vigente (el
            # binding lo muestra cuando currentSource == external)
            in_use = [
                c for c in obj.findChildren(QObject) if c.property("text") == "In use"
            ]
            assert in_use, "la fuente vigente se marca"
        finally:
            obj.deleteLater()
            engine.deleteLater()

    def test_visible_strings_translated(self):
        import re

        src = _qml("enrichment/ArtworkSourceDialog.qml")
        for raw in (
            "Choose artwork",
            "Cover Art Archive",
            "Local artwork",
            "In use",
            "Automatic",
            "Cancel",
        ):
            bare = re.findall(r'(?<!qsTr\()"' + re.escape(raw) + r'"', src)
            assert not bare, f"raw string sin qsTr: {raw!r}"
        assert src.count("qsTr(") >= 8
