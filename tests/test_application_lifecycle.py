"""M11.3 Reliability Seal — guaranteed application lifecycle (AR-04).

The entry point must call shutdown() on EVERY exit path (normal exit, run()
exception, initialize() failure). shutdown() must be safe for partial
initialization and never run twice. First-error-wins: a shutdown failure
during an error exit is a logged secondary diagnostic, never a mask.
"""

import pytest


class _FakeContainer:
    def __init__(self):
        self.initialize_calls = 0
        self.run_calls = 0
        self.shutdown_calls = 0
        self.fail_initialize = False
        self.fail_run = False
        self.shutdown_raises = False

    def initialize(self):
        self.initialize_calls += 1
        if self.fail_initialize:
            raise RuntimeError("initialize boom")

    def run(self):
        self.run_calls += 1
        if self.fail_run:
            raise RuntimeError("run boom")
        return 42

    def shutdown(self):
        self.shutdown_calls += 1
        if self.shutdown_raises:
            raise RuntimeError("shutdown boom")


@pytest.fixture
def entry(monkeypatch):
    import michi.__main__ as entry_mod

    captured: list = []
    monkeypatch.setattr(entry_mod, "ApplicationContainer", lambda: captured[0])
    return entry_mod, captured


class TestGuaranteedShutdown:
    def test_normal_exit_calls_shutdown_exactly_once(self, entry):
        entry_mod, captured = entry
        fake = _FakeContainer()
        captured.append(fake)
        result = entry_mod.main()
        assert result == 42
        assert fake.initialize_calls == 1
        assert fake.run_calls == 1
        assert fake.shutdown_calls == 1

    def test_run_exception_still_calls_shutdown(self, entry):
        entry_mod, captured = entry
        fake = _FakeContainer()
        fake.fail_run = True
        captured.append(fake)
        with pytest.raises(RuntimeError, match="run boom"):
            entry_mod.main()
        assert fake.shutdown_calls == 1
        assert fake.run_calls == 1

    def test_initialize_failure_calls_shutdown(self, entry):
        entry_mod, captured = entry
        fake = _FakeContainer()
        fake.fail_initialize = True
        captured.append(fake)
        with pytest.raises(RuntimeError, match="initialize boom"):
            entry_mod.main()
        # shutdown is verified safe for partial initialization
        assert fake.shutdown_calls == 1
        assert fake.initialize_calls == 1

    def test_shutdown_exception_fatal_on_normal_exit(self, entry):
        """On the NORMAL exit path a shutdown failure is fatal (never
        swallowed); no second shutdown attempt occurs."""
        entry_mod, captured = entry
        fake = _FakeContainer()
        fake.shutdown_raises = True
        captured.append(fake)
        with pytest.raises(RuntimeError, match="shutdown boom"):
            entry_mod.main()
        assert fake.shutdown_calls == 1

    def test_original_exception_semantics_preserved(self, entry, capsys):
        """First-error-wins: when run() AND shutdown() both fail during an
        error exit, the ORIGINAL run exception propagates; the shutdown
        failure is a logged secondary diagnostic."""
        entry_mod, captured = entry
        fake = _FakeContainer()
        fake.fail_run = True
        fake.shutdown_raises = True
        captured.append(fake)
        with pytest.raises(RuntimeError, match="run boom"):
            entry_mod.main()
        assert fake.shutdown_calls == 1
        assert "shutdown failed while handling an error" in capsys.readouterr().err

    def test_partial_container_shutdown_safe(self):
        """shutdown() on a NEVER-initialized container must be safe (every
        step guards on container state) — this is what makes the pattern
        valid after an initialize() failure."""
        from michi.bootstrap import ApplicationContainer

        container = ApplicationContainer()
        container.shutdown()  # must not raise on a fresh container
