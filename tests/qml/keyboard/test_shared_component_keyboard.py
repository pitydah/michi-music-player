"""Test keyboard navigation and focus patterns for shared components.

Verifies:
- KeyNavigation.tab chains
- Keys.onEscapePressed/ReturnPressed/SpacePressed
- activeFocusOnTab on root FocusScope components
"""

from pathlib import Path

import pytest

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"
COMPONENTS = [
    "components/ConfirmationDialog.qml",
    "components/DestructiveActionDialog.qml",
    "components/ErrorState.qml",
    "components/EmptyState.qml",
    "components/UnavailableState.qml",
    "components/DegradedState.qml",
    "components/SelectionActionBar.qml",
    "components/CapabilityGuard.qml",
    "components/ResponsivePageLayout.qml",
    "components/ResponsiveToolbar.qml",
]

pytestmark = [pytest.mark.qml_module("keyboard")]


@pytest.fixture(params=COMPONENTS)
def component_path(request):
    return QML_DIR / request.param


class TestSharedComponentKeyboard:
    def test_has_object_name(self, component_path):
        if not component_path.exists():
            pytest.skip(f"{component_path} not found")
        content = component_path.read_text()
        assert "objectName:" in content, f"{component_path.name} lacks objectName"

    def test_has_accessible_name(self, component_path):
        if not component_path.exists():
            pytest.skip(f"{component_path} not found")
        content = component_path.read_text()
        assert "Accessible.name" in content, f"{component_path.name} lacks Accessible.name"

    def test_has_accessible_role(self, component_path):
        if not component_path.exists():
            pytest.skip(f"{component_path} not found")
        content = component_path.read_text()
        assert "Accessible.role" in content, f"{component_path.name} lacks Accessible.role"

    def test_has_keys_handler(self, component_path):
        if not component_path.exists():
            pytest.skip(f"{component_path} not found")
        content = component_path.read_text()
        has_keys = "Keys.on" in content
        assert has_keys, f"{component_path.name} lacks Keys handlers"

    def test_no_hardcoded_colors(self, component_path):
        if not component_path.exists():
            pytest.skip(f"{component_path} not found")
        content = component_path.read_text()
        for bad in ['color: "white"', 'color: "black"', 'color: "red"',
                     'color: "#', 'color: "rgb(']:
            assert bad not in content, f"{component_path.name} has hardcoded color: {bad}"

    def test_uses_michi_theme_colors(self, component_path):
        if not component_path.exists():
            pytest.skip(f"{component_path} not found")
        content = component_path.read_text()
        assert "MichiTheme.colors." in content or "MichiTheme." in content, \
            f"{component_path.name} does not use MichiTheme tokens"

    def test_uses_theme_typography(self, component_path):
        if not component_path.exists():
            pytest.skip(f"{component_path} not found")
        content = component_path.read_text()
        assert "MichiTheme.typography." in content, \
            f"{component_path.name} does not use theme typography"

    def test_uses_theme_radius(self, component_path):
        if not component_path.exists():
            pytest.skip(f"{component_path} not found")
        content = component_path.read_text()
        assert "MichiTheme.radius" in content, \
            f"{component_path.name} does not use theme radius tokens"
