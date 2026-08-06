"""No orphan productive services: every MANAGED/DOMAIN component has a consumer.

Infrastructure roots (database, event_bus, worker_manager, process_controller,
settings_manager, paths, ...) are declared explicitly and are exempt: they are
consumed by the composition layer itself.
"""
from __future__ import annotations

from core.service_manifest import SERVICE_MANIFEST, ServiceClass

# Explicit infrastructure roots — consumed by composition/builders, not by
# another manifest descriptor. Kept in sync with ADR-001 infrastructure set.
INFRASTRUCTURE_ROOTS = frozenset({
    "database",
    "event_bus",
    "worker_manager",
    "process_controller",
    "settings_manager",
    "paths",
    "runtime_persistence",
    "job_service",
    "action_registry",
    "provider_manager",
})


def _referenced_by_other_descriptor(name: str) -> bool:
    for other, desc in SERVICE_MANIFEST.items():
        if other == name:
            continue
        if name in desc.dependencies or name in desc.consumers:
            return True
    return False


# Documented exceptions: standalone components whose consumers cannot be
# listed today (production wiring unverified — audit S4).
DOCUMENTED_EXCEPTIONS = frozenset({
    "knowledge_broker",
})


def test_no_orphan_productive_service() -> None:
    orphans = []
    for name, desc in SERVICE_MANIFEST.items():
        if name in INFRASTRUCTURE_ROOTS or desc.alias_of is not None:
            continue
        if name in DOCUMENTED_EXCEPTIONS:
            continue
        if desc.service_class not in (
            ServiceClass.MANAGED_SERVICE,
            ServiceClass.DOMAIN_SERVICE,
        ):
            continue
        if desc.consumers:
            continue
        if not _referenced_by_other_descriptor(name):
            orphans.append(name)
    assert orphans == [], (
        f"productive services without consumers: {orphans}"
    )


def test_infrastructure_roots_are_declared() -> None:
    missing = sorted(
        root for root in INFRASTRUCTURE_ROOTS
        if root not in SERVICE_MANIFEST
    )
    assert missing == [], f"infrastructure roots missing from manifest: {missing}"
