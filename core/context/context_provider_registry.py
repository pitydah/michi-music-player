"""ContextProviderRegistry — canonical snapshot sections from registered providers.

Each snapshot section (playback, queue, library, audio, ecosystem, jobs,
radio, recognition, errors, capabilities) is produced by exactly one provider
registered under its section key. Providers are plain callables invoked with
the owning ``ContextService`` (which exposes the injected real services via
``services``); they never hardcode capability values — a missing or unhealthy
service yields ``available: False`` with a reason (ADR-002, ADR-005).
"""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger("michi.context_provider_registry")

ContextProvider = Callable[[Any], dict[str, Any]]


class ContextProviderRegistry:
    """Register and build snapshot sections through section-keyed providers."""

    def __init__(self) -> None:
        self._providers: dict[str, ContextProvider] = {}

    def register(self, section_key: str, provider: ContextProvider) -> None:
        if not (callable(provider) or hasattr(provider, "build")):
            raise TypeError(f"Provider for '{section_key}' is not callable")
        if section_key in self._providers:
            logger.debug("ContextProviderRegistry: re-registering '%s'", section_key)
        self._providers[section_key] = provider

    def unregister(self, section_key: str) -> None:
        self._providers.pop(section_key, None)

    def has(self, section_key: str) -> bool:
        return section_key in self._providers

    def build_section(self, section_key: str, context) -> dict[str, Any]:
        provider = self._providers.get(section_key)
        if provider is None:
            return {
                "available": False,
                "reason": f"provider_not_registered:{section_key}",
            }
        try:
            builder = getattr(provider, "build", provider)
            section = builder(context) or {}
            if not isinstance(section, dict):
                logger.warning(
                    "ContextProviderRegistry: provider '%s' returned %s",
                    section_key, type(section).__name__,
                )
                return {"available": False, "reason": f"invalid_section:{section_key}"}
            return section
        except Exception as exc:
            logger.exception("ContextProviderRegistry: '%s' failed", section_key)
            return {
                "available": False,
                "reason": f"provider_error:{section_key}",
                "error": str(exc)[:200],
            }

    def build_all(self, context) -> dict[str, dict[str, Any]]:
        return {
            section_key: self.build_section(section_key, context)
            for section_key in self.list_registered()
        }

    def list_registered(self) -> list[str]:
        return sorted(self._providers.keys())
