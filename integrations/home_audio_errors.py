"""Home Audio errors."""
class HomeAudioError(Exception): pass
class SnapcastConnectionError(HomeAudioError): pass
class HomeAssistantError(HomeAudioError): pass
