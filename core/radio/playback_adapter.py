"""RadioPlaybackAdapter — formal playback boundary over PlayerService.

The canonical radio service never talks to an audio engine directly. It talks
to this adapter, which translates the *effective* player state (readback, never
optimistic) into radio session states.

Contract (FASE 5 P0 stabilization):

- ``load_stream(url)`` returns False — never True-on-absent-player — when there
  is no player service, no ``play_url`` method, or the call raised. The error
  is readable through :meth:`get_error`.
- ``get_state()`` is the PlayerService truth mapped to :class:`SessionState`:
  ``playing`` -> ``PLAYING``, ``paused``/``buffering`` -> ``BUFFERING``,
  ``reconnecting`` -> ``RECONNECTING``, ``stopped`` -> ``STOPPED``.
- An absent player is an explicit failure — the adapter never fabricates
  success when no backend is wired.
"""

from __future__ import annotations

import logging

from core.radio.models import SessionState, RadioError

logger = logging.getLogger("core.radio.playback_adapter")

_PLAYER_TO_SESSION: dict[str, SessionState] = {
    "playing": SessionState.PLAYING,
    "paused": SessionState.BUFFERING,
    "buffering": SessionState.BUFFERING,
    "reconnecting": SessionState.RECONNECTING,
    "stopped": SessionState.STOPPED,
    "idle": SessionState.IDLE,
}


class RadioPlaybackAdapter:
    """Translate PlayerService capabilities into the radio session contract.

    Args:
        player_service: The application ``PlayerService`` (or any object with
            ``play_url``/``stop``/``state`` semantics). May be None — in that
            case every playback operation fails explicitly.
        clock: Callable[[], float] returning monotonic seconds (tests).
    """

    def __init__(self, player_service=None, clock=None):
        self._player = player_service
        self._clock = clock or self._default_clock
        self._error = RadioError.NONE
        self._error_message = ""
        self._url = ""

    @staticmethod
    def _default_clock() -> float:
        import time
        return time.monotonic()

    @property
    def available(self) -> bool:
        """Whether a real player backend is wired (never True by default)."""
        return self._player is not None and hasattr(self._player, "play_url")

    def load_stream(self, url: str) -> bool:
        """Ask the player to start the stream. False == explicit failure."""
        if self._player is None:
            self._set_error(
                RadioError.BACKEND_UNAVAILABLE, "No player service available",
            )
            return False
        play_url = getattr(self._player, "play_url", None)
        if play_url is None:
            self._set_error(
                RadioError.BACKEND_UNAVAILABLE, "Player has no play_url",
            )
            return False
        try:
            play_url(url)
        except Exception as exc:  # noqa: BLE001 - adapter boundary
            logger.debug("Radio load_stream failed: %s", exc, exc_info=True)
            self._set_error(RadioError.CONNECTION_FAILED, str(exc))
            return False
        self._url = url
        self._error = RadioError.NONE
        self._error_message = ""
        return True

    def play(self) -> bool:
        """Resume the loaded stream. State readback is the confirmation."""
        if self._player is None:
            self._set_error(
                RadioError.BACKEND_UNAVAILABLE, "No player service available",
            )
            return False
        resume = getattr(self._player, "resume", None)
        if resume is None:
            return True
        try:
            resume()
        except Exception as exc:  # noqa: BLE001 - adapter boundary
            self._set_error(RadioError.CONNECTION_FAILED, str(exc))
            return False
        return True

    def stop(self) -> bool:
        """Stop playback. False == explicit failure (never silent success)."""
        if self._player is None:
            self._set_error(
                RadioError.BACKEND_UNAVAILABLE, "No player service available",
            )
            return False
        stop = getattr(self._player, "stop", None)
        if stop is None:
            self._set_error(
                RadioError.BACKEND_UNAVAILABLE, "Player has no stop",
            )
            return False
        try:
            stop()
        except Exception as exc:  # noqa: BLE001 - adapter boundary
            self._set_error(RadioError.CONNECTION_FAILED, str(exc))
            return False
        self._error = RadioError.NONE
        self._error_message = ""
        return True

    def get_state(self) -> SessionState:
        """PlayerService truth mapped to a session state.

        Exceptions while reading the player state are explicit failures, not
        silent fallbacks.
        """
        if self._player is None:
            return SessionState.FAILED
        try:
            state = getattr(self._player, "state", "")
            if callable(state):
                state = state()
        except Exception:  # noqa: BLE001 - adapter boundary
            self._set_error(RadioError.UNKNOWN, "Player state read failed")
            return SessionState.FAILED
        mapped = _PLAYER_TO_SESSION.get(str(state or "").lower())
        if mapped is None:
            return SessionState.CONNECTING
        return mapped

    def get_error(self) -> tuple[RadioError, str]:
        """Current adapter error: (RadioError, message)."""
        return self._error, self._error_message

    def _set_error(self, error: RadioError, message: str):
        self._error = error
        self._error_message = message
