
from core.dependency_graph import SERVICE_ORDER, SERVICE_DEPENDENCIES, resolve_order
import pytest
pytestmark = [pytest.mark.qml_module("worker_manager")]


class TestServiceOrderIsList:
    def test_service_order_is_list(self):
        assert isinstance(SERVICE_ORDER, list)

    def test_service_order_not_empty(self):
        assert len(SERVICE_ORDER) > 0

    def test_service_order_unique(self):
        assert len(SERVICE_ORDER) == len(set(SERVICE_ORDER))

    def test_all_services_are_strings(self):
        assert all(isinstance(s, str) for s in SERVICE_ORDER)


class TestServiceDependencies:
    def test_dependencies_is_dict(self):
        assert isinstance(SERVICE_DEPENDENCIES, dict)

    def test_dependency_values_are_sets(self):
        for deps in SERVICE_DEPENDENCIES.values():
            assert isinstance(deps, set)

    def test_dependencies_exist_in_order(self):
        order_set = set(SERVICE_ORDER)
        for deps in SERVICE_DEPENDENCIES.values():
            for d in deps:
                assert d in order_set, f"Dependency '{d}' not in SERVICE_ORDER"

    def test_no_self_dependency(self):
        for svc, deps in SERVICE_DEPENDENCIES.items():
            assert svc not in deps, f"{svc} depends on itself"


class TestResolveOrder:
    def test_resolve_order_returns_list(self):
        ordered = resolve_order()
        assert isinstance(ordered, list)

    def test_resolve_order_contains_all(self):
        ordered = resolve_order()
        assert set(ordered) == set(SERVICE_ORDER)

    def test_resolve_order_no_duplicates(self):
        ordered = resolve_order()
        assert len(ordered) == len(set(ordered))

    def test_dependencies_before_dependents(self):
        ordered = resolve_order()
        pos = {svc: i for i, svc in enumerate(ordered)}
        for svc, deps in SERVICE_DEPENDENCIES.items():
            for dep in deps:
                assert pos[dep] < pos[svc], f"{dep} should come before {svc}"

    def test_resolve_order_is_deterministic(self):
        assert resolve_order() == resolve_order()
