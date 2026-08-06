"""Recognition snapshot section — recognition provider availability."""

from __future__ import annotations

from typing import Any


class RecognitionSectionProvider:
    section_key = "recognition"

    def build(self, context) -> dict[str, Any]:
        recognition = context.services.get("recognition_service")
        if recognition is None:
            return {
                "available": False,
                "reason": "recognition_service_missing",
                "providers": 0,
            }
        try:
            providers = []
            if hasattr(recognition, "providers"):
                raw = recognition.providers
                providers = list(raw or [])
            elif hasattr(recognition, "list_providers"):
                providers = list(recognition.list_providers() or [])
            return {
                "available": True,
                "providers": len(providers),
                "provider_names": [getattr(p, "name", str(p)) for p in providers][:10],
            }
        except Exception as exc:
            return {
                "available": False,
                "reason": "recognition_readback_failed",
                "error": str(exc)[:200],
                "providers": 0,
            }
