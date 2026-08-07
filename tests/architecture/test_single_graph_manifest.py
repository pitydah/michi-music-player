"""FASE 1 P0: SERVICE_MANIFEST is the ONLY source of truth for container lifecycle.

Source scan + behaviour: no second inventory (BUILTIN_DEPENDENCIES, frozen name
lists, historical order index) and no second dependency graph inside
``core.service_container``. The deprecated compatibility views may only be
*defined* there — never called from an execution path.
"""
from __future__ import annotations

import re
from pathlib import Path

import core.service_container as sc_module
from core.service_manifest import (
    SERVICE_MANIFEST,
    LifecycleKind,
    ServicePriority,
)

_SOURCE = Path(sc_module.__file__).read_text(encoding="utf-8")

# Identifiers that must not exist at all in the container module.
BANNED_IDENTIFIERS = ("BUILTIN_DEPENDENCIES", "SERVICE_ORDER_INDEX")

# Deprecated manifest-derived compatibility views: only their definition may
# appear in the source — any call site is an execution-path reference.
DEPRECATED_VIEWS = (
    "_required_names",
    "_optional_names",
    "_capability_gated_names",
    "_deferred_physical_names",
    "_deferred_names",
    "_all_names",
)


def _alias_target(name: str) -> str:
    desc = SERVICE_MANIFEST.get(name)
    if desc is not None and desc.alias_of is not None:
        return desc.alias_of
    return name


def _resolved_dependencies(name: str) -> tuple[str, ...]:
    desc = SERVICE_MANIFEST.get(name)
    if desc is None:
        return ()
    return tuple(_alias_target(dep) for dep in desc.dependencies)


def test_no_legacy_dependency_tables_in_source() -> None:
    for identifier in BANNED_IDENTIFIERS:
        assert identifier not in _SOURCE, (
            f"legacy identifier '{identifier}' still present in service_container.py"
        )


def test_no_frozen_name_list_constants() -> None:
    for identifier in ("REQUIRED_NAMES", "OPTIONAL_NAMES", "CAPABILITY_GATED_NAMES"):
        assert identifier not in _SOURCE, (
            f"frozen name list '{identifier}' still present in service_container.py"
        )


def test_deprecated_views_never_called_from_execution() -> None:
    for view in DEPRECATED_VIEWS:
        call_sites = re.findall(rf"\b(?:self|ServiceContainer)\.{view}\(", _SOURCE)
        assert call_sites == [], (
            f"deprecated view '{view}' still called in service_container.py: {call_sites}"
        )


def test_build_order_matches_manifest_dependencies() -> None:
    container = sc_module.ServiceContainer()
    order = container.build_order()
    index = {name: i for i, name in enumerate(order)}

    for name, desc in SERVICE_MANIFEST.items():
        if desc.alias_of is not None:
            continue
        for dep in _resolved_dependencies(name):
            assert dep in index, f"dependency '{dep}' of '{name}' missing from build order"
            assert index[dep] < index[name], (
                f"dependency '{dep}' must start before '{name}'"
            )


def test_build_order_excludes_aliases() -> None:
    aliases = [
        name for name, desc in SERVICE_MANIFEST.items()
        if desc.alias_of is not None
    ]
    order = sc_module.ServiceContainer().build_order()
    for alias in aliases:
        assert alias not in order, (
            f"alias '{alias}' must not be a lifecycle node in build order"
        )


def test_lifecycle_start_order_is_manifest_managed_only() -> None:
    container = sc_module.ServiceContainer()
    order = container._lifecycle_start_order()

    expected = [
        name for name, desc in SERVICE_MANIFEST.items()
        if desc.lifecycle == LifecycleKind.MANAGED and desc.alias_of is None
    ]
    assert len(order) == len(expected)
    assert set(order) == set(expected)

    index = {name: i for i, name in enumerate(order)}
    for name in order:
        for dep in _resolved_dependencies(name):
            if dep in index:
                assert index[dep] < index[name], (
                    f"MANAGED '{name}' starts before dependency '{dep}'"
                )


def test_health_counts_come_from_manifest() -> None:
    container = sc_module.ServiceContainer()
    health = container.health()

    expected_required = sum(
        1 for desc in SERVICE_MANIFEST.values()
        if desc.priority == ServicePriority.REQUIRED
    )
    expected_optional = sum(
        1 for desc in SERVICE_MANIFEST.values()
        if desc.priority == ServicePriority.OPTIONAL
    )
    expected_capability_gated = sum(
        1 for desc in SERVICE_MANIFEST.values()
        if desc.priority == ServicePriority.CAPABILITY_GATED
    )
    assert health["required"] == expected_required
    assert health["optional"] == expected_optional
    assert health["capability_gated"] == expected_capability_gated
    assert health["manifest_entries"] == len(SERVICE_MANIFEST)
