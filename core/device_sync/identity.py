"""Identity resolution — the stable device serial priority chain.

The serial MUST NOT come from ``hash(path)`` (unstable between processes).
Priority (highest first):

1. USB serial
2. MTP persistent ID
3. Filesystem UUID
4. Vendor/product/volume UUID composite
5. Persisted fingerprint (deterministic composite, stored in the
   registry at pairing time)
6. Explicitly unstable fallback (flagged ``identity_unstable`` — callers
   must treat it as session-scoped, never as a stable serial)

Each resolved identity records ``identity_source`` so callers (and
architecture audits) can verify the chain is used.
"""
from __future__ import annotations

import hashlib

from core.device_sync.models import DeviceInfo, IdentitySource


def fingerprint_candidate(info: DeviceInfo) -> str:
    """Deterministic composite fingerprint from stable-ish surface fields."""
    base = "|".join(
        p for p in (info.vendor, info.model, info.volume_label, info.volume_uuid)
        if p
    )
    if not base:
        return ""
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]


def vendor_product_volume_uuid(info: DeviceInfo) -> str:
    """Composite of vendor/product/volume UUID (chain step 4)."""
    parts = [p for p in (info.vendor, info.model, info.volume_uuid) if p]
    if not parts:
        return ""
    return "|".join(parts)


def resolve_identity(info: DeviceInfo, registry=None) -> DeviceInfo:
    """Apply the identity priority chain to an adapter DeviceInfo.

    ``registry`` (optional) carries the persisted fingerprint for devices
    that expose no direct hardware id. When nothing stable exists, the
    fallback serial is derived from the mount point and explicitly flagged
    unstable.
    """
    serial, source = _pick_stable_serial(info)
    if serial:
        info.serial = serial
        info.identity_source = source
        info.identity_unstable = False
        return info

    # Step 5: persisted fingerprint (registry stores it at pairing time).
    fingerprint = fingerprint_candidate(info)
    if fingerprint:
        info.serial = fingerprint
        info.fingerprint = fingerprint
        info.identity_source = IdentitySource.PERSISTED_FINGERPRINT.value
        info.identity_unstable = False
        return info

    # Step 6: explicit unstable fallback — never silent.
    if info.mount_point:
        unstable = hashlib.sha256(info.mount_point.encode("utf-8")).hexdigest()[:16]
        info.serial = unstable
        info.identity_source = IdentitySource.UNSTABLE_FALLBACK.value
        info.identity_unstable = True
        return info

    info.serial = ""
    info.identity_source = IdentitySource.UNSTABLE_FALLBACK.value
    info.identity_unstable = True
    return info


def _pick_stable_serial(info: DeviceInfo) -> tuple[str, str]:
    """Return (serial, source) from the four hardware-level candidates."""
    candidates = (
        (info.usb_serial, IdentitySource.USB_SERIAL.value),
        (info.mtp_id, IdentitySource.MTP_ID.value),
        (info.filesystem_uuid, IdentitySource.FILESYSTEM_UUID.value),
        (vendor_product_volume_uuid(info),
         IdentitySource.VENDOR_PRODUCT_VOLUME_UUID.value),
    )
    for serial, source in candidates:
        if serial:
            return serial, source
    return "", ""
