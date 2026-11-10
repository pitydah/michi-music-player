"""Firmware distribution domain models (R6) — wire-neutral.

GitHub URLs stay in infrastructure; the domain carries versions, asset names
and provenance only. Official distribution channel: GitHub Releases of
``pitydah/michi-music-stream`` (STREAM-REQ-004, still OPEN upstream).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from michi_ecosystem.domain.flashing import FirmwareManifest


class FirmwareChannel(StrEnum):
    STABLE = "stable"
    DEV = "dev"


@dataclass(frozen=True)
class FirmwareRelease:
    version: str
    tag: str
    board: str
    channel: FirmwareChannel
    manifest_asset: str
    bundle_asset: str
    source_commit: str = ""


@dataclass(frozen=True)
class FirmwareProvenance:
    repository: str
    release_tag: str
    source_commit: str
    manifest_sha256: str
    bundle_sha256: str


@dataclass(frozen=True)
class ResolvedFirmware:
    release: FirmwareRelease
    manifest: FirmwareManifest
    artifacts_dir: Path
    provenance: FirmwareProvenance
