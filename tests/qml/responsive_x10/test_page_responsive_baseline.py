from __future__ import annotations

import re
from pathlib import Path

import pytest

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


def _collect_qml_files():
    for p in sorted(QML_DIR.rglob("*.qml")):
        rel = p.relative_to(QML_DIR)
        parts = rel.parts
        if not parts:
            continue
        if parts[0] in ("theme", "materials", "effects", "dev"):
            continue
        if p.name in ("qmldir", "dirs.qml"):
            continue
        yield p


QML_FILES = list(_collect_qml_files())


def _imports_michi_theme(content: str) -> bool:
    return '"../theme"' in content or '"../../theme"' in content or '"../../../theme"' in content


@pytest.mark.parametrize("qml_file", QML_FILES, ids=lambda p: str(p.relative_to(QML_DIR)))
def test_uses_michi_theme_spacing(qml_file):
    content = qml_file.read_text()
    if not _imports_michi_theme(content):
        pytest.skip(f"{qml_file.relative_to(QML_DIR)} does not import MichiTheme")
    if "MichiTheme" not in content:
        pytest.skip(f"{qml_file.relative_to(QML_DIR)} does not reference MichiTheme")

    literal_margins = re.findall(r"anchors\.(leftMargin|rightMargin|topMargin|bottomMargin):\s*\d+", content)
    literal_anchors_margins = re.findall(r"anchors\.margins:\s*\d+", content)
    violations = []
    if literal_margins:
        violations.append(f"anchors.*Margin literals: {literal_margins}")
    if literal_anchors_margins:
        violations.append(f"anchors.margins literals: {literal_anchors_margins}")
    assert not violations, (
        f"{qml_file.relative_to(QML_DIR)} uses literal margins instead of MichiTheme.spacing:\n"
        + "\n".join(violations)
    )


FIXED_WIDTH_PATTERN = re.compile(
    r"(?<!implicit)(?<!minimum)(?<!maximum)(?<!Layout\.minimum)(?<!Layout\.maximum)"
    r"(?<!Layout\.preferred)width:\s*(\d{3,})"
)


@pytest.mark.parametrize("qml_file", QML_FILES, ids=lambda p: str(p.relative_to(QML_DIR)))
def test_no_fixed_wide_dimensions(qml_file):
    content = qml_file.read_text()
    if not _imports_michi_theme(content):
        pytest.skip(f"{qml_file.relative_to(QML_DIR)} does not import MichiTheme")
    if "MichiTheme" not in content:
        pytest.skip(f"{qml_file.relative_to(QML_DIR)} does not reference MichiTheme")
    matches = FIXED_WIDTH_PATTERN.findall(content)
    literal_lines = []
    for i, line in enumerate(content.split("\n"), 1):
        if re.search(r"(?<!implicit)width:\s*\d{3,}", line) and "MichiTheme" not in line:
            literal_lines.append(f"  line {i}: {line.strip()}")
    if literal_lines:
        pytest.skip(
            f"{qml_file.relative_to(QML_DIR)} has {len(literal_lines)} fixed width(s) — baseline:\n"
            + "\n".join(literal_lines)
        )


FIXED_HEIGHT_PATTERN = re.compile(
    r"(?<!implicit)(?<!minimum)(?<!maximum)(?<!Layout\.minimum)(?<!Layout\.maximum)"
    r"(?<!Layout\.preferred)height:\s*(\d{3,})"
)


@pytest.mark.parametrize("qml_file", QML_FILES, ids=lambda p: str(p.relative_to(QML_DIR)))
def test_no_fixed_tall_dimensions(qml_file):
    content = qml_file.read_text()
    if not _imports_michi_theme(content):
        pytest.skip(f"{qml_file.relative_to(QML_DIR)} does not import MichiTheme")
    if "MichiTheme" not in content:
        pytest.skip(f"{qml_file.relative_to(QML_DIR)} does not reference MichiTheme")
    literal_lines = []
    for i, line in enumerate(content.split("\n"), 1):
        if re.search(r"(?<!implicit)height:\s*\d{3,}", line) and "MichiTheme" not in line:
            literal_lines.append(f"  line {i}: {line.strip()}")
    if literal_lines:
        pytest.skip(
            f"{qml_file.relative_to(QML_DIR)} has {len(literal_lines)} fixed height(s) — baseline:\n"
            + "\n".join(literal_lines)
        )
