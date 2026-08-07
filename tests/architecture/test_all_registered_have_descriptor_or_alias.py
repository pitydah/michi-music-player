"""Every registered key has a manifest descriptor or is declared as an alias.

Extends test_service_manifest_complete with the alias rule: alias descriptors
must point at an existing manifest key (never themselves) and the alias
target must be a registered key in the productive composition.
"""
from __future__ import annotations

from core.service_manifest import SERVICE_MANIFEST

from tests.architecture._helpers import registered_keys


def test_every_registered_key_has_descriptor_or_alias() -> None:
    missing = sorted(registered_keys() - set(SERVICE_MANIFEST))
    assert missing == [], (
        f"Keys registered by composition without descriptor or alias: {missing}"
    )


def test_aliases_declared_explicitly() -> None:
    aliases = [
        (name, desc.alias_of) for name, desc in SERVICE_MANIFEST.items()
        if desc.alias_of is not None
    ]
    assert aliases, "no aliases declared"
    for name, target in aliases:
        assert target is not None
        assert target in SERVICE_MANIFEST, (
            f"alias '{name}' points at undeclared key '{target}'"
        )
        assert target != name, f"alias '{name}' cannot point at itself"


def test_alias_targets_are_registered_keys() -> None:
    registered = registered_keys()
    for name, desc in SERVICE_MANIFEST.items():
        if desc.alias_of is not None:
            assert desc.alias_of in registered, (
                f"alias '{name}' target '{desc.alias_of}' is never registered"
            )
            assert name in registered, (
                f"alias key '{name}' is never registered"
            )


def test_alias_target_is_not_itself_an_alias() -> None:
    for name, desc in SERVICE_MANIFEST.items():
        if desc.alias_of is None:
            continue
        target = SERVICE_MANIFEST[desc.alias_of]
        assert target.alias_of is None, (
            f"alias '{name}' targets '{desc.alias_of}' which is itself an alias"
        )
