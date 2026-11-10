"""MICHI-F1 provisioning blob (master plan §137.3).

Bounded binary format for the factory bootstrap:

    magic "MICHI-F1" | schema u8 | nonce[16] | len u16be | payload JSON | crc32be

The payload never appears in logs or reprs: the request type redacts its
password. Generation here covers the immediate NVS bootstrap path; the final
``factory_cfg`` partition import arrives in E6.
"""

from __future__ import annotations

import json
import os
import struct
import zlib

from michi_ecosystem.domain.flashing import ProvisioningRequest

MAGIC = b"MICHI-F1"
SCHEMA_VERSION = 1
SUPPORTED_FACTORY_FORMAT = "michi-f1"
NONCE_BYTES = 16
MAX_PAYLOAD_BYTES = 512
_HEADER = struct.Struct(">8sB16sH")
_CRC = struct.Struct(">I")


class ProvisioningError(ValueError):
    """The provisioning request or blob is invalid."""


def build_provisioning_blob(
    request: ProvisioningRequest, *, nonce: bytes | None = None
) -> bytes:
    """Build a bounded MICHI-F1 blob for the given transient request."""
    body = json.dumps(
        {
            "ssid": request.ssid,
            "password": request.password,
            "region": request.region,
            "device_name": request.device_name,
        },
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    if not request.ssid:
        raise ProvisioningError("ssid must not be empty")
    if len(body) > MAX_PAYLOAD_BYTES:
        raise ProvisioningError(
            f"provisioning payload exceeds {MAX_PAYLOAD_BYTES} bytes"
        )
    nonce_bytes = os.urandom(NONCE_BYTES) if nonce is None else nonce
    if len(nonce_bytes) != NONCE_BYTES:
        raise ProvisioningError(f"nonce must be {NONCE_BYTES} bytes")
    header = _HEADER.pack(MAGIC, SCHEMA_VERSION, nonce_bytes, len(body))
    crc = zlib.crc32(header + body) & 0xFFFFFFFF
    return header + body + _CRC.pack(crc)


def parse_provisioning_blob(data: bytes) -> ProvisioningRequest:
    """Validate a MICHI-F1 blob and return its transient request."""
    if len(data) < _HEADER.size + _CRC.size:
        raise ProvisioningError("blob is too short")
    magic, schema, _nonce, length = _HEADER.unpack_from(data, 0)
    if magic != MAGIC:
        raise ProvisioningError("bad MICHI-F1 magic")
    if schema != SCHEMA_VERSION:
        raise ProvisioningError(f"unsupported provisioning schema: {schema}")
    if length > MAX_PAYLOAD_BYTES:
        raise ProvisioningError("provisioning payload exceeds bounds")
    body_start = _HEADER.size
    crc_start = body_start + length
    if crc_start + _CRC.size != len(data):
        raise ProvisioningError("blob length does not match its header")
    expected = _CRC.unpack_from(data, crc_start)[0]
    actual = zlib.crc32(data[:crc_start]) & 0xFFFFFFFF
    if actual != expected:
        raise ProvisioningError("blob CRC-32 mismatch")
    try:
        payload = json.loads(data[body_start:crc_start].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProvisioningError(f"invalid provisioning payload: {exc}") from exc
    if not isinstance(payload, dict):
        raise ProvisioningError("provisioning payload must be a JSON object")
    ssid = payload.get("ssid")
    password = payload.get("password")
    if not isinstance(ssid, str) or not ssid:
        raise ProvisioningError("provisioning payload is missing ssid")
    if not isinstance(password, str):
        raise ProvisioningError("provisioning payload is missing password")
    return ProvisioningRequest(
        ssid=ssid,
        password=password,
        region=str(payload.get("region", "")),
        device_name=str(payload.get("device_name", "")),
    )
