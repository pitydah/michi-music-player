from __future__ import annotations

import json
from pathlib import Path

import pytest

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"
ROOT = QML_DIR.parent
PAGE_FILES = sorted(QML_DIR.rglob("*.qml"))

BASELINE_PATH = ROOT / "docs" / "uiux" / "baselines" / "accessibility-audit.json"


def _load_known_debt() -> tuple[set[str], set[str]]:
    role_missing: set[str] = set()
    name_missing: set[str] = set()
    try:
        data = json.loads(BASELINE_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return role_missing, name_missing
    for key in data.get("fingerprints", {}):
        parts = key.split(":", 2)
        if len(parts) < 3:
            continue
        file_rel, _control, detail = parts
        if "missing Accessible.role" in detail:
            role_missing.add(file_rel)
        if "missing Accessible.name" in detail:
            name_missing.add(file_rel)
    # Casos adicionales no detectados por el baseline audit
    name_missing.add("Main.qml")
    name_missing.add("pages/library/LibrarySearchField.qml")
    name_missing.add("pages/library/SourceEditorDialog.qml")
    name_missing.add("pages/library/SourceExclusionEditor.qml")
    name_missing.add("pages/library/album/AlbumViewSelector.qml")
    name_missing.add("pages/lyrics/LyricsEditDialog.qml")
    name_missing.add("pages/playlists/SmartPlaylistEditor.qml")
    name_missing.add("pages/radio/RadioEditDialog.qml")
    role_missing.add("Main.qml")
    return role_missing, name_missing


KNOWN_MISSING_ROLE, KNOWN_MISSING_OBJECTNAME = _load_known_debt()


def _is_component(path: Path) -> bool:
    rel = path.relative_to(QML_DIR)
    return str(rel).startswith("components/")


def _is_theme(path: Path) -> bool:
    rel = path.relative_to(QML_DIR)
    return str(rel).startswith("theme/")


def _is_material(path: Path) -> bool:
    rel = path.relative_to(QML_DIR)
    return str(rel).startswith("materials/") or str(rel).startswith("effects/")


def _is_import_or_qmldir(path: Path) -> bool:
    return path.name in ("qmldir", "dirs.qml")


PAGE_FILES_FILTERED = [
    p for p in PAGE_FILES
    if not _is_component(p) and not _is_theme(p)
    and not _is_material(p) and not _is_import_or_qmldir(p)
]


def _rel(path: Path) -> str:
    return str(path.relative_to(QML_DIR))


def _role_params():
    result = []
    for p in PAGE_FILES_FILTERED:
        rel = _rel(p)
        marks = []
        if rel in KNOWN_MISSING_ROLE:
            marks.append(pytest.mark.xfail(strict=True, reason="Legacy accessibility debt"))
        result.append(pytest.param(p, marks=marks, id=rel))
    return result


def _name_params():
    result = []
    for p in PAGE_FILES_FILTERED:
        rel = _rel(p)
        marks = []
        if rel in KNOWN_MISSING_OBJECTNAME:
            marks.append(pytest.mark.xfail(strict=True, reason="Legacy accessibility debt"))
        result.append(pytest.param(p, marks=marks, id=rel))
    return result


@pytest.mark.parametrize("qml_file", _role_params())
def test_page_has_accessible_role(qml_file):
    content = qml_file.read_text()
    assert "Accessible.role" in content, (
        f"{qml_file.relative_to(QML_DIR)} lacks Accessible.role on root"
    )


@pytest.mark.parametrize("qml_file", _name_params())
def test_page_has_object_name(qml_file):
    content = qml_file.read_text()
    assert "objectName" in content, (
        f"{qml_file.relative_to(QML_DIR)} lacks objectName on root"
    )
