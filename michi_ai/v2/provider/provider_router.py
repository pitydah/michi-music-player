from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Protocol

from michi_ai.v2.core.cancellation import CancellationToken
from michi_ai.v2.core.models import (
    ProviderRequest, ProviderResponse, ProviderType,
)

logger = logging.getLogger(__name__)

_LOCALHOST_HOSTS: frozenset[str] = frozenset({"127.0.0.1", "::1", "localhost"})


class AIProvider(Protocol):
    def chat(self, request: ProviderRequest, cancellation_token: CancellationToken | None = None) -> ProviderResponse: ...
    def check_health(self) -> bool: ...


class RuleProvider:
    def chat(self, request: ProviderRequest, cancellation_token: CancellationToken | None = None) -> ProviderResponse:
        return ProviderResponse(
            provider="rule",
            model="rules-v1",
            text=self._generate_rule_response(request),
        )

    def check_health(self) -> bool:
        return True

    def _generate_rule_response(self, request: ProviderRequest) -> str:
        return ("I understand your request. Based on the available rules, I can help with "
                "playback control, library search, playlist management, and other music player tasks. "
                "Please be more specific about what you'd like to do.")


class LocalModelProvider:
    def __init__(self, base_url: str = "http://127.0.0.1:11434", model: str = "llama3.2", timeout: int = 30) -> None:
        if not self._is_localhost(base_url):
            raise ValueError(f"Only localhost URLs allowed, got: {base_url}")
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._default_timeout = timeout
        self._chat_endpoint = f"{self._base_url}/api/chat"

    def chat(self, request: ProviderRequest, cancellation_token: CancellationToken | None = None) -> ProviderResponse:
        start = time.monotonic()
        try:
            payload = {
                "model": request.model or self._model,
                "messages": list(request.messages),
                "stream": False,
                "options": {
                    "temperature": request.temperature,
                    "num_predict": request.max_tokens,
                },
            }
            timeout = request.timeout_seconds or self._default_timeout
            data = json.dumps(payload).encode("utf-8")

            req = urllib.request.Request(
                self._chat_endpoint,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            if cancellation_token:
                cancellation_token.check()

            with urllib.request.urlopen(req, timeout=timeout) as resp:
                response_data = json.loads(resp.read().decode("utf-8"))

            latency = (time.monotonic() - start) * 1000
            message = response_data.get("message", {})
            content = message.get("content", "")

            return ProviderResponse(
                provider="ollama",
                model=response_data.get("model", self._model),
                latency_ms=latency,
                raw_size=len(content),
                text=content,
            )

        except urllib.error.HTTPError as e:
            latency = (time.monotonic() - start) * 1000
            return ProviderResponse(
                provider="ollama", model=self._model, latency_ms=latency,
                validation_errors=(f"HTTP {e.code}: {e.reason}",),
                fallback_used=True, text="",
            )
        except urllib.error.URLError as e:
            latency = (time.monotonic() - start) * 1000
            return ProviderResponse(
                provider="ollama", model=self._model, latency_ms=latency,
                validation_errors=(f"Connection failed: {e.reason}",),
                fallback_used=True, text="",
            )
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            return ProviderResponse(
                provider="ollama", model=self._model, latency_ms=latency,
                validation_errors=(str(e),),
                fallback_used=True, text="",
            )

    def check_health(self) -> bool:
        try:
            req = urllib.request.Request(f"{self._base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    @staticmethod
    def _is_localhost(url: str) -> bool:
        return any(host in url for host in _LOCALHOST_HOSTS)


class DisabledProvider:
    def chat(self, request: ProviderRequest, cancellation_token: CancellationToken | None = None) -> ProviderResponse:
        return ProviderResponse(
            provider="disabled",
            model="",
            text="AI assistant is disabled.",
            fallback_used=True,
        )

    def check_health(self) -> bool:
        return False


class ProviderRouter:
    def __init__(self) -> None:
        self._providers: dict[ProviderType, AIProvider] = {
            ProviderType.RULE: RuleProvider(),
            ProviderType.DISABLED: DisabledProvider(),
        }
        self._active_type: ProviderType = ProviderType.RULE

    def register(self, provider_type: ProviderType, provider: AIProvider) -> None:
        self._providers[provider_type] = provider

    def set_active(self, provider_type: ProviderType) -> None:
        if provider_type in self._providers:
            self._active_type = provider_type
        else:
            logger.warning("Provider type '%s' not registered", provider_type)

    @property
    def active(self) -> ProviderType:
        return self._active_type

    def chat(self, request: ProviderRequest, cancellation_token: CancellationToken | None = None) -> ProviderResponse:
        provider = self._providers.get(self._active_type)
        if provider is None:
            provider = self._providers.get(ProviderType.RULE)
        response = provider.chat(request, cancellation_token)
        if not response.text and response.fallback_used:
            fallback = self._providers.get(ProviderType.RULE)
            if fallback and fallback is not provider:
                fb_response = fallback.chat(request, cancellation_token)
                return ProviderResponse(
                    provider=f"{response.provider}->rule",
                    model=fb_response.model,
                    latency_ms=response.latency_ms + fb_response.latency_ms,
                    text=fb_response.text,
                    fallback_used=True,
                )
        return response

    def check_health(self) -> dict[str, bool]:
        return {pt.value: p.check_health() for pt, p in self._providers.items()}

    def get_provider(self, provider_type: ProviderType) -> AIProvider | None:
        return self._providers.get(provider_type)
