"""Manifest completeness: every registered key has a descriptor."""
from __future__ import annotations

from core.service_manifest import SERVICE_MANIFEST, LifecycleKind

from tests.architecture._helpers import STANDALONE_MANIFEST_KEYS, registered_keys


def test_every_registered_key_has_descriptor() -> None:
    missing = sorted(registered_keys() - set(SERVICE_MANIFEST))
    assert missing == [], (
        f"Keys registered by composition builders without manifest descriptor: {missing}"
    )


def test_registered_keys_match_composition() -> None:
    assert len(registered_keys()) == 64, (
        f"Expected 64 registered keys, found {len(registered_keys())}"
    )


def test_manifest_has_no_unknown_registered_keys() -> None:
    extra = sorted(
        set(SERVICE_MANIFEST)
        - registered_keys()
        - STANDALONE_MANIFEST_KEYS
    )
    assert extra == [], (
        f"Manifest declares keys that are neither registered nor standalone: {extra}"
    )


def test_every_descriptor_has_valid_name() -> None:
    for name, desc in SERVICE_MANIFEST.items():
        assert desc.name == name, (
            f"Descriptor name mismatch for key '{name}'"
        )


def test_every_managed_descriptor_has_priority() -> None:
    from core.service_manifest import ServicePriority

    for name, desc in SERVICE_MANIFEST.items():
        assert isinstance(desc.priority, ServicePriority), (
            f"Descriptor '{name}' lacks a priority"
        )


def test_lifecycle_kinds_are_valid() -> None:
    for name, desc in SERVICE_MANIFEST.items():
        assert isinstance(desc.lifecycle, LifecycleKind), (
            f"Descriptor '{name}' has invalid lifecycle {desc.lifecycle!r}"
        )


def test_alias_descriptor_is_passive() -> None:
    desc = SERVICE_MANIFEST["library_filtered_query_service"]
    assert desc.lifecycle == LifecycleKind.PASSIVE, (
        "library_filtered_query_service is an alias and must be PASSIVE"
    )


def test_mpris_adapter_is_external_and_optional() -> None:
    desc = SERVICE_MANIFEST["mpris_adapter"]
    assert desc.lifecycle == LifecycleKind.EXTERNAL
    assert desc.optional is True
