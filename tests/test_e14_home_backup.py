"""E14/M3: encrypted Home backup bounds, restore and export permissions."""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from michi_ecosystem.application import home_backup
from michi_ecosystem.application.home_backup import BackupError, HomeBackupService
from michi_ecosystem.domain.home import (
    DeviceRole,
    DeviceRosterEntry,
    HomeRootPublicIdentity,
    MembershipStatus,
    MichiHomeId,
    MichiHomeProfile,
    RevocationRecord,
)
from michi_ecosystem.infrastructure.home.key_envelope import seal

PASSWORD = "correct horse battery staple"


class _Keystore:
    def __init__(self, envelope: bytes | None) -> None:
        self.envelope = envelope

    def load_envelope(self) -> bytes | None:
        return self.envelope

    def save_envelope(self, envelope: bytes) -> None:
        self.envelope = envelope

    def delete_envelope(self) -> None:
        self.envelope = None


class _Profiles:
    def __init__(self, profile: MichiHomeProfile | None) -> None:
        self.profile = profile

    def load_profile(self) -> MichiHomeProfile | None:
        return self.profile

    def save_profile(self, profile: MichiHomeProfile) -> None:
        self.profile = profile

    def delete_profile(self) -> None:
        self.profile = None


class _Roster:
    def __init__(self, entries: tuple[DeviceRosterEntry, ...] = ()) -> None:
        self.entries = entries

    def list_entries(self) -> tuple[DeviceRosterEntry, ...]:
        return self.entries

    def replace_all(self, entries: tuple[DeviceRosterEntry, ...]) -> None:
        self.entries = entries


class _Revocations:
    def __init__(self, records: tuple[RevocationRecord, ...] = ()) -> None:
        self.records = records

    def list_records(self) -> tuple[RevocationRecord, ...]:
        return self.records

    def replace_all(self, records: tuple[RevocationRecord, ...]) -> None:
        self.records = records


def _profile() -> MichiHomeProfile:
    return MichiHomeProfile(
        home_id=MichiHomeId.generate(),
        name="Casa",
        root=HomeRootPublicIdentity(public_key="public-root-key"),
        created_at="2026-11-10T00:00:00Z",
    )


def _entry(index: int, status: MembershipStatus = MembershipStatus.ACTIVE):
    return DeviceRosterEntry(
        device_michi_id=f"device-{index:04d}",
        device_name=f"Device {index}",
        roles=(DeviceRole.DESKTOP_PLAYER,),
        status=status,
        membership_serial=f"serial-{index:04d}",
    )


def _service(
    *,
    entries: tuple[DeviceRosterEntry, ...] = (),
    records: tuple[RevocationRecord, ...] = (),
    profile: MichiHomeProfile | None = None,
) -> tuple[HomeBackupService, _Keystore, _Profiles, _Roster, _Revocations]:
    profile = profile or _profile()
    keystore = _Keystore(seal(b"private-home-root", PASSWORD))
    profiles = _Profiles(profile)
    roster = _Roster(entries)
    revocations = _Revocations(records)
    service = HomeBackupService(
        keystore=keystore,
        profiles=profiles,
        roster=roster,
        revocations=revocations,
        clock=lambda: "2026-11-10T00:00:00Z",
    )
    return service, keystore, profiles, roster, revocations


def test_empty_home_round_trip(tmp_path: Path) -> None:
    service, _, _, roster, revocations = _service()
    path = tmp_path / "empty.michi-backup"
    service.create_backup(path, PASSWORD)
    assert service.inspect_backup(path).home_id == service._profiles.profile.home_id
    assert service.verify_backup(path, PASSWORD) is True
    service.restore_backup(path, PASSWORD)
    assert roster.entries == ()
    assert revocations.records == ()


def test_hundred_devices_and_revocations_round_trip(tmp_path: Path) -> None:
    entries = tuple(_entry(i) for i in range(100))
    profile = _profile()
    records = tuple(
        RevocationRecord(home_id=profile.home_id, device_michi_id=f"device-{i:04d}")
        for i in range(20)
    )
    service, _, _, roster, revocations = _service(
        entries=entries, records=records, profile=profile
    )
    path = tmp_path / "large.michi-backup"
    service.create_backup(path, PASSWORD)
    assert path.stat().st_size <= home_backup.MAX_HOME_BACKUP_BYTES
    assert service.verify_backup(path, PASSWORD) is True
    service.restore_backup(path, PASSWORD)
    assert roster.entries == entries
    assert revocations.records == records


def test_entry_limit_is_rejected_before_sealing(tmp_path: Path) -> None:
    service, _, _, _, _ = _service(
        entries=tuple(_entry(i) for i in range(home_backup.MAX_BACKUP_ENTRIES + 1))
    )
    path = tmp_path / "too-many.michi-backup"
    with pytest.raises(BackupError, match="BACKUP_TOO_LARGE"):
        service.create_backup(path, PASSWORD)
    assert not path.exists()


def test_generated_backup_never_exceeds_the_accepted_file_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, _, _, _, _ = _service()
    monkeypatch.setattr(home_backup, "MAX_HOME_BACKUP_BYTES", 16)
    with pytest.raises(BackupError, match="BACKUP_TOO_LARGE"):
        service.create_backup(tmp_path / "bounded.michi-backup", PASSWORD)


def test_truncated_backup_is_rejected(tmp_path: Path) -> None:
    service, _, _, _, _ = _service()
    path = tmp_path / "truncated.michi-backup"
    service.create_backup(path, PASSWORD)
    path.write_bytes(path.read_bytes()[: path.stat().st_size // 2])
    assert service.verify_backup(path, PASSWORD) is False
    with pytest.raises(BackupError, match="BACKUP_INVALID"):
        service.restore_backup(path, PASSWORD)


def test_wrong_password_is_rejected(tmp_path: Path) -> None:
    service, _, _, _, _ = _service()
    path = tmp_path / "sealed.michi-backup"
    service.create_backup(path, PASSWORD)
    assert service.verify_backup(path, "wrong password") is False
    with pytest.raises(BackupError, match="BACKUP_OPEN_FAILED"):
        service.restore_backup(path, "wrong password")


def test_tampered_metadata_never_verifies(tmp_path: Path) -> None:
    service, _, _, _, _ = _service()
    path = tmp_path / "tampered.michi-backup"
    service.create_backup(path, PASSWORD)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["michi_backup"]["home_id"] = "b" * 16
    path.write_text(json.dumps(document), encoding="utf-8")
    assert service.verify_backup(path, PASSWORD) is False
    with pytest.raises(BackupError, match="BACKUP_HOME_MISMATCH"):
        service.restore_backup(path, PASSWORD)


def test_declared_entry_count_is_bounded_before_decrypt(tmp_path: Path) -> None:
    service, _, _, _, _ = _service()
    path = tmp_path / "counted.michi-backup"
    service.create_backup(path, PASSWORD)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["michi_backup"]["roster_count"] = home_backup.MAX_BACKUP_ENTRIES + 1
    path.write_text(json.dumps(document), encoding="utf-8")
    assert service.verify_backup(path, PASSWORD) is False
    with pytest.raises(BackupError, match="BACKUP_TOO_LARGE"):
        service.restore_backup(path, PASSWORD)


def test_export_preserves_an_existing_user_directory_and_protects_the_file(
    tmp_path: Path,
) -> None:
    export_dir = tmp_path / "exports"
    export_dir.mkdir(mode=0o775)
    export_dir.chmod(0o775)
    service, _, _, _, _ = _service()
    path = export_dir / "export.michi-backup"
    service.create_backup(path, PASSWORD)
    assert stat.S_IMODE(export_dir.stat().st_mode) == 0o775
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert service.verify_backup(path, PASSWORD) is True
