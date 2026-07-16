"""Verify all theme tokens exist and have valid values."""
from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


@pytest.fixture
def engine(qapp):
    return QQmlEngine(qapp)


def _get_singleton(engine, qml_path: str):
    engine.addImportPath(str(QML_DIR))
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / qml_path)))
    assert component.isReady(), f"Failed to load {qml_path}: {component.errorString()}"
    obj = component.create()
    assert obj is not None, f"Failed to create {qml_path}"
    return obj


class TestMichiColorsTokens:
    QML_PATH = "theme/MichiColors.qml"

    @pytest.fixture
    def colors(self, engine):
        return _get_singleton(engine, self.QML_PATH)

    def test_bg_app(self, colors):
        assert colors.bgApp

    def test_bg_content(self, colors):
        assert colors.bgContent

    def test_accent_blue(self, colors):
        assert colors.accentBlue

    def test_accent(self, colors):
        assert colors.accent

    def test_accent_surface(self, colors):
        assert colors.accentSurface

    def test_accent_selection(self, colors):
        assert colors.accentSelection

    def test_surface_card(self, colors):
        assert colors.surfaceCard

    def test_surface_card_hover(self, colors):
        assert colors.surfaceCardHover

    def test_surface_card_elevated(self, colors):
        assert colors.surfaceCardElevated

    def test_surface_elevated(self, colors):
        assert colors.surfaceElevated

    def test_surface_overlay(self, colors):
        assert colors.surfaceOverlay

    def test_success(self, colors):
        assert colors.success

    def test_warning(self, colors):
        assert colors.warning

    def test_error(self, colors):
        assert colors.error

    def test_text_on_error(self, colors):
        assert colors.textOnError

    def test_text_on_success(self, colors):
        assert colors.textOnSuccess

    def test_border_hover(self, colors):
        assert colors.borderHover

    def test_border_focus(self, colors):
        assert colors.borderFocus

    def test_border_error(self, colors):
        assert colors.borderError

    def test_accent_secondary(self, colors):
        assert colors.accentSecondary

    def test_text_primary(self, colors):
        assert colors.textPrimary

    def test_text_normal(self, colors):
        assert colors.textNormal

    def test_text_secondary(self, colors):
        assert colors.textSecondary

    def test_text_muted(self, colors):
        assert colors.textMuted

    def test_border_subtle(self, colors):
        assert colors.borderSubtle

    def test_border_card(self, colors):
        assert colors.borderCard

    def test_border_active(self, colors):
        assert colors.borderActive

    def test_focus_halo(self, colors):
        assert colors.focusHalo


class TestMichiTypographyTokens:
    QML_PATH = "theme/MichiTypography.qml"

    @pytest.fixture
    def typography(self, engine):
        return _get_singleton(engine, self.QML_PATH)

    def test_display_size(self, typography):
        assert typography.displaySize == 32

    def test_hero_title_size(self, typography):
        assert typography.heroTitleSize == 28

    def test_page_title_size(self, typography):
        assert typography.pageTitleSize == 22

    def test_section_title_size(self, typography):
        assert typography.sectionTitleSize == 20

    def test_card_title_size(self, typography):
        assert typography.cardTitleSize == 16

    def test_body_size(self, typography):
        assert typography.bodySize == 14

    def test_secondary_size(self, typography):
        assert typography.secondarySize == 13

    def test_caption_size(self, typography):
        assert typography.captionSize == 12

    def test_badge_size(self, typography):
        assert typography.badgeSize == 10

    def test_meta_size(self, typography):
        assert typography.metaSize == 11

    def test_button_size(self, typography):
        assert typography.buttonSize == 14

    def test_monospace_size(self, typography):
        assert typography.monospaceSize == 13

    def test_weight_light(self, typography):
        assert typography.weightLight == 300

    def test_weight_normal(self, typography):
        assert typography.weightNormal == 400

    def test_weight_medium(self, typography):
        assert typography.weightMedium == 500

    def test_weight_semi_bold(self, typography):
        assert typography.weightSemiBold == 600

    def test_weight_bold(self, typography):
        assert typography.weightBold == 700


class TestMichiSpacingTokens:
    QML_PATH = "theme/MichiSpacing.qml"

    @pytest.fixture
    def spacing(self, engine):
        return _get_singleton(engine, self.QML_PATH)

    def test_xxs(self, spacing):
        assert spacing.xxs == 2

    def test_xs(self, spacing):
        assert spacing.xs == 4

    def test_sm(self, spacing):
        assert spacing.sm == 8

    def test_md(self, spacing):
        assert spacing.md == 12

    def test_lg(self, spacing):
        assert spacing.lg == 16

    def test_xl(self, spacing):
        assert spacing.xl == 24

    def test_xxl(self, spacing):
        assert spacing.xxl == 32

    def test_xxxl(self, spacing):
        assert spacing.xxxl == 48

    def test_page(self, spacing):
        assert spacing.page == 40


class TestMichiMotionTokens:
    QML_PATH = "theme/MichiMotion.qml"

    @pytest.fixture
    def motion(self, engine):
        return _get_singleton(engine, self.QML_PATH)

    def test_duration_instant(self, motion):
        assert motion.durationInstant == 80

    def test_duration_fast(self, motion):
        assert motion.durationFast == 120

    def test_duration_normal(self, motion):
        assert motion.durationNormal == 200

    def test_duration_slow(self, motion):
        assert motion.durationSlow == 300

    def test_fast(self, motion):
        assert motion.fast == 120

    def test_normal(self, motion):
        assert motion.normal == 160

    def test_slow(self, motion):
        assert motion.slow == 220

    def test_reduced(self, motion):
        assert motion.reduced == 40

    def test_easing_in_out(self, motion):
        assert motion.easing.inOut is not None

    def test_easing_out(self, motion):
        assert motion.easing.out is not None

    def test_easing_in(self, motion):
        assert getattr(motion.easing, "in") is not None

    def test_easing_standard(self, motion):
        assert motion.easing.standard is not None


class TestMichiThemeTokens:
    QML_PATH = "theme/MichiTheme.qml"

    @pytest.fixture
    def theme(self, engine):
        return _get_singleton(engine, self.QML_PATH)

    def test_colors_section(self, theme):
        assert theme.colors is not None

    def test_typography_section(self, theme):
        assert theme.typography is not None

    def test_spacing_section(self, theme):
        assert theme.spacing is not None

    def test_motion_section(self, theme):
        assert theme.motion is not None

    def test_radius_section(self, theme):
        assert theme.radius is not None
        assert theme.radius.xs == 2
        assert theme.radius.sm == 4
        assert theme.radius.md == 8
        assert theme.radius.lg == 12
        assert theme.radius.xl == 16
        assert theme.radius.pill == 999

    def test_opacity_section(self, theme):
        assert theme.opacity is not None
        assert theme.opacity.enabled == 1.0
        assert theme.opacity.disabled == 0.4
        assert theme.opacity.hover == 0.85
        assert theme.opacity.pressed == 0.7
        assert theme.opacity.muted == 0.6

    def test_breakpoints_section(self, theme):
        assert theme.breakpoints is not None
        assert theme.breakpoints.compact == 800
        assert theme.breakpoints.medium == 1200
        assert theme.breakpoints.wide == 1600

    def test_density_section(self, theme):
        assert theme.density is not None
        assert theme.density.compact == 32
        assert theme.density.regular == 44
        assert theme.density.comfortable == 56

    def test_minimum_interactive_size(self, theme):
        assert theme.minimumInteractiveSize == 44


class TestThemeStoreTokens:
    QML_PATH = "theme/ThemeStore.qml"

    @pytest.fixture
    def store(self, engine):
        return _get_singleton(engine, self.QML_PATH)

    def test_reduce_motion_property(self, store):
        assert hasattr(store, "reduceMotion")

    def test_font_scale_property(self, store):
        assert hasattr(store, "fontScale")

    def test_high_contrast_property(self, store):
        assert hasattr(store, "highContrast")
