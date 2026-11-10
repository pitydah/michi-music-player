"""Vendored Michi Link contract bundle: integrity, loading and validation.

The bundle under ``contracts/michi-link/receiver-v1-lite`` is vendored by
``scripts/sync_contracts.py`` (fail-closed against ``UPSTREAM_LOCK.json``) and
is never edited by hand (master plan §128, §155.1).

Integrity verification is stdlib-only; JSON Schema validation needs the
``contracts`` extra (jsonschema + referencing).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
# The bundle ships inside the package so contract validation works from the
# installed wheel (the Player never runs from the incubator checkout).
PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BUNDLE_ROOT = PACKAGE_ROOT / "contracts" / "michi-link" / "receiver-v1-lite"

_HEX_DIGITS = set("0123456789abcdef")
_MANIFEST_NAME = "manifest.json"


class BundleIntegrityError(RuntimeError):
    """The vendored bundle does not match its manifest (fail closed)."""


class ContractViolation(ValueError):  # noqa: N818
    """A payload violates the vendored contract schema."""

    def __init__(self, schema_name: str, messages: Sequence[str]) -> None:
        self.schema_name = schema_name
        self.messages = list(messages)
        detail = "; ".join(self.messages) if self.messages else "invalid payload"
        super().__init__(f"{schema_name}: {detail}")


def _read_manifest(root: Path) -> dict[str, Any]:
    manifest_path = root / _MANIFEST_NAME
    if not manifest_path.is_file():
        raise BundleIntegrityError(f"bundle is missing {_MANIFEST_NAME}: {root}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BundleIntegrityError(f"bundle manifest is invalid: {exc}") from exc
    if not isinstance(manifest, dict):
        raise BundleIntegrityError("bundle manifest must be a JSON object")
    return manifest


def verify_bundle_files(root: Path = DEFAULT_BUNDLE_ROOT) -> None:
    """Verify every manifest-listed file exists with its recorded SHA-256.

    Unlisted files (other than the manifest itself) are rejected: the bundle
    must be exactly what the upstream shipped.
    """
    manifest = _read_manifest(root)
    version = manifest.get("version")
    if not isinstance(version, str) or not version:
        raise BundleIntegrityError("bundle manifest is missing its version")
    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        raise BundleIntegrityError("bundle manifest is missing its files list")

    listed: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise BundleIntegrityError("manifest file entries must be objects")
        relative = entry.get("path")
        digest = entry.get("sha256")
        if not isinstance(relative, str) or not relative:
            raise BundleIntegrityError("manifest entry is missing its path")
        if relative in listed:
            raise BundleIntegrityError(f"duplicate manifest entry: {relative}")
        listed.add(relative)
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or not set(digest) <= _HEX_DIGITS
        ):
            raise BundleIntegrityError(f"invalid sha256 for {relative}")
        target = root / relative
        if not target.is_file():
            raise BundleIntegrityError(f"manifest lists a missing file: {relative}")
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != digest:
            raise BundleIntegrityError(f"SHA-256 mismatch for {relative}")

    unlisted = {
        str(item.relative_to(root))
        for item in root.rglob("*")
        if item.is_file() and str(item.relative_to(root)) != _MANIFEST_NAME
    } - listed
    if unlisted:
        raise BundleIntegrityError(
            "bundle contains files missing from the manifest: "
            + ", ".join(sorted(unlisted))
        )


@dataclass(frozen=True)
class ContractBundle:
    """Loaded receiver-v1-lite contract bundle."""

    root: Path
    version: str
    upstream_commit: str
    schema_count: int
    _schemas: Mapping[str, Mapping[str, Any]] = field(repr=False)
    _registry: Any = field(repr=False)

    def schema_names(self) -> tuple[str, ...]:
        return tuple(sorted(self._schemas))

    def schema(self, name: str) -> Mapping[str, Any]:
        file_name = name if name.endswith(".json") else f"{name}.schema.json"
        try:
            return self._schemas[file_name]
        except KeyError as exc:
            raise KeyError(f"unknown contract schema: {name}") from exc

    def validate(self, schema_name: str, payload: Mapping[str, Any]) -> None:
        """Validate a payload; raises ContractViolation (fail closed)."""
        import jsonschema

        schema = self.schema(schema_name)
        validator = jsonschema.Draft7Validator(schema, registry=self._registry)
        errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.path))
        if errors:
            messages = [
                f"{'/'.join(str(part) for part in error.path) or '<root>'}: "
                f"{error.message}"
                for error in errors[:5]
            ]
            raise ContractViolation(schema_name, messages)


def load_bundle(root: Path = DEFAULT_BUNDLE_ROOT) -> ContractBundle:
    """Load and verify the vendored bundle (fail closed on integrity errors)."""
    from referencing import Registry, Resource

    verify_bundle_files(root)
    manifest = _read_manifest(root)

    schemas: dict[str, Mapping[str, Any]] = {}
    for schema_path in sorted((root / "schemas").glob("*.json")):
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        schemas[schema_path.name] = schema

    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema))
        for schema in schemas.values()
        if "$id" in schema
    )

    commit_path = root / "UPSTREAM_COMMIT"
    upstream_commit = (
        commit_path.read_text(encoding="utf-8").strip() if commit_path.is_file() else ""
    )

    return ContractBundle(
        root=root,
        version=str(manifest["version"]),
        upstream_commit=upstream_commit,
        schema_count=len(schemas),
        _schemas=schemas,
        _registry=registry,
    )
