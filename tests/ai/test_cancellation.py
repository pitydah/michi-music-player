from __future__ import annotations

import threading

from michi_ai.v2.core.cancellation import (
    CancellationError, CancellationSource, CancellationToken,
    CancellationTokenRegistry,
)


class TestCancellationToken:
    def test_not_cancelled_by_default(self):
        token = CancellationToken()
        assert token.cancelled is False
        assert token.reason == ""

    def test_cancel_sets_flag(self):
        token = CancellationToken()
        token.cancel("user cancelled")
        assert token.cancelled is True
        assert token.reason == "user cancelled"

    def test_check_raises_when_cancelled(self):
        token = CancellationToken()
        token.cancel("stopped")
        try:
            token.check()
            assert False, "Should have raised"
        except CancellationError as e:
            assert "stopped" in str(e)

    def test_check_does_not_raise_when_active(self):
        token = CancellationToken()
        token.check()

    def test_wait_returns_true_when_cancelled(self):
        token = CancellationToken()
        token.cancel()
        assert token.wait(timeout=0.1) is True

    def test_wait_returns_false_when_not_cancelled(self):
        token = CancellationToken()
        assert token.wait(timeout=0.01) is False


class TestCancellationSource:
    def test_create_token(self):
        source = CancellationSource()
        token = source.token
        assert token is not None
        assert token.cancelled is False

    def test_cancel_via_source(self):
        source = CancellationSource()
        token = source.token
        source.cancel("test")
        assert token.cancelled is True
        assert token.reason == "test"

    def test_reset_creates_new_token(self):
        source = CancellationSource()
        old_token = source.token
        old_token.cancel()
        source.reset()
        new_token = source.token
        assert new_token is not old_token
        assert new_token.cancelled is False


class TestCancellationTokenRegistry:
    def test_register_and_cancel(self):
        registry = CancellationTokenRegistry()
        source = CancellationSource()
        registry.register("plan_1", source)
        result = registry.cancel("plan_1", "stopped")
        assert result is True
        assert source.token.cancelled is True

    def test_cancel_unknown_returns_false(self):
        registry = CancellationTokenRegistry()
        result = registry.cancel("nonexistent", "test")
        assert result is False

    def test_remove(self):
        registry = CancellationTokenRegistry()
        source = CancellationSource()
        registry.register("plan_1", source)
        registry.remove("plan_1")
        result = registry.cancel("plan_1", "test")
        assert result is False

    def test_get_returns_source(self):
        registry = CancellationTokenRegistry()
        source = CancellationSource()
        registry.register("plan_1", source)
        assert registry.get("plan_1") is source
        assert registry.get("nonexistent") is None

    def test_concurrent_cancel(self):
        registry = CancellationTokenRegistry()
        source = CancellationSource()
        registry.register("plan_1", source)
        errors = []

        def cancel_thread():
            try:
                registry.cancel("plan_1", "from thread")
            except Exception as e:
                errors.append(e)

        t = threading.Thread(target=cancel_thread)
        t.start()
        t.join()

        assert source.token.cancelled
        assert not errors
