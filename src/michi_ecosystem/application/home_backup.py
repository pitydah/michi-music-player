"""Encrypted Home backup (R5): versioned, authenticated, portable.

Backup file layout:

    {"michi_backup": {metadata}, "envelope": b64(sealed payload)}

- metadata is plain (no secrets): readable by ``inspect_backup`` without the
  password;
- the sealed payload contains: the ORIGINAL encrypted Home envelope (so no
  re-encryption of private material on restore), the public profile, and the
  roster + revocation records.
"""

from __future__ import annotations

import base64
import json
import time
from collections.abc import Callable
from pathlib import Path

from michi_ecosystem.domain.home import (
    DeviceRole,
    DeviceRosterEntry,
    HomeBackupMetadata,
    HomeRootPublicIdentity,
    MembershipStatus,
    MichiHomeId,
    MichiHomeProfile,
    RevocationRecord,
)
from michi_ecosystem.infrastructure.home.key_envelope import (
    EnvelopeError,
    open_sealed,
    seal,
)
from michi_ecosystem.infrastructure.home.keystore import _atomic_write
from michi_ecosystem.ports.home import (
    DeviceRosterRepositoryPort,
    HomeKeyStorePort,
    HomeRepositoryPort,
    RevocationRepositoryPort,
)

BACKUP_FORMAT_VERSION = 1
MAX_HOME_BACKUP_BYTES = 4 * 1024 * 1024  # never parse unbounded external files


class BackupError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def _check_backup_size(path: Path) -> None:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise BackupError("BACKUP_INVALID", f"no se pudo leer {path}") from exc
    if size > MAX_HOME_BACKUP_BYTES:
        raise BackupError(
            "BACKUP_TOO_LARGE",
            f"el backup excede {MAX_HOME_BACKUP_BYTES} bytes",
        )


def _b64e(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64d(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class HomeBackupService:
    def __init__(
        self,
        *,
        keystore: HomeKeyStorePort,
        profiles: HomeRepositoryPort,
        roster: DeviceRosterRepositoryPort | None = None,
        revocations: RevocationRepositoryPort | None = None,
        clock: Callable[[], str] | None = None,
    ) -> None:
        self._keystore = keystore
        self._profiles = profiles
        self._roster = roster
        self._revocations = revocations
        self._clock = clock or _now_iso

    def _require_context(
        self,
    ) -> tuple[DeviceRosterRepositoryPort, RevocationRepositoryPort]:
        if self._roster is None or self._revocations is None:
            raise BackupError(
                "BACKUP_CONTEXT_MISSING",
                "roster/revocations no disponibles para esta operación",
            )
        return self._roster, self._revocations

    # ── create / inspect / verify ───────────────────────────────────────

    def create_backup(self, path: Path, password: str) -> HomeBackupMetadata:
        roster, revocations = self._require_context()
        envelope = self._keystore.load_envelope()
        profile = self._profiles.load_profile()
        if envelope is None or profile is None:
            raise BackupError("HOME_MISSING", "no hay un Home para respaldar")
        payload = {
            "backup_version": BACKUP_FORMAT_VERSION,
            "home_id": profile.home_id.value,
            "home_envelope": _b64e(envelope),
            "profile": {
                "home_id": profile.home_id.value,
                "home_name": profile.name,
                "home_root_public_key": profile.root.public_key,
                "key_scheme": profile.root.key_scheme,
                "created_at": profile.created_at,
            },
            "roster": [self._dump_entry(entry) for entry in roster.list_entries()],
            "revocations": [
                self._dump_record(record) for record in revocations.list_records()
            ],
        }
        sealed = seal(
            json.dumps(payload, separators=(",", ":")).encode("utf-8"), password
        )
        metadata = {
            "format_version": BACKUP_FORMAT_VERSION,
            "home_id": profile.home_id.value,
            "created_at": self._clock(),
            "kdf": "argon2id",
            "includes_roster": True,
        }
        document = {"michi_backup": metadata, "envelope": _b64e(sealed)}
        _atomic_write(path, json.dumps(document, separators=(",", ":")).encode())
        return HomeBackupMetadata(
            format_version=BACKUP_FORMAT_VERSION,
            home_id=profile.home_id,
            created_at=str(metadata["created_at"]),
            kdf="argon2id",
        )

    def inspect_backup(self, path: Path) -> HomeBackupMetadata:
        metadata = self._read_metadata(path)
        return HomeBackupMetadata(
            format_version=int(metadata["format_version"]),
            home_id=MichiHomeId(str(metadata["home_id"])),
            created_at=str(metadata.get("created_at", "")),
            kdf=str(metadata.get("kdf", "")),
            includes_roster=bool(metadata.get("includes_roster", False)),
        )

    def verify_backup(self, path: Path, password: str) -> bool:
        """Full coherence, not just decryptability (A7): tampered visible
        metadata must never verify as true."""
        try:
            header = self._read_metadata(path)
            payload = self._decrypt_payload(path, password)
            home_id = MichiHomeId(str(payload["home_id"]))
            self._check_consistency(header, payload, home_id)
        except (BackupError, KeyError, ValueError, TypeError):
            return False
        return True

    def _check_consistency(
        self, header: dict, payload: dict, home_id: MichiHomeId
    ) -> None:
        if str(header.get("home_id", "")) != home_id.value:
            raise BackupError("BACKUP_HOME_MISMATCH", "header y payload no coinciden")
        profile_home = str((payload.get("profile") or {}).get("home_id", ""))
        if profile_home != home_id.value:
            raise BackupError(
                "BACKUP_HOME_MISMATCH", "el perfil no pertenece a este Home"
            )
        for item in payload.get("revocations", []):
            if str(item.get("home_id", "")) != home_id.value:
                raise BackupError(
                    "BACKUP_HOME_MISMATCH",
                    "una revocación pertenece a otro Home",
                )

    # ── restore ─────────────────────────────────────────────────────────

    def restore_backup(self, path: Path, password: str) -> HomeBackupMetadata:
        roster, revocations = self._require_context()
        header = self._read_metadata(path)
        if int(header.get("format_version", 0)) != BACKUP_FORMAT_VERSION:
            raise BackupError(
                "BACKUP_VERSION_UNSUPPORTED",
                f"versión {header.get('format_version')} no soportada",
            )
        payload = self._decrypt_payload(path, password)
        version = int(payload.get("backup_version", 0))
        if version != BACKUP_FORMAT_VERSION:
            raise BackupError(
                "BACKUP_VERSION_UNSUPPORTED", f"versión {version} no soportada"
            )
        home_id = MichiHomeId(str(payload["home_id"]))
        self._check_consistency(header, payload, home_id)
        existing = self._profiles.load_profile()
        if existing is not None and existing.home_id != home_id:
            raise BackupError(
                "HOME_CONFLICT",
                "ya existe un Home distinto; restaura en un destino limpio",
            )

        # Validate everything before writing anything.
        try:
            envelope = _b64d(str(payload["home_envelope"]))
            profile_data = payload["profile"]
            profile = MichiHomeProfile(
                home_id=MichiHomeId(str(profile_data["home_id"])),
                name=str(profile_data["home_name"]),
                root=HomeRootPublicIdentity(
                    public_key=str(profile_data["home_root_public_key"]),
                    key_scheme=str(profile_data.get("key_scheme", "ed25519")),
                ),
                created_at=str(profile_data.get("created_at", "")),
            )
            entries = tuple(
                self._load_entry(item) for item in payload.get("roster", [])
            )
            records = tuple(
                self._load_record(item) for item in payload.get("revocations", [])
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise BackupError("BACKUP_INVALID", f"contenido inválido: {exc}") from exc

        # Apply with global rollback: after a failed restore the original
        # Home state must be unchanged (all-or-nothing semantics).
        previous_envelope = self._keystore.load_envelope()
        previous_profile = self._profiles.load_profile()
        previous_entries = roster.list_entries()
        previous_records = revocations.list_records()
        try:
            self._keystore.save_envelope(envelope)
            self._profiles.save_profile(profile)
            roster.replace_all(entries)
            revocations.replace_all(records)
        except Exception as exc:
            try:
                revocations.replace_all(previous_records)
                roster.replace_all(previous_entries)
                if previous_profile is not None:
                    self._profiles.save_profile(previous_profile)
                if previous_envelope is not None:
                    self._keystore.save_envelope(previous_envelope)
                else:
                    delete = getattr(self._keystore, "delete_envelope", None)
                    if delete is not None:
                        delete()
                if previous_profile is None:
                    delete_profile = getattr(self._profiles, "delete_profile", None)
                    if delete_profile is not None:
                        delete_profile()
            except Exception as rollback_exc:
                raise BackupError("RESTORE_ROLLBACK_FAILED", str(rollback_exc)) from exc
            raise BackupError("RESTORE_FAILED", str(exc)) from exc
        return HomeBackupMetadata(
            format_version=version,
            home_id=home_id,
            created_at=self._clock(),
            kdf="argon2id",
        )

    # ── internals ───────────────────────────────────────────────────────

    def _read_metadata(self, path: Path) -> dict:
        _check_backup_size(path)
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
            return document["michi_backup"]
        except (OSError, KeyError, ValueError) as exc:
            raise BackupError("BACKUP_INVALID", "archivo de backup inválido") from exc

    def _decrypt_payload(self, path: Path, password: str) -> dict:
        _check_backup_size(path)
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
            sealed = _b64d(str(document["envelope"]))
        except (OSError, KeyError, json.JSONDecodeError, ValueError) as exc:
            raise BackupError("BACKUP_INVALID", "archivo de backup inválido") from exc
        try:
            payload = json.loads(open_sealed(sealed, password).decode("utf-8"))
        except (EnvelopeError, json.JSONDecodeError) as exc:
            raise BackupError(
                "BACKUP_OPEN_FAILED", "contraseña incorrecta o backup dañado"
            ) from exc
        if not isinstance(payload, dict):
            raise BackupError("BACKUP_INVALID", "payload inválido")
        return payload

    @staticmethod
    def _dump_entry(entry: DeviceRosterEntry) -> dict:
        return {
            "device_michi_id": entry.device_michi_id,
            "device_name": entry.device_name,
            "roles": [role.value for role in entry.roles],
            "status": entry.status.value,
            "membership_serial": entry.membership_serial,
        }

    @staticmethod
    def _load_entry(item: dict) -> DeviceRosterEntry:
        return DeviceRosterEntry(
            device_michi_id=str(item["device_michi_id"]),
            device_name=str(item["device_name"]),
            roles=tuple(DeviceRole(role) for role in item["roles"]),
            status=MembershipStatus(str(item["status"])),
            membership_serial=str(item.get("membership_serial", "")),
        )

    @staticmethod
    def _dump_record(record: RevocationRecord) -> dict:
        return {
            "home_id": record.home_id.value,
            "device_michi_id": record.device_michi_id,
            "reason": record.reason,
            "revoked_at": record.revoked_at,
            "replacement_serial": record.replacement_serial,
        }

    @staticmethod
    def _load_record(item: dict) -> RevocationRecord:
        return RevocationRecord(
            home_id=MichiHomeId(str(item["home_id"])),
            device_michi_id=str(item["device_michi_id"]),
            reason=str(item.get("reason", "")),
            revoked_at=str(item.get("revoked_at", "")),
            replacement_serial=str(item.get("replacement_serial", "")),
        )
