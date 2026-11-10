"""Flashing domain: creation modes, honest FSM stages and plan authority.

Offsets, segments and hashes come only from a verified firmware manifest; the
host never guesses offsets (master plan §133, §136). Execution is gated by an
explicit approval: ``DraftFlashPlan`` must pass preflight and become an
``ApprovedFlashPlan`` bound to device fingerprint, manifest digest and
provisioning fingerprint — ``execute`` refuses anything else (fail closed).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class CreationMode(StrEnum):
    CREATE_NEW = "create_new"
    UPDATE_EXISTING = "update_existing"
    FACTORY_RECREATE = "factory_recreate"


class FlashStage(StrEnum):
    IDLE = "idle"
    DEVICE_DETECTION = "device_detection"
    VERIFYING_FIRMWARE = "verifying_firmware"
    PREFLIGHT = "preflight"
    PREPARING_FLASH = "preparing_flash"
    ERASING = "erasing"
    FLASHING_BOOT = "flashing_boot"
    FLASHING_PARTITION_TABLE = "flashing_partition_table"
    FLASHING_OTA_DATA = "flashing_ota_data"
    FLASHING_APP = "flashing_app"
    FLASHING_PROVISIONING = "flashing_provisioning"
    VERIFYING_FLASH = "verifying_flash"
    REBOOTING = "rebooting"
    WAITING_FOR_NETWORK = "waiting_for_network"
    WAITING_FOR_DISCOVERY = "waiting_for_discovery"
    VERIFYING_IDENTITY = "verifying_identity"
    LINKING = "linking"
    READY = "ready"
    FAILED = "failed"
    CANCELLED = "cancelled"


_SEGMENT_STAGES = {
    "bootloader": FlashStage.FLASHING_BOOT,
    "partition-table": FlashStage.FLASHING_PARTITION_TABLE,
    "partition_table": FlashStage.FLASHING_PARTITION_TABLE,
    "ota_data": FlashStage.FLASHING_OTA_DATA,
    "otadata": FlashStage.FLASHING_OTA_DATA,
    "ota-data": FlashStage.FLASHING_OTA_DATA,
    "app": FlashStage.FLASHING_APP,
    "application": FlashStage.FLASHING_APP,
    "factory": FlashStage.FLASHING_APP,
}

# Canonical write order for segment stages.
SEGMENT_STAGE_ORDER = (
    FlashStage.FLASHING_BOOT,
    FlashStage.FLASHING_PARTITION_TABLE,
    FlashStage.FLASHING_OTA_DATA,
    FlashStage.FLASHING_APP,
)


def stage_for_segment(name: str) -> FlashStage:
    """Map a manifest segment name to its write stage (defaults to app)."""
    return _SEGMENT_STAGES.get(name.lower(), FlashStage.FLASHING_APP)


def stage_sequence(
    *,
    erase_first: bool,
    segment_names: tuple[str, ...],
    include_provisioning: bool,
    post_flash_requested: bool = False,
) -> tuple[FlashStage, ...]:
    """Deterministic sequence containing only stages with real work.

    Without a post-flash verifier the sequence stops at REBOOTING: LINKING and
    READY require discovery/identity evidence and are never decorative.
    """
    stages: list[FlashStage] = [
        FlashStage.VERIFYING_FIRMWARE,
        FlashStage.PREPARING_FLASH,
    ]
    if erase_first:
        stages.append(FlashStage.ERASING)
    present = {stage_for_segment(name) for name in segment_names}
    for stage in SEGMENT_STAGE_ORDER:
        if stage in present:
            stages.append(stage)
    if include_provisioning:
        stages.append(FlashStage.FLASHING_PROVISIONING)
    stages.append(FlashStage.VERIFYING_FLASH)
    stages.append(FlashStage.REBOOTING)
    if post_flash_requested:
        stages.extend(
            (
                FlashStage.WAITING_FOR_NETWORK,
                FlashStage.WAITING_FOR_DISCOVERY,
                FlashStage.VERIFYING_IDENTITY,
                FlashStage.LINKING,
                FlashStage.READY,
            )
        )
    return tuple(stages)


@dataclass(frozen=True)
class FlashSegment:
    """One manifest segment; offset and hash come from the manifest only."""

    name: str
    offset: int
    sha256: str
    file: str
    size: int | None = None


@dataclass(frozen=True)
class PhysicalDeviceIdentity:
    """Stable physical board identity — the port is only a transport locator."""

    chip_target: str
    chip_uid: str
    mac: str | None = None
    usb_serial: str | None = None
    vid: int | None = None
    pid: int | None = None

    def fingerprint(self) -> str:
        parts = [self.chip_target, self.chip_uid]
        if self.usb_serial:
            parts.append(self.usb_serial)
        return "|".join(parts)


@dataclass(frozen=True)
class FactoryPartitionDescriptor:
    """Writable provisioning partition (capacity ≠ artifact size).

    Values must come from the firmware manifest produced by Stream tooling
    (STREAM-REQ-002); nothing is ever hardcoded here.
    """

    name: str
    offset: int
    capacity: int
    format: str = "michi-f1"
    schema_version: int = 1


@dataclass(frozen=True)
class FlashOperationProfile:
    """Which segments an operation may write.

    UPDATE must never blindly write every segment (partition table, bootloader
    and OTA data can destroy persistence assumptions even without an erase).
    Until Stream publishes authoritative update metadata (STREAM-REQ-006), an
    UPDATE without an explicit allow-list fails closed.
    """

    operation: CreationMode
    allowed_segment_names: tuple[str, ...] | None = None

    def allows(self, segment_name: str) -> bool:
        if self.allowed_segment_names is None:
            return True
        return segment_name in self.allowed_segment_names


def profile_for(
    manifest: FirmwareManifest, mode: CreationMode
) -> FlashOperationProfile:
    if mode is CreationMode.UPDATE_EXISTING:
        return FlashOperationProfile(
            operation=mode,
            allowed_segment_names=manifest.update_segment_names,
        )
    return FlashOperationProfile(operation=mode, allowed_segment_names=None)


@dataclass(frozen=True)
class FirmwareManifest:
    """USB flash manifest published by michi-music-stream tooling."""

    version: str
    board: str
    segments: tuple[FlashSegment, ...]
    min_version: str = ""
    channel: str = "stable"
    factory_partition: FactoryPartitionDescriptor | None = None
    update_segment_names: tuple[str, ...] | None = None
    product: str = ""
    chip_target: str = ""
    release_tag: str = ""
    source_commit: str = ""
    flash_size: int | None = None
    minimum_ecosystem_version: str = ""
    protocol_compatibility: tuple[str, ...] = ()
    partition_table_digest: str = ""
    source: str = ""


@dataclass(frozen=True)
class ProvisioningRequest:
    """Transient Wi-Fi material; the password never appears in repr/logs."""

    ssid: str
    password: str = field(repr=False)
    region: str = ""
    device_name: str = ""

    def __repr__(self) -> str:
        return (
            f"ProvisioningRequest(ssid={self.ssid!r}, password=<redacted>, "
            f"region={self.region!r}, device_name={self.device_name!r})"
        )


@dataclass(frozen=True)
class FlashPlanDraft:
    """Unapproved write plan; harmless by itself, cannot be executed."""

    mode: CreationMode
    port: str
    board: str
    manifest: FirmwareManifest
    artifacts_dir: str
    erase_first: bool
    factory_recreate_confirmed: bool = False
    provisioning_blob: bytes | None = field(default=None, repr=False)


@dataclass(frozen=True)
class ApprovedFlashPlan:
    """Preflighted plan bound to the exact device, manifest and provisioning.

    If any bound value changes between approval and execution, ``execute``
    fails closed with ``APPROVAL_INVALIDATED``.
    """

    plan: FlashPlanDraft
    approval_id: str
    manifest_digest: str
    device_fingerprint: str
    provisioning_fingerprint: str = ""
    approved_at_ms: int = 0
    finding_codes: tuple[str, ...] = ()
    post_flash_requested: bool = False
