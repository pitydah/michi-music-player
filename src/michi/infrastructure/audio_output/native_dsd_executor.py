"""AP2-F08 — parent-side Native DSD executor over the supervised host.

The executor owns no native objects. It stages one immutable plan, asks the
child for a dedicated DSD pipeline, proves the returned pad evidence with the
pure inspector, and only then commits/starts. A failed preparation aborts the
child pipeline and never publishes an execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from michi.application.dsd_output_planner import NativeDsdOutputPlan
from michi.infrastructure.audio_output.dsd_runtime_inspector import (
    ObservedPad,
    inspect_native_dsd_branch,
)
from michi.infrastructure.audio_output.strict_dsd_sink import (
    StrictDsdSinkRecipe,
    recipe_from_native_plan,
)


class NativeDsdExecutionError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class NativeDsdPrepared:
    plan: NativeDsdOutputPlan
    recipe: StrictDsdSinkRecipe
    execution_id: str
    identity: dict[str, Any]
    observations: tuple[ObservedPad, ...]


def _source_family(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".dsf":
        return "dsf"
    if suffix in (".dff", ".dsdiff"):
        return "dff"
    raise NativeDsdExecutionError(
        "NATIVE_DSD_SOURCE_FAMILY_UNKNOWN",
        f"{path.suffix!r} is not a demonstrated DSD container",
    )


def _observations_from_identity(identity: dict[str, Any]) -> tuple[ObservedPad, ...]:
    raw = identity.get("observations")
    if not isinstance(raw, list) or not raw:
        raise NativeDsdExecutionError(
            "NATIVE_DSD_HOST_EVIDENCE_MISSING", "host returned no pad observations"
        )
    observations: list[ObservedPad] = []
    for item in raw:
        if not isinstance(item, dict):
            raise NativeDsdExecutionError(
                "NATIVE_DSD_HOST_EVIDENCE_INVALID", "observation is not an object"
            )
        fields = item.get("fields")
        if not isinstance(fields, list) or not all(
            isinstance(pair, list) and len(pair) == 2 for pair in fields
        ):
            raise NativeDsdExecutionError(
                "NATIVE_DSD_HOST_EVIDENCE_INVALID", "observation fields are invalid"
            )
        try:
            observations.append(
                ObservedPad(
                    element_name=str(item["element_name"]),
                    factory=str(item["factory"]),
                    pad_name=str(item["pad_name"]),
                    direction=str(item["direction"]),
                    role=str(item["role"]),
                    media_type=str(item["media_type"]),
                    fields=tuple((str(k), str(v)) for k, v in fields),
                    caps_state=str(item["caps_state"]),
                    linked=bool(item["linked"]),
                    selected_device=str(item.get("selected_device") or ""),
                    execution_id=str(item.get("execution_id") or ""),
                    binding_generation=int(item.get("binding_generation") or 0),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise NativeDsdExecutionError(
                "NATIVE_DSD_HOST_EVIDENCE_INVALID", str(exc)
            ) from exc
    return tuple(observations)


class NativeDsdOutputExecutor:
    def __init__(self, port: object) -> None:
        self._port = port

    @staticmethod
    def _expected(plan: NativeDsdOutputPlan) -> dict[str, Any]:
        return {
            "plan_id": plan.plan_id,
            "execution_id": plan.execution_id,
            "device": plan.binding_locator,
            "binding_generation": plan.binding_generation,
        }

    def prepare(self, plan: NativeDsdOutputPlan, path: Path) -> NativeDsdPrepared:
        if not isinstance(plan, NativeDsdOutputPlan):
            raise NativeDsdExecutionError(
                "NATIVE_DSD_PLAN_INVALID", "expected a NativeDsdOutputPlan"
            )
        path = Path(path)
        if not path.is_file():
            raise NativeDsdExecutionError("NATIVE_DSD_SOURCE_UNAVAILABLE", str(path))
        recipe = recipe_from_native_plan(plan)
        payload = {
            "path": str(path),
            "plan_id": plan.plan_id,
            "execution_id": plan.execution_id,
            "binding_generation": plan.binding_generation,
            "stable_device_id": plan.stable_device_id,
            "locator": plan.binding_locator,
            "gst_format": plan.gst_format,
            "gst_rate_bytes_per_second_per_channel": (
                plan.gst_rate_bytes_per_second_per_channel
            ),
            "channels": plan.alsa_tuple.channels,
            "source_bits_per_second_per_channel": plan.source.bit_rate_hz,
            "normalize_reversed_bytes": plan.normalize_reversed_bytes,
            "requires_dsdconvert": recipe.requires_dsdconvert,
            "source_family": _source_family(path),
            "sink_factory": recipe.sink_factory,
        }
        try:
            identity = self._port.prepare_native_dsd(payload)
        except Exception as exc:  # noqa: BLE001 - typed infrastructure boundary
            code = getattr(exc, "code", "NATIVE_DSD_HOST_PREPARE_FAILED")
            raise NativeDsdExecutionError(str(code), str(exc)) from exc
        try:
            self._validate_identity(plan, identity)
            observations = _observations_from_identity(identity)
            inspect_native_dsd_branch(
                observations,
                recipe,
                expected_execution_id=plan.execution_id,
                expected_binding_generation=plan.binding_generation,
                expected_device=plan.binding_locator,
                graph_inspection_complete=bool(identity.get("prerolled", False)),
            )
        except Exception as exc:
            self.abort(plan)
            code = getattr(exc, "code", "NATIVE_DSD_HOST_EVIDENCE_INVALID")
            raise NativeDsdExecutionError(str(code), str(exc)) from exc
        return NativeDsdPrepared(
            plan=plan,
            recipe=recipe,
            execution_id=plan.execution_id,
            identity=identity,
            observations=observations,
        )

    def _validate_identity(self, plan: NativeDsdOutputPlan, identity: Any) -> None:
        if not isinstance(identity, dict):
            raise NativeDsdExecutionError(
                "NATIVE_DSD_HOST_EVIDENCE_INVALID", "identity is not an object"
            )
        for field, expected in (
            ("plan_id", plan.plan_id),
            ("execution_id", plan.execution_id),
            ("device", plan.binding_locator),
            ("binding_generation", plan.binding_generation),
            ("format", plan.gst_format),
            ("rate", plan.gst_rate_bytes_per_second_per_channel),
            ("channels", plan.alsa_tuple.channels),
            ("sink_factory", "alsasink"),
            ("prerolled", True),
            ("lab_sink", False),
        ):
            if identity.get(field) != expected:
                raise NativeDsdExecutionError(
                    "NATIVE_DSD_HOST_IDENTITY_MISMATCH",
                    f"{field}={identity.get(field)!r} != {expected!r}",
                )

    def commit(self, prepared: NativeDsdPrepared) -> dict[str, Any]:
        return self._port.commit_native_dsd(self._expected(prepared.plan))

    def start(self, prepared: NativeDsdPrepared) -> dict[str, Any]:
        return self._port.start_native_dsd()

    def pause(self) -> dict[str, Any]:
        return self._port.pause_native_dsd()

    def resume(self) -> dict[str, Any]:
        return self._port.resume_native_dsd()

    def stop(self, prepared: NativeDsdPrepared) -> dict[str, Any]:
        return self._port.stop_native_dsd(self._expected(prepared.plan))

    def abort(self, plan: NativeDsdOutputPlan) -> dict[str, Any]:
        try:
            return self._port.abort_native_dsd(self._expected(plan))
        except Exception:  # noqa: BLE001 - abort is cleanup, never the error
            return {"aborted": False, "stale": True}
