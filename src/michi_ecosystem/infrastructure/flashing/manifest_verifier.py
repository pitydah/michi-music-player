"""Firmware flash manifest loading and verification (master plan §136).

The manifest is produced by michi-music-stream build/release tooling
(STREAM-REQ-002); this module never guesses offsets — it validates that the
manifest is coherent and that every artifact matches its SHA-256.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath

from michi_ecosystem.domain.flashing import (
    FactoryPartitionDescriptor,
    FirmwareManifest,
    FlashSegment,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
# Structural sanity bound only (upstream publishes the real flash size:
# STREAM-REQ-002); beyond this is rejected as absurd.
MAX_STRUCTURAL_ADDRESS = 0x4000_0000  # 1 GiB


class ManifestError(ValueError):
    """The manifest is malformed, incoherent or mismatched with its artifacts."""


def load_manifest(path: Path) -> FirmwareManifest:
    """Load and validate a flash manifest (fail closed)."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestError(f"manifest is not readable JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise ManifestError("manifest must be a JSON object")

    version = raw.get("version")
    board = raw.get("board")
    if not isinstance(version, str) or not version:
        raise ManifestError("manifest is missing 'version'")
    if not isinstance(board, str) or not board:
        raise ManifestError("manifest is missing 'board'")

    entries = raw.get("segments")
    if not isinstance(entries, list) or not entries:
        raise ManifestError("manifest is missing 'segments'")

    segments: list[FlashSegment] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ManifestError("segment entries must be objects")
        name = entry.get("name")
        offset = entry.get("offset")
        sha256 = entry.get("sha256")
        file_name = entry.get("file")
        size = entry.get("size")
        if not isinstance(name, str) or not name:
            raise ManifestError("segment is missing 'name'")
        if not isinstance(offset, int) or offset < 0:
            raise ManifestError(f"segment {name}: invalid offset")
        if not isinstance(sha256, str) or not _SHA256_RE.match(sha256):
            raise ManifestError(f"segment {name}: invalid sha256")
        if not isinstance(file_name, str) or not file_name:
            raise ManifestError(f"segment {name}: missing 'file'")
        file_name = _require_safe_relative_path(file_name, name)
        if size is not None and (not isinstance(size, int) or size < 0):
            raise ManifestError(f"segment {name}: invalid size")
        segments.append(
            FlashSegment(
                name=name,
                offset=offset,
                sha256=sha256,
                file=file_name,
                size=size,
            )
        )

    factory_partition = _parse_factory_partition(raw.get("factory_partition"), segments)
    update_segment_names = _parse_update_segments(raw.get("update_segments"), segments)
    metadata = _parse_optional_metadata(raw)

    manifest = FirmwareManifest(
        version=version,
        board=board,
        segments=tuple(segments),
        min_version=str(raw.get("min_version", "")),
        channel=str(raw.get("channel", "stable")),
        factory_partition=factory_partition,
        update_segment_names=update_segment_names,
        product=metadata["product"],
        chip_target=metadata["chip_target"],
        release_tag=metadata["release_tag"],
        source_commit=metadata["source_commit"],
        flash_size=metadata["flash_size"],
        minimum_ecosystem_version=metadata["minimum_ecosystem_version"],
        protocol_compatibility=metadata["protocol_compatibility"],
        partition_table_digest=metadata["partition_table_digest"],
        source=str(path),
    )
    verify_layout(manifest)
    return manifest


def _parse_optional_metadata(raw: dict) -> dict:
    """Normalized optional provenance metadata (wire format NOT frozen: D4)."""

    def text(key: str) -> str:
        value = raw.get(key, "")
        if value is None:
            return ""
        if not isinstance(value, str):
            raise ManifestError(f"'{key}' must be a string")
        return value

    flash_size = raw.get("flash_size")
    if flash_size is not None and (not isinstance(flash_size, int) or flash_size <= 0):
        raise ManifestError("'flash_size' must be a positive integer")
    digest = text("partition_table_digest")
    if digest and not _SHA256_RE.match(digest):
        raise ManifestError("'partition_table_digest' must be a sha256 hex")
    protocols = raw.get("protocol_compatibility", [])
    if protocols is None:
        protocols = []
    if not isinstance(protocols, list) or any(
        not isinstance(item, str) for item in protocols
    ):
        raise ManifestError("'protocol_compatibility' must be a list of strings")
    return {
        "product": text("product"),
        "chip_target": text("chip_target"),
        "release_tag": text("release_tag"),
        "source_commit": text("source_commit"),
        "flash_size": flash_size,
        "minimum_ecosystem_version": text("minimum_ecosystem_version"),
        "protocol_compatibility": tuple(protocols),
        "partition_table_digest": digest,
    }


def _require_safe_relative_path(file_name: str, segment: str) -> str:
    """segment.file must be a safe POSIX relative path (no escapes)."""
    if file_name.startswith(("/", "\\")) or "\\" in file_name:
        raise ManifestError(f"segment {segment}: unsafe file path {file_name!r}")
    if len(file_name) >= 2 and file_name[1] == ":":
        raise ManifestError(
            f"segment {segment}: drive-style path rejected {file_name!r}"
        )
    posix = PurePosixPath(file_name)
    if posix.is_absolute() or any(part in ("..", "") for part in posix.parts):
        raise ManifestError(f"segment {segment}: path traversal rejected {file_name!r}")
    return str(posix)


def _parse_factory_partition(
    raw: object, segments: tuple[FlashSegment, ...]
) -> FactoryPartitionDescriptor | None:
    """Parse the factory partition descriptor (object form) or legacy name.

    The object form is the forward contract requested from Stream tooling
    (STREAM-REQ-002); the legacy string form resolves capacity from the named
    segment so old fixtures keep working — never production offsets.
    """
    if raw is None:
        return None
    if isinstance(raw, str):
        for segment in segments:
            if segment.name == raw:
                return FactoryPartitionDescriptor(
                    name=segment.name,
                    offset=segment.offset,
                    capacity=segment.size or 0,
                )
        raise ManifestError(
            f"legacy 'factory_partition' names a missing segment: {raw}"
        )
    if not isinstance(raw, dict):
        raise ManifestError("'factory_partition' must be an object or a string")
    name = raw.get("name")
    offset = raw.get("offset")
    capacity = raw.get("capacity")
    fmt = raw.get("format", "michi-f1")
    schema_version = raw.get("schema_version", 1)
    if not isinstance(name, str) or not name:
        raise ManifestError("factory partition is missing 'name'")
    if not isinstance(offset, int) or offset < 0:
        raise ManifestError("factory partition has an invalid 'offset'")
    if not isinstance(capacity, int) or capacity < 0:
        raise ManifestError("factory partition has an invalid 'capacity'")
    if not isinstance(fmt, str) or not fmt:
        raise ManifestError("factory partition has an invalid 'format'")
    if not isinstance(schema_version, int) or schema_version < 0:
        raise ManifestError("factory partition has an invalid 'schema_version'")
    return FactoryPartitionDescriptor(
        name=name,
        offset=offset,
        capacity=capacity,
        format=fmt,
        schema_version=schema_version,
    )


def _parse_update_segments(
    raw: object, segments: tuple[FlashSegment, ...]
) -> tuple[str, ...] | None:
    """Optional update allow-list; every name must exist and be unique."""
    if raw is None:
        return None
    if not isinstance(raw, list) or not raw:
        raise ManifestError("'update_segments' must be a non-empty list")
    names: list[str] = []
    known = {segment.name for segment in segments}
    for entry in raw:
        if not isinstance(entry, str) or not entry:
            raise ManifestError("'update_segments' entries must be strings")
        if entry in names:
            raise ManifestError(f"duplicate update segment: {entry}")
        if entry not in known:
            raise ManifestError(f"update segment does not exist in segments: {entry}")
        names.append(entry)
    return tuple(names)


def verify_layout(manifest: FirmwareManifest) -> None:
    """Segments must have unique names/offsets and must not overlap."""
    names: set[str] = set()
    offsets: set[int] = set()
    ordered = sorted(manifest.segments, key=lambda segment: segment.offset)
    for segment in ordered:
        if segment.name in names:
            raise ManifestError(f"duplicate segment name: {segment.name}")
        if segment.offset in offsets:
            raise ManifestError(f"duplicate segment offset: {segment.offset}")
        names.add(segment.name)
        offsets.add(segment.offset)
    for current, following in zip(ordered, ordered[1:], strict=False):
        if (
            current.size is not None
            and current.offset + current.size > following.offset
        ):
            raise ManifestError(
                f"segments overlap: {current.name} ends past {following.name}"
            )
    for segment in ordered:
        _check_address_bounds(segment.offset, segment.size, segment.name)

    factory = manifest.factory_partition
    if factory is not None:
        if factory.capacity <= 0:
            raise ManifestError(
                "factory partition capacity must be > 0 for a usable partition"
            )
        _check_address_bounds(factory.offset, factory.capacity, "factory_partition")
        factory_start = factory.offset
        factory_end = factory.offset + factory.capacity
        for segment in ordered:
            if segment.name == factory.name:
                continue  # the descriptor describes that same partition
            if segment.size is None:
                continue
            seg_start = segment.offset
            seg_end = segment.offset + segment.size
            if seg_start < factory_end and factory_start < seg_end:
                raise ManifestError(
                    "FACTORY_PARTITION_OVERLAP: factory partition "
                    f"[{hex(factory_start)}, {hex(factory_end)}) overlaps "
                    f"segment {segment.name} [{hex(seg_start)}, {hex(seg_end)})"
                )


def _check_address_bounds(offset: int, size: int | None, name: str) -> None:
    end = offset + (size or 0)
    if offset < 0 or end < offset or end > MAX_STRUCTURAL_ADDRESS:
        raise ManifestError(
            f"{name}: address range out of structural bounds "
            f"[{hex(offset)}, {hex(end)})"
        )


def verify_artifact(
    manifest: FirmwareManifest, segment: FlashSegment, root: Path
) -> None:
    """The artifact must exist and match the manifest SHA-256 (and size)."""
    artifact = root / segment.file
    try:
        artifact.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ManifestError(f"artifact path escapes its root: {segment.file}") from exc
    if not artifact.is_file():
        raise ManifestError(f"artifact missing: {artifact}")
    data = artifact.read_bytes()
    if segment.size is not None and len(data) != segment.size:
        raise ManifestError(
            f"artifact size mismatch for {segment.name}: "
            f"expected {segment.size}, got {len(data)}"
        )
    digest = hashlib.sha256(data).hexdigest()
    if digest != segment.sha256:
        raise ManifestError(f"artifact SHA-256 mismatch for {segment.name}")


def verify_manifest_for_board(manifest: FirmwareManifest, board: str) -> None:
    if manifest.board != board:
        raise ManifestError(
            f"manifest board {manifest.board!r} does not match {board!r}"
        )
