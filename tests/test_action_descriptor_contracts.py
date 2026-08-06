"""ActionDescriptor-driven registration validates against real container.

New actions register through ActionDescriptor with a service_key + method;
``validate_all`` must check the REAL ServiceContainer contracts
(container.contains + callable on the resolved service), not loose getattr.
"""
from __future__ import annotations

from core.favorite_service import FavoriteService
from core.service_container import ServiceContainer
from ui_qml_bridge.action_registry import ActionDescriptor, ActionRegistry


def _container() -> ServiceContainer:
    c = ServiceContainer()
    c.register("favorite_service", FavoriteService())
    return c


def test_valid_descriptor_validates_clean() -> None:
    reg = ActionRegistry(container=_container())
    action = ActionDescriptor(
        action_id="favorite_status",
        title="Estado favorito",
        category="track",
        service_key="favorite_service",
        method_name="is_favorite",
    )
    reg.register(action)
    issues = reg.validate_all()
    assert [i for i in issues if i["action_id"] == "favorite_status"] == []


def test_missing_service_is_reported() -> None:
    reg = ActionRegistry(container=_container())
    action = ActionDescriptor(
        action_id="ghost",
        title="Ghost",
        category="track",
        service_key="no_such_service",
        method_name="is_favorite",
    )
    reg.register(action)
    issues = reg.validate_all()
    assert {
        "action_id": "ghost", "issue": "service_not_found",
        "service": "no_such_service",
    } in issues


def test_missing_method_is_reported() -> None:
    reg = ActionRegistry(container=_container())
    action = ActionDescriptor(
        action_id="bad_method",
        title="Bad",
        category="track",
        service_key="favorite_service",
        method_name="no_such_method",
    )
    reg.register(action)
    issues = reg.validate_all()
    assert {
        "action_id": "bad_method", "issue": "method_not_found",
        "method": "no_such_method",
        "service": "FavoriteService",
    } in issues


def test_service_key_and_service_name_aliases() -> None:
    action = ActionDescriptor(
        action_id="a", title="A", category="track",
        service_key="favorite_service", method_name="is_favorite",
    )
    assert action.service_key == "favorite_service"
    assert action.service_name == "favorite_service"
