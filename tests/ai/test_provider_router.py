from __future__ import annotations

from michi_ai.v2.core.models import ProviderRequest, ProviderType
from michi_ai.v2.provider.provider_router import (
    DisabledProvider, LocalModelProvider, ProviderRouter, RuleProvider,
)


class TestRuleProvider:
    def test_chat_returns_response(self):
        provider = RuleProvider()
        request = ProviderRequest(messages=({"role": "user", "content": "hello"},))
        response = provider.chat(request)
        assert response.provider == "rule"
        assert response.text != ""

    def test_health_returns_true(self):
        provider = RuleProvider()
        assert provider.check_health() is True


class TestDisabledProvider:
    def test_chat_says_disabled(self):
        provider = DisabledProvider()
        request = ProviderRequest()
        response = provider.chat(request)
        assert response.fallback_used is True

    def test_health_returns_false(self):
        provider = DisabledProvider()
        assert provider.check_health() is False


class TestLocalModelProvider:
    def test_rejects_non_localhost(self):
        try:
            LocalModelProvider(base_url="http://example.com:11434")
            assert False, "Should have rejected remote URL"
        except ValueError as e:
            assert "localhost" in str(e).lower()

    def test_accepts_localhost(self):
        provider = LocalModelProvider(base_url="http://127.0.0.1:11434")
        assert provider is not None

    def test_accepts_localhost_v6(self):
        provider = LocalModelProvider(base_url="http://[::1]:11434")
        assert provider is not None

    def test_accepts_localhost_name(self):
        provider = LocalModelProvider(base_url="http://localhost:11434")
        assert provider is not None

    def test_is_localhost_check(self):
        assert LocalModelProvider._is_localhost("http://127.0.0.1:11434")
        assert LocalModelProvider._is_localhost("http://localhost:11434")
        assert LocalModelProvider._is_localhost("http://[::1]:11434")
        assert not LocalModelProvider._is_localhost("http://example.com")


class TestProviderRouter:
    def test_default_active_is_rule(self):
        router = ProviderRouter()
        assert router.active == ProviderType.RULE

    def test_register_and_set_active(self):
        router = ProviderRouter()
        provider = RuleProvider()
        router.register(ProviderType.LOCAL_MODEL, provider)
        router.set_active(ProviderType.LOCAL_MODEL)
        assert router.active == ProviderType.LOCAL_MODEL

    def test_set_active_unknown_does_nothing(self):
        router = ProviderRouter()
        router.set_active(ProviderType.LOCAL_MODEL)
        assert router.active == ProviderType.RULE  # unchanged

    def test_chat_with_rule_provider(self):
        router = ProviderRouter()
        request = ProviderRequest(messages=({"role": "user", "content": "hi"},))
        response = router.chat(request)
        assert response.text != ""

    def test_chat_with_disabled_falls_back(self):
        router = ProviderRouter()
        router.set_active(ProviderType.DISABLED)
        request = ProviderRequest()
        response = router.chat(request)
        assert response.text != ""  # falls back to rule

    def test_health_checks(self):
        router = ProviderRouter()
        health = router.check_health()
        assert "RULE" in health
        assert "DISABLED" in health

    def test_get_provider(self):
        router = ProviderRouter()
        provider = router.get_provider(ProviderType.RULE)
        assert provider is not None

    def test_get_provider_unknown(self):
        router = ProviderRouter()
        provider = router.get_provider(ProviderType.LOCAL_MODEL)
        assert provider is None
