from __future__ import annotations

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
QML = ROOT / "ui_qml"


def test_static_uiux_audit_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/audit_qml_ui.py"), "--strict", "--json"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert result.returncode == 0, payload["issues"]
    assert payload["ok"] is True


def test_contextual_search_has_one_visual_owner() -> None:
    for relative, removed_id in (
        ("pages/library/LibraryPage.qml", "librarySearch"),
        ("pages/radio/RadioPage.qml", "radioSearch"),
        ("pages/playlists/PlaylistsPage.qml", "playlistSearch"),
    ):
        source = (QML / relative).read_text(encoding="utf-8")
        assert "headerSearchEnabled: true" in source
        assert f"id: {removed_id}" not in source


def test_foundation_controls_share_geometry_and_focus_tokens() -> None:
    icon_button = (QML / "components/MichiIconButton.qml").read_text(encoding="utf-8")
    search = (QML / "components/MichiSearchField.qml").read_text(encoding="utf-8")
    segmented = (QML / "components/MichiSegmentedControl.qml").read_text(encoding="utf-8")

    assert "property bool circular: false" in icon_button
    assert "root.circular ? width / 2 : MichiTheme.radius.md" in icon_button
    assert "MichiTheme.focusWidth" in icon_button
    assert "radius: MichiTheme.radius.md" in search
    assert "implicitHeight: MichiTheme.minimumInteractiveSize" in segmented


def test_original_texture_assets_are_valid_svg() -> None:
    for filename in ("michi-grain.svg", "michi-contours.svg"):
        path = QML / "assets/textures" / filename
        assert path.exists()
        root = ET.parse(path).getroot()
        assert root.tag.endswith("svg")


def test_product_copy_does_not_invent_a_premium_paywall() -> None:
    ui_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in QML.rglob("*.qml")
    ).lower()
    assert "suscripción premium" not in ui_text
    assert "suscripcion premium" not in ui_text


def test_shell_owns_loading_and_error_chrome_once() -> None:
    app_shell = (QML / "shell/AppShell.qml").read_text(encoding="utf-8")
    page_stack = (QML / "shell/PageStack.qml").read_text(encoding="utf-8")
    assert "id: loadingOverlay" in app_shell
    assert "id: errorOverlay" in app_shell
    assert "id: loadingIndicator" not in page_stack
    assert "Error de ruta" not in page_stack
