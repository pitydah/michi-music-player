class AudioBackendError(Exception):
    """Base exception for all audio backend errors."""


class BackendNotAvailableError(AudioBackendError):
    """Raised when the requested backend is not available."""


class BackendConnectionError(AudioBackendError):
    """Raised when backend connection fails."""


class BackendPlaybackError(AudioBackendError):
    """Raised when a playback operation fails."""


class BackendCapabilityError(AudioBackendError):
    """Raised when the backend cannot perform the requested operation."""
