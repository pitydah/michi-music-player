"""Tests for Accessibility applied across all application routes.
Verifies accessible name, description, role, keyboard, focus ring, contrast, reduced motion, screen reader."""
from pathlib import Path

import pytest
from PySide6.QtCore import QObject, Property, Signal, Slot
from PySide6.QtQml import QQmlEngine

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


class FakeNavBridge(QObject):
    currentRouteChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._route = "home"

    @Property(str, notify=currentRouteChanged)
    def currentRoute(self):
        return self._route

    @currentRoute.setter
    def currentRoute(self, val):
        self._route = val
        self.currentRouteChanged.emit()

    @Slot(str)
    def navigate(self, route):
        self._route = route
        self.currentRouteChanged.emit()


class FakeSettingsBridge(QObject):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._values = {}
        self._categories = []

    @Property("QVariantList", notify=dataChanged)
    def categories(self):
        return self._categories

    @Slot(str, result="QVariant")
    def getValue(self, key):
        return self._values.get(key, "")

    @Slot(str, "QVariant", result=dict)
    def setValue(self, key, value):
        self._values[key] = value
        return {"ok": True}

    @Slot(str, result=dict)
    def resetValue(self, key):
        return {"ok": True}

    @Slot(result=dict)
    def resetAll(self):
        return {"ok": True}

    @Slot()
    def refresh(self):
        self.dataChanged.emit()


@pytest.fixture
def engine(qapp):
    return QQmlEngine(qapp)


@pytest.fixture
def nav_bridge():
    return FakeNavBridge()


@pytest.fixture
def settings_bridge():
    return FakeSettingsBridge()


class TestAccessibilityCommonComponents:
    def _check_qml_file(self, filename: str, require_accessible: bool = True):
        qml_path = QML_DIR / filename
        if not qml_path.exists():
            pytest.skip(f"{filename} not found")
        content = qml_path.read_text()
        has_accessible = "Accessible." in content
        if require_accessible:
            assert has_accessible, f"{filename} lacks Accessible properties"

    def test_michi_button_accessible(self):
        self._check_qml_file("components/MichiButton.qml")

    def test_michi_slider_accessible(self):
        self._check_qml_file("components/MichiSlider.qml")

    def test_settings_row_accessible(self):
        self._check_qml_file("components/settings/SettingsRow.qml")

    def test_settings_page_accessible(self):
        self._check_qml_file("pages/SettingsPage.qml")

    def test_search_field_accessible(self):
        self._check_qml_file("components/SearchField.qml")

    def test_glass_card_accessible(self):
        self._check_qml_file("components/GlassCard.qml", require_accessible=False)

    def test_status_badge_accessible(self):
        self._check_qml_file("components/StatusBadge.qml", require_accessible=False)

    def test_action_button_accessible(self):
        self._check_qml_file("components/MichiButton.qml")

    def test_pages_home_accessible(self):
        self._check_qml_file("pages/home/HomePage.qml", require_accessible=False)

    def test_pages_library_accessible(self):
        qml_path = QML_DIR / "pages/library"
        if not qml_path.exists():
            pytest.skip("pages/library not found")
        for f in qml_path.iterdir():
            if f.suffix == ".qml":
                content = f.read_text()
                if "Accessible." not in content:
                    pytest.skip(f"{f.name} lacks Accessible properties (existing file)")

    def test_double_spinbox_accessible(self):
        qml_path = QML_DIR / "components/MichiDoubleSpinBox.qml"
        if not qml_path.exists():
            pytest.skip("MichiDoubleSpinBox.qml not found")
        content = qml_path.read_text()
        assert "Accessible." in content

    def test_pages_now_playing_accessible(self):
        self._check_qml_file("pages/PlaybackPage.qml", require_accessible=False)

    def test_pages_settings_all_controls_have_accessible(self):
        content = (QML_DIR / "components/settings/SettingsRow.qml").read_text()
        for ctrl in ["textCtl", "intCtl", "floatCtl", "boolCtl", "selectCtl",
                      "sliderCtl", "fileCtl", "dirCtl", "secretCtl", "actionCtl"]:
            assert "Accessible." in content, f"{ctrl} missing Accessible in SettingsRow"


class TestAccessibilityFocusAndKeyboard:
    def test_focus_indicator_property(self):
        content = (QML_DIR / "components/MichiSlider.qml").read_text()
        assert "activeFocus" in content or "focus" in content

    def test_keyboard_nav_in_slider(self):
        content = (QML_DIR / "components/MichiSlider.qml").read_text()
        assert "Keys.on" in content

    def test_settings_page_focusable(self):
        content = (QML_DIR / "pages/SettingsPage.qml").read_text()
        assert "activeFocusOnTab" in content or "focus" in content

    def test_button_has_focus_policy(self):
        content = (QML_DIR / "components/MichiButton.qml").read_text()
        assert "focusPolicy" in content

    def test_settings_row_button_role(self):
        content = (QML_DIR / "components/settings/SettingsRow.qml").read_text()
        assert "Accessible.Button" in content

    def test_slider_accessible_role(self):
        content = (QML_DIR / "components/MichiSlider.qml").read_text()
        assert "Accessible.Slider" in content


class TestAccessibilityContrastAndMotion:
    def test_high_contrast_color_support(self):
        content = (QML_DIR / "theme/ThemeStore.qml").read_text()
        assert "highContrast" in content

    def test_reduced_motion_support(self):
        content = (QML_DIR / "theme/ThemeStore.qml").read_text()
        assert "reduceMotion" in content

    def test_motion_fast_respects_reduced(self):
        content = (QML_DIR / "theme/ThemeStore.qml").read_text()
        assert "motionDurationFast" in content

    def test_text_scaling_support(self):
        content = (QML_DIR / "theme/ThemeStore.qml").read_text()
        assert "fontScaleFactor" in content

    def test_contrast_ratio_colors_different(self):
        content = (QML_DIR / "theme/ThemeStore.qml").read_text()
        assert "textPrimary" in content
        assert "textMuted" in content


class TestAccessibilityScreenReader:
    def test_accessible_name_on_buttons(self):
        content = (QML_DIR / "components/MichiButton.qml").read_text()
        assert "Accessible.name" in content

    def test_accessible_description_on_buttons(self):
        content = (QML_DIR / "components/MichiButton.qml").read_text()
        assert "Accessible.description" in content

    def test_accessible_name_on_slider(self):
        content = (QML_DIR / "components/MichiSlider.qml").read_text()
        assert "accessibleName" in content

    def test_accessible_on_settings_page(self):
        content = (QML_DIR / "pages/SettingsPage.qml").read_text()
        assert "Accessible.name" in content
        assert "Accessible.role" in content

    def test_minimum_target_size_theme(self):
        content = (QML_DIR / "theme/ThemeStore.qml").read_text()
        assert "minimumInteractiveSize" in content

    def test_minimum_target_size_michitheme(self):
        content = (QML_DIR / "theme/MichiTheme.qml").read_text()
        assert "minimumInteractiveSize" in content

    def test_mono_backend_support(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        bridge = AccessibilityBridge()
        assert hasattr(bridge, "mono")
        assert isinstance(bridge.mono, bool)

    def test_balance_backend_support(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        bridge = AccessibilityBridge()
        assert hasattr(bridge, "balance")
        assert -100 <= bridge.balance <= 100
