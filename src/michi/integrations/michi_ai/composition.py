"""Player-side composition and lifecycle ownership for Michi AI."""

from __future__ import annotations

from typing import Any, Protocol

from michi_ai.integration import MichiAI, build_host_gateway_set

from michi.application.library_service import LibraryService
from michi.application.library_track_resolver import LibraryTrackResolver
from michi.integrations.michi_ai.library_gateway import PlayerLibraryGateway

PLAYER_AI_CAPABILITIES: tuple[str, ...] = (
    "library.read",
    "library.search",
)


class _PlayerServiceGraph(Protocol):
    library: LibraryService
    track_resolver: LibraryTrackResolver


class PlayerMichiAIIntegration:
    """Owns the optional Michi AI facade and its pending-plan lifecycle."""

    def __init__(self, runtime: MichiAI) -> None:
        self._runtime: MichiAI | None = runtime

    @property
    def is_shutdown(self) -> bool:
        return self._runtime is None

    def process(self, request: str, session_id: str | None = None) -> Any:
        return self._active().process(request, session_id=session_id)

    def create_session(self) -> str:
        return self._active().create_session()

    def confirm(self, confirmation_id: str) -> Any:
        return self._active().confirm(confirmation_id)

    def reject(self, confirmation_id: str) -> Any:
        return self._active().reject(confirmation_id)

    def cancel(self, plan_id: str) -> Any:
        return self._active().cancel(plan_id)

    def get_status(self) -> Any:
        return self._active().get_status()

    def get_capabilities(self) -> tuple[str, ...]:
        return self._active().get_capabilities()

    def shutdown(self) -> None:
        runtime = self._runtime
        if runtime is None:
            return
        self._runtime = None
        error: Exception | None = None
        try:
            pending_plans = runtime.get_pending_plans()
        except Exception as exc:
            error = exc
            pending_plans = ()
        for plan in pending_plans:
            try:
                runtime.cancel(plan.plan_id)
            except Exception as exc:
                error = error or exc
        if error is not None:
            raise error

    def _active(self) -> MichiAI:
        if self._runtime is None:
            raise RuntimeError("Michi AI integration is shut down")
        return self._runtime


def build_player_michi_ai(graph: _PlayerServiceGraph) -> PlayerMichiAIIntegration:
    """Compose the first real Player integration with explicit capabilities."""
    gateways = build_host_gateway_set(
        library=PlayerLibraryGateway(graph.library, graph.track_resolver)
    )
    runtime = MichiAI(
        gateways=gateways,
        capabilities=PLAYER_AI_CAPABILITIES,
    )
    return PlayerMichiAIIntegration(runtime)
