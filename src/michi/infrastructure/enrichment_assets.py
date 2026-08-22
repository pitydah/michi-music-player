"""Filesystem enrichment asset store (M6.9A) — EXTERNAL ARTWORK ONLY.

M6.9A ARTWORK FIREWALL: three independent artwork authorities exist
(LOCAL embedded/folder, USER override, EXTERNAL downloaded). This store
owns ONLY the external one, in its own directory. It must never reuse or
mutate the canonical local artwork cache and never write downloaded
artwork into audio files.
"""

import logging
from pathlib import Path

from michi.application.enrichment_ports import EnrichmentAssetStorePort

logger = logging.getLogger(__name__)


class FilesystemEnrichmentAssetStore(EnrichmentAssetStorePort):
    """Stores downloaded enrichment assets under an enrichment-owned dir."""

    def __init__(self, root_dir: Path) -> None:
        self._root = root_dir

    def store(self, asset_id: str, data: bytes, mime_type: str) -> str | None:
        del mime_type  # content stored raw; mime is caller metadata
        try:
            self._root.mkdir(parents=True, exist_ok=True)
            # asset_id is caller-controlled: reject path traversal.
            safe_id = Path(asset_id).name
            if safe_id != asset_id:
                logger.warning("enrichment asset id rejected: %r", asset_id)
                return None
            target = self._root / safe_id
            target.write_bytes(data)
            return str(target)
        except OSError as exc:
            logger.warning("enrichment asset store failed: %s", exc)
            return None

    def path_for(self, asset_id: str) -> Path | None:
        safe_id = Path(asset_id).name
        if safe_id != asset_id:
            return None
        target = self._root / safe_id
        return target if target.is_file() else None

    def clear(self) -> None:
        try:
            for path in self._root.iterdir():
                if path.is_file():
                    path.unlink()
        except OSError as exc:
            logger.warning("enrichment asset clear failed: %s", exc)
