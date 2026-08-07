"""Actions require an explicit ActionContext (Slice 3).

Executing without a context is deprecated: it logs a warning and destructive
actions without a bound handler are refused with REQUIRE_CONTEXT.
"""
from __future__ import annotations

import logging

from ui_qml_bridge.action_registry import ActionDescriptor, ActionRegistry


def test_execute_without_context_logs_deprecation(caplog) -> None:
    reg = ActionRegistry()
    with caplog.at_level(logging.WARNING, logger="michi.action_registry"):
        reg.execute("navigate_home")
    assert any(
        "without ActionContext is deprecated" in r.message
        for r in caplog.records
        if r.name == "michi.action_registry"
    )


def test_execute_with_context_does_not_log_deprecation(caplog) -> None:
    from core.action_context import ActionContext

    reg = ActionRegistry()
    action = ActionDescriptor(
        action_id="ctx_action",
        title="Ctx",
        category="test",
        handler=lambda ctx: {"ok": True, "entity": ctx.entity_id},
    )
    reg.register(action)
    with caplog.at_level(logging.WARNING, logger="michi.action_registry"):
        result = reg.execute("ctx_action", ActionContext(entity_id="42"))
    assert result["ok"] is True
    assert result["entity"] == "42"
    assert not any("deprecated" in r.message for r in caplog.records)


def test_destructive_action_without_context_requires_context() -> None:
    reg = ActionRegistry()
    action = ActionDescriptor(
        action_id="destructive_no_handler",
        title="Destructive",
        category="test",
        destructive=True,
    )
    reg.register(action)
    result = reg.execute("destructive_no_handler")
    assert result == {"ok": False, "code": "REQUIRE_CONTEXT",
                      "action_id": "destructive_no_handler",
                      "message": "This action requires an explicit ActionContext"}


def test_descriptor_requires_context_flag_is_enforced() -> None:
    reg = ActionRegistry()
    action = ActionDescriptor(
        action_id="explicit_only",
        title="Explicit",
        category="test",
        handler=lambda: {"ok": True},
        requires_context=True,
    )
    reg.register(action)
    result = reg.execute("explicit_only")
    assert result["code"] == "REQUIRE_CONTEXT"


def test_descriptor_requires_context_flag_declares_requirement() -> None:
    """The descriptor contract surfaces the context requirement to callers."""
    action = ActionDescriptor(
        action_id="a", title="A", category="test",
        destructive=True, requires_context=True,
    )
    assert action.destructive is True
    assert action.requires_context is True
