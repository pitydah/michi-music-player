"""SettingsService.reset_all must be transactional (ADR-005): no bare per-key
loop returning ``ok: not errors``, no nominal ``open()`` without navigation
dispatch.
"""
from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SETTINGS_SERVICE = PROJECT_ROOT / "core" / "settings_service.py"


def _source() -> str:
    return SETTINGS_SERVICE.read_text(encoding="utf-8")


def _function_source(tree: ast.Module, name: str) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def test_reset_all_has_compensation_branch() -> None:
    """reset_all must contain a rollback/compensation path, not a bare loop."""
    tree = ast.parse(_source())
    fn = _function_source(tree, "reset_all")
    assert fn is not None, "reset_all() must exist"
    text = ast.get_source_segment(_source(), fn) or ""

    assert any(token in text for token in ("rolled_back", "rollback", "compensat")), (
        "reset_all() has no compensation/rollback branch"
    )
    assert "reversed(applied)" in text or "previous_snapshot" in text, (
        "reset_all() must capture previous values to compensate"
    )


def test_reset_all_not_bare_per_key_loop() -> None:
    """No per-key loop whose result is simply ``ok: not errors``."""
    tree = ast.parse(_source())
    fn = _function_source(tree, "reset_all")
    text = ast.get_source_segment(_source(), fn) or ""
    assert "not errors" not in text, "bare ok=not errors semantics found"
    assert '"status"' in text, "reset_all() must report an explicit status"


def test_reset_all_reports_restart_required() -> None:
    tree = ast.parse(_source())
    fn = _function_source(tree, "reset_all")
    text = ast.get_source_segment(_source(), fn) or ""
    assert "restart_required" in text, "reset_all() must report restart-required keys"


def test_open_delegates_navigation_or_is_absent() -> None:
    """open() must not return nominal success without navigation dispatch."""
    tree = ast.parse(_source())
    fn = _function_source(tree, "open")
    if fn is None:
        return
    text = ast.get_source_segment(_source(), fn) or ""
    assert "navigate" in text or "navigation" in text, (
        "open() must delegate to NavigationService"
    )
    assert "NAVIGATION_UNAVAILABLE" in text or "NAVIGATION_REQUESTED" in text, (
        "open() must report real dispatch status"
    )
