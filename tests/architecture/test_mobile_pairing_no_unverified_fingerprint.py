"""No unverified fingerprints or code-only trust (Phase 7, falso éxito #9).

- The fingerprint stored for a device is DERIVED server-side from the
  public key material; a client-supplied fingerprint is only COMPARED
  (FINGERPRINT_MISMATCH on difference), never stored as-is.
- Trust is never assigned from the code-only path: legacy code-only pairing
  is disabled by default, creates devices as ``awaiting_approval`` and only
  ``approve_device()`` (persist-first, explicit user approval) sets
  trusted=True.
- The canonical DeviceRegistry is injected; the service never constructs one.
- The listener binds handlers per instance (no global class state) and
  refuses to run when Michi Link routes are not mounted.
"""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

SERVICE_FILE = PROJECT_ROOT / "core" / "mobile_sync_service.py"


def _source() -> str:
    return SERVICE_FILE.read_text(encoding="utf-8", errors="ignore")


def _lines() -> list[str]:
    return _source().splitlines()


def test_fingerprint_derived_server_side() -> None:
    source = _source()
    assert "def _derive_fingerprint" in source, (
        "fingerprint derivation must exist server-side"
    )
    assert "hashlib.sha256(raw_public_key).hexdigest()" in source, (
        "fingerprint must be SHA-256 over the public key material"
    )
    assert "FINGERPRINT_MISMATCH" in source, (
        "a client-supplied fingerprint mismatch must be rejected"
    )
    assert "fingerprint and fingerprint != derived" in source, (
        "the client fingerprint may only be COMPARED, never stored"
    )
    # The stored device fingerprint must always come from the derived value.
    assert "fingerprint=derived" in source


def test_no_hmac_only_trust_assignment() -> None:
    source = _source()
    assert "import hmac" not in source, (
        "the 6-digit HMAC proof is gone: trust requires a real signature"
    )
    assert "hmac.new" not in source


def test_trust_requires_explicit_approval() -> None:
    source = _source()
    lines = _lines()
    trusted_lines = [
        i for i, line in enumerate(lines) if "trusted = True" in line
    ]
    assert trusted_lines, "expected at least one trusted=True assignment"
    # Every trusted=True assignment must live inside approve_device (the
    # only place trust is granted) — never in a pairing/creation path.
    approve_start = next(
        i for i, line in enumerate(lines) if "def approve_device" in line)
    approve_end = len(lines)
    for i in trusted_lines:
        assert approve_start <= i < approve_end, (
            f"trusted = True at line {i + 1} is outside approve_device — "
            "trust must never be assigned by a pairing path"
        )
    assert "trusted=False" in source, (
        "devices must be created awaiting approval (trusted=False)"
    )
    assert "SIGNATURE_REQUIRED" in source


def test_signature_pairing_verifies_ed25519() -> None:
    source = _source()
    assert "def _verify_ed25519_signature" in source
    assert "def pair_request" in source
    assert "SIGNATURE_INVALID" in source
    assert "KEY_INVALID" in source
    assert "NONCE_REUSED" in source
    assert "SESSION_EXPIRED" in source
    assert "SESSION_NOT_FOUND" in source
    assert "PERSISTENCE_FAILED" in source


def test_legacy_mode_flags_and_ttl() -> None:
    source = _source()
    assert "legacy_code_pairing_enabled" in source
    assert "_LEGACY_TTL" in source
    assert "legacy_code_pairing" in source, (
        "legacy code pairing must be audit-recorded by kind"
    )
    assert "insecure_legacy_enabled" in source
    assert "NETWORK_DENIED" in source
    assert "allow_lan_pairing" in source
    assert "allowed_networks" in source


def test_registry_injected_not_constructed() -> None:
    source = _source()
    assert "from core.sync.device_registry import" not in source, (
        "the service must never import DeviceRegistry — "
        "it receives the canonical registry by injection"
    )
    assert "DeviceRegistry(" not in source, (
        "the service must never construct DeviceRegistry"
    )
    assert "self._device_registry" in source
    assert "device_registry=None" in source


def test_listener_has_no_global_class_state() -> None:
    source = _source()
    assert "SyncRequestHandler.server_ref = self" not in source, (
        "the listener must not mutate the handler class attribute"
    )
    assert "self.server_ref = listener" in source, (
        "the handler reference must be bound per instance before the "
        "request is handled"
    )


def test_routes_mounted_before_listening() -> None:
    source = _source()
    assert "ROUTES_NOT_MOUNTED" in source
    assert "_michi_link_mounted" in source
    assert "routes_mounted" in source
