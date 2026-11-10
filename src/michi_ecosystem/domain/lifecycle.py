"""Canonical host-side post-flash lifecycle statuses (C5).

Vocabulary only: enum values match the strings already emitted by the
pipeline (QML/harness contracts unchanged). ``VERIFIED`` is reserved and must
never be emitted without device evidence (STREAM-REQ-007); the host-side
final software state is ``DEVICE_CONFIRMATION_PENDING``.
"""

from __future__ import annotations

from enum import StrEnum


class FlashStatus(StrEnum):
    NOT_STARTED = ""
    FLASHING = "FLASHING"
    FLASH_READY = "FLASH_READY"
    FLASH_FAILED = "FLASH_FAILED"


class NetworkStatus(StrEnum):
    NOT_CHECKED = ""
    WAITING_FOR_DEVICE = "WAITING_FOR_DEVICE"
    DEVICE_DISCOVERED = "DEVICE_DISCOVERED"
    LAN_VERIFIED = "LAN_VERIFIED"
    LAN_FAILED = "LAN_FAILED"


class HomeStatus(StrEnum):
    NOT_REQUESTED = "HOME_NOT_REQUESTED"
    # Flashed with an enrollment candidate, awaiting device confirmation.
    DEVICE_CONFIRMATION_PENDING = "HOME_ENROLLMENT_PENDING_DEVICE_CONFIRMATION"
    # No enrollment requested; future device verification still pending.
    VERIFICATION_PENDING = "HOME_VERIFICATION_PENDING"
    # Reserved: only reachable with real device evidence.
    VERIFIED = "HOME_VERIFIED"
    ABORTED = "HOME_ENROLLMENT_ABORTED"
    SETTLEMENT_FAILED = "HOME_SETTLEMENT_FAILED"
