"""Assistant errors."""
class AssistantError(Exception): pass
class AssistantTimeoutError(AssistantError): pass
class AssistantToolError(AssistantError): pass
