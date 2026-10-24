"""AP2-F09 — process-supervised ALSA DoP probe deadline."""

from __future__ import annotations

import time

from michi.domain.dop import DopCarrierLayout, DopCarrierSupport, memory_contract_for
from michi.infrastructure.audio_devices.alsa_dop_probe import (
    DopCarrierProbeEvidence,
    DopCarrierProbeRequest,
)
from michi.infrastructure.audio_devices.dop_probe_supervisor import (
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
