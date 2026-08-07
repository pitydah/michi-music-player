"""Radio snapshot section — radio station and history state."""

from __future__ import annotations

from typing import Any


class RadioSectionProvider:
    section_key = "radio"

    def build(self, context) -> dict[str, Any]:
        radio = context.services.get("radio_service")
        if radio is None:
            return {
                "available": False,
                "reason": "radio_service_missing",
                "stations": 0,
            }
        try:
            stations = 0
            if hasattr(radio, "get_stations"):
                stations = len(radio.get_stations() or [])
            elif hasattr(radio, "list_all"):
                try:
                    page = radio.list_all(page_size=1)
                    stations = int(getattr(page, "total", 0) or len(getattr(page, "items", []) or []))
                except Exception:
                    stations = 0
            history = []
            if hasattr(radio, "get_history"):
                history = (radio.get_history(limit=5) or [])[:5]
            return {
                "available": True,
                "stations": stations,
                "recent_stations": [
                    {
                        "name": getattr(s, "name", None) or (s.get("name") if isinstance(s, dict) else None),
                    }
                    for s in history
                ],
            }
        except Exception as exc:
            return {
                "available": False,
                "reason": "radio_readback_failed",
                "error": str(exc)[:200],
                "stations": 0,
            }
