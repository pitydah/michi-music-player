"""No in-memory-only persistent features (Slice 7).

- MobileSyncService must persist pairing/trust/revocation (DB write path
  exists; the in-memory dict is only a cache loaded from the DB).
- The QR key is ``qr_data_uri`` (+ ``qr_mime_type`` + ``qr_payload``);
  ``qr_svg`` may survive only as a deprecated alias, never as the primary
  key consumed by the bridge.
- The bridge must consume service health instead of fabricating fields.
"""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

SERVICE_FILE = PROJECT_ROOT / "core" / "mobile_sync_service.py"
BRIDGE_FILE = PROJECT_ROOT / "ui_qml_bridge" / "mobile_sync_bridge.py"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_paired_devices_persist_to_db() -> None:
    source = _source(SERVICE_FILE)
    # The in-memory cache must be backed by a DB load + write path.
    assert "self._paired_devices" in source
    assert "mobile_sync_devices" in source, (
        "mobile_sync_service must reference the mobile_sync_devices table"
    )
    assert "_load_devices" in source, (
        "mobile_sync_service must load persisted devices on construction"
    )
    assert "INSERT OR REPLACE INTO mobile_sync_devices" in source, (
        "mobile_sync_service must persist devices (INSERT path)"
    )
    assert "DELETE FROM mobile_sync_devices" in source, (
        "mobile_sync_service must remove devices (DELETE path)"
    )
    assert "_persist_device" in source and "_delete_device" in source


def test_pairing_state_is_loaded_not_only_in_memory() -> None:
    source = _source(SERVICE_FILE)
    assert "self._load_devices()" in source, (
        "constructor must hydrate the cache from the DB"
    )
    assert "SELECT device_id, name, public_key" in source, (
        "load path must read device identity columns"
    )


def test_qr_keys_are_data_uri_not_svg() -> None:
    source = _source(SERVICE_FILE)
    assert "qr_data_uri" in source
    assert "qr_mime_type" in source
    assert "qr_payload" in source
    # qr_svg may exist only as a deprecated alias next to the new keys.
    qr_svg_lines = [
        line.strip() for line in source.splitlines()
        if "qr_svg" in line
    ]
    assert qr_svg_lines, "expected a deprecated qr_svg alias"
    for line in qr_svg_lines:
        assert "deprecated" in line.lower(), (
            f"qr_svg must be marked deprecated, got: {line}"
        )


def test_bridge_uses_qr_data_uri_and_service_health() -> None:
    bridge = _source(BRIDGE_FILE)
    # The bridge must prefer qr_data_uri; the deprecated key may survive
    # only as a fallback for old service instances.
    assert "result.get(\"qr_data_uri\"" in bridge, (
        "bridge must consume qr_data_uri first (not the deprecated qr_svg key)"
    )
    assert "self._svc.health()" in bridge, (
        "bridge must consume service health, not fabricate it"
    )
    assert '"available": False' in bridge, (
        "bridge health must report unavailable explicitly without a service"
    )
    assert "qr_svg" not in bridge, (
        "bridge must not reference the deprecated qr_svg key at all"
    )
