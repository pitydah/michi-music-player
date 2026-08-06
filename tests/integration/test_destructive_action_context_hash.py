"""Confirmation is bound to the ActionContext hash (Slice 3).

Confirming a destructive action for one context never authorizes a different
context: a different selection version, entity or parameter set produces a
different hash and the execution is rejected with CONFIRMATION_MISMATCH.
"""
from __future__ import annotations

from core.action_context import ActionContext
from core.confirmation_service import ConfirmationService
from core.service_container import ServiceContainer
from ui_qml_bridge.action_registry import ActionDescriptor, ActionRegistry


def _make_registry() -> ActionRegistry:
    container = ServiceContainer()
    container.register("confirmation_service", ConfirmationService())
    reg = ActionRegistry(container=container)
    action = ActionDescriptor(
        action_id="delete_track",
        title="Eliminar pista",
        category="track",
        destructive=True,
        requires_confirmation=True,
        handler=lambda ctx: {"ok": True, "entity": ctx.entity_id,
                             "version": ctx.selection_version},
    )
    reg.register(action)
    return reg


def _confirm(container: ServiceContainer, action_id: str,
             context: ActionContext) -> None:
    cs = container.require("confirmation_service")
    req = cs.confirm(action_id, command_hash=context.command_hash(action_id),
                     entity_refs=(context.public_ref,))
    approved = cs.approve(req.token)
    assert approved is not None


def test_confirm_and_execute_same_context_succeeds() -> None:
    reg = _make_registry()
    ctx_a = ActionContext(entity_type="track", entity_id="uid-1",
                          public_ref="track_42", selection_version=3)
    _confirm(reg._container, "delete_track", ctx_a)
    result = reg.execute("delete_track", ctx_a)
    assert result == {"ok": True, "entity": "uid-1", "version": 3}


def test_execute_different_context_hash_is_rejected() -> None:
    reg = _make_registry()
    ctx_a = ActionContext(entity_type="track", entity_id="uid-1",
                          public_ref="track_42", selection_version=3)
    ctx_b = ActionContext(entity_type="track", entity_id="uid-2",
                          public_ref="track_43", selection_version=4)
    _confirm(reg._container, "delete_track", ctx_a)
    result = reg.execute("delete_track", ctx_b)
    assert result["code"] == "CONFIRMATION_MISMATCH"
    assert result["context_hash"] == ctx_b.command_hash("delete_track")


def test_execute_without_confirmation_requires_it() -> None:
    reg = _make_registry()
    ctx = ActionContext(entity_type="track", entity_id="uid-1",
                        selection_version=1)
    result = reg.execute("delete_track", ctx)
    assert result["code"] == "CONFIRMATION_REQUIRED"
    assert result["context_hash"] == ctx.command_hash("delete_track")


def test_selection_version_change_invalidates_confirmation() -> None:
    """Same entity but a newer selection version is a different context."""
    reg = _make_registry()
    ctx_old = ActionContext(entity_type="track", entity_id="uid-1",
                            selection_version=2)
    ctx_new = ActionContext(entity_type="track", entity_id="uid-1",
                            selection_version=9)
    _confirm(reg._container, "delete_track", ctx_old)
    result = reg.execute("delete_track", ctx_new)
    assert result["code"] == "CONFIRMATION_MISMATCH"
