"""XDG Home key store (R2) — product paths, never repository-relative.

Storage root: ``$XDG_DATA_HOME/michi/home`` (fallback ``~/.local/share``).
The path belongs to the PRODUCT (Michi), so it survives the eventual deletion
of the michi-ecosystem repository without migration. Writes are atomic
(temp + fsync + rename) with restrictive permissions.
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path

from michi_ecosystem.domain.home import (
    HomeRootPublicIdentity,
    MichiHomeId,
    MichiHomeProfile,
)

_ENVELOPE_NAME = "home-root.envelope"
_PROFILE_NAME = "home-profile.json"


def default_home_dir(environ: Mapping[str, str] | None = None) -> Path:
    env = os.environ if environ is None else environ
    base = env.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "michi" / "home"


def _atomic_write(
    path: Path, payload: bytes, *, preserve_parent_permissions: bool = False
) -> None:
    parent_existed = path.parent.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not parent_existed or not preserve_parent_permissions:
        os.chmod(path.parent, 0o700)
    descriptor, temp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}-", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, 0o600)
        os.replace(temp_name, path)
        # Durability: fsync the parent directory so the rename survives power
        # loss (best effort on platforms that support directory fsync).
        with contextlib.suppress(OSError):
            dir_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(temp_name)
        raise


class XdgHomeKeyStore:
    """Encrypted-envelope storage (content opaque to this adapter)."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or default_home_dir()
        self._path = self.root / _ENVELOPE_NAME

    @property
    def envelope_path(self) -> Path:
        return self._path

    def exists(self) -> bool:
        return self._path.is_file()

    def load_envelope(self) -> bytes | None:
        if not self._path.is_file():
            return None
        return self._path.read_bytes()

    def save_envelope(self, envelope: bytes) -> None:
        _atomic_write(self._path, envelope)

    def delete_envelope(self) -> None:
        self._path.unlink(missing_ok=True)


class XdgHomeProfileRepository:
    """Public Home profile persistence (never contains secret material)."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or default_home_dir()
        self._path = self.root / _PROFILE_NAME

    def load_profile(self) -> MichiHomeProfile | None:
        if not self._path.is_file():
            return None
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return MichiHomeProfile(
            home_id=MichiHomeId(str(data["home_id"])),
            name=str(data["home_name"]),
            root=HomeRootPublicIdentity(
                public_key=str(data["home_root_public_key"]),
                key_scheme=str(data.get("key_scheme", "ed25519")),
            ),
            created_at=str(data.get("created_at", "")),
        )

    def delete_profile(self) -> None:
        self._path.unlink(missing_ok=True)

    def save_profile(self, profile: MichiHomeProfile) -> None:
        payload = json.dumps(
            {
                "home_id": profile.home_id.value,
                "home_name": profile.name,
                "home_root_public_key": profile.root.public_key,
                "key_scheme": profile.root.key_scheme,
                "created_at": profile.created_at,
            },
            separators=(",", ":"),
        ).encode("utf-8")
        _atomic_write(self._path, payload)
