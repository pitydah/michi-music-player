"""Structural tests for the M9-R2.3 premium material composition overhaul.

Covers: cached deterministic grain assets, the real backdrop blur (MultiEffect)
gated to high glass quality, the reinforced sheen/glint/rim layers, and
per-surface tile seeds.
"""

from pathlib import Path

QML_ROOT = Path("src/michi/presentation/qml")


def read(rel_path: str) -> str:
    return Path(QML_ROOT, rel_path).read_text(encoding="utf-8")


# ── Cached grain catalog (R1 + R7) ───────────────────────────────────────────


def test_grain_uses_cached_assets_and_seeded_variants():
    texture = read("primitives/MichiMaterialTexture.qml")
    # The grain catalog is decoded once by Qt and shared by every surface.
    assert "michi-grain.svg" not in texture
    assert "toDataURL" not in texture
    assert "Canvas {" not in texture
    assert "property int tileSeed: 0" in texture
    assert 'property string textureName: "grain-graphite-01"' in texture
    assert 'resolved = "grain-graphite-02"' in texture
    assert 'return "../assets/" + resolved + ".svg"' in texture
    assert "asynchronous: true" in texture
    assert "cache: true" in texture
    assert "fillMode: Image.Tile" in texture
    assert "smooth: true" in texture
    for asset in (
        "grain-glass-01.svg",
        "grain-graphite-01.svg",
        "grain-graphite-02.svg",
        "paper-editorial-01.svg",
    ):
        assert Path(QML_ROOT, "assets", asset).is_file()
    # Quality-aware opacity (stronger than the old 0.09/0.16).
    assert 'MichiThemeState.glassQuality === "high" ? 0.36' in texture
    assert ": 0.22" in texture


def test_glass_exposes_tile_seed_and_surfaces_decorrelate():
    glass = read("primitives/MichiGlassSurface.qml")
    assert "property int tileSeed: 0" in glass
    assert "tileSeed: root.tileSeed" in glass
    for rel in [
        "shell/Sidebar.qml",
        "views/LibraryToolbar.qml",
        "views/LibrarySourcePopover.qml",
        "views/LibraryViewOptionsPopup.qml",
        "components/QueuePanel.qml",
        "controls/MichiPopup.qml",
        "controls/MichiMenu.qml",
        "controls/MichiDialog.qml",
        "patterns/ToastHost.qml",
        "patterns/ErrorState.qml",
        "patterns/InspectorPanel.qml",
    ]:
        assert "tileSeed:" in read(rel), rel
    # AlbumDetail/ArtistDetail use their own main-authority layout with the
    # M6.9 enrichment surface — not MichiGlassSurface — so they are not
    # part of the tile-seed decorrelation gate.


# ── Real backdrop blur (R5) ───────────────────────────────────────────────────


def test_backdrop_blur_uses_multi_effect_gated_to_high_quality():
    glass = read("primitives/MichiGlassSurface.qml")
    assert "import QtQuick.Effects" in glass
    assert "MultiEffect {" in glass
    assert "ShaderEffectSource {" in glass
    assert "sourceItem: root.window" in glass
    assert 'MichiThemeState.glassQuality === "high"' in glass
    assert 'root.elevation !== "subtle"' in glass
    assert "blurMax: MichiElevation.modalBlur" in glass
    assert "MichiElevation.standardBlur" in glass


# ── Reinforced glass layers (R2, R3, R4, R6) ──────────────────────────────────


def test_sheen_glint_and_rim_are_tokens_and_present():
    colors = read("theme/MichiSemanticColors.qml")
    assert "glassSheen: Qt.rgba(1, 1, 1, 0.06)" in colors
    assert "glassGlint: Qt.rgba(1, 1, 1, 0.07)" in colors
    assert "glassGlintStrong" in colors
    assert "innerHighlight: Qt.rgba(1, 1, 1, 0.075)" in colors
    assert "glassShadow: Qt.rgba(0, 0, 0, 0.26)" in colors
    glass = read("primitives/MichiGlassSurface.qml")
    # the specular glint is the brand cat silhouette (SVG vector path),
    # not a circle
    assert "import QtQuick.Shapes" in glass
    assert "PathSvg" in glass
    assert "RadialGradient" in glass
    assert "M78.013 0.298" in glass  # start of the normalized cat path
    assert "MichiSemanticColors.glassGlint" in glass
    assert "parent.height * 0.5, 56" in glass


# ── Now Playing Bar polish (textures / motion / buttons, positions frozen) ───


def test_bar_backplane_shares_the_film_grain():
    bar = read("player/NowPlayingBar.qml")
    assert "MichiMaterialTexture {" in bar
    assert "tileSeed: 17" in bar
    assert "visible: !MichiAccessibility.highContrast" in bar


def test_play_button_crossfades_and_breathes():
    bar = read("player/NowPlayingBar.qml")
    # two stacked icons crossfading on status
    assert 'name: "play"' in bar and 'name: "pause"' in bar
    assert 'opacity: root.status === "playing" ? 0 : 1' in bar
    assert 'opacity: root.status === "playing" ? 1 : 0' in bar
    # gradient base + state overlay (no raw Qt.rgba in the bar)
    assert "gradient: Gradient {" in bar
    assert "MichiSemanticColors.surfacePressed" in bar
    # breathing aura while playing
    assert "SequentialAnimation on opacity" in bar
    assert 'running: root.status === "playing"' in bar


def test_slider_handles_react_to_hover():
    bar = read("player/NowPlayingBar.qml")
    assert "scale: timeline.pressed ? 1.08 : timeline.hovered ? 1.04 : 1" in bar
    assert "scale: volumeSlider.pressed ? 1.08" in bar
    assert "hoverEnabled: true" in bar


def test_bar_time_formatting_delegates_to_michi_format():
    bar = read("player/NowPlayingBar.qml")
    assert "return MichiFormat.formatDuration(seconds * 1000)" in bar
    assert "var minutes = Math.floor(safe / 60)" not in bar
