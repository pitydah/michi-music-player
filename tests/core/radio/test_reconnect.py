
from core.radio.reconnect import ReconnectPolicy, RadioScheduler
from core.radio.models import ReconnectPolicyConfig, RadioError


class TestReconnectPolicy:
    def test_starts_with_zero_attempts(self):
        policy = ReconnectPolicy()
        assert policy.attempt == 0

    def test_should_retry_when_enabled(self):
        policy = ReconnectPolicy(ReconnectPolicyConfig(enabled=True, max_attempts=5))
        policy.start()
        assert policy.should_retry()

    def test_should_not_retry_when_disabled(self):
        policy = ReconnectPolicy(ReconnectPolicyConfig(enabled=False))
        policy.start()
        assert not policy.should_retry()

    def test_should_not_retry_after_max_attempts(self):
        policy = ReconnectPolicy(ReconnectPolicyConfig(enabled=True, max_attempts=2))
        policy.start()
        policy._attempt = 2
        assert not policy.should_retry()

    def test_should_not_retry_when_cancelled(self):
        policy = ReconnectPolicy()
        policy.start()
        policy.cancel()
        assert not policy.should_retry()

    def test_delay_increases_exponentially(self):
        policy = ReconnectPolicy(ReconnectPolicyConfig(base_delay_ms=1000, jitter_ms=0))
        policy.start()
        delay1 = policy.next_delay_ms()
        delay2 = policy.next_delay_ms()
        delay3 = policy.next_delay_ms()
        assert delay1 == 0
        assert delay2 >= 1000
        assert delay3 >= 2000

    def test_delay_capped_at_max(self):
        policy = ReconnectPolicy(
            ReconnectPolicyConfig(base_delay_ms=10000, max_delay_ms=15000, jitter_ms=0),
        )
        policy.start()
        for _ in range(5):
            policy._attempt = 5
        delay = policy.next_delay_ms()
        assert delay <= 15000

    def test_recoverable_errors(self):
        policy = ReconnectPolicy()
        assert policy.is_error_recoverable(RadioError.CONNECTION_FAILED)
        assert policy.is_error_recoverable(RadioError.CONNECTION_TIMEOUT)

    def test_unrecoverable_errors(self):
        policy = ReconnectPolicy()
        assert not policy.is_error_recoverable(RadioError.URL_INVALID)
        assert not policy.is_error_recoverable(RadioError.CANCELLED)
        assert not policy.is_error_recoverable(RadioError.UNSUPPORTED_CONTENT_TYPE)

    def test_reset(self):
        policy = ReconnectPolicy()
        policy.start()
        policy.next_delay_ms()
        policy.reset()
        assert policy.attempt == 0

    def test_should_not_retry_after_max_time(self):
        policy = ReconnectPolicy(
            ReconnectPolicyConfig(enabled=True, max_total_seconds=0, max_attempts=100),
        )
        policy.start()
        assert not policy.should_retry()

    def test_jitter_adds_variation(self):
        policy = ReconnectPolicy(ReconnectPolicyConfig(base_delay_ms=1000, jitter_ms=500))
        policy.start()
        delays = [policy.next_delay_ms() for _ in range(5)]
        assert any(d > 1000 for d in delays) or any(d < 1000 for d in delays)


class TestRadioScheduler:
    def test_schedule_and_cancel(self):
        scheduler = RadioScheduler()
        called = []
        token = scheduler.schedule(50, lambda: called.append(1))
        assert token is not None
        scheduler.cancel(token)
        scheduler.close()
        assert called == []

    def test_close_cancels_all(self):
        scheduler = RadioScheduler()
        called = []
        scheduler.schedule(50, lambda: called.append(1))
        scheduler.schedule(50, lambda: called.append(2))
        scheduler.close()
        assert called == []
