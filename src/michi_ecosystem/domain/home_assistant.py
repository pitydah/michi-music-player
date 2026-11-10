"""Home Assistant connectivity model (E12.1).

Activation and connectivity are different facts:

- the integration can be configured but disabled;
- an enable operation can succeed while the broker link later drops;
- a legacy adapter may not expose ongoing connection monitoring at all.

The UI must never claim "connected" merely because the integration is enabled.
"""

from __future__ import annotations

from enum import StrEnum


class HomeAssistantConnectionState(StrEnum):
    DISABLED = "disabled"
    CONFIGURED = "configured"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    # A host adapter that predates connectivity reporting: honest "we do not
    # know" instead of a fabricated connection.
    UNKNOWN = "unknown"


_TRANSPORT_EVENTS: dict[str, HomeAssistantConnectionState] = {
    "connecting": HomeAssistantConnectionState.CONNECTING,
    "connected": HomeAssistantConnectionState.CONNECTED,
    "reconnecting": HomeAssistantConnectionState.RECONNECTING,
    "disconnected": HomeAssistantConnectionState.DISCONNECTED,
    "error": HomeAssistantConnectionState.ERROR,
}


def state_from_transport_event(event: object) -> HomeAssistantConnectionState | None:
    """Map a transport connectivity event; unknown events are ignored."""
    if not isinstance(event, str):
        return None
    return _TRANSPORT_EVENTS.get(event.strip().lower())
