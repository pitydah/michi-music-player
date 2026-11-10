"""Michi Ecosystem Player Coupling Kit (E13).

The single stable host-facing API. A future Player integration should import
ONLY this module (plus the dataclasses it re-exports) to:

1. build the runtime with host-owned adapters,
2. bind the seven QML context properties,
3. register the canonical 14 routes,
4. forward navigation and inject detail-page models,
5. start/stop background services,
6. close deterministically and query availability.

The kit never owns navigation, playback or trust authority.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from importlib import resources
from pathlib import Path

from michi_ecosystem.composition import (
    AccountEnvironment,
    EcosystemRuntime,
    FactoryEnvironment,
    HomeEnvironment,
    build_ecosystem_runtime,
)
from michi_ecosystem.integration.player_host import (
    CONTEXT_PROPERTIES,
    EXTERNAL_ROUTES,
    PAGE_ROUTES,
    apply_page_model,
    bind_player_context,
    connect_page_navigation,
    connect_player_navigation,
    register_player_routes,
    route_errors,
    route_manifest,
)

HOST_API_VERSION = 1
COMPATIBILITY_RESOURCE = "ECOSYSTEM_HOST_COMPATIBILITY.json"


def compatibility_manifest() -> dict[str, object]:
    """Packaged compatibility manifest (versioned, validated by tests)."""
    raw = (
        resources.files("michi_ecosystem")
        .joinpath(COMPATIBILITY_RESOURCE)
        .read_text(encoding="utf-8")
    )
    return json.loads(raw)


class EcosystemCouplingKit:
    """Owns one Ecosystem runtime for a host process (Player-side seam)."""

    def __init__(
        self,
        *,
        dashboard_service: object,
        factory: FactoryEnvironment,
        home_state_dir: Path | None = None,
        account_state_dir: Path | None = None,
        **host_options: object,
    ) -> None:
        self._runtime = build_ecosystem_runtime(
            dashboard_service=dashboard_service,
            factory=factory,
            home=(
                HomeEnvironment(state_dir=Path(home_state_dir))
                if home_state_dir is not None
                else None
            ),
            account=(
                AccountEnvironment(state_dir=Path(account_state_dir))
                if account_state_dir is not None
                else None
            ),
            **host_options,
        )

    @property
    def runtime(self) -> EcosystemRuntime:
        return self._runtime

    # ── QML / routes ────────────────────────────────────────────────────

    @staticmethod
    def qml_root() -> Path:
        """Installed package QML root (never a repository-relative path)."""
        return Path(__file__).resolve().parents[1] / "qml" / "ecosystem"

    def bind(self, context: object) -> None:
        bind_player_context(context, self._runtime)

    def register_routes(
        self,
        register: Callable[[str, Path], None],
        *,
        player_qml: Path | None = None,
    ) -> tuple[str, ...]:
        return register_player_routes(register, self.qml_root(), player_qml=player_qml)

    def connect_navigation(self, open_route: Callable[[str], None]) -> None:
        connect_player_navigation(self._runtime, open_route)

    @staticmethod
    def connect_page(page: object, open_route: Callable[[str], None]) -> bool:
        return connect_page_navigation(page, open_route)

    @staticmethod
    def apply_model(page: object, route_id: str, model: object) -> tuple[str, ...]:
        return apply_page_model(page, route_id, model)  # type: ignore[arg-type]

    def preflight(self, *, player_qml: Path | None = None) -> tuple[str, ...]:
        """Asset + Player design-system preflight for the 14 routes."""
        return route_errors(self.qml_root(), player_qml)

    @staticmethod
    def manifest() -> tuple[dict[str, object], ...]:
        return route_manifest()

    @staticmethod
    def compatibility() -> dict[str, object]:
        return compatibility_manifest()

    # ── lifecycle ───────────────────────────────────────────────────────

    def start(self) -> bool:
        return self._runtime.start()

    def stop(self) -> bool:
        """Stop background discovery; persistent stores stay open."""
        runner = self._runtime.discovery_runner
        return runner.stop() if runner is not None else True

    def close(self, *, timeout: float = 5.0) -> None:
        self._runtime.close(timeout=timeout)

    def availability(self) -> dict[str, object]:
        return self._runtime.availability()

    @staticmethod
    def context_properties() -> tuple[str, ...]:
        return CONTEXT_PROPERTIES

    @staticmethod
    def external_routes() -> tuple[str, ...]:
        return EXTERNAL_ROUTES

    @staticmethod
    def routes() -> tuple[str, ...]:
        return tuple(route.route_id for route in PAGE_ROUTES)
