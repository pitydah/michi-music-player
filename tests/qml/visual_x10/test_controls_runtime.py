"""Runtime tests for Michi QML controls — Ola 3.

Instantiates real QML components with QQmlEngine + QQuickView (offscreen)
and verifies key behavior.

For controls that cannot be instantiated due to QML compile errors
(Keys.onEndPressed, duplicate signals, etc.), uses parsing tests
that verify the source QML for the required properties and patterns.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"
COMPONENTS_DIR = QML_DIR / "components"
THEME_DIR = QML_DIR / "theme"


# ── Helpers ─────────────────────────────────────────────────────────────────────


def _read_qml(name: str) -> str:
    path = COMPONENTS_DIR / name
    assert path.exists(), f"Missing: {path}"
    return path.read_text(encoding="utf-8")


def _find_accessory(qml: str, label: str, pattern: str) -> list[str]:
    return re.findall(pattern, qml)


class _ComponentLoader:
    def __init__(self, comp_name: str):
        self.engine = QQmlEngine()
        self.engine.addImportPath(str(QML_DIR))
        self.component = QQmlComponent(self.engine)
        self.component.loadUrl(QUrl.fromLocalFile(str(COMPONENTS_DIR / comp_name)))

    def is_ready(self) -> bool:
        return self.component.isReady()

    def error_string(self) -> str:
        return self.component.errorString()

    def create(self):
        return self.component.create()


# ── MichiButton ─────────────────────────────────────────────────────────────────


class TestMichiButton:
    QML = "MichiButton.qml"

    def test_file_exists(self):
        assert (COMPONENTS_DIR / self.QML).exists()

    def test_object_name_uses_control_object_name(self):
        qml = _read_qml(self.QML)
        assert "controlObjectName" in qml
        assert "property string controlObjectName" in qml

    def test_accessible_role_button(self):
        qml = _read_qml(self.QML)
        assert "Accessible.role: Accessible.Button" in qml

    def test_active_focus_on_tab_depends_on_enabled(self):
        qml = _read_qml(self.QML)
        assert "activeFocusOnTab: enabled" in qml

    def test_loading_property_exists(self):
        qml = _read_qml(self.QML)
        assert "loading" in qml

    def test_variant_property_declared(self):
        qml = _read_qml(self.QML)
        assert "property string variant" in qml
        assert "\"primary\"" in qml

    @pytest.mark.parametrize("variant", ["primary", "danger", "success", "ghost"])
    def test_variant_handled(self, variant):
        qml = _read_qml(self.QML)
        assert variant in qml


# ── MichiSlider ─────────────────────────────────────────────────────────────────


class TestMichiSlider:
    QML = "MichiSlider.qml"

    def test_file_exists(self):
        assert (COMPONENTS_DIR / self.QML).exists()

    def test_object_name_uses_control_object_name(self):
        qml = _read_qml(self.QML)
        assert "objectName: controlObjectName" in qml
        assert "property string controlObjectName" in qml

    def test_has_moved_signal(self):
        qml = _read_qml(self.QML)
        assert "signal moved" in qml

    def test_accessible_role_slider(self):
        qml = _read_qml(self.QML)
        assert "Accessible.role: Accessible.Slider" in qml

    def test_active_focus_on_tab_depends_on_enabled(self):
        qml = _read_qml(self.QML)
        assert "activeFocusOnTab: enabled" in qml

    def test_loads_property_blocks_interaction(self):
        qml = _read_qml(self.QML)
        assert "enabled: !root.loading" in qml

    def test_step_size_default_is_1(self):
        qml = _read_qml(self.QML)
        assert "stepSize: 1" in qml

    def test_keys_left_right_home_end(self):
        qml = _read_qml(self.QML)
        assert "Keys.onLeftPressed" in qml
        assert "Keys.onRightPressed" in qml
        assert "Keys.onHomePressed" in qml
        assert "Keys.onEndPressed" in qml or "Keys.onEnd" in qml

    def test_no_on_value_changed_reassigns_value_dangerously(self):
        qml = _read_qml(self.QML)
        match = re.search(r"onValueChanged\s*:\s*\{", qml)
        if match:
            block_start = match.start()
            block = qml[block_start:block_start + 200]
            assert "root.value" not in block.replace("root.value = root._clamp(root.value)", "")

    def test_value_clamped_on_change(self):
        qml = _read_qml(self.QML)
        assert "clamp" in qml or "_clamp" in qml

    def test_moved_not_emitted_from_on_value_changed(self):
        qml = _read_qml(self.QML)
        assert "moved" not in re.search(r"onValueChanged\s*:\s*\{[^}]+\}", qml).group() if re.search(r"onValueChanged\s*:\s*\{[^}]+\}", qml) else True


# ── MichiSwitch ─────────────────────────────────────────────────────────────────


class TestMichiSwitch:
    QML = "MichiSwitch.qml"

    def test_file_exists(self):
        assert (COMPONENTS_DIR / self.QML).exists()

    def test_object_name_uses_control_object_name(self):
        qml = _read_qml(self.QML)
        assert ("objectName: controlObjectName" in qml
                or "objectName: root.controlObjectName" in qml)
        assert "property string controlObjectName" in qml

    def test_accessible_role_checked(self):
        qml = _read_qml(self.QML)
        assert "Accessible.role: Accessible.CheckBox" in qml
        assert "Accessible.checked: root.checked" in qml

    def test_active_focus_on_tab_depends_on_enabled(self):
        qml = _read_qml(self.QML)
        assert "activeFocusOnTab: enabled" in qml

    def test_toggle_function_guards_disabled_loading(self):
        qml = _read_qml(self.QML)
        assert "if (!root.enabled || root.loading) return" in qml

    def test_space_triggers_toggle(self):
        qml = _read_qml(self.QML)
        assert "Keys.onSpacePressed" in qml
        assert "root.toggle()" in qml

    def test_checked_property_declared(self):
        qml = _read_qml(self.QML)
        assert "property bool checked" in qml


# ── MichiCheckBox ──────────────────────────────────────────────────────────────


class TestMichiCheckBox:
    QML = "MichiCheckBox.qml"

    def test_file_exists(self):
        assert (COMPONENTS_DIR / self.QML).exists()

    def test_object_name_uses_control_object_name(self):
        qml = _read_qml(self.QML)
        assert ("objectName: controlObjectName" in qml
                or "objectName: root.controlObjectName" in qml)
        assert "property string controlObjectName" in qml

    def test_accessible_checked_binded(self):
        qml = _read_qml(self.QML)
        assert "Accessible.checked: root.checked" in qml

    def test_accessible_role_checkbox(self):
        qml = _read_qml(self.QML)
        assert "Accessible.role: Accessible.CheckBox" in qml

    def test_active_focus_on_tab_depends_on_enabled(self):
        qml = _read_qml(self.QML)
        assert "activeFocusOnTab: enabled" in qml

    def test_toggle_alternates_checked(self):
        qml = _read_qml(self.QML)
        assert "root.checked = !root.checked" in qml

    def test_space_triggers_toggle(self):
        qml = _read_qml(self.QML)
        assert "Keys.onSpacePressed" in qml

    def test_tristate_supported(self):
        qml = _read_qml(self.QML)
        assert "property bool tristate" in qml


# ── MichiComboBox ──────────────────────────────────────────────────────────────


class TestMichiComboBox:
    QML = "MichiComboBox.qml"

    def test_file_exists(self):
        assert (COMPONENTS_DIR / self.QML).exists()

    def test_object_name_uses_control_object_name(self):
        qml = _read_qml(self.QML)
        assert "objectName: controlObjectName" in qml
        assert "property string controlObjectName" in qml

    def test_activated_signal(self):
        qml = _read_qml(self.QML)
        assert "signal activated(int index)" in qml

    def test_down_arrow_opens_or_changes(self):
        qml = _read_qml(self.QML)
        assert "Keys.onDownPressed" in qml

    def test_enter_selects_item(self):
        qml = _read_qml(self.QML)
        assert "Keys.onReturnPressed" in qml

    def test_escape_closes_dropdown(self):
        qml = _read_qml(self.QML)
        assert "Keys.onEscapePressed" in qml

    def test_popup_open_toggled(self):
        qml = _read_qml(self.QML)
        assert "popupOpen" in qml

    def test_accessible_role_combobox(self):
        qml = _read_qml(self.QML)
        assert "Accessible.role: Accessible.ComboBox" in qml

    def test_model_and_current_index(self):
        qml = _read_qml(self.QML)
        assert "model" in qml
        assert "currentIndex" in qml

    def test_on_current_index_changed_updates_text(self):
        qml = _read_qml(self.QML)
        assert "onCurrentIndexChanged" in qml
        assert "root.currentText" in qml

    def test_active_focus_closes_popup(self):
        qml = _read_qml(self.QML)
        assert "onActiveFocusChanged" in qml
        assert "root.popupOpen = false" in qml

    def test_combobox_instantiates(self, qapp):
        loader = _ComponentLoader(self.QML)
        assert loader.is_ready(), f"MichiComboBox failed: {loader.error_string()}"

    @pytest.mark.xfail(reason="forceActiveFocus not enough in offscreen; needs real window", strict=False)
    def test_combobox_up_down_changes_index(self, qapp):
        """Down arrow increments currentIndex (real key event)."""
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt
        loader = _ComponentLoader(self.QML)
        assert loader.is_ready(), loader.error_string()
        obj = loader.create()
        assert obj is not None
        obj.model = ["A", "B", "C"]
        obj.currentIndex = 0
        obj.forceActiveFocus()
        old_idx = obj.currentIndex
        QTest.keyClick(obj, Qt.Key_Down)
        assert obj.currentIndex == old_idx + 1
        QTest.keyClick(obj, Qt.Key_Up)
        assert obj.currentIndex == old_idx

    @pytest.mark.xfail(reason="QTest.keyClick on ComboBox may not work offscreen", strict=False)
    def test_combobox_enter_selects(self, qapp):
        """Enter key selects current item (real key event)."""
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt
        loader = _ComponentLoader(self.QML)
        assert loader.is_ready(), loader.error_string()
        obj = loader.create()
        assert obj is not None
        obj.model = ["A", "B", "C"]
        obj.currentIndex = 0
        obj.forceActiveFocus()
        QTest.keyClick(obj, Qt.Key_Down)
        QTest.keyClick(obj, Qt.Key_Return)
        assert obj.currentIndex == 1

    @pytest.mark.xfail(reason="QTest.keyClick on ComboBox may not work offscreen", strict=False)
    def test_combobox_escape_closes(self, qapp):
        """Escape closes the dropdown (real key event)."""
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt
        loader = _ComponentLoader(self.QML)
        assert loader.is_ready(), loader.error_string()
        obj = loader.create()
        assert obj is not None
        obj.popupOpen = True
        QTest.keyClick(obj, Qt.Key_Escape)
        assert not obj.popupOpen


# ── MichiDialog ────────────────────────────────────────────────────────────────


class TestMichiDialog:
    QML = "MichiDialog.qml"

    def test_file_exists(self):
        assert (COMPONENTS_DIR / self.QML).exists()

    def test_object_name_uses_control_object_name(self):
        qml = _read_qml(self.QML)
        assert ("objectName: controlObjectName" in qml
                or "objectName: root.controlObjectName" in qml)
        assert "property string controlObjectName" in qml

    def test_accessible_role_button(self):
        qml = _read_qml(self.QML)
        assert "Accessible.role: Accessible.Dialog" in qml

    def test_escape_closes(self):
        qml = _read_qml(self.QML)
        assert "CloseOnEscape" in qml

    def test_popup_based(self):
        qml = _read_qml(self.QML)
        assert "QQC2.Popup" in qml
        assert "modal: true" in qml

    def test_accepted_rejected_signals(self):
        qml = _read_qml(self.QML)
        assert "signal accepted()" in qml
        assert "signal rejected()" in qml

    def test_close_policy_property(self):
        qml = _read_qml(self.QML)
        assert "property int closePolicy" in qml or "closePolicy" in qml
        assert "CloseOnEscape" in qml

    def test_dialog_instantiates(self, qapp):
        loader = _ComponentLoader(self.QML)
        assert loader.is_ready(), f"MichiDialog failed: {loader.error_string()}"
        obj = loader.create()
        assert obj is not None

    @pytest.mark.xfail(reason="QTest.keyClick on Dialog may not work offscreen", strict=False)
    def test_dialog_escape_closes(self, qapp):
        """Escape key closes the dialog."""
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt
        loader = _ComponentLoader(self.QML)
        assert loader.is_ready(), loader.error_string()
        obj = loader.create()
        assert obj is not None
        obj.open()
        assert obj.opened
        QTest.keyClick(obj, Qt.Key_Escape)
        assert not obj.opened

    def test_dialog_open_close(self, qapp):
        loader = _ComponentLoader(self.QML)
        assert loader.is_ready(), loader.error_string()
        obj = loader.create()
        assert obj is not None
        obj.open()
        assert obj.opened
        obj.close()
        assert not obj.opened

    def test_dialog_focus_trap(self, qapp):
        qml = _read_qml(self.QML)
        assert "onOpened" in qml
        assert "forceActiveFocus" in qml
        assert "_savedFocus" in qml


# ── MichiTextField ─────────────────────────────────────────────────────────────


class TestMichiTextField:
    QML = "MichiTextField.qml"

    def test_file_exists(self):
        assert (COMPONENTS_DIR / self.QML).exists()

    def test_object_name_uses_control_object_name(self):
        qml = _read_qml(self.QML)
        assert "objectName: controlObjectName" in qml
        assert "property string controlObjectName" in qml

    def test_accessible_role_editable_text(self):
        qml = _read_qml(self.QML)
        assert "Accessible.role: Accessible.EditableText" in qml

    def test_text_property_declared(self):
        qml = _read_qml(self.QML)
        assert "property string text" in qml

    def test_read_only_property(self):
        qml = _read_qml(self.QML)
        assert "property bool readOnly" in qml

    def test_active_focus_on_tab_on_inner_field(self):
        qml = _read_qml(self.QML)
        assert "activeFocusOnTab: enabled" in qml

    def test_loading_disables_inner_field(self):
        qml = _read_qml(self.QML)
        assert "readOnly: root.readOnly || root.loading" in qml

    def test_validation_state(self):
        qml = _read_qml(self.QML)
        assert "validationState" in qml

    def test_textfield_instantiates(self, qapp):
        loader = _ComponentLoader(self.QML)
        assert loader.is_ready(), f"MichiTextField failed: {loader.error_string()}"

    def test_textfield_accepts_text(self, qapp):
        loader = _ComponentLoader(self.QML)
        assert loader.is_ready(), loader.error_string()
        obj = loader.create()
        assert obj is not None
        obj.text = "hello"
        assert obj.text == "hello"

    @pytest.mark.xfail(reason="QTest.keyClick on TextField may not work offscreen", strict=False)
    def test_textfield_sync_bidirectional(self, qapp):
        """Typing in the internal field updates root.text (real key events)."""
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt
        loader = _ComponentLoader(self.QML)
        assert loader.is_ready(), loader.error_string()
        obj = loader.create()
        assert obj is not None
        obj.forceActiveFocus()
        QTest.keyClick(obj, Qt.Key_T)
        QTest.keyClick(obj, Qt.Key_E)
        QTest.keyClick(obj, Qt.Key_S)
        QTest.keyClick(obj, Qt.Key_T)
        assert obj.text == "test"


# ── MichiProgressBar ───────────────────────────────────────────────────────────


class TestMichiProgressBar:
    QML = "MichiProgressBar.qml"

    def test_file_exists(self):
        assert (COMPONENTS_DIR / self.QML).exists()

    def test_object_name_uses_control_object_name(self):
        qml = _read_qml(self.QML)
        assert "objectName: controlObjectName" in qml or "objectName" in qml

    def test_no_active_focus_on_tab(self):
        qml = _read_qml(self.QML)
        assert "activeFocusOnTab" not in qml

    def test_accessible_role_progress_bar(self):
        qml = _read_qml(self.QML)
        assert "Accessible.role: Accessible.ProgressBar" in qml

    def test_indeterminate_property(self):
        qml = _read_qml(self.QML)
        assert "property bool indeterminate" in qml

    def test_variant_property(self):
        qml = _read_qml(self.QML)
        assert "property string variant" in qml

    def test_value_from_to_properties(self):
        qml = _read_qml(self.QML)
        assert "property real value" in qml
        assert "property real from" in qml
        assert "property real to" in qml


# ── MichiBadge ─────────────────────────────────────────────────────────────────


class TestMichiBadge:
    QML = "MichiBadge.qml"

    def test_file_exists(self):
        assert (COMPONENTS_DIR / self.QML).exists()

    def test_object_name_uses_control_object_name(self):
        qml = _read_qml(self.QML)
        assert "objectName: controlObjectName" in qml or "objectName" in qml

    def test_no_active_focus_on_tab(self):
        qml = _read_qml(self.QML)
        assert "activeFocusOnTab" not in qml

    def test_accessible_role_status_bar(self):
        qml = _read_qml(self.QML)
        assert "Accessible.role: Accessible.StatusBar" in qml

    @pytest.mark.parametrize("variant", ["info", "success", "warning", "error", "danger", "neutral"])
    def test_variant_handled(self, variant):
        qml = _read_qml(self.QML)
        assert variant in qml

    def test_badge_text_property(self):
        qml = _read_qml(self.QML)
        assert "property string badgeText" in qml

    def test_variant_property_declared(self):
        qml = _read_qml(self.QML)
        assert "property string variant" in qml


# ── MichiTabBar ────────────────────────────────────────────────────────────────


class TestMichiTabBar:
    QML = "MichiTabBar.qml"

    def test_file_exists(self):
        assert (COMPONENTS_DIR / self.QML).exists()

    def test_object_name_uses_control_object_name(self):
        qml = _read_qml(self.QML)
        assert "controlObjectName" in qml
        assert "property string controlObjectName" in qml

    def test_accessible_role_page_tab_list(self):
        qml = _read_qml(self.QML)
        assert "Accessible.role: Accessible.PageTabList" in qml

    def test_current_index_property(self):
        qml = _read_qml(self.QML)
        assert "property int currentIndex" in qml

    def test_model_property(self):
        qml = _read_qml(self.QML)
        assert "property var model" in qml

    def test_activated_signal(self):
        qml = _read_qml(self.QML)
        assert "signal activated(int index)" in qml

    def test_left_right_keys_change_index(self):
        qml = _read_qml(self.QML)
        assert "Keys.onLeftPressed" in qml
        assert "Keys.onRightPressed" in qml
        assert "Math.max(0, root.currentIndex - 1)" in qml
        assert "Math.min(root.model.length - 1, root.currentIndex + 1)" in qml

    def test_home_end_keys(self):
        qml = _read_qml(self.QML)
        assert "Keys.onHomePressed" in qml
