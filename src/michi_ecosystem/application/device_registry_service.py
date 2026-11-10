"""Unified Device Registry service (E11.5-B/C).

Multiple observations for the same canonical device are merged deterministically
without creating a new trust authority.  Source-specific evidence remains
separate so stale discovery data can disappear without deleting Home roster
state and so AirCat can never manufacture trust.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from enum import StrEnum

from michi_ecosystem.domain.device_registry import (
    DeviceCapability,
    DeviceDescriptor,
    DeviceRegistryError,
    DeviceTransport,
    DeviceType,
    HomeMembershipState,
    canonical_id_for,
)


class DeviceSource(StrEnum):
    HOME_ROSTER = "home_roster"
    MICHI_LINK = "michi_link"
    DISCOVERY = "discovery"
    AIRCAT = "aircat"
    USB = "usb"
    FACTORY_METADATA = "factory_metadata"


_SOURCE_PRIORITY: dict[DeviceSource, int] = {
    DeviceSource.HOME_ROSTER: 100,
    DeviceSource.MICHI_LINK: 90,
    DeviceSource.FACTORY_METADATA: 80,
    DeviceSource.DISCOVERY: 70,
    DeviceSource.AIRCAT: 60,
    DeviceSource.USB: 50,
}

_MEMBERSHIP_PRIORITY = {
    HomeMembershipState.NONE: 0,
    HomeMembershipState.PENDING: 1,
    HomeMembershipState.ACTIVE: 2,
    HomeMembershipState.REVOKED: 3,
}


class RegistryConflictError(DeviceRegistryError):
    pass


class DeviceRegistryService:
    """In-memory evidence registry; persistence remains owned by source systems."""

    def __init__(self) -> None:
        self._evidence: dict[str, dict[DeviceSource, DeviceDescriptor]] = {}
        self._listeners: list[Callable[[tuple[DeviceDescriptor, ...]], None]] = []
        self._batch_depth = 0
        self._notification_pending = False
        self._lock = threading.RLock()
        # Listener callbacks are external I/O/QObject seams. A failed observer
        # must never make an already committed Home revoke look rolled back.
        self._dispatch_lock = threading.RLock()
        self._revision = 0
        self._last_dispatched_revision = -1
        self._listener_failure_count = 0

    def ingest_discovered_node(self, node) -> None:
        """Project verified discovery presence without turning presence into trust.

        Signed announce verification proves device identity, not Home membership.
        The Home roster remains the only trust/membership source.
        """
        presence = node.presence
        roles = set(presence.roles)
        if "audio_receiver" in roles:
            device_type = DeviceType.MUSIC_STREAM
        elif "mobile_player" in roles or "sync_client" in roles:
            device_type = DeviceType.MOBILE
        elif "music_server" in roles or "playback_host" in roles:
            device_type = DeviceType.MICRO_SERVER
        elif "desktop_player" in roles:
            device_type = DeviceType.DESKTOP_PLAYER
        else:
            device_type = DeviceType.UNKNOWN

        capabilities: set[DeviceCapability] = {DeviceCapability.DIAGNOSTICS}
        if "audio_receiver" in roles or "playback_host" in roles:
            capabilities.add(DeviceCapability.PLAYBACK_ENDPOINT)
        if "remote_controller" in roles:
            capabilities.add(DeviceCapability.REMOTE_CONTROLLER)
        if "sync_client" in roles:
            capabilities.add(DeviceCapability.CONTENT_SYNC)
        # Discovery feature flags enrich capability *availability* only.
        feature_map = {str(k): bool(v) for k, v in presence.features.items()}
        if feature_map.get("firmware_update"):
            capabilities.add(DeviceCapability.FIRMWARE_UPDATE)
        if feature_map.get("network_reprovision"):
            capabilities.add(DeviceCapability.NETWORK_REPROVISION)
        if feature_map.get("factory_recreate"):
            capabilities.add(DeviceCapability.FACTORY_RECREATE)

        canonical = canonical_id_for(
            michi_id=presence.michi_id,
            local_id=(
                f"discovery:{presence.device_id}" if not presence.michi_id else None
            ),
        )
        self.ingest(
            DeviceSource.DISCOVERY,
            DeviceDescriptor(
                canonical_id=canonical,
                michi_id=presence.michi_id,
                name=presence.name,
                type=device_type,
                online=True,
                transports=frozenset({DeviceTransport.WHISKER}),
                capabilities=frozenset(capabilities),
                last_seen_ms=node.last_seen_ms,
            ),
        )

    def sync_discovery_nodes(self, nodes: tuple[object, ...]) -> None:
        """Replace transient discovery evidence as an all-or-nothing update.

        The merged registry never emits a transient empty/offline snapshot while
        one discovery poll is being replaced; this avoids dashboard flicker and
        Home Assistant remove/re-add churn.
        """
        with self.batch():
            self.clear_source(DeviceSource.DISCOVERY)
            for node in nodes:
                self.ingest_discovered_node(node)

    def ingest(self, source: DeviceSource, descriptor: DeviceDescriptor) -> None:
        """Store one source observation after enforcing source boundaries."""
        self._validate_source_boundary(source, descriptor)
        # Validate against a candidate, never against mutated live evidence.
        # A collision must leave get/list_devices and every subscriber usable.
        with self._lock:
            bucket = dict(self._evidence.get(descriptor.canonical_id, {}))
            bucket[source] = descriptor
            self._merge(descriptor.canonical_id, bucket)
            self._evidence[descriptor.canonical_id] = bucket
            self._revision += 1
        self._notify()

    def remove_evidence(self, source: DeviceSource, canonical_id: str) -> None:
        with self._lock:
            bucket = self._evidence.get(canonical_id)
            if bucket is None or source not in bucket:
                return
            # Never mutate a shared evidence bucket while readers use it.
            remaining = dict(bucket)
            remaining.pop(source)
            if remaining:
                self._evidence[canonical_id] = remaining
            else:
                self._evidence.pop(canonical_id, None)
            self._revision += 1
        self._notify()

    def clear_source(self, source: DeviceSource) -> None:
        with self.batch():
            for canonical_id in tuple(self._evidence):
                self.remove_evidence(source, canonical_id)

    @contextmanager
    def batch(self) -> Iterator[None]:
        """Serializable savepoint: nested failures restore the prior snapshot.

        Hold the lock across the ENTIRE transaction so a second discovery/
        Home/MQTT worker cannot interleave with a half-applied replacement.
        Publish the final snapshot only after releasing the registry lock.
        """
        self._lock.acquire()
        before = {key: dict(bucket) for key, bucket in self._evidence.items()}
        previous_pending = self._notification_pending
        previous_revision = self._revision
        self._batch_depth += 1
        committed = False
        try:
            yield
            committed = True
        except BaseException:
            self._evidence = before
            self._notification_pending = previous_pending
            self._revision = previous_revision
            raise
        finally:
            self._batch_depth -= 1
            notify = committed and self._batch_depth == 0 and self._notification_pending
            if notify:
                self._notification_pending = False
            self._lock.release()
            if notify:
                self._notify()

    def subscribe(
        self, listener: Callable[[tuple[DeviceDescriptor, ...]], None]
    ) -> Callable[[], None]:
        """Register a listener and send a snapshot without holding the lock."""
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)
            snapshot = self.list_devices()
        try:
            listener(snapshot)
        except Exception:
            # Initial hydration is also an observer seam; a disconnected
            # optional adapter must never prevent runtime construction.
            with self._lock:
                self._listener_failure_count += 1

        def _unsubscribe() -> None:
            with self._lock:
                if listener in self._listeners:
                    self._listeners.remove(listener)

        return _unsubscribe

    @property
    def listener_failure_count(self) -> int:
        """Non-secret diagnostic count for optional observer failures."""
        with self._lock:
            return self._listener_failure_count

    def _notify(self) -> None:
        # Serialize observer projections, not evidence mutations. A newer
        # transaction may commit during an old delivery; it must be delivered
        # AFTER the old one, never before it. Re-check the current revision to
        # suppress delayed/out-of-order duplicate deliveries.
        with self._dispatch_lock:
            with self._lock:
                if self._batch_depth > 0:
                    self._notification_pending = True
                    return
                revision = self._revision
                if revision <= self._last_dispatched_revision:
                    return
                listeners = tuple(self._listeners)
                snapshot = self.list_devices() if listeners else ()
                self._last_dispatched_revision = revision
            for listener in listeners:
                with self._lock:
                    if revision != self._revision:
                        # A reentrant listener mutated the Registry; its own
                        # nested dispatch already delivered the newer state.
                        break
                try:
                    listener(snapshot)
                except Exception:
                    # Observer failures (e.g. MQTT temporarily disconnected)
                    # MUST NOT unwind a committed Home revoke or hide the
                    # update from the remaining QML consumers. Do not record
                    # exception text: it may contain URLs or secrets.
                    with self._lock:
                        self._listener_failure_count += 1

    def get(self, canonical_id: str) -> DeviceDescriptor | None:
        with self._lock:
            bucket = self._evidence.get(canonical_id)
            return self._merge(canonical_id, bucket) if bucket else None

    def list_devices(self) -> tuple[DeviceDescriptor, ...]:
        with self._lock:
            devices = [
                self._merge(key, bucket) for key, bucket in self._evidence.items()
            ]
            return tuple(
                sorted(devices, key=lambda item: (item.type.value, item.name.lower()))
            )

    def by_type(self, device_type: DeviceType) -> tuple[DeviceDescriptor, ...]:
        return tuple(d for d in self.list_devices() if d.type is device_type)

    def ecosystem_projection(self, canonical_id: str) -> dict[str, object] | None:
        """Trust/control projection used by Ecosystem.  No sync controls live here."""
        device = self.get(canonical_id)
        if device is None:
            return None
        return {
            "canonicalId": device.canonical_id,
            "michiId": device.michi_id or "",
            "name": device.name,
            "type": device.type.value,
            "online": device.online,
            "homeMembership": device.home_membership.value,
            "trusted": device.trusted_home_member,
            "version": device.app_or_firmware_version or "",
            "lastSeenMs": device.last_seen_ms
            if device.last_seen_ms is not None
            else -1,
            "transports": sorted(item.value for item in device.transports),
            "capabilities": sorted(item.value for item in device.capabilities),
        }

    def devices_projection(self, canonical_id: str) -> dict[str, object] | None:
        """Content projection.  It consumes trust but never owns or mutates it."""
        device = self.get(canonical_id)
        if device is None:
            return None
        if device.type not in {DeviceType.MOBILE, DeviceType.GENERIC_DAP}:
            return None
        return {
            "canonicalId": device.canonical_id,
            "michiId": device.michi_id or "",
            "name": device.name,
            "type": device.type.value,
            "online": device.online,
            "syncAllowed": device.sync_allowed,
            "aircat": DeviceCapability.AIRCAT in device.capabilities,
            "storageTarget": DeviceCapability.STORAGE_TARGET in device.capabilities,
            "transports": sorted(item.value for item in device.transports),
        }

    @staticmethod
    def _validate_source_boundary(
        source: DeviceSource, device: DeviceDescriptor
    ) -> None:
        # Michi Home roster is the only registry source allowed to assert
        # membership/trust. Discovery, Michi Link presence and transports are
        # evidence about a device, never a second Home authority.
        if (
            source is not DeviceSource.HOME_ROSTER
            and device.home_membership is not HomeMembershipState.NONE
        ):
            raise DeviceRegistryError(
                f"{source.value} evidence must not carry Home membership"
            )
        if source is DeviceSource.AIRCAT:
            if device.type is not DeviceType.MOBILE or not device.michi_id:
                raise DeviceRegistryError(
                    "AirCat evidence is reserved for identified Michi "
                    "Music Mobile devices"
                )
            if DeviceTransport.AIRCAT not in device.transports:
                raise DeviceRegistryError(
                    "AirCat evidence must declare the AirCat transport"
                )
            allowed = {
                DeviceCapability.CONTENT_SYNC,
                DeviceCapability.AIRCAT,
                DeviceCapability.STORAGE_TARGET,
            }
            if not device.capabilities.issubset(allowed):
                raise DeviceRegistryError(
                    "AirCat evidence may expose sync/storage capabilities only"
                )
        if (
            source is DeviceSource.USB
            and device.type is DeviceType.GENERIC_DAP
            and DeviceTransport.USB not in device.transports
        ):
            raise DeviceRegistryError("generic DAP USB evidence must declare USB")

    @staticmethod
    def _first_non_empty(
        ordered: Iterable[tuple[DeviceSource, DeviceDescriptor]], field: str
    ) -> str | None:
        for _source, descriptor in ordered:
            value = getattr(descriptor, field)
            if value is not None and str(value).strip():
                return str(value)
        return None

    def _merge(
        self,
        canonical_id: str,
        bucket: dict[DeviceSource, DeviceDescriptor] | None,
    ) -> DeviceDescriptor:
        if not bucket:
            raise KeyError(canonical_id)
        ordered = sorted(
            bucket.items(), key=lambda pair: _SOURCE_PRIORITY[pair[0]], reverse=True
        )

        michi_ids = {d.michi_id for _, d in ordered if d.michi_id}
        if len(michi_ids) > 1:
            raise RegistryConflictError(
                f"conflicting michi_id evidence for {canonical_id}: {sorted(michi_ids)}"
            )

        explicit_types = {
            d.type for _, d in ordered if d.type is not DeviceType.UNKNOWN
        }
        if len(explicit_types) > 1:
            raise RegistryConflictError(
                f"conflicting device types for {canonical_id}: "
                f"{sorted(item.value for item in explicit_types)}"
            )

        memberships = [d.home_membership for _, d in ordered]
        membership = max(memberships, key=lambda item: _MEMBERSHIP_PRIORITY[item])
        home_ids = {d.michi_home_id for _, d in ordered if d.michi_home_id}
        if len(home_ids) > 1:
            raise RegistryConflictError(
                f"conflicting michi_home_id evidence for {canonical_id}"
            )

        transports: set[DeviceTransport] = set()
        capabilities: set[DeviceCapability] = set()
        last_seen_values: list[int] = []
        for _source, descriptor in ordered:
            transports.update(descriptor.transports)
            capabilities.update(descriptor.capabilities)
            if descriptor.last_seen_ms is not None:
                last_seen_values.append(descriptor.last_seen_ms)

        name = self._first_non_empty(ordered, "name") or canonical_id
        version = self._first_non_empty(ordered, "app_or_firmware_version")
        device_type = next(iter(explicit_types), DeviceType.UNKNOWN)
        return DeviceDescriptor(
            canonical_id=canonical_id,
            michi_id=next(iter(michi_ids), None),
            name=name,
            type=device_type,
            michi_home_id=next(iter(home_ids), None),
            home_membership=membership,
            online=any(d.online for _, d in ordered),
            transports=frozenset(transports),
            capabilities=frozenset(capabilities),
            app_or_firmware_version=version,
            last_seen_ms=max(last_seen_values) if last_seen_values else None,
        )
