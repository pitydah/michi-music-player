"""Productive-native firewall tests for the hosted architecture.

Invariants:
- the PRODUCTIVE parent composition never calls GStreamer state transitions;
- production bootstrap selects the hosted provider, not the in-process one;
- the in-process provider/port remain available ONLY for injected
  test/diagnostic compositions and for the child implementation.
"""

from __future__ import annotations

import sys
from pathlib import Path

from michi.infrastructure.audio_engines.gstreamer_host_client import (
    GStreamerHostSupervisor,
)
from michi.infrastructure.audio_engines.gstreamer_host_port import (
    GStreamerHostedAudioPort,
)
from michi.infrastructure.audio_engines.providers import (
    GStreamerEngineProvider,
    GStreamerHostedEngineProvider,
)

REPO = Path(__file__).resolve().parents[2]
FAKE_HOST = Path(__file__).parent / "gst_host_engine_fake.py"

#: Parent-productive modules: these must never contain native lifecycle calls.
PRODUCTIVE_PARENT_MODULES = (
    REPO / "src/michi/bootstrap/__init__.py",
    REPO / "src/michi/infrastructure/audio_engines/providers.py",
    REPO / "src/michi/infrastructure/audio_engines/gstreamer_host_port.py",
    REPO / "src/michi/infrastructure/audio_engines/gstreamer_host_client.py",
)

FORBIDDEN_SNIPPETS = (
    ".set_state(",
    ".get_state(",
    "ElementFactory.make(",
    "import gi",
    "from gi",
)


def test_productive_parent_modules_never_touch_native_lifecycle() -> None:
    for module in PRODUCTIVE_PARENT_MODULES:
        source = module.read_text(encoding="utf-8")
        for snippet in FORBIDDEN_SNIPPETS:
            assert snippet not in source, f"{module.name} contains {snippet!r}"


def test_in_process_port_construction_is_confined_to_the_test_provider() -> None:
    """``providers.py`` may construct the in-process port ONLY inside the
    explicitly-injected (test/diagnostic) provider class; bootstrap and the
    hosted modules must never construct it."""
    providers_path = REPO / "src/michi/infrastructure/audio_engines/providers.py"
    providers = providers_path.read_text(encoding="utf-8")
    occurrences = providers.count("GStreamerAudioPort(")
    assert occurrences == 1
    in_process_start = providers.index("class GStreamerEngineProvider")
    hosted_start = providers.index("class GStreamerHostedEngineProvider")
    occurrence = providers.index("GStreamerAudioPort(")
    assert in_process_start < occurrence < hosted_start
    bootstrap = (REPO / "src/michi/bootstrap/__init__.py").read_text(encoding="utf-8")
    assert "GStreamerAudioPort(" not in bootstrap
    for module in (
        REPO / "src/michi/infrastructure/audio_engines/gstreamer_host_port.py",
        REPO / "src/michi/infrastructure/audio_engines/gstreamer_host_client.py",
    ):
        assert "GStreamerAudioPort(" not in module.read_text(encoding="utf-8")


def test_bootstrap_defaults_to_the_hosted_provider() -> None:
    source = (REPO / "src/michi/bootstrap/__init__.py").read_text(encoding="utf-8")
    assert "GStreamerHostedEngineProvider(" in source
    assert "runtime_gstreamer_bindings is not None" in source
    # The in-process provider survives only behind the explicit-bindings branch.
    hosted_marker = "GStreamerHostedEngineProvider(\n            direct_executor"
    injected_marker = "GStreamerEngineProvider(\n            direct_executor"
    hosted_index = source.index(hosted_marker)
    injected_index = source.index(injected_marker)
    assert injected_index < hosted_index


def _supervisor_factory():
    def command(fd: int) -> list[str]:
        return [
            sys.executable,
            str(FAKE_HOST),
            "--fd",
            str(fd),
            "--engine-behavior",
            "normal",
        ]

    return GStreamerHostSupervisor(
        command_factory=command,
        start_timeout_s=1.5,
        command_timeout_s=1.0,
        terminate_grace_s=0.3,
        term_grace_s=0.3,
        kill_grace_s=0.5,
    )


def test_hosted_provider_open_close_owns_a_hosted_port() -> None:
    provider = GStreamerHostedEngineProvider(supervisor_factory=_supervisor_factory)
    assert provider.probe().available is True
    port = provider.open()
    try:
        assert isinstance(port, GStreamerHostedAudioPort)
        assert provider.current_port is port
        assert provider.direct_executor is None
        supervisor = provider.current_supervisor
        assert supervisor is not None and supervisor.pid_alive()
    finally:
        provider.close()
    assert provider.current_port is None
    assert provider.current_supervisor is None


def test_hosted_provider_close_keeps_ownership_when_reap_fails(monkeypatch) -> None:
    from michi.infrastructure.audio_engines import gstreamer_host_client

    provider = GStreamerHostedEngineProvider(supervisor_factory=_supervisor_factory)
    port = provider.open()
    try:
        monkeypatch.setattr(
            gstreamer_host_client.GStreamerHostSupervisor,
            "shutdown",
            lambda self, graceful=True: gstreamer_host_client.REAP_PENDING,
        )
        from michi.infrastructure.audio_engines.gstreamer_host_client import (
            OutputHostShutdownError,
        )

        try:
            provider.close()
        except OutputHostShutdownError:
            pass
        else:  # pragma: no cover - the refusal must be explicit
            raise AssertionError("close must refuse a non-reaped host")
        # Ownership retained for retry/diagnosis; the live incarnation is real.
        assert provider.current_port is port
    finally:
        monkeypatch.undo()
        provider.close()


def test_in_process_provider_is_still_available_for_injected_compositions() -> None:
    # Structural evidence that the in-process adapter was not removed: only
    # its productive default wiring changed.
    assert GStreamerEngineProvider is not None
    assert GStreamerHostedEngineProvider is not GStreamerEngineProvider
