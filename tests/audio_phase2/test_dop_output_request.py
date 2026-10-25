"""AP2-F09 — exclusive DoP OutputRequest contract."""

from __future__ import annotations

import pytest

from michi.application.output_session_service import OutputRequest, OutputSessionError
from tests.dop.test_dop_planner import _plan


def test_dop_request_carries_only_the_plan() -> None:
    plan = _plan()
    request = OutputRequest.dop(plan, "profile:dop")
    assert request.dop_plan is plan
    assert request.native_dsd_plan is None
    assert request.facts is None
    assert request.selected_device_id == plan.stable_device_id
    assert request.selected_profile_id == "profile:dop"


def test_dop_request_rejects_native_combination() -> None:
    plan = _plan()
    with pytest.raises(OutputSessionError) as info:
        OutputRequest(
            None,
            plan.stable_device_id,
            "profile:dop",
            object(),  # type: ignore[arg-type]
            plan,
        )
    assert info.value.code == "OUTPUT_REQUEST_EXCLUSIVE"


def test_dop_request_rejects_device_mismatch() -> None:
    with pytest.raises(OutputSessionError) as info:
        OutputRequest(None, "dev:other", "profile", None, _plan())
    assert info.value.code == "OUTPUT_REQUEST_DOP_DEVICE_MISMATCH"
