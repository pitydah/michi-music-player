"""POST-R4 P9 (E2/E5) — enrichment manual surface contracts.

- EnrichmentInlineState.qml is DEAD (no productive consumer): negative
  gate — the file must not exist;
- visible strings of the manual match surface are translatable (no raw
  strings);
- the manual match rows are AUDITABLE: provider identity + external id
  are rendered (never an opaque name + button list).
"""

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

QML = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"


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
