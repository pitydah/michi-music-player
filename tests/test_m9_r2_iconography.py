"""Tests for M9-R2 Iconography and UI Gallery coverage."""

from pathlib import Path

QML = Path("src/michi/presentation/qml")


def _text(relative: str) -> str:
    return (QML / relative).read_text()


def test_iconography_uses_24x24_native_grid() -> None:
    icon_src = _text("primitives/MichiIcon.qml")
    assert "ctx.scale(w / 24.0, h / 24.0)" in icon_src
    assert 'ctx.lineCap = "round"' in icon_src
    assert 'ctx.lineJoin = "round"' in icon_src


def test_p0_and_p1_icons_defined() -> None:
    icon_src = _text("primitives/MichiIcon.qml")
    p0_icons = [
        "settings",
        "sliders",
        "equalizer",
        "pin",
        "view-path",
        "more",
    ]
    p1_icons = [
        "audio-output",
        "audio-engine",
        "device",
        "artist",
        "genre",
        "history",
        "recent",
        "queue",
        "repeat-one",
    ]
    for name in p0_icons + p1_icons:
        assert f'root.name === "{name}"' in icon_src, (
            f"Icon {name} missing in MichiIcon.qml"
        )


def test_equalizer_is_distinct_from_sliders() -> None:
    icon_src = _text("primitives/MichiIcon.qml")
    assert 'root.name === "equalizer"' in icon_src
    assert 'root.name === "sliders"' in icon_src
    branch = icon_src.split(
        '} else if (root.name === "sliders" || root.name === "equalizer") {'
    )[1].split('} else if (root.name === "sort") {')[0]
    assert "5, 19, 5, 11" in branch  # Equalizer vertical bars
    assert "6, 4, 6, 20" in branch  # Sliders rails


def test_ui_gallery_has_iconography_section_with_sizes() -> None:
    gallery_src = _text("dev/MichiUIGallery.qml")
    assert "Iconography" in gallery_src
    assert "width: 16" in gallery_src
    assert "width: 20" in gallery_src
    assert "width: 24" in gallery_src
    assert "Active (Aurora)" in gallery_src
