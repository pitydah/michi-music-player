from __future__ import annotations

from core.lyrics.models import LyricsAttribution, ProviderContract


class LyricsAttributionPolicy:
    def __init__(self):
        self._policies: dict[str, ProviderContract] = {}

    def register(self, contract: ProviderContract):
        self._policies[contract.provider_id] = contract

    def get_attribution(self, provider_id: str) -> LyricsAttribution | None:
        contract = self._policies.get(provider_id)
        if contract:
            return contract.attribution
        return None

    def requires_attribution(self, provider_id: str) -> bool:
        attr = self.get_attribution(provider_id)
        return bool(attr and (attr.source_label or attr.provider_url))

    def format_attribution(self, provider_id: str) -> str:
        attr = self.get_attribution(provider_id)
        if not attr:
            return ""
        parts = []
        if attr.source_label:
            parts.append(attr.source_label)
        if attr.provider_url:
            parts.append(attr.provider_url)
        return " — ".join(parts)
