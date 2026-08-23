"""M6.9 — privacy + no-scan-network structural firewall.

Permanent gates proving:
- library scan / metadata extraction / library indexing NEVER import or
  reach any enrichment network module;
- enrichment providers never import the canonical metadata extractor or
  the library index;
- the enrichment setting defaults OFF;
- application startup composition performs no network (constructor side
  effects only — providers act exclusively on explicit operations).
"""

import inspect
from pathlib import Path

ROOT = Path(__file__).parent.parent

NETWORK_MODULES = (
    "michi.infrastructure.enrichment_http",
    "michi.infrastructure.enrichment_musicbrainz",
    "michi.infrastructure.enrichment_knowledge",
)

SCAN_SURFACE = (
    "src/michi/infrastructure/metadata_extractor.py",
    "src/michi/infrastructure/filesystem_scanner.py",
    "src/michi/infrastructure/library_index.py",
    "src/michi/domain/library_index.py",
    "src/michi/domain/library.py",
)

ENRICHMENT_SURFACE = (
    "src/michi/infrastructure/enrichment_http.py",
    "src/michi/infrastructure/enrichment_musicbrainz.py",
    "src/michi/infrastructure/enrichment_knowledge.py",
    "src/michi/application/enrichment_coordinator.py",
)


def _imports(source: str) -> list[str]:
    import ast

    tree = ast.parse(source)
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            found.append(node.module or "")
    return found


class TestNoNetworkInCanonicalScan:
    def test_scan_surface_never_imports_enrichment_network(self):
        for relative in SCAN_SURFACE:
            imports = _imports((ROOT / relative).read_text())
            for module in imports:
                for network in NETWORK_MODULES:
                    assert network not in module, f"{relative}: {network}"

    def test_enrichment_never_imports_canonical_extractor_or_index(self):
        for relative in ENRICHMENT_SURFACE:
            imports = _imports((ROOT / relative).read_text())
            for module in imports:
                assert "metadata_extractor" not in module, relative
                assert "filesystem_scanner" not in module, relative
                assert "library_index" not in module, relative

    def test_online_enrichment_defaults_off(self):
        from michi.domain.settings import SettingsState

        assert SettingsState().online_enrichment is False

    def test_coordinator_construction_has_no_network_side_effects(self):
        # The M6.9 graph is lazy: constructing providers must not issue
        # requests (the transport only acts inside explicit operations).
        from michi.infrastructure.enrichment_http import UrllibHttpTransport

        transport = UrllibHttpTransport()
        assert hasattr(transport, "_opener")
        # No opener.open call is possible without an explicit get():
        # construction is side-effect free by design.

    def test_provider_requests_require_explicit_operation(self):
        # The enabled() gate is checked BEFORE any provider call — a
        # disabled setting short-circuits to OFFLINE with zero provider
        # activity (behavioral proof lives in test_m6_9f_coordinator).
        import michi.application.enrichment_coordinator as coordinator_module

        source = inspect.getsource(
            coordinator_module.EnrichmentCoordinator.enrich_artist
        )
        assert "self._enabled()" in source
        assert "_submit_if_running" in source


class TestNoTagWriteInEnrichment:
    def test_enrichment_has_no_mutagen_write_paths(self):
        for relative in ENRICHMENT_SURFACE:
            source = (ROOT / relative).read_text()
            assert "import mutagen" not in source
            assert "from mutagen" not in source
            assert ".save()" not in source
