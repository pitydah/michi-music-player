from __future__ import annotations

from pathlib import Path

import pytest

from ui_qml_bridge.route_registry import ROUTES

from .qml_component_helper import load_qml_component, QML_ROOT

REPO = Path(__file__).resolve().parents[3]
PLACEHOLDER_SOURCE = "../pages/PlaceholderPage.qml"
PLACEHOLDER_FULL = QML_ROOT / "pages" / "PlaceholderPage.qml"


def _iter_functional_routes():
    for route_key, spec in ROUTES.items():
        if spec.get("status") == "functional":
            source = spec.get("source", "")
            yield route_key, source


FUNCTIONAL_ROUTES = list(_iter_functional_routes())


@pytest.mark.parametrize(
    ("route", "source"),
    [pytest.param(r, s, id=r) for r, s in FUNCTIONAL_ROUTES],
)
def test_functional_route_loads_successfully(qapp, route: str, source: str) -> None:
    result = load_qml_component(source, timeout_ms=10000)

    failures = []
    if result["status"] != "Ready":
        failures.append(f"status={result['status']} (expected Ready)")
    if result["errors"]:
        for err in result["errors"]:
            failures.append(
                f"  {err['url']}:{err['line']}:{err['column']} — {err['description']}"
            )
    if result["object"] is None:
        failures.append("object is None")

    source_resolved = Path(result["source"])
    if source_resolved == PLACEHOLDER_FULL:
        failures.append(
            f"resolved to PlaceholderPage.qml instead of {source}"
        )

    if result.get("component"):
        result["component"].deleteLater()
    if result.get("object"):
        result["object"].deleteLater()
    if result.get("engine"):
        result["engine"].deleteLater()

    assert not failures, (
        f"Route '{route}' ({source}) failed:\n" + "\n".join(failures)
    )
