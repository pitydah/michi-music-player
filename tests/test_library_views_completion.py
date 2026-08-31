import json
from pathlib import Path

from library_views_fixtures import make_many_album_rows

ROOT = Path(__file__).parents[1]
QML = ROOT / "src/michi/presentation/qml"


def _text(relative: str) -> str:
    return (QML / relative).read_text(encoding="utf-8")


def test_all_contextual_options_have_a_real_consumer() -> None:
    popup = _text("views/LibraryViewOptionsPopup.qml")
    albums = _text("views/AlbumsView.qml")
    consumers = {
        "gallery": (
            "artworkSize",
            "spacing",
            "metadataLevel",
            "quickActions",
            "precisionMetadata",
            "inspector",
        ),
        "flow": (
            "coverSize",
            "visibleAlbums",
            "depth",
            "ambientColor",
            "metadataLevel",
        ),
        "vinyl": (
            "sleeveSize",
            "spacing",
            "reveal",
            "metadataLevel",
            "artworkLabel",
            "inspector",
        ),
        "chronology": (
            "grouping",
            "direction",
            "density",
            "metadataLevel",
            "showPeriodDensity",
        ),
        "editorial": (
            "heroVisible",
            "informationRichness",
            "cachedEnrichmentVisible",
            "archiveLayout",
        ),
        "studioList": (
            "density",
            "artworkSize",
            "precisionMetadata",
            "inspector",
            "artistColumn",
            "yearColumn",
            "tracksColumn",
            "durationColumn",
            "formatColumn",
        ),
    }
    combined = popup + albums + _text("views/LibraryView.qml")
    for section, keys in consumers.items():
        assert f'"{section}"' in popup
        for key in keys:
            assert key in popup, f"{section}.{key} is not exposed"
            assert key in combined, f"{section}.{key} has no consumer"


def test_material_palette_and_enrichment_firewall_are_explicit() -> None:
    texture = _text("primitives/MichiMaterialTexture.qml")
    bridge = (ROOT / "src/michi/presentation/enrichment_bridge.py").read_text()
    library_bridge = (ROOT / "src/michi/presentation/library_bridge.py").read_text()
    assert "Canvas {" not in texture
    assert "toDataURL" not in texture
    assert "def browse_album_cached" in bridge
    cached_body = bridge.split("def browse_album_cached", 1)[1].split(
        "def refresh_artist", 1
    )[0]
    assert "_start_album_operation" not in cached_body
    assert '"artworkPalette"' in library_bridge
    assert '"accentSafe"' in library_bridge


def test_scale_fixture_has_10k_stable_canonical_keys() -> None:
    rows = make_many_album_rows()
    assert len(rows) == 10_000
    assert len({row["key"] for row in rows}) == 10_000
    assert sum(row["containsHighResolution"] for row in rows) == 1429


def test_new_qml_is_packaged_and_singleton_registered() -> None:
    project = (ROOT / "pyproject.toml").read_text()
    qmldir = _text("theme/qmldir")
    required = (
        "media/MichiVinylDisc.qml",
        "patterns/LibraryAlbumInspector.qml",
        "primitives/MichiMaterial.qml",
        "theme/MichiMaterialRole.qml",
    )
    assert "presentation/qml/media/*.qml" in project
    assert "presentation/qml/patterns/*.qml" in project
    assert "presentation/qml/primitives/*.qml" in project
    assert "presentation/qml/assets/*.svg" in project
    assert "singleton MichiMaterialRole 1.0 MichiMaterialRole.qml" in qmldir
    assert not [relative for relative in required if not (QML / relative).is_file()]


def test_visual_qa_manifest_covers_every_view_breakpoint_and_state() -> None:
    manifest_path = ROOT / "docs/library_views_visual_qa_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["views"] == [
        "gallery",
        "album-flow",
        "listening-wall",
        "chronology",
        "editorial",
        "studio-list",
    ]
    assert manifest["widths"] == [680, 900, 1200, 1440, 1920, 2560]
    for state in (
        "idle",
        "selected",
        "keyboard-focus",
        "reduced-motion",
        "high-contrast",
    ):
        assert state in manifest["states"]
