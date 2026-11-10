"""Canonical ecosystem device model (E11.5-B).

The registry model deliberately separates *device identity* from transport,
presence, Home membership and UI projection.  A ``michi_id`` is the canonical
cryptographic identity for Michi devices.  Generic USB DAPs do not have one
and therefore use a stable local canonical id supplied by the USB adapter.

No source in this module grants trust.  In particular AirCat is only a
content-transfer capability consumed by Michi Devices; it never establishes
Home membership or Michi Link trust.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DeviceRegistryError(ValueError):
    """A device descriptor violated a registry invariant."""


class DeviceType(StrEnum):
    DESKTOP_PLAYER = "desktop_player"
    MUSIC_STREAM = "music_stream"
    MICRO_SERVER = "micro_server"
    BIG_SERVER = "big_server"
    MOBILE = "mobile"
    GENERIC_DAP = "generic_dap"
    UNKNOWN = "unknown"


class HomeMembershipState(StrEnum):
    NONE = "none"
    PENDING = "pending"
    ACTIVE = "active"
    REVOKED = "revoked"


class DeviceTransport(StrEnum):
    MICHI_LINK = "michi_link"
    MDNS = "mdns"
    WHISKER = "whisker"
    LOCAL_API = "local_api"
    USB = "usb"
    AIRCAT = "aircat"


class DeviceCapability(StrEnum):
    PLAYBACK_ENDPOINT = "playback_endpoint"
    REMOTE_CONTROLLER = "remote_controller"
    CONTENT_SYNC = "content_sync"
    AIRCAT = "aircat"
    FACTORY_RECREATE = "factory_recreate"
    FIRMWARE_UPDATE = "firmware_update"
    HOME_ASSISTANT_EXPOSABLE = "home_assistant_exposable"
    STORAGE_TARGET = "storage_target"
    DIAGNOSTICS = "diagnostics"
    NETWORK_REPROVISION = "network_reprovision"


@dataclass(frozen=True)
class DeviceDescriptor:
    """Merged, wire-neutral read model used by Ecosystem and Michi Devices."""

    canonical_id: str
    name: str
    type: DeviceType
    michi_id: str | None = None
    michi_home_id: str | None = None
    home_membership: HomeMembershipState = HomeMembershipState.NONE
    online: bool = False
    transports: frozenset[DeviceTransport] = frozenset()
    capabilities: frozenset[DeviceCapability] = frozenset()
    app_or_firmware_version: str | None = None
    last_seen_ms: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.canonical_id, str) or not self.canonical_id.strip():
            raise DeviceRegistryError("canonical_id must not be empty")
        if not isinstance(self.name, str) or not self.name.strip():
            raise DeviceRegistryError("device name must not be empty")
        if self.michi_id is not None and not str(self.michi_id).strip():
            raise DeviceRegistryError("michi_id must be null or non-empty")
        if self.michi_id is not None:
            expected = canonical_id_for(michi_id=self.michi_id)
            if self.canonical_id != expected:
                raise DeviceRegistryError(
                    "canonical_id must be derived from michi_id for Michi devices"
                )
        if self.home_membership is not HomeMembershipState.NONE:
            if self.michi_id is None or not self.michi_home_id:
                raise DeviceRegistryError(
                    "Home membership requires both michi_id and michi_home_id"
                )
        elif self.michi_home_id is not None:
            raise DeviceRegistryError(
                "michi_home_id must be null when Home membership is none"
            )
        if self.last_seen_ms is not None and self.last_seen_ms < 0:
            raise DeviceRegistryError("last_seen_ms must be >= 0")
        if self.type is DeviceType.GENERIC_DAP:
            if self.michi_id is not None:
                raise DeviceRegistryError("generic DAP must not claim a michi_id")
            if DeviceTransport.AIRCAT in self.transports:
                raise DeviceRegistryError("generic DAP must not expose AirCat")
            if self.home_membership is not HomeMembershipState.NONE:
                raise DeviceRegistryError("generic DAP must not join Michi Home")

    @property
    def trusted_home_member(self) -> bool:
        return self.home_membership is HomeMembershipState.ACTIVE

    @property
    def sync_allowed(self) -> bool:
        """Content sync is capability-driven and trust-gated for Michi Mobile."""
        if self.type is DeviceType.MOBILE:
            return (
                DeviceCapability.CONTENT_SYNC in self.capabilities
                and self.trusted_home_member
            )
        if self.type is DeviceType.GENERIC_DAP:
            return DeviceCapability.STORAGE_TARGET in self.capabilities
        return DeviceCapability.CONTENT_SYNC in self.capabilities

    @property
    def home_assistant_allowed(self) -> bool:
        """External automation is capability + trust gated.

        A local Desktop Player may be exposed by its owning host without a Home
        roster entry. Network devices (Stream/Micro/Mobile) must be active Home
        members before Home Assistant can control them.
        """
        if DeviceCapability.HOME_ASSISTANT_EXPOSABLE not in self.capabilities:
            return False
        if self.type is DeviceType.DESKTOP_PLAYER:
            return True
        return self.trusted_home_member

    def has(self, capability: DeviceCapability) -> bool:
        return capability in self.capabilities


def canonical_id_for(*, michi_id: str | None, local_id: str | None = None) -> str:
    """Build a deterministic registry key without conflating identity domains."""
    if michi_id and str(michi_id).strip():
        return f"michi:{str(michi_id).strip()}"
    if local_id and str(local_id).strip():
        return f"local:{str(local_id).strip()}"
    raise DeviceRegistryError("michi_id or local_id is required")
