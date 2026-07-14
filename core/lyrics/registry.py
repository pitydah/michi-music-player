from __future__ import annotations

import logging

from core.lyrics.interfaces import LyricsProvider
from core.lyrics.models import ProviderContract

logger = logging.getLogger("michi.lyrics.registry")


class LyricsProviderRegistry:
    def __init__(self):
        self._providers: dict[str, LyricsProvider] = {}
        self._contracts: dict[str, ProviderContract] = {}

    def register(self, provider: LyricsProvider):
        c = provider.contract
        self._providers[c.provider_id] = provider
        self._contracts[c.provider_id] = c
        logger.info("Registered provider: %s (priority=%d)", c.provider_id, c.priority)

    def unregister(self, provider_id: str):
        self._providers.pop(provider_id, None)
        self._contracts.pop(provider_id, None)

    def get(self, provider_id: str) -> LyricsProvider | None:
        return self._providers.get(provider_id)

    def list_enabled(self) -> list[LyricsProvider]:
        enabled = [
            p for pid, p in self._providers.items()
            if self._contracts.get(pid, ProviderContract(provider_id=pid)).enabled
        ]
        enabled.sort(key=lambda p: self._contracts.get(p.contract.provider_id, ProviderContract(provider_id=p.contract.provider_id)).priority)
        return enabled

    def resolve_order(self, provider_ids: list[str] | None = None) -> list[LyricsProvider]:
        if provider_ids:
            ordered = []
            for pid in provider_ids:
                p = self._providers.get(pid)
                if p and self._contracts.get(pid, ProviderContract(provider_id=pid)).enabled:
                    ordered.append(p)
            return ordered
        return self.list_enabled()

    def close_all(self):
        for provider in self._providers.values():
            try:
                provider.close()
            except Exception:
                logger.exception("Error closing provider %s", provider.contract.provider_id)
        self._providers.clear()
        self._contracts.clear()
