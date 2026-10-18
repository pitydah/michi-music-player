"""Regression: host-lost listener attachment is keyed by WEAK IDENTITY.

A closed/reopened hosted port must never inherit another object's listener
registration through a recycled ``id(port)``.
"""

from __future__ import annotations

import gc

from michi.infrastructure.audio_processing.hosted_transport import (
    HostedProcessingTransport,
)


class _Port:
    def __init__(self) -> None:
        self.listeners: list = []

    def add_host_lost_listener(self, callback) -> None:
        self.listeners.append(callback)

    def query_processing_capabilities(self) -> dict:
        return {"gstreamer_version": "fake", "factories": {}}


def test_same_port_is_attached_once_and_fanout_reaches_listeners() -> None:
    port = _Port()
    transport = HostedProcessingTransport(lambda: port)
    reasons: list[str] = []
    transport.add_host_lost_listener(reasons.append)
    transport.query_capabilities()
    transport.query_capabilities()
    assert len(port.listeners) == 1
    port.listeners[0]("SIGKILL")
    assert reasons == ["SIGKILL"]


def test_replacement_port_attaches_after_the_old_one_dies() -> None:
    ports = [_Port()]
    transport = HostedProcessingTransport(lambda: ports[0])
    transport.query_capabilities()
    assert len(transport._attached_ports) == 1
    del ports[0]
    gc.collect()
    # Weak identity: no stale registry entry survives the port.
    assert len(transport._attached_ports) == 0

    replacement = _Port()
    ports.append(replacement)
    transport.query_capabilities()
    assert len(replacement.listeners) == 1
