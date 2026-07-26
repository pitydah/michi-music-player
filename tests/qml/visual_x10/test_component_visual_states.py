from __future__ import annotations

import re
from pathlib import Path

import pytest

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"
COMPONENTS_DIR = QML_DIR / "components"

MICHI_COMPONENTS = sorted(
    str(p.relative_to(COMPONENTS_DIR))
    for p in COMPONENTS_DIR.rglob("Michi*.qml")
)

FOUNDATION_SUBDIRS = {"foundations", "states", "layout"}


def _is_foundation(rel_path: str) -> bool:
    return any(rel_path.startswith(d + "/") for d in FOUNDATION_SUBDIRS)


def _is_foundation_or_mock(content: str) -> bool:
    return "QtObject" in content or "export function" in content


@pytest.mark.parametrize("rel_path", MICHI_COMPONENTS)
def test_michi_component_file_exists(rel_path):
    path = COMPONENTS_DIR / rel_path
    assert path.exists(), f"Missing component: {path}"


@pytest.mark.parametrize("rel_path", MICHI_COMPONENTS)
def test_michi_component_object_name(rel_path):
    if _is_foundation(rel_path):
        pytest.skip(f"{rel_path} is a foundation — objectName optional")
    content = (COMPONENTS_DIR / rel_path).read_text()
    assert "objectName" in content or "id: root" in content, \
        f"{rel_path} lacks objectName"


@pytest.mark.parametrize("rel_path", MICHI_COMPONENTS)
def test_michi_component_accessible_role(rel_path):
    if _is_foundation(rel_path):
        pytest.skip(f"{rel_path} is a foundation — Accessible.role optional")
    if Path(rel_path).name in _EXEMPT_ACCESSIBLE_ROLE:
        pytest.skip(f"{rel_path} exempted from Accessible.role check")
    content = (COMPONENTS_DIR / rel_path).read_text()
    assert "Accessible.role" in content, f"{rel_path} lacks Accessible.role"


_EXEMPT_ACCESSIBLE_ROLE = {
    "MichiFeatureCard.qml",
    "MichiPageHeader.qml",
}

_EXEMPT_ACCESSIBLE_NAME = {
    "MichiWarmSlider.qml",
}


@pytest.mark.parametrize("rel_path", MICHI_COMPONENTS)
def test_michi_component_accessible_name(rel_path):
    if _is_foundation(rel_path):
        pytest.skip(f"{rel_path} is a foundation — Accessible.name optional")
    if Path(rel_path).name in _EXEMPT_ACCESSIBLE_NAME:
        pytest.skip(f"{rel_path} exempted from Accessible.name check")
    content = (COMPONENTS_DIR / rel_path).read_text()
    has_name = "Accessible.name" in content or "accessibleName" in content
    assert has_name, f"{rel_path} lacks Accessible.name"


HARDCODED_PATTERNS = [
    ("color literal", r'color:\s*["\']#'),
    ("anchors.margins literal", r"anchors\.margins:\s*\d+"),
    ("width literal > 50", r"(?<!implicit)width:\s*[5-9]\d{2,}"),
    ("height literal > 50", r"(?<!implicit)height:\s*[5-9]\d{2,}"),
    ("pixelSize literal", r"pixelSize:\s*\d+"),
    ("spacing literal", r"spacing:\s*\d+"),
]


def _is_exempt_hardcoded(rel_path: str) -> bool:
    exempt = {
        "MichiAlbumRow.qml", "MichiBanner.qml", "MichiDoubleSpinBox.qml",
        "MichiLibraryToolbar.qml", "MichiPageHeader.qml",
        "MichiSegmentedControl.qml", "MichiTabBar.qml", "MichiToast.qml",
        "MichiTrackRow.qml",
    }
    return Path(rel_path).name in exempt


@pytest.mark.parametrize("rel_path", MICHI_COMPONENTS)
def test_no_obvious_hardcoded_values(rel_path):
    content = (COMPONENTS_DIR / rel_path).read_text()
    if _is_foundation_or_mock(content):
        pytest.skip(f"{rel_path} is a foundation/mock — no theme enforcement expected")
    if "MichiTheme" not in content:
        pytest.skip(f"{rel_path} does not import MichiTheme — skip hardcoded check")
    if _is_exempt_hardcoded(rel_path):
        pytest.skip(f"{rel_path} exempted from hardcoded check")
    violations = []
    for label, pattern in HARDCODED_PATTERNS:
        matches = re.findall(pattern, content)
        if matches:
            violations.append(f"  {label}: {matches}")
    assert not violations, f"{rel_path} has potential hardcoded values:\n" + "\n".join(violations)
