"""AP2-F09 — productive DoP executor over the supervised GStreamer host.

The executor turns an already-authorized DopExecutionPlanV2 into one host
execution. It never selects a DAC, a policy, a rate or a layout.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from michi.application.dop_planner import DopExecutionPlanV2


class DopExecutionError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class DopPrepared:
    plan: DopExecutionPlanV2
    execution_id: str
    identity: dict[str, Any]
    observations: tuple[dict[str, Any], ...]


def _host_carrier_format(alsa_format: str) -> str:
    return "S32LE" if alsa_format in ("S32_LE", "S32LE") else alsa_format


def _source_family(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".dsf":
        return "dsf"
    if suffix in (".dff", ".dsdiff"):
        return "dff"
    raise DopExecutionError("DOP_SOURCE_FAMILY_UNKNOWN", str(path.suffix))


def _str(item: dict[str, Any], name: str) -> str:
    value = item.get(name)
    if not isinstance(value, str) or not value:
        raise DopExecutionError("DOP_HOST_EVIDENCE_INVALID", f"{name} required")
    return value


def _int(item: dict[str, Any], name: str) -> int:
    value = item.get(name)
    if not isinstance(value, int) or isinstance(value, bool):
        raise DopExecutionError("DOP_HOST_EVIDENCE_INVALID", f"{name} must be int")
    return value


def _bool(item: dict[str, Any], name: str) -> bool:
    value = item.get(name)
    if not isinstance(value, bool):
        raise DopExecutionError("DOP_HOST_EVIDENCE_INVALID", f"{name} must be bool")
    return value


class DopOutputExecutor:
    def __init__(self, port: object, *, sink_factory: str = "alsasink") -> None:
        self._port = port
        self._sink_factory = sink_factory

    @staticmethod
    def _expected(plan: DopExecutionPlanV2) -> dict[str, Any]:
        return {
            "plan_id": plan.plan_id,
            "execution_id": plan.execution_id,
            "stable_device_id": plan.stable_device_id,
            "device": plan.binding_locator,
            "binding_generation": plan.binding_generation,
            "host_generation": plan.host_generation,
        }

    def prepare(self, plan: DopExecutionPlanV2, path: Path) -> DopPrepared:
        if not isinstance(plan, DopExecutionPlanV2):
            raise DopExecutionError("DOP_PLAN_INVALID", "DopExecutionPlanV2 required")
        path = Path(path)
        if not path.is_file():
            raise DopExecutionError("DOP_SOURCE_UNAVAILABLE", str(path))
        if plan.processing_policy != "DOP_ONLY":
            raise DopExecutionError(
                "DOP_PROCESSING_POLICY_INVALID", plan.processing_policy
            )
        payload = {
            "path": str(path),
            "plan_id": plan.plan_id,
            "execution_id": plan.execution_id,
            "host_generation": plan.host_generation,
            "binding_generation": plan.binding_generation,
            "stable_device_id": plan.stable_device_id,
            "locator": plan.binding_locator,
            "source_family": _source_family(path),
            "source_rate_hz": plan.source.bit_rate_hz // 8,
            "carrier_rate_hz": plan.carrier_rate.frames_per_second,
            "carrier_format": _host_carrier_format(plan.memory_contract.alsa_format),
            "channels": plan.source.channels,
            "reverse_payload_bits": plan.reverse_payload_bits,
            "sink_factory": self._sink_factory,
        }
        try:
            identity = self._port.prepare_dop(payload)
            self._validate(plan, path, identity)
        except DopExecutionError:
            self._abort_quietly(plan)
            raise
        except Exception as exc:  # noqa: BLE001 - typed host boundary
            self._abort_quietly(plan)
            code = getattr(exc, "code", "DOP_PREPARE_FAILED")
            raise DopExecutionError(str(code), str(exc)) from exc
        observations = identity.get("observations") or []
        return DopPrepared(
            plan=plan,
            execution_id=plan.execution_id,
            identity=dict(identity),
            observations=tuple(observations),
        )

    def _validate(self, plan: DopExecutionPlanV2, path: Path, identity: Any) -> None:
        if not isinstance(identity, dict):
            raise DopExecutionError("DOP_HOST_EVIDENCE_INVALID", "identity not object")
        for name in ("plan_id", "execution_id", "stable_device_id", "device", "path"):
            _str(identity, name)
        if Path(identity["path"]).resolve() != path.resolve():
            raise DopExecutionError("DOP_HOST_IDENTITY_MISMATCH", "source path")
        if Path(identity["device"]).as_posix() != Path(plan.binding_locator).as_posix():
            raise DopExecutionError("DOP_HOST_IDENTITY_MISMATCH", "device")
        checks = {
            "plan_id": plan.plan_id,
            "execution_id": plan.execution_id,
            "stable_device_id": plan.stable_device_id,
            "binding_generation": plan.binding_generation,
            "host_generation": plan.host_generation,
            "carrier_rate_hz": plan.carrier_rate.frames_per_second,
            "carrier_format": _host_carrier_format(plan.memory_contract.alsa_format),
            "channels": plan.source.channels,
            "dop": True,
            "prerolled": True,
            "plugin_revision": "michidop-rust-0.1.0",
        }
        for name, expected in checks.items():
            if name in ("dop", "prerolled"):
                if _bool(identity, name) is not expected:
                    raise DopExecutionError(
                        "DOP_HOST_IDENTITY_MISMATCH", f"{name} != {expected}"
                    )
            elif identity.get(name) != expected:
                raise DopExecutionError(
                    "DOP_HOST_IDENTITY_MISMATCH",
                    f"{name}={identity.get(name)!r} != {expected!r}",
                )
        observations = identity.get("observations")
        if not isinstance(observations, list) or not observations:
            raise DopExecutionError("DOP_HOST_EVIDENCE_MISSING", "observations")
        carrier = [
            item
            for item in observations
            if isinstance(item, dict)
            and item.get("factory") == "michidop"
            and item.get("media_type") == "audio/x-raw"
            and item.get("caps_state") == "NEGOTIATED_CURRENT"
        ]
        if not carrier:
            raise DopExecutionError(
                "DOP_CARRIER_MISMATCH", "no negotiated michidop audio/x-raw pad"
            )
        fields = dict(carrier[0].get("fields") or [])
        if fields.get("format") != _host_carrier_format(
            plan.memory_contract.alsa_format
        ):
            raise DopExecutionError("DOP_CARRIER_MISMATCH", "format")
        if fields.get("rate") != str(plan.carrier_rate.frames_per_second):
            raise DopExecutionError("DOP_CARRIER_MISMATCH", "rate")
        if fields.get("channels") != str(plan.source.channels):
            raise DopExecutionError("DOP_CARRIER_MISMATCH", "channels")

    def commit(self, prepared: DopPrepared) -> dict[str, Any]:
        return self._port.commit_dop(self._expected(prepared.plan))

    def start(self, prepared: DopPrepared) -> dict[str, Any]:
        result = self._port.start_dop()
        if result.get("confirmed") is not True:
            raise DopExecutionError("DOP_PLAYING_NOT_CONFIRMED", "host did not confirm")
        return result

    def pause(self, prepared: DopPrepared) -> dict[str, Any]:
        result = self._port.pause_dop()
        if result.get("confirmed") is not True:
            raise DopExecutionError("DOP_PAUSE_NOT_CONFIRMED", "host did not confirm")
        return result

    def resume(self, prepared: DopPrepared) -> dict[str, Any]:
        result = self._port.resume_dop()
        if result.get("confirmed") is not True:
            raise DopExecutionError("DOP_RESUME_NOT_CONFIRMED", "host did not confirm")
        return result

    def stop(self, prepared: DopPrepared, reason: str = "stop") -> dict[str, Any]:
        return self._port.stop_dop(self._expected(prepared.plan))

    def abort(
        self, prepared: DopPrepared | None, reason: str = "abort"
    ) -> dict[str, Any]:
        if prepared is None:
            return {"aborted": True, "already": True}
        return self._port.abort_dop(self._expected(prepared.plan))

    def query_identity(self) -> dict[str, Any]:
        return self._port.query_dop_identity()

    def query_evidence(self) -> dict[str, Any]:
        return self._port.query_dop_evidence()

    def _abort_quietly(self, plan: DopExecutionPlanV2) -> None:
        try:
            self._port.abort_dop(self._expected(plan))
        except Exception:  # noqa: BLE001 - best-effort compensation
            return
