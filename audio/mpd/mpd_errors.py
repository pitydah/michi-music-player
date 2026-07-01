"""MPD-specific errors."""


class MpdError(Exception):
    """Base MPD error."""


class MpdConnectionError(MpdError):
    """Connection refused, timeout, or not reachable."""


class MpdProtocolError(MpdError):
    """Malformed response or unexpected ACK."""


class MpdAckError(MpdError):
    """MPD returned an ACK error."""


class MpdNotRunningError(MpdError):
    """MPD daemon is not running or not installed."""
