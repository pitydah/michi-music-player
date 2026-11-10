"""Canonical Ecosystem dashboard orchestration facade.

E11.5 keeps legacy/host dashboard sections (spaces, Micro service detail,
health...) but overlays identity-sensitive sections from the internal canonical
sources.  This prevents the QML dashboard from becoming a second device
registry or from treating discovery presence as Home trust.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Protocol

from michi_ecosystem.application.device_registry_service import DeviceRegistryService
from michi_ecosystem.application.ecosystem_doctor import EcosystemDoctor
from michi_ecosystem.application.home_assistant_service import HomeAssistantService
from michi_ecosystem.application.local_account_service import LocalAccountService
from michi_ecosystem.application.spaces_service import SpaceError, SpacesService
from michi_ecosystem.domain.device_registry import DeviceType, HomeMembershipState


class DiscoverySnapshotProvider(Protocol):
    def snapshot(self) -> tuple[Any, ...]: ...

    def ui_state(self) -> str: ...


class DashboardProvider(Protocol):
    def dashboard_snapshot(self) -> dict[str, Any]: ...


class EcosystemDashboardService:
    """Merge host operational summaries with canonical E11.5 product state."""

    def __init__(
        self,
        base: DashboardProvider,
        *,
        registry: DeviceRegistryService,
        discovery: DiscoverySnapshotProvider | None = None,
        account: LocalAccountService | None = None,
        home_assistant: HomeAssistantService | None = None,
        doctor: EcosystemDoctor | None = None,
        spaces: SpacesService | None = None,
    ) -> None:
        if not callable(getattr(base, "dashboard_snapshot", None)):
            raise TypeError("base dashboard provider must expose dashboard_snapshot()")
        self._base = base
        self._registry = registry
        self._discovery = discovery
        self._account = account
        self._home_assistant = home_assistant
        self._doctor = doctor
        self._spaces = spaces

    def dashboard_snapshot(self) -> dict[str, Any]:
        raw = self._base.dashboard_snapshot()
        snapshot: dict[str, Any] = deepcopy(raw if isinstance(raw, dict) else {})
        devices = self._registry.list_devices()
        michi_devices = [device for device in devices if device.michi_id]

        snapshot["devices"] = {
            "total": len(michi_devices),
            "trusted": sum(
                device.home_membership is HomeMembershipState.ACTIVE
                for device in michi_devices
            ),
            "items": [self._device_item(device) for device in michi_devices[:8]],
        }

        mobiles = [
            device for device in michi_devices if device.type is DeviceType.MOBILE
        ]
        trusted_mobile = next(
            (
                device
                for device in mobiles
                if device.home_membership is HomeMembershipState.ACTIVE
            ),
            None,
        )
        snapshot["mobile"] = {
            "trusted": sum(
                device.home_membership is HomeMembershipState.ACTIVE
                for device in mobiles
            ),
            "name": trusted_mobile.name if trusted_mobile else "",
            "online": trusted_mobile.online if trusted_mobile else False,
            "version": (
                trusted_mobile.app_or_firmware_version or ""
                if trusted_mobile is not None
                else ""
            ),
        }

        streams = [
            device for device in michi_devices if device.type is DeviceType.MUSIC_STREAM
        ]
        if streams:
            snapshot["streams"] = {
                "configured": len(streams),
                "devices": [
                    {
                        "name": device.name,
                        "state": self._device_state(device),
                    }
                    for device in streams
                ],
            }

        if self._discovery is not None:
            nodes = self._discovery.snapshot()
            discovery: dict[str, Any] = {"state": self._discovery.ui_state()}
            if len(nodes) == 1:
                discovery.update(
                    {
                        "device_name": nodes[0].presence.name,
                        "count": 1,
                    }
                )
            elif nodes:
                discovery["count"] = len(nodes)
            snapshot["discovery"] = discovery

        if self._account is not None:
            account = self._account.current_account() or self._account.account_summary()
            snapshot["account"] = {
                "exists": account is not None,
                "authenticated": self._account.authenticated,
                "display_name": account.display_name if account is not None else "",
            }
        else:
            snapshot.setdefault(
                "account", {"exists": False, "authenticated": False, "display_name": ""}
            )

        integrations = snapshot.get("integrations")
        if not isinstance(integrations, dict):
            integrations = {}
        active = {str(item) for item in integrations.get("active", ())}
        available = {str(item) for item in integrations.get("available", ())}
        if self._home_assistant is not None:
            (active if self._home_assistant.enabled else available).add(
                "Home Assistant"
            )
            if self._home_assistant.enabled:
                available.discard("Home Assistant")
            else:
                active.discard("Home Assistant")
        snapshot["integrations"] = {
            "active": sorted(active),
            "available": sorted(available),
        }
        if self._spaces is not None:
            try:
                local_spaces = self._spaces.list_spaces()
                snapshot["spaces"] = {
                    "count": len(local_spaces),
                    "names": [space.name for space in local_spaces],
                }
            except SpaceError:
                snapshot["spaces"] = {"count": 0, "names": []}
        if self._doctor is not None:
            current = self._doctor.projection(snapshot, devices)
            snapshot["doctor"] = current
            snapshot["health"] = {
                "state": current["state"],
                "issues": [
                    {
                        "code": issue["code"],
                        "title": issue["title"],
                        "detail": issue["detail"],
                        "severity": issue["severity"],
                    }
                    for issue in current["issues"]
                ],
            }
        return snapshot

    @staticmethod
    def _device_state(device) -> str:
        if device.home_membership is HomeMembershipState.REVOKED:
            return "revoked"
        if device.home_membership is HomeMembershipState.PENDING:
            return "pending"
        if device.online:
            return "ready"
        return "offline"

    @classmethod
    def _device_item(cls, device) -> dict[str, str]:
        return {"name": device.name, "state": cls._device_state(device)}
