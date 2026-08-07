"""D2: the RADIO search provider is wired with the composed station repo.

Composition (``core.composition.ecosystem``) builds the canonical
``SqliteStationRepository`` and registers it as ``radio_station_repository``;
the RADIO search provider must receive that SAME instance (identity, not a
copy) when it is registered on ``search_provider_registry``. The provider
never constructs its own repository.
"""
from __future__ import annotations

from pathlib import Path

from core.event_bus import EventBus
from core.search.models import SearchDomain
from core.search.providers import SearchProviderRegistry
from core.service_container import ServiceContainer

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _build_container(tmp_path, monkeypatch) -> ServiceContainer:
    """Controlled composition build: only the pieces the radio wiring needs.

    Uses a throwaway radio DB path so the repository initializes in tmp,
    never against the real user data directory. The snapserver manager is
    stubbed because its constructor starts a QTimer — a native Qt object
    that must never be created without a running QApplication (it would
    corrupt the process-wide event dispatcher and segfault pytest later).
    """
    monkeypatch.setattr(
        "core.paths.radio_database_path", lambda: str(tmp_path / "radio.db")
    )
    from core.composition.ecosystem import build as eco

    class _StubSnapServerManager:
        def configure(self, *args, **kwargs) -> None:
            pass

    monkeypatch.setattr(
        "integrations.snapcast.snapserver_manager.SnapServerManager",
        _StubSnapServerManager,
    )

    container = ServiceContainer()
    container.register("event_bus", EventBus())
    container.register("playback_service", None)
    registry = SearchProviderRegistry()
    container.register("search_provider_registry", registry)
    eco(container)
    return container


def test_radio_provider_wired_with_composed_repo(tmp_path, monkeypatch) -> None:
    container = _build_container(tmp_path, monkeypatch)

    repo = container.get("radio_station_repository")
    assert repo is not None, "radio stack must compose"
    registry = container.get("search_provider_registry")
    provider = registry.provider(SearchDomain.RADIO)
    assert provider is not None, "RADIO provider must be registered"
    assert provider._repo is repo, (
        "RADIO provider must use the SAME SqliteStationRepository instance "
        "registered for radio (identity, not a copy)"
    )


def test_radio_provider_has_working_repo_identity(tmp_path, monkeypatch) -> None:
    container = _build_container(tmp_path, monkeypatch)

    repo = container.get("radio_station_repository")
    provider = container.get("search_provider_registry").provider(
        SearchDomain.RADIO
    )
    assert provider._repo is not None
    assert provider._repo._db_path == str(tmp_path / "radio.db")


def test_radio_registration_lives_in_ecosystem_composition() -> None:
    """Wiring source scan: the broken library-DB registration is gone and the
    canonical wiring registers SearchDomain.RADIO with the composed repo."""
    library_source = (PROJECT_ROOT / "core" / "composition" / "library.py").read_text(
        encoding="utf-8"
    )
    ecosystem_source = (
        PROJECT_ROOT / "core" / "composition" / "ecosystem.py"
    ).read_text(encoding="utf-8")

    assert "RadioSearchRepository" not in library_source
    assert "SearchDomain.RADIO" in ecosystem_source
    assert "RadioStationSearchProvider(station_repo)" in ecosystem_source
