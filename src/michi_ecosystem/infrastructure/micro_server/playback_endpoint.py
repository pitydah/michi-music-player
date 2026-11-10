"""Remote Micro Server playback endpoint (E9 substrate).

Implements ``PlaybackControlEndpoint`` over the authoritative endpoints:

- ``GET /api/v1/playback/state``
- ``POST /api/v1/playback/control`` (commands: play, pause, resume, toggle,
  stop, next, previous, seek, set_volume, shuffle, repeat).

``mute``/``unmute`` are NOT exposed: Micro implements them as
``set_volume(0)`` / ``set_volume(80)`` (fixed), so a reversible mute would be
a lie (MICRO-REQ-002). Silence is a volume change; the host restores the
previous volume explicitly.

Selection epochs guard against stale responses and duplicate in-flight
commands are rejected instead of double-issued. Nothing here owns local
playback; the Player remains the only local authority (master plan §156).
"""

from __future__ import annotations

import threading
from typing import Any

from michi_ecosystem.domain.playback import (
    CommandOutcome,
    PlaybackSnapshot,
    RemoteCommand,
)
from michi_ecosystem.domain.trust import TargetAuthorization, TrustState
from michi_ecosystem.infrastructure.micro_server.client import MicroServerClient
from michi_ecosystem.ports.micro_server import MicroServerRequestError
from michi_ecosystem.ports.playback_control import (
    PlaybackControlError,
    StaleResponseError,
)

_COMMAND_FIELD: dict[RemoteCommand, str | None] = {
    RemoteCommand.SEEK: "position_ms",
    RemoteCommand.SET_VOLUME: "volume",
    RemoteCommand.SHUFFLE: "value",
    RemoteCommand.REPEAT: "value",
}


class RemoteMicroServerPlaybackEndpoint:
    def __init__(
        self, client: MicroServerClient, *, target_id: str = "micro-server"
    ) -> None:
        self._client = client
        self._target_id: str | None = None
        self._authorization: TargetAuthorization | None = None
        self._epoch = 0
        self._default_target = target_id
        self._lock = threading.Lock()
        self._inflight: tuple[str, int | None, int | None, object | None] | None = None
        self._capabilities: frozenset[str] | None = None

    # ── selection ───────────────────────────────────────────────────────

    def select_target(self, authorization: TargetAuthorization) -> None:
        """Select a remote target; requires identity AND trusted pairing.

        A bare signed announce (identity only) is never sufficient for remote
        control (master plan §156, fail closed).
        """
        if not authorization.identity_verified:
            raise PlaybackControlError(
                "IDENTITY_UNVERIFIED",
                "el objetivo remoto no tiene identidad verificada",
            )
        if authorization.trust_state is not TrustState.TRUSTED:
            raise PlaybackControlError(
                "TRUST_REQUIRED",
                "el objetivo remoto no está vinculado "
                f"(estado: {authorization.trust_state})",
            )
        with self._lock:
            self._target_id = authorization.target_id or self._default_target
            self._authorization = authorization
            self._epoch += 1
            self._capabilities = None

    def clear_target(self) -> None:
        with self._lock:
            self._target_id = None
            self._epoch += 1
            self._capabilities = None

    def selection_epoch(self) -> int:
        return self._epoch

    def has_target(self) -> bool:
        return self._target_id is not None

    # ── capabilities ────────────────────────────────────────────────────

    def capabilities(self) -> frozenset[str]:
        if self._capabilities is not None:
            return self._capabilities
        try:
            info = self._client.server_info().info
        except MicroServerRequestError as exc:
            raise PlaybackControlError(exc.code, exc.message, exc.status) from exc
        capabilities: set[str] = set()
        if info.feature_enabled("playback"):
            capabilities.update({"playback", "volume"})
        if info.feature_enabled("queue"):
            capabilities.add("queue")
        self._capabilities = frozenset(capabilities)
        return self._capabilities

    # ── data plane ──────────────────────────────────────────────────────

    def snapshot(self) -> PlaybackSnapshot:
        self._require_target()
        epoch = self._epoch
        try:
            payload = self._client.playback_state()
        except MicroServerRequestError as exc:
            raise PlaybackControlError(exc.code, exc.message, exc.status) from exc
        self._assert_fresh(epoch)
        return PlaybackSnapshot.from_payload(payload)

    def send(
        self,
        command: str,
        *,
        position_ms: int | None = None,
        volume: int | None = None,
        value: object | None = None,
    ) -> CommandOutcome:
        self._require_target()
        try:
            parsed = RemoteCommand(command)
        except ValueError as exc:
            raise PlaybackControlError(
                "INVALID_COMMAND", f"unknown playback command: {command!r}"
            ) from exc

        if parsed in (RemoteCommand.MUTE, RemoteCommand.UNMUTE):
            # Micro: mute -> set_volume(0); unmute -> set_volume(80) FIXED
            # (crates/michi-api/src/routes/v1/playback.rs). Not reversible.
            raise PlaybackControlError(
                "MUTE_NOT_REVERSIBLE",
                "mute remoto no es reversible en Micro (unmute fija "
                "volumen 80); usa set_volume(0) y restaura desde el host",
            )

        key = (parsed.value, position_ms, volume, value)
        with self._lock:
            if self._inflight == key:
                raise PlaybackControlError(
                    "DUPLICATE_COMMAND", f"{parsed.value} is already in flight"
                )
            self._inflight = key

        try:
            body: dict[str, Any] = {"command": parsed.value}
            field = _COMMAND_FIELD.get(parsed)
            if field == "position_ms" and position_ms is not None:
                body["position_ms"] = position_ms
            elif field == "volume" and volume is not None:
                body["volume"] = volume
            elif field == "value" and value is not None:
                body["value"] = value

            epoch = self._epoch
            try:
                payload = self._client.playback_control(body)
            except MicroServerRequestError as exc:
                raise PlaybackControlError(exc.code, exc.message, exc.status) from exc
            self._assert_fresh(epoch)
            return CommandOutcome(
                command=parsed.value,
                status=str(payload.get("status", "")),
                payload=dict(payload),
            )
        finally:
            with self._lock:
                self._inflight = None

    # ── internals ───────────────────────────────────────────────────────

    def _require_target(self) -> None:
        if self._target_id is None:
            raise PlaybackControlError(
                "NO_TARGET", "no remote playback target is selected"
            )

    def _assert_fresh(self, epoch: int) -> None:
        if epoch != self._epoch:
            raise StaleResponseError()
