"""E11.6 Spaces: local grouping only; never modifies Home membership."""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from michi_ecosystem.domain.device_registry import DeviceDescriptor, HomeMembershipState


class SpaceError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class Space:
    space_id: str
    home_id: str
    name: str
    devices: tuple[str, ...] = ()

    def projection(self) -> dict[str, object]:
        return {
            "id": self.space_id,
            "homeId": self.home_id,
            "name": self.name,
            "devices": list(self.devices),
            "deviceCount": len(self.devices),
        }


class SpaceStore(Protocol):
    def list(self, home_id: str) -> tuple[Space, ...]: ...
    def add(self, space: Space) -> None: ...
    def rename(self, home_id: str, space_id: str, name: str) -> bool: ...
    def remove(self, home_id: str, space_id: str) -> bool: ...
    def assign(self, home_id: str, space_id: str, device_id: str) -> bool: ...
    def unassign(self, home_id: str, space_id: str, device_id: str) -> bool: ...
    def close(self) -> None: ...


_NAME = re.compile(r"^[^\x00-\x1f\x7f]{1,48}$")


class SpacesService:
    def __init__(
        self,
        store: SpaceStore,
        *,
        home_id: Callable[[], str | None],
        owner_authorized: Callable[[], bool],
        device_lookup: Callable[[str], DeviceDescriptor | None],
    ) -> None:
        self._store = store
        self._home_id = home_id
        self._authorized = owner_authorized
        self._device_lookup = device_lookup

    @property
    def home_available(self) -> bool:
        return bool(self._home_id())

    def _current_home(self) -> str:
        home = self._home_id()
        if not home:
            raise SpaceError("HOME_UNAVAILABLE")
        return home

    def _owner(self) -> str:
        home = self._current_home()
        if not self._authorized():
            raise SpaceError("OWNER_REQUIRED")
        return home

    @staticmethod
    def _name(value: str) -> str:
        name = value.strip() if isinstance(value, str) else ""
        if not _NAME.fullmatch(name):
            raise SpaceError("INVALID_NAME")
        return name

    def reconcile_revocations(self) -> None:
        """Permanently detach explicitly revoked/moved devices, never infer trust.

        Missing discovery evidence is *not* a revocation. A disappeared record
        remains hidden until a trusted roster observation can recover it.
        """
        home = self._current_home()
        for space in self._store.list(home):
            for canonical_id in space.devices:
                device = self._device_lookup(canonical_id)
                if device is not None and (
                    device.home_membership is HomeMembershipState.REVOKED
                    or (device.michi_home_id and device.michi_home_id != home)
                ):
                    self._store.unassign(home, space.space_id, canonical_id)

    def list_spaces(self) -> tuple[Space, ...]:
        home = self._current_home()
        # Read models must not write to SQLite. Explicit revocation handling is
        # performed by the Registry callback and mutation paths.
        visible: list[Space] = []
        for space in self._store.list(home):
            trusted = []
            for canonical_id in space.devices:
                device = self._device_lookup(canonical_id)
                if (
                    device is not None
                    and device.home_membership is HomeMembershipState.ACTIVE
                    and device.michi_home_id == home
                ):
                    trusted.append(canonical_id)
            visible.append(Space(space.space_id, home, space.name, tuple(trusted)))
        return tuple(visible)

    def create(self, name: str) -> Space:
        home = self._owner()
        normalized = self._name(name)
        if len(self._store.list(home)) >= 64:
            raise SpaceError("SPACE_LIMIT")
        if any(
            s.name.casefold() == normalized.casefold() for s in self._store.list(home)
        ):
            raise SpaceError("DUPLICATE_NAME")
        space = Space(uuid.uuid4().hex, home, normalized)
        self._store.add(space)
        return space

    def rename(self, space_id: str, name: str) -> None:
        home = self._owner()
        new_name = self._name(name)
        if any(
            s.space_id != space_id and s.name.casefold() == new_name.casefold()
            for s in self._store.list(home)
        ):
            raise SpaceError("DUPLICATE_NAME")
        if not self._store.rename(home, space_id, new_name):
            raise SpaceError("SPACE_UNKNOWN")

    def remove(self, space_id: str) -> None:
        home = self._owner()
        self.reconcile_revocations()
        # SqliteSpacesStore enforces SPACE_NOT_EMPTY under a single lock,
        # so another writer cannot race a UI-only count check.
        if not self._store.remove(home, space_id):
            raise SpaceError("SPACE_UNKNOWN")

    def assign(self, space_id: str, canonical_id: str) -> None:
        home = self._owner()
        device = self._device_lookup(canonical_id)
        if (
            device is None
            or device.canonical_id != canonical_id
            or device.home_membership is not HomeMembershipState.ACTIVE
            or device.michi_home_id != home
        ):
            raise SpaceError("DEVICE_NOT_TRUSTED")
        # Preserve the previous association when authorization or Home switches
        # while a move is in progress. Revocations instead detach permanently.
        previous_space = next(
            (
                space.space_id
                for space in self._store.list(home)
                if canonical_id in space.devices
            ),
            None,
        )
        if not self._store.assign(home, space_id, canonical_id):
            raise SpaceError("SPACE_UNKNOWN")
        # Membership or OWNER can change while the local DB operation is in
        # progress. A revocation callback might already have run before INSERT;
        # revalidate after the write and remove any now-stale assignment.
        current = self._device_lookup(canonical_id)
        try:
            if self._home_id() != home:
                raise SpaceError("HOME_UNAVAILABLE")
            if not self._authorized():
                raise SpaceError("OWNER_REQUIRED")
            if (
                current is None
                or current.canonical_id != canonical_id
                or current.home_membership is not HomeMembershipState.ACTIVE
                or current.michi_home_id != home
            ):
                raise SpaceError("DEVICE_NOT_TRUSTED")
        except BaseException:
            # Do not resurrect a revoked/moved identity.  For Home/session
            # races restore the prior assignment, but only if our write is
            # still the current assignment: a later user's move wins.
            current = self._device_lookup(canonical_id)
            still_member = (
                current is not None
                and current.home_membership is HomeMembershipState.ACTIVE
                and current.michi_home_id == home
            )
            rollback = getattr(self._store, "rollback_move_if_current", None)
            prior = previous_space if still_member else None
            if callable(rollback):
                rollback(home, canonical_id, space_id, prior)
            else:
                self._store.unassign(home, space_id, canonical_id)
                if prior is not None:
                    self._store.assign(home, prior, canonical_id)
            raise

    def unassign(self, space_id: str, canonical_id: str) -> None:
        if not self._store.unassign(self._owner(), space_id, canonical_id):
            raise SpaceError("SPACE_UNKNOWN")

    def close(self) -> None:
        self._store.close()
