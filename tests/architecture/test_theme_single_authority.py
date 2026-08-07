"""Theme/Accessibility single authority — state lives in the services.

Source scan: ``theme_bridge`` and ``accessibility_bridge`` must have NO direct
QSettings access for theme/accessibility keys (no ``SETTINGS``/``settings_manager``
imports) and no state attributes of their own: they only re-expose service
state. The canonical services own the state attributes.
"""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

THEME_BRIDGE = PROJECT_ROOT / "ui_qml_bridge" / "theme_bridge.py"
A11Y_BRIDGE = PROJECT_ROOT / "ui_qml_bridge" / "accessibility_bridge.py"
THEME_SERVICE = PROJECT_ROOT / "core" / "theme_service.py"
A11Y_SERVICE = PROJECT_ROOT / "core" / "accessibility_service.py"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _no_qsettings_access(path: Path) -> list[str]:
    src = _source(path)
    violations: list[str] = []
    if "SETTINGS" in src:
        violations.append("direct SETTINGS reference")
    if "settings_manager" in src:
        violations.append("settings_manager import")
    if "setValue" in src or ".value(" in src:
        violations.append("direct settings read/write")
    return violations


def test_theme_bridge_has_no_qsettings_access() -> None:
    assert _no_qsettings_access(THEME_BRIDGE) == []


def test_accessibility_bridge_has_no_qsettings_access() -> None:
    assert _no_qsettings_access(A11Y_BRIDGE) == []


def test_theme_service_owns_theme_state() -> None:
    src = _source(THEME_SERVICE)
    for attr in ("_theme", "_accent_color", "_compact_mode"):
        assert attr in src, f"ThemeService must own state attribute {attr}"
    assert "backgroundChanged" in src
    assert "register_consumer" in src
    assert "health" in src


def test_accessibility_service_owns_a11y_state() -> None:
    src = _source(A11Y_SERVICE)
    for attr in ("_font_scale", "_high_contrast", "_reduced_motion",
                 "_reduce_transparency", "_focus_indicators", "_mono", "_balance"):
        assert attr in src, f"AccessibilityService must own state attribute {attr}"
    assert "register_consumer" in src
    assert "health" in src


def test_bridges_delegate_to_service_state() -> None:
    theme_src = _source(THEME_BRIDGE)
    assert "self._service" in theme_src
    a11y_src = _source(A11Y_BRIDGE)
    assert "self._svc" in a11y_src


def test_bridges_register_as_consumers() -> None:
    theme_src = _source(THEME_BRIDGE)
    assert "register_consumer" in theme_src
    a11y_src = _source(A11Y_BRIDGE)
    assert "register_consumer" in a11y_src


def test_background_extraction_has_no_parallel_theme_state() -> None:
    bg = _source(PROJECT_ROOT / "core" / "background_theme_service.py")
    assert "SETTINGS" not in bg
    assert "settings_manager" not in bg
