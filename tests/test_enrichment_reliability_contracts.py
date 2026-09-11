"""POST-R4 P10 — enrichment reliability contracts (13.5/13.6).

- Asset read integrity: un archivo de asset corrompido DESPUÉS de
  guardarse no se proyecta como válido (path_for verifica el checksum);
- Response size policy: JSON = 8 MiB por defecto, requests de imagen =
  10 MiB explícito (nunca una única constante global).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from michi.application.enrichment_ports import (  # noqa: E402
    HttpRequest,
)
from michi.domain.enrichment import (  # noqa: E402
    EnrichmentAssetRecord,
    EnrichmentEntityKind,
)
from michi.infrastructure.enrichment_assets import (  # noqa: E402
    FilesystemEnrichmentAssetStore,
)
from michi.infrastructure.enrichment_http import (  # noqa: E402
    MAX_PROVIDER_BODY_BYTES,
)


def _store(tmp_path):
    return FilesystemEnrichmentAssetStore(tmp_path)


# POST-R4 P10: PNG 4x4 válido hardcodeado (el decode usa QImageReader,
# no Pillow): el test es autónomo — nunca lee ficheros de un entorno
# local (el CI los tendría ausentes).
_PNG_4X4 = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000400000004080200000026930929"
    "0000001349444154789c63e4129163800126380b2f07000ca80044326d0da30000"
    "000049454e44ae426082"
)


def _record(asset_id, mime_type):
    return EnrichmentAssetRecord(
        asset_id=asset_id,
        entity_kind=EnrichmentEntityKind.ALBUM,
        external_entity_id=asset_id,
        mime_type=mime_type,
        provider="coverartarchive",
    )


class TestAssetReadIntegrity:
    def test_valid_asset_resolves(self, tmp_path):
        store = _store(tmp_path)
        stored = store.store(
            _record("album-rg-1", "image/png"),
            _PNG_4X4,
        )
        assert stored is not None
        path = store.path_for("album-rg-1")
        assert path is not None and path.exists()

    def test_corrupted_asset_after_store_is_invalid(self, tmp_path):
        """El bug: guardar una imagen válida y corromper los bytes
        después → path_for DEBE devolver None (nunca proyectar el asset
        corrupto como válido)."""
        store = _store(tmp_path)
        stored = store.store(
            _record("album-rg-2", "image/png"),
            _PNG_4X4,
        )
        assert stored is not None
        path = store.path_for("album-rg-2")
        assert path is not None, "el asset intacto resuelve"
        # corromper los bytes DESPUÉS del guardado
        path.write_bytes(b"corrupted-not-image")
        assert store.path_for("album-rg-2") is None, (
            "el asset corrupto NO se proyecta como válido"
        )

    def test_truncated_asset_is_invalid(self, tmp_path):
        store = _store(tmp_path)
        stored = store.store(
            _record("album-rg-3", "image/png"),
            _PNG_4X4,
        )
        assert stored is not None
        path = store.path_for("album-rg-3")
        assert path is not None
        path.write_bytes(_PNG_4X4[:10])  # truncado
        assert store.path_for("album-rg-3") is None


class TestResponseSizePolicy:
    def test_json_default_is_eight_mib(self):
        assert HttpRequest(url="https://x").max_response_bytes == 8 * 1024 * 1024
        assert MAX_PROVIDER_BODY_BYTES == 8 * 1024 * 1024

    def test_image_request_sets_explicit_ten_mib(self):
        coord_src = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "michi"
            / "application"
            / "enrichment_coordinator.py"
        ).read_text(encoding="utf-8")
        assert "max_response_bytes=10 * 1024 * 1024" in coord_src, (
            "la request de imagen fija su techo de 10 MiB"
        )

    def test_request_carries_its_own_limit(self):
        assert (
            HttpRequest(
                url="https://img", max_response_bytes=10 * 1024 * 1024
            ).max_response_bytes
            == 10 * 1024 * 1024
        )
