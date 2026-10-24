"""AP2-F09 — process-supervised ALSA DoP probe deadline."""

from __future__ import annotations

import time

import pytest

from michi.domain.dop import DopCarrierLayout, DopCarrierSupport, memory_contract_for
from michi.infrastructure.audio_devices.alsa_dop_probe import (
    DopCarrierProbeEvidence,
    DopCarrierProbeRequest,
)
from michi.infrastructure.audio_devices.dop_probe_supervisor import (
    AsyncDopProbeService,
    DopProbeQueueFullError,
    probe_dop_carrier_supervised,
)


def _request() -> DopCarrierProbeRequest:
    contract = memory_contract_for(DopCarrierLayout.S32_LE_LSB24)
    return DopCarrierProbeRequest(
        DopCarrierLayout.S32_LE_LSB24, contract.alsa_format, 176_400, 2
    )


def _fake_probe(*args, **kwargs):
    return DopCarrierProbeEvidence(
        stable_device_id="usb:test",
        binding_locator="hw:3,0",
        binding_generation=1,
        request=_request(),
        negotiated_rate_hz=176_400,
        negotiated_format="S32_LE",
        negotiated_channels=2,
        support=DopCarrierSupport.QUALIFIED,
        disposition="test",
        errno_code=None,
        environment_fingerprint="env:1",
        evidence_ref="ref",
    )


def _slow_probe(*args, **kwargs):
    time.sleep(1.0)
    return _fake_probe()


def _failing_probe(*args, **kwargs):
    raise RuntimeError("alsa failed")


def _run(probe, timeout=1.0):
    return probe_dop_carrier_supervised(
        "usb:test",
        "hw:3,0",
        1,
        _request(),
        environment="env:1",
        timeout_s=timeout,
        probe_callable=probe,
        process_context="fork",
    )


def test_supervised_probe_success() -> None:
    outcome = _run(_fake_probe)
    assert outcome.status == "OK"
    assert outcome.evidence is not None
    assert outcome.evidence.support is DopCarrierSupport.QUALIFIED


def test_supervised_probe_timeout_terminates_worker() -> None:
    started = time.monotonic()
    outcome = _run(_slow_probe, timeout=0.05)
    assert outcome.status == "TIMEOUT"
    assert time.monotonic() - started < 0.5


def test_supervised_probe_error_is_typed() -> None:
    outcome = _run(_failing_probe)
    assert outcome.status == "ERROR"
    assert "RuntimeError" in outcome.detail


def test_supervisor_marks_evidence_as_supervised() -> None:
    outcome = _run(_fake_probe)
    assert outcome.evidence is not None
    assert outcome.evidence.provenance == "ALSA_SUPERVISED"


def test_async_service_is_non_blocking_and_bounded() -> None:
    service = AsyncDopProbeService(
        max_concurrent=1, queue_limit=1, process_context="fork"
    )
    try:
        started = time.monotonic()
        first = service.submit(
            "usb:test",
            "hw:3,0",
            1,
            _request(),
            environment="env:1",
            timeout_s=3.0,
            probe_callable=_slow_probe,
        )
        assert time.monotonic() - started < 0.2
        second = service.submit(
            "usb:test",
            "hw:3,0",
            1,
            _request(),
            environment="env:1",
            timeout_s=3.0,
            probe_callable=_slow_probe,
        )
        with pytest.raises(DopProbeQueueFullError):
            service.submit(
                "usb:test",
                "hw:3,0",
                1,
                _request(),
                environment="env:1",
                timeout_s=1.0,
                probe_callable=_fake_probe,
            )
        assert first.result(2.0).status == "OK"
        assert second.result(2.0).status == "OK"
    finally:
        service.shutdown()


def test_async_service_cancels_child_and_returns_cancelled() -> None:
    service = AsyncDopProbeService(
        max_concurrent=1, queue_limit=0, process_context="fork"
    )
    try:
        future = service.submit(
            "usb:test",
            "hw:3,0",
            1,
            _request(),
            environment="env:1",
            timeout_s=1.0,
            probe_callable=_slow_probe,
        )
        assert future.cancel() is True
        outcome = future.result(2.0)
        assert outcome.status == "CANCELLED"
        assert future.done() is True
    finally:
        service.shutdown()


def test_async_service_timeout_is_typed() -> None:
    service = AsyncDopProbeService(
        max_concurrent=1, queue_limit=0, process_context="fork"
    )
    try:
        future = service.submit(
            "usb:test",
            "hw:3,0",
            1,
            _request(),
            environment="env:1",
            timeout_s=0.05,
            probe_callable=_slow_probe,
        )
        assert future.result(2.0).status == "TIMEOUT"
    finally:
        service.shutdown()


def test_async_service_stale_binding_is_not_delivered() -> None:
    service = AsyncDopProbeService(
        max_concurrent=1, queue_limit=0, process_context="fork"
    )
    try:
        future = service.submit(
            "usb:test",
            "hw:3,0",
            1,
            _request(),
            environment="env:1",
            timeout_s=1.0,
            probe_callable=_fake_probe,
            binding_check=lambda *_args: False,
        )
        outcome = future.result(2.0)
        assert outcome.status == "STALE_BINDING"
        assert outcome.evidence is None
    finally:
        service.shutdown()


def test_supervised_probe_success_with_spawn() -> None:
    outcome = probe_dop_carrier_supervised(
        "usb:test",
        "hw:3,0",
        1,
        _request(),
        environment="env:1",
        timeout_s=2.0,
        probe_callable=_fake_probe,
        process_context="spawn",
    )
    assert outcome.status == "OK"
    assert outcome.evidence is not None
    assert outcome.evidence.provenance == "ALSA_SUPERVISED"
