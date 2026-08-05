"""DOMAIN_SERVICE components must declare consumers or be referenced."""
from __future__ import annotations

from core.service_manifest import SERVICE_MANIFEST, ServiceClass

# Documented exceptions: components whose consumers cannot be listed today.
#   - library_filtered_query_service: pure alias of library_query_service.
#   - knowledge_broker: standalone, production wiring unverified (audit S4).
DOCUMENTED_EXCEPTIONS = frozenset({
    "library_filtered_query_service",
    "knowledge_broker",
})


def _referenced_by_other_descriptor(name: str) -> bool:
    for other, desc in SERVICE_MANIFEST.items():
        if other == name:
            continue
        if name in desc.dependencies or name in desc.consumers:
            return True
    return False


def test_domain_services_have_consumers_or_references() -> None:
    orphaned = []
    for name, desc in SERVICE_MANIFEST.items():
        if desc.service_class != ServiceClass.DOMAIN_SERVICE:
            continue
        if desc.consumers or name in DOCUMENTED_EXCEPTIONS:
            continue
        if not _referenced_by_other_descriptor(name):
            orphaned.append(name)
    assert orphaned == [], (
        f"DOMAIN_SERVICE components without consumers: {orphaned}"
    )
