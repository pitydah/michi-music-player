from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

from michi.integration.storage_migration import (
    StorageMigrationError,
    migrate_state,
)


def _write(root: Path, name: str, payload: bytes) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def test_existing_legacy_home_is_copied_verbatim_with_a_backup(tmp_path: Path) -> None:
    legacy = tmp_path / "legacy-home"
    _write(legacy, "home-root.envelope", b"sealed-root-material")
    _write(legacy, "home-profile.json", b'{"home_id":"home-1"}')
    _write(legacy, "home-state.db", b"sqlite-bytes")
    _write(legacy, "ecosystem/spaces/spaces.db", b"spaces")

    result = migrate_state(
        source=legacy,
        target=tmp_path / "state" / "home",
        backup_root=tmp_path / "state" / "migration-backups",
    )

    assert result.state == "migrated"
    assert result.file_count == 4
    assert Path(result.target).joinpath("home-root.envelope").read_bytes() == (
        b"sealed-root-material"
    )
    assert Path(result.target).joinpath("ecosystem/spaces/spaces.db").read_bytes() == (
        b"spaces"
    )
    assert Path(result.backup).joinpath("home-profile.json").read_bytes() == (
        b'{"home_id":"home-1"}'
    )
    # The legacy Home remains untouched as the rollback source.
    assert legacy.joinpath("home-root.envelope").read_bytes() == b"sealed-root-material"


def test_existing_target_is_never_overwritten_or_merged(tmp_path: Path) -> None:
    legacy = tmp_path / "legacy-home"
    _write(legacy, "home-root.envelope", b"old")
    target = tmp_path / "state" / "home"
    _write(target, "home-root.envelope", b"current")

    result = migrate_state(
        source=legacy,
        target=target,
        backup_root=tmp_path / "state" / "migration-backups",
    )

    assert result.state == "target_present"
    assert target.joinpath("home-root.envelope").read_bytes() == b"current"
    assert not (tmp_path / "state" / "migration-backups").exists()


def test_missing_legacy_state_does_not_create_a_home(tmp_path: Path) -> None:
    result = migrate_state(
        source=tmp_path / "missing",
        target=tmp_path / "state" / "home",
        backup_root=tmp_path / "state" / "migration-backups",
    )

    assert result.state == "no_legacy"
    assert not (tmp_path / "state" / "home").exists()


def test_empty_legacy_state_is_a_no_op(tmp_path: Path) -> None:
    legacy = tmp_path / "legacy-home"
    legacy.mkdir()

    result = migrate_state(
        source=legacy,
        target=tmp_path / "state" / "home",
        backup_root=tmp_path / "state" / "migration-backups",
    )

    assert result.state == "no_legacy"
    assert not (tmp_path / "state" / "home").exists()


def test_symlink_in_legacy_state_is_refused(tmp_path: Path) -> None:
    if os.name != "posix":
        pytest.skip("symlink permissions are POSIX-specific")
    legacy = tmp_path / "legacy-home"
    legacy.mkdir()
    secret = _write(tmp_path, "secret", b"do-not-follow")
    (legacy / "link").symlink_to(secret)

    with pytest.raises(StorageMigrationError, match="symlink"):
        migrate_state(
            source=legacy,
            target=tmp_path / "state" / "home",
            backup_root=tmp_path / "state" / "migration-backups",
        )

    assert not (tmp_path / "state" / "home").exists()
    backups = tmp_path / "state" / "migration-backups"
    assert not backups.exists() or not any(backups.iterdir())


@pytest.fixture(scope="module")
def qapp():
    qt = pytest.importorskip("PySide6.QtGui")
    app = qt.QGuiApplication.instance()
    if app is None:
        app = qt.QGuiApplication([])
    yield app


def test_host_migrates_legacy_state_once_and_keeps_the_original(
    tmp_path: Path, qapp
) -> None:
    from michi.integration.ecosystem_host import EcosystemPlayerHost
    from tests.test_e14_ecosystem_integration import (
        PLAYER_QML,
        _Dashboard,
        _Discovery,
        _factory,
    )

    legacy_home = tmp_path / "legacy-home"
    _write(legacy_home, "notes.txt", b"legacy-home-marker")
    legacy_account = tmp_path / "legacy-account"
    legacy_account.mkdir(parents=True)
    sqlite3.connect(legacy_account / "account.db").close()

    host = EcosystemPlayerHost(
        dashboard_service=_Dashboard(),
        player_qml_root=PLAYER_QML,
        state_root=tmp_path / "ecosystem",
        factory=_factory(),
        discovery_source=_Discovery(),
        legacy_home_dir=legacy_home,
        legacy_account_dir=legacy_account,
    )

    try:
        assert host.storage_migration["home"].state == "migrated"
        assert host.storage_migration["account"].state == "migrated"
        assert (tmp_path / "ecosystem/home/notes.txt").read_bytes() == (
            b"legacy-home-marker"
        )
        assert (tmp_path / "ecosystem/account/account.db").exists()
        assert legacy_home.joinpath("notes.txt").exists()
    finally:
        host.close(force=True)
