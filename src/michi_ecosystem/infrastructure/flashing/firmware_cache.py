"""Firmware cache (R6) — optimization only, never authority.

Every reuse re-verifies the manifest and every segment artifact by SHA-256;
an invalid cache entry is purged and the release is re-downloaded.
"""

from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path

from michi_ecosystem.domain.firmware import FirmwareRelease
from michi_ecosystem.domain.flashing import FirmwareManifest
from michi_ecosystem.infrastructure.flashing.manifest_verifier import (
    ManifestError,
    load_manifest,
    verify_artifact,
)


def default_cache_root(environ: dict[str, str] | None = None) -> Path:
    env = os.environ if environ is None else environ
    base = env.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "michi" / "firmware" / "music-stream"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class FirmwareCache:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or default_cache_root()

    def release_dir(self, release: FirmwareRelease) -> Path:
        return self.root / release.tag / release.board

    def purge(self, release: FirmwareRelease) -> None:
        shutil.rmtree(self.release_dir(release), ignore_errors=True)

    def is_verified(self, release: FirmwareRelease, manifest: FirmwareManifest) -> bool:
        """Re-verify a cached release; the cache is never trusted as-is."""
        base = self.release_dir(release)
        manifest_file = base / release.manifest_asset
        if not manifest_file.is_file() or manifest.board != release.board:
            return False
        try:
            cached_manifest = load_manifest(manifest_file)
        except ManifestError:
            return False
        if cached_manifest.board != manifest.board:
            return False
        artifacts = base / "artifacts"
        for segment in cached_manifest.segments:
            try:
                verify_artifact(cached_manifest, segment, artifacts)
            except ManifestError:
                return False
        return True
