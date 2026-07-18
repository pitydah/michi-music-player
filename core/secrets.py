"""Secrets management — redaction, secure storage, and keyring integration."""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("michi.secrets")

_SENSITIVE_KEYS: set[str] = {
    "home_audio/ha_token", "mpd/password", "connections/ha_token",
    "connections/ha_password", "connections/snapcast_password",
    "ai/api_key", "recognition/audd_token", "recognition/acoustid_api_key",
    "api_key",
}

_SECRET_PATTERN = re.compile(r'(token|password|secret|api_key|auth)["\']?\s*[:=]\s*["\']?([^"\'&\s]+)', re.IGNORECASE)


def is_sensitive(key: str) -> bool:
    return key in _SENSITIVE_KEYS or any(k in key.lower() for k in ("token", "password", "secret", "api_key"))


def redact(value: Any, max_visible: int = 4) -> str:
    s = str(value)
    if not s or len(s) < max_visible + 4:
        return "****"
    return s[:max_visible] + "****"


def redact_dict(d: dict, depth: int = 0) -> dict:
    if depth > 5:
        return {"redacted": True}
    result = {}
    for k, v in d.items():
        if is_sensitive(str(k)):
            result[k] = redact(v)
        elif isinstance(v, dict):
            result[k] = redact_dict(v, depth + 1)
        else:
            result[k] = v
    return result


def redact_string(text: str) -> str:
    return _SECRET_PATTERN.sub(r'\1=****', text)


def sanitize_log(message: str) -> str:
    return _SECRET_PATTERN.sub(r'\1=****', message)
