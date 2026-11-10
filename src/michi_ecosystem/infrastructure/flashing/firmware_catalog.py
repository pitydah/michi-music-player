"""Local firmware catalog (development channel until Stream publishes artifacts).

michi-music-stream must publish flash manifests (segments + offsets + hashes)
from its build/release tooling — tracked as STREAM-REQ-002. Until then this
catalog only loads manifests from an explicit local directory (no invented
defaults, fail closed when absent).
"""

from __future__ import annotations

import re
from pathlib import Path

from michi_ecosystem.domain.flashing import FirmwareManifest
from michi_ecosystem.infrastructure.flashing.manifest_verifier import load_manifest


def _version_key(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", text)) or (0,)


class LocalFirmwareCatalog:
    """Loads ``*.manifest.json`` files from a local directory."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = root
        self._manifests: dict[str, FirmwareManifest] = {}
        if root is not None:
            self.reload()

    def reload(self) -> None:
        self._manifests.clear()
        if self._root is None or not self._root.is_dir():
            return
        for path in sorted(self._root.rglob("*.manifest.json")):
            manifest = load_manifest(path)
            self._manifests[str(path)] = manifest

    def all(self) -> tuple[FirmwareManifest, ...]:
        return tuple(self._manifests.values())

    def recommended(
        self, board: str, channel: str = "stable"
    ) -> FirmwareManifest | None:
        candidates = [
            manifest
            for manifest in self._manifests.values()
            if manifest.board == board and manifest.channel == channel
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda manifest: _version_key(manifest.version))

    def load(self, reference: str) -> FirmwareManifest:
        for manifest in self._manifests.values():
            if manifest.version == reference or manifest.source == reference:
                return manifest
        path = Path(reference)
        if path.is_file():
            return load_manifest(path)
        raise KeyError(f"unknown firmware reference: {reference}")


# Explicit dev-only alias: never the productive firmware source.
LocalDevFirmwareRepository = LocalFirmwareCatalog
