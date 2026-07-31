"""Visual-system contracts for elevated surfaces and semantic badges."""

from pathlib import Path

import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine


QML_ROOT = Path(__file__).resolve().parents[2] / "ui_qml"


def _source(relative_path: str) -> str:
    return (QML_ROOT / relative_path).read_text()


def _component(engine: QQmlEngine, relative_path: str) -> QQmlComponent:
    engine.addImportPath(str(QML_ROOT))
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_ROOT / relative_path)))
    return component


def test_cards_delegate_tonal_elevation_to_base_surface() -> None:
    source = _source("components/MichiCard.qml")

    assert "MichiBaseSurface {" in source
    assert "level: root.elevated || root.variant === \"elevated\" ? 3 : 2" in source
    assert "TextureOverlay" not in source
    assert "ShaderEffect" not in source


def test_popup_and_input_materials_use_canonical_elevation() -> None:
    popup = _source("materials/PopupMaterial.qml")
    input_material = _source("materials/InputMaterial.qml")

    assert "MichiBaseSurface {" in popup
    assert "level: 4" in popup
    assert "MichiBaseSurface {" in input_material
    assert "level: 3" in input_material
    assert "TextureOverlay" not in popup
    assert "ShaderEffect" not in popup


def test_dialog_primitives_reuse_popup_material() -> None:
    assert "PopupMaterial {" in _source("components/MichiDialog.qml")
    assert "PopupMaterial {" in _source("components/dialogs/BaseDialog.qml")


def test_hero_has_one_glow_gradient_and_one_contour_texture() -> None:
    source = _source("materials/HeroMaterial.qml")

    assert "color: MichiTheme.colors.surfaceHero" in source
    assert source.count("gradient: Gradient") == 1
    assert source.count("TextureOverlay {") == 1
    assert 'variant: "contours"' in source


def test_surface_aliases_follow_the_elevation_hierarchy() -> None:
    source = _source("theme/MichiColors.qml")

    assert "readonly property color surfaceCard: surfaceElevation2" in source
    assert "readonly property color surfaceCardHover: surfaceElevation3" in source
    assert "readonly property color surfacePopup: surfaceElevation4" in source
    assert "readonly property color surfaceInput: surfaceElevation3" in source


def test_status_badge_aliases_resolve_to_semantic_kinds() -> None:
    source = _source("components/StatusBadge.qml")

    assert 'case "experimental": return "warning"' in source
    assert 'default: return "info"' in source
    assert 'case "disconnected": return "error"' in source
    assert "badgeExperimentalBg" not in source
    assert "colors.experimental" not in source


def test_status_badge_is_the_single_canonical_badge() -> None:
    components = QML_ROOT / "components"

    assert (components / "StatusBadge.qml").exists()
    assert not (components / "MichiBadge.qml").exists()
    assert not (components / "ConnectionStatusBadge.qml").exists()
    assert not (components / "ServiceHealthBadge.qml").exists()


def test_card_runtime_uses_level_two_and_elevates_to_level_three(qapp) -> None:
    engine = QQmlEngine(qapp)
    component = _component(engine, "components/MichiCard.qml")
    assert component.isReady(), component.errorString()
    card = component.create()
    assert card is not None, component.errorString()
    surface = card.findChild(QObject, "michiCardBackground")
    assert surface is not None

    assert surface.property("level") == 2
    card.setProperty("elevated", True)
    assert surface.property("level") == 3

    card.deleteLater()
    engine.deleteLater()


@pytest.mark.parametrize(
    ("kind", "semantic_kind"),
    [
        ("succeeded", "success"),
        ("experimental", "warning"),
        ("failed", "error"),
        ("disconnected", "error"),
        ("running", "info"),
    ],
)
def test_status_badge_runtime_normalizes_aliases(qapp, kind: str, semantic_kind: str) -> None:
    engine = QQmlEngine(qapp)
    component = _component(engine, "components/StatusBadge.qml")
    assert component.isReady(), component.errorString()
    badge = component.create()
    assert badge is not None, component.errorString()

    badge.setProperty("kind", kind)
    assert badge.property("semanticKind") == semantic_kind

    badge.deleteLater()
    engine.deleteLater()
