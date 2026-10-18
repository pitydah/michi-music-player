"""AP2-F06 WU1 — Direct/Managed staging mutual exclusion (P0).

A single load may consume AT MOST one family's staged recipe. Conflicts are
rejected BEFORE any state mutation, and unit-family supersession is one-shot.
"""

from __future__ import annotations

import pytest

from michi.infrastructure.audio_engines.gstreamer import (
    DirectSinkBuildError,
    GStreamerAudioPort,
)
from michi.infrastructure.audio_output.direct_output_executor import (
    DirectExecutionHandle,
    DirectLoadPreparation,
)
from michi.infrastructure.audio_output.strict_sink import StrictSinkRecipe


class _FakeDirectExecutor:
    def __init__(self) -> None:
        self.recipes: dict[object, object] = {}

    def recipe_for_load(self, handle):
        return self.recipes[handle]


def _recipe(plan_id: str = "direct:1") -> StrictSinkRecipe:
    return StrictSinkRecipe(
        plan_id=plan_id,
        sink_factory="alsasink",
        device="hw:2,0",
        media_type="audio/x-raw",
        gst_format="S16LE",
        rate_hz=44100,
        channels=2,
        layout="interleaved",
    )


def _preparation(recipe: StrictSinkRecipe):
    return DirectLoadPreparation(
        handle=DirectExecutionHandle(generation=1, plan_id=recipe.plan_id),
        recipe=recipe,
        candidate_volume=1.0,
    )


def _port(executor: object | None = None) -> GStreamerAudioPort:
    return GStreamerAudioPort(bindings=None, direct_executor=executor)


def test_managed_then_direct_staging_is_rejected_before_mutation() -> None:
    executor = _FakeDirectExecutor()
    port = _port(executor)
    recipe = _recipe()
    port.stage_managed_load(_recipe("managed:1"))
    with pytest.raises(Exception) as info:
        port.stage_direct_load(_preparation(recipe), executor=executor)
    assert getattr(info.value, "code", "") == "DIRECT_STAGE_CONFLICT"
    # Neither staged payload was mutated by the rejected attempt.
    assert port._pending_direct_load is None
    assert port._pending_managed_recipe is not None
    assert port._pending_managed_recipe.plan_id == "managed:1"


def test_direct_then_managed_staging_is_rejected_before_mutation() -> None:
    executor = _FakeDirectExecutor()
    port = _port(executor)
    recipe = _recipe()
    executor.recipes[DirectExecutionHandle(generation=1, plan_id=recipe.plan_id)] = (
        recipe
    )
    port.stage_direct_load(_preparation(recipe), executor=executor)
    with pytest.raises(Exception) as info:
        port.stage_managed_load(_recipe("managed:1"))
    assert getattr(info.value, "code", "") == "MANAGED_STAGE_CONFLICT"
    assert port._pending_managed_recipe is None
    assert port._pending_direct_load is not None
    assert port._pending_direct_load.recipe.plan_id == recipe.plan_id


def test_same_family_staging_is_one_shot_supersession() -> None:
    port = _port()
    port.stage_managed_load(_recipe("managed:1"))
    port.stage_managed_load(_recipe("managed:2"))
    assert port._pending_managed_recipe.plan_id == "managed:2"
    # A rejected managed stage never clears the previous staged payload.
    with pytest.raises(DirectSinkBuildError):
        port.stage_managed_load(None)
    assert port._pending_managed_recipe.plan_id == "managed:2"


def test_managed_stage_requires_an_explicit_selected_alsa_device() -> None:
    port = _port()
    with pytest.raises(Exception) as info:
        port.stage_managed_load(
            StrictSinkRecipe(
                plan_id="managed:bad",
                sink_factory="autoaudiosink",
                device="hw:2,0",
                media_type="audio/x-raw",
                gst_format="S16LE",
                rate_hz=44100,
                channels=2,
                layout="interleaved",
            )
        )
    assert getattr(info.value, "code", "") == "MANAGED_STAGE_INVALID"
    with pytest.raises(Exception) as info:
        port.stage_managed_load(
            StrictSinkRecipe(
                plan_id="managed:bad2",
                sink_factory="alsasink",
                device="",
                media_type="audio/x-raw",
                gst_format="S16LE",
                rate_hz=44100,
                channels=2,
                layout="interleaved",
            )
        )
    assert getattr(info.value, "code", "") == "MANAGED_STAGE_INVALID"


def test_managed_identity_starts_unmanaged() -> None:
    port = _port()
    assert port.managed_identity() == {"managed": False}
