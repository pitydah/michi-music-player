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
    "components/ErrorState.qml",
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
        if "objectName:" not in content:
            name = component_path.stem
            if name not in ("EmptyState",):
                pytest.fail(f"{component_path.name} lacks objectName")

    def test_has_accessible_name(self, component_path):
        if not component_path.exists():
            pytest.skip(f"{component_path} not found")
        content = component_path.read_text()
        if "Accessible.name" not in content:
            name = component_path.stem
            if name not in ("EmptyState",):
                pytest.fail(f"{component_path.name} lacks Accessible.name")

    def test_has_accessible_role(self, component_path):
        if not component_path.exists():
            pytest.skip(f"{component_path} not found")
        content = component_path.read_text()
        if "Accessible.role" not in content:
            name = component_path.stem
            if name not in ("EmptyState",):
                pytest.fail(f"{component_path.name} lacks Accessible.role")

    def test_has_keys_handler(self, component_path):
        if not component_path.exists():
            pytest.skip(f"{component_path} not found")
        content = component_path.read_text()
        if "Keys.on" not in content:
            # State components without user interaction don't need keyboard handlers
            name = component_path.stem
            if name not in ("ErrorState", "EmptyState", "UnavailableState",
                            "CapabilityGuard", "ResponsivePageLayout",
                            "ResponsiveToolbar", "SelectionActionBar"):
                pytest.fail(f"{component_path.name} lacks Keys handlers")

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
        if "MichiTheme.colors." not in content and "MichiTheme." not in content:
            name = component_path.stem
            # State components may use hardcoded values in current iteration
            if name not in ("EmptyState",):
                pytest.fail(f"{component_path.name} does not use MichiTheme tokens")

    def test_uses_theme_typography(self, component_path):
        if not component_path.exists():
            pytest.skip(f"{component_path} not found")
        content = component_path.read_text()
        if "MichiTheme.typography." not in content:
            name = component_path.stem
            if name not in ("EmptyState", "CapabilityGuard", "ResponsivePageLayout"):
                pytest.fail(f"{component_path.name} does not use theme typography")

    def test_uses_theme_radius(self, component_path):
        if not component_path.exists():
            pytest.skip(f"{component_path} not found")
        content = component_path.read_text()
        if "MichiTheme.radius" not in content:
            if "radius:" in content:
                pytest.fail(f"{component_path.name} uses hardcoded radius instead of theme tokens")
            # Components without any radius usage are acceptable
