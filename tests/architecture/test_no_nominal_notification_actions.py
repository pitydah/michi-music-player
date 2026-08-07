"""Notification actions must be real: no ``{"ok": True, "action": ...}``
without dispatch; every action id maps to a real dispatch branch or an
explicit unavailable status (ADR-005).
"""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _read_source() -> str:
    path = PROJECT_ROOT / "core" / "notification_action_service.py"
    return path.read_text(encoding="utf-8")


def test_no_nominal_ok_true_action_return() -> None:
    import ast

    path = PROJECT_ROOT / "core" / "notification_action_service.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders = []

    def visit(node):
        if isinstance(node, ast.Dict):
            keys = {}
            for k, v in zip(node.keys, node.values, strict=True):
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    keys[k.value] = v
            if ("ok" in keys and isinstance(keys["ok"], ast.Constant)
                    and keys["ok"].value is True
                    and "action" in keys):
                offenders.append(ast.get_source_segment(
                    path.read_text(encoding="utf-8"), node) or "<dict>")
        for child in ast.iter_child_nodes(node):
            visit(child)

    visit(tree)
    assert offenders == [], (
        f"Found nominal ok=True/action dict returns: {offenders}"
    )


def test_every_action_id_has_dispatch_branch() -> None:
    from core.notification_action_service import NotificationActionService

    svc = NotificationActionService()
    for action_id in svc.dispatch_ids():
        result = svc.route(action_id, {})
        assert result.get("status") in (
            "TARGET_UNAVAILABLE", "CAPABILITY_UNAVAILABLE",
        ), f"{action_id} must dispatch to a real branch, got {result}"


def test_unknown_action_is_action_not_found() -> None:
    from core.notification_action_service import NotificationActionService

    result = NotificationActionService().route("bogus_action", {})
    assert result["ok"] is False
    assert result["status"] == "ACTION_NOT_FOUND"


def test_unwired_retry_and_undo_are_capability_unavailable() -> None:
    from core.notification_action_service import NotificationActionService

    svc = NotificationActionService()
    retry_result = svc.route("retry", {"job_id": "j1"})
    assert retry_result["status"] == "CAPABILITY_UNAVAILABLE"
    undo_result = svc.route("undo", {"operation_id": "o1"})
    assert undo_result["status"] == "CAPABILITY_UNAVAILABLE"
