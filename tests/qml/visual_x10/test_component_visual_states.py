from __future__ import annotations

from pathlib import Path

import pytest

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"
COMPONENTS_DIR = QML_DIR / "components"

MICHI_COMPONENTS = sorted(
    str(p.relative_to(COMPONENTS_DIR))
    for p in COMPONENTS_DIR.rglob("Michi*.qml")
)


@pytest.mark.parametrize("rel_path", MICHI_COMPONENTS)
def test_michi_component_file_exists(rel_path):
    path = COMPONENTS_DIR / rel_path
    assert path.exists(), f"Missing component: {path}"


@pytest.mark.parametrize("rel_path", MICHI_COMPONENTS)
def test_michi_component_object_name(rel_path):
    content = (COMPONENTS_DIR / rel_path).read_text()
    assert "objectName" in content, f"{rel_path} lacks objectName"


@pytest.mark.parametrize("rel_path", MICHI_COMPONENTS)
def test_michi_component_accessible_role(rel_path):
    content = (COMPONENTS_DIR / rel_path).read_text()
    assert "Accessible.role" in content, f"{rel_path} lacks Accessible.role"


@pytest.mark.parametrize("rel_path", MICHI_COMPONENTS)
def test_michi_component_accessible_name(rel_path):
    content = (COMPONENTS_DIR / rel_path).read_text()
    assert "Accessible.name" in content, f"{rel_path} lacks Accessible.name"


HARDCODED_PATTERNS = [
    ("color literal", r'color:\s*["\']#'),
    ("anchors.margins literal", r"anchors\.margins:\s*\d+"),
    ("width literal > 50", r"(?<!implicit)width:\s*[5-9]\d{2,}"),
    ("height literal > 50", r"(?<!implicit)height:\s*[5-9]\d{2,}"),
    ("pixelSize literal", r"pixelSize:\s*\d+"),
    ("spacing literal", r"spacing:\s*\d+"),
]


def _is_foundation_or_mock(content: str) -> bool:
    return "QtObject" in content or "export function" in content


@pytest.mark.parametrize("rel_path", MICHI_COMPONENTS)
def test_no_obvious_hardcoded_values(rel_path):
    content = (COMPONENTS_DIR / rel_path).read_text()
    if _is_foundation_or_mock(content):
        pytest.skip(f"{rel_path} is a foundation/mock — no theme enforcement expected")
    if "MichiTheme" not in content:
        pytest.skip(f"{rel_path} does not import MichiTheme — skip hardcoded check")
    violations = []
    for label, pattern in HARDCODED_PATTERNS:
        import re
        matches = re.findall(pattern, content)
        if matches:
            violations.append(f"  {label}: {matches}")
    assert not violations, f"{rel_path} has potential hardcoded values:\n" + "\n".join(violations)
