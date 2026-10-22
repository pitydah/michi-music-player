"""AP2-F08 — dedicated Native DSD pipeline inside the supervised host.

This module lives in the CHILD process and owns only native GStreamer
objects. It never uses playbin3/decodebin3: the pipeline is explicit

    filesrc -> avdemux_dsf|dff-demux -> [dsdconvert] -> capsfilter -> sink

The parent owns plan/binding/execution authority; this runtime executes one
immutable request and reports primitive pad observations. The parent must
prove those observations with the pure branch inspector before committing.
"""

from __future__ import annotations

import contextlib
import os
from dataclasses import dataclass
from typing import Any


class NativeDsdHostError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class _NativeRequest:
    path: str
    plan_id: str
    execution_id: str
    binding_generation: int
    stable_device_id: str
    locator: str
    gst_format: str
    gst_rate: int
    channels: int
    source_bits: int
    normalize_reversed_bytes: bool
    requires_dsdconvert: bool
    source_family: str
    sink_factory: str


def _require_str(payload: dict[str, Any], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value.strip():
        raise NativeDsdHostError(
            "NATIVE_DSD_HOST_PAYLOAD_INVALID", f"{name} must be a non-empty string"
        )
    return value


def _require_int(
    payload: dict[str, Any], name: str, *, allow_zero: bool = False
) -> int:
    value = payload.get(name)
    minimum = 0 if allow_zero else 1
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise NativeDsdHostError(
            "NATIVE_DSD_HOST_PAYLOAD_INVALID",
            f"{name} must be an integer >= {minimum}",
        )
    return value


def _require_bool(payload: dict[str, Any], name: str) -> bool:
    value = payload.get(name)
    if not isinstance(value, bool):
        raise NativeDsdHostError(
            "NATIVE_DSD_HOST_PAYLOAD_INVALID", f"{name} must be boolean"
        )
    return value


def _parse_request(payload: dict[str, Any]) -> _NativeRequest:
    if not isinstance(payload, dict):
        raise NativeDsdHostError(
            "NATIVE_DSD_HOST_PAYLOAD_INVALID", "payload must be an object"
        )
    request = _NativeRequest(
        path=_require_str(payload, "path"),
        plan_id=_require_str(payload, "plan_id"),
        execution_id=_require_str(payload, "execution_id"),
        binding_generation=_require_int(payload, "binding_generation", allow_zero=True),
        stable_device_id=_require_str(payload, "stable_device_id"),
        locator=_require_str(payload, "locator"),
        gst_format=_require_str(payload, "gst_format"),
        gst_rate=_require_int(payload, "gst_rate_bytes_per_second_per_channel"),
        channels=_require_int(payload, "channels"),
        source_bits=_require_int(payload, "source_bits_per_second_per_channel"),
        normalize_reversed_bytes=_require_bool(payload, "normalize_reversed_bytes"),
        requires_dsdconvert=_require_bool(payload, "requires_dsdconvert"),
        source_family=_require_str(payload, "source_family"),
        sink_factory=_require_str(payload, "sink_factory"),
    )
    if request.gst_format not in {
        "DSDU8",
        "DSDU16LE",
        "DSDU16BE",
        "DSDU32LE",
        "DSDU32BE",
    }:
        raise NativeDsdHostError("NATIVE_DSD_HOST_FORMAT_INVALID", request.gst_format)
    if request.source_family not in ("dsf", "dff"):
        raise NativeDsdHostError(
            "NATIVE_DSD_HOST_FAMILY_INVALID", request.source_family
        )
    if request.sink_factory not in ("alsasink", "fakesink"):
        raise NativeDsdHostError("NATIVE_DSD_HOST_SINK_INVALID", request.sink_factory)
    if (
        request.sink_factory == "fakesink"
        and os.environ.get("MICHI_GST_LAB_SINK") != "fakesink"
    ):
        raise NativeDsdHostError(
            "NATIVE_DSD_HOST_SINK_FORBIDDEN",
            "fakesink is only allowed under the explicit lab switch",
        )
    return request


class NativeDsdHostRuntime:
    """One native DSD pipeline owned by the child process."""

    def __init__(self) -> None:
        self._gst = None
        self._pipeline = None
        self._request: _NativeRequest | None = None
        self._identity: dict[str, Any] | None = None
        self._committed = False
        self._errors: list[dict[str, str]] = []
        self._eos = False
        self._lab_sink = False

    def _ensure_gst(self):
        if self._gst is not None:
            return self._gst
        import gi

        gi.require_version("Gst", "1.0")
        import gi.repository

        gst = gi.repository.Gst
        gst.init(None)
        self._gst = gst
        return gst

    def prepare(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = _parse_request(payload)
        self.close()
        gst = self._ensure_gst()
        self._request = request
        self._lab_sink = request.sink_factory == "fakesink"
        pipeline = gst.Pipeline.new("michi-native-dsd")
        if pipeline is None:
            raise NativeDsdHostError(
                "NATIVE_DSD_HOST_PIPELINE_FAILED", "pipeline creation failed"
            )
        filesrc = gst.ElementFactory.make("filesrc", "src")
        demux_factory = (
            "avdemux_dsf" if request.source_family == "dsf" else "avdemux_dsdiff"
        )
        demux = gst.ElementFactory.make(demux_factory, "demux")
        if filesrc is None or demux is None:
            raise NativeDsdHostError(
                "NATIVE_DSD_DEMUXER_UNAVAILABLE",
                f"filesrc/{demux_factory} unavailable in this runtime",
            )
        filesrc.set_property("location", request.path)
        elements = [filesrc, demux]
        dsdconvert = None
        if request.requires_dsdconvert:
            dsdconvert = gst.ElementFactory.make("dsdconvert", "dsdconvert")
            if dsdconvert is None:
                raise NativeDsdHostError(
                    "NATIVE_DSD_CONVERTER_UNAVAILABLE", "dsdconvert unavailable"
                )
            elements.append(dsdconvert)
        capsfilter = gst.ElementFactory.make("capsfilter", "dsd_caps")
        sink = gst.ElementFactory.make(request.sink_factory, "sink")
        if capsfilter is None or sink is None:
            raise NativeDsdHostError(
                "NATIVE_DSD_HOST_SINK_CREATE_FAILED",
                f"{request.sink_factory}/capsfilter unavailable",
            )
        caps = gst.Caps.from_string(
            "audio/x-dsd,"
            f"format={request.gst_format},"
            f"rate={request.gst_rate},"
            f"channels={request.channels},"
            "layout=interleaved,reversed-bytes=false"
        )
        if caps is None or caps.get_size() == 0:
            raise NativeDsdHostError("NATIVE_DSD_HOST_CAPS_INVALID", "invalid caps")
        capsfilter.set_property("caps", caps)
        if request.sink_factory == "alsasink":
            sink.set_property("device", request.locator)
        elements.extend([capsfilter, sink])
        for element in elements:
            if not pipeline.add(element):
                raise NativeDsdHostError(
                    "NATIVE_DSD_HOST_PIPELINE_FAILED",
                    f"cannot add {element.get_name()}",
                )
        if not filesrc.link(demux):
            raise NativeDsdHostError("NATIVE_DSD_HOST_LINK_FAILED", "filesrc -> demux")

        def _on_pad_added(_demux, pad) -> None:
            # Only the elementary audio pad belongs to this Native branch.
            if not pad.get_name().startswith("audio_"):
                return
            target = dsdconvert if dsdconvert is not None else capsfilter
            sinkpad = target.get_static_pad("sink")
            if sinkpad is None or pad.is_linked() or sinkpad.is_linked():
                return
            if pad.link(sinkpad) != gst.PadLinkReturn.OK:
                self._errors.append(
                    {
                        "code": "NATIVE_DSD_DYNAMIC_LINK_FAILED",
                        "detail": (
                            f"{pad.get_name()} -> {target.get_name()}: "
                            "Gst.Pad.link did not return OK"
                        ),
                    }
                )

        demux.connect("pad-added", _on_pad_added)
        chain_head = dsdconvert if dsdconvert is not None else capsfilter
        if dsdconvert is not None and not dsdconvert.link(capsfilter):
            raise NativeDsdHostError(
                "NATIVE_DSD_HOST_LINK_FAILED", "dsdconvert -> capsfilter"
            )
        if not capsfilter.link(sink):
            raise NativeDsdHostError(
                "NATIVE_DSD_HOST_LINK_FAILED", "capsfilter -> sink"
            )
        self._pipeline = pipeline
        pipeline.set_state(gst.State.PAUSED)
        ret, state, _pending = pipeline.get_state(10 * gst.SECOND)
        if ret == gst.StateChangeReturn.FAILURE or state != gst.State.PAUSED:
            detail = self._bus_error() or f"state={state.value_name}"
            self.close()
            raise NativeDsdHostError("NATIVE_DSD_HOST_PREROLL_FAILED", detail)
        if self._errors:
            detail = self._errors[0].get("detail", "native DSD link failure")
            self.close()
            raise NativeDsdHostError("NATIVE_DSD_HOST_LINK_FAILED", detail)
        observations = self._observe(
            filesrc, demux, dsdconvert, capsfilter, sink, chain_head
        )
        raw = [
            item
            for item in observations
            if item["media_type"] == "audio/x-raw"
            and item["caps_state"] == "NEGOTIATED_CURRENT"
        ]
        if raw:
            self.close()
            raise NativeDsdHostError(
                "NATIVE_DSD_PCM_CONVERSION_DETECTED",
                f"{len(raw)} negotiated audio/x-raw pads in the Native branch",
            )
        self._identity = {
            "plan_id": request.plan_id,
            "execution_id": request.execution_id,
            "binding_generation": request.binding_generation,
            "stable_device_id": request.stable_device_id,
            "device": request.locator,
            "format": request.gst_format,
            "rate": request.gst_rate,
            "channels": request.channels,
            "source_bits": request.source_bits,
            "sink_factory": request.sink_factory,
            "lab_sink": self._lab_sink,
            "factories": [item["factory"] for item in observations],
            "observations": observations,
            "prerolled": True,
            "path": request.path,
        }
        return dict(self._identity)

    def _bus_error(self) -> str:
        if self._pipeline is None:
            return ""
        bus = self._pipeline.get_bus()
        if bus is None:
            return ""
        message = bus.timed_pop_filtered(0, self._gst.MessageType.ERROR)
        if message is None:
            return ""
        err, debug = message.parse_error()
        return f"{err}: {debug}"

    def _observe(
        self, filesrc, demux, dsdconvert, capsfilter, sink, chain_head
    ) -> list[dict[str, Any]]:
        observations: list[dict[str, Any]] = []
        for pad in demux.srcpads:
            observations.append(self._pad_observation(pad, demux, "source", "src"))
            break
        if dsdconvert is not None:
            observations.append(
                self._pad_observation(
                    dsdconvert.get_static_pad("src"), dsdconvert, "dsdconvert", "src"
                )
            )
        observations.append(
            self._pad_observation(
                capsfilter.get_static_pad("src"), capsfilter, "capsfilter", "src"
            )
        )
        observations.append(
            self._pad_observation(sink.get_static_pad("sink"), sink, "sink", "sink")
        )
        return observations

    def _pad_observation(
        self, pad, element, role: str, direction: str
    ) -> dict[str, Any]:
        current = pad.get_current_caps() if pad is not None else None
        template = pad.get_pad_template_caps() if pad is not None else None
        if current is not None and current.get_size() > 0:
            caps = current
            caps_state = "NEGOTIATED_CURRENT"
        elif template is not None and template.get_size() > 0:
            caps = template
            caps_state = "TEMPLATE_CAPABILITY"
        else:
            caps = None
            caps_state = "UNAVAILABLE"
        structure = caps.get_structure(0) if caps is not None else None
        fields: list[list[str]] = []
        if structure is not None:
            for index in range(structure.n_fields()):
                name = structure.nth_field_name(index)
                try:
                    value = structure.get_value(name)
                except Exception:  # noqa: BLE001 - opaque GstBitmask
                    continue
                fields.append([str(name), str(value)])
        factory = element.get_factory()
        request = self._request
        return {
            "element_name": element.get_name(),
            "factory": factory.get_name() if factory is not None else "",
            "pad_name": pad.get_name() if pad is not None else "",
            "direction": direction,
            "role": role,
            "media_type": structure.get_name() if structure is not None else "",
            "fields": fields,
            "caps_state": caps_state,
            "caps": caps.to_string() if caps is not None else "",
            "linked": bool(pad.is_linked()) if pad is not None else False,
            "selected_device": request.locator if request is not None else "",
            "execution_id": request.execution_id if request is not None else "",
            "binding_generation": (
                request.binding_generation if request is not None else 0
            ),
        }

    def commit(self, expected: dict[str, Any]) -> dict[str, Any]:
        self._require_expected(expected)
        self._committed = True
        return {"committed": True, "identity": dict(self._identity or {})}

    def start(self) -> dict[str, Any]:
        if not self._committed or self._pipeline is None:
            raise NativeDsdHostError(
                "NATIVE_DSD_HOST_NOT_COMMITTED", "commit before start"
            )
        if self._errors:
            raise NativeDsdHostError(
                "NATIVE_DSD_HOST_LINK_FAILED",
                self._errors[0].get("detail", "native DSD link failure"),
            )
        gst = self._ensure_gst()
        self._pipeline.set_state(gst.State.PLAYING)
        self._drain_bus()
        return {
            "state": "PLAYING",
            "eos": self._eos,
            "errors": list(self._errors),
        }

    def pause(self) -> dict[str, Any]:
        if self._pipeline is None:
            raise NativeDsdHostError(
                "NATIVE_DSD_HOST_NOT_PREPARED", "no pipeline to pause"
            )
        self._pipeline.set_state(self._gst.State.PAUSED)
        return {"state": "PAUSED"}

    def resume(self) -> dict[str, Any]:
        if not self._committed or self._pipeline is None:
            raise NativeDsdHostError(
                "NATIVE_DSD_HOST_NOT_COMMITTED", "commit before resume"
            )
        self._pipeline.set_state(self._gst.State.PLAYING)
        return {"state": "PLAYING"}

    def stop(self, expected: dict[str, Any] | None = None) -> dict[str, Any]:
        if expected is not None and self._identity is not None:
            try:
                self._require_expected(expected)
            except NativeDsdHostError as exc:
                return {"stopped": False, "stale": True, "code": exc.code}
        self.close()
        return {"stopped": True, "stale": False}

    def abort(self, expected: dict[str, Any] | None = None) -> dict[str, Any]:
        if expected is not None and self._identity is not None:
            try:
                self._require_expected(expected)
            except NativeDsdHostError:
                return {"aborted": False, "stale": True}
        self.close()
        return {"aborted": True, "stale": False}

    def query_identity(self) -> dict[str, Any]:
        self._drain_bus()
        if self._identity is None:
            return {"native_dsd": False}
        payload = dict(self._identity)
        payload["native_dsd"] = True
        payload["committed"] = self._committed
        payload["eos"] = self._eos
        payload["errors"] = list(self._errors)
        payload["state"] = self._state_name()
        return payload

    def query_evidence(self) -> dict[str, Any]:
        return self.query_identity()

    def _drain_bus(self) -> None:
        if self._pipeline is None:
            return
        gst = self._gst
        bus = self._pipeline.get_bus()
        if bus is None:
            return
        while True:
            message = bus.timed_pop_filtered(
                0, gst.MessageType.ERROR | gst.MessageType.EOS
            )
            if message is None:
                return
            if message.type == gst.MessageType.EOS:
                self._eos = True
            elif message.type == gst.MessageType.ERROR:
                err, debug = message.parse_error()
                self._errors.append(
                    {"code": "NATIVE_DSD_HOST_BUS_ERROR", "detail": f"{err}: {debug}"}
                )

    def _state_name(self) -> str:
        if self._pipeline is None:
            return "NULL"
        _ret, state, _pending = self._pipeline.get_state(0)
        return state.value_name

    def _require_expected(self, expected: dict[str, Any]) -> None:
        identity = self._identity
        if identity is None:
            raise NativeDsdHostError(
                "NATIVE_DSD_HOST_NOT_PREPARED", "no native DSD pipeline"
            )
        for field in (
            "plan_id",
            "execution_id",
            "device",
            "binding_generation",
        ):
            if str(expected.get(field)) != str(identity.get(field)):
                raise NativeDsdHostError(
                    "NATIVE_DSD_HOST_IDENTITY_MISMATCH",
                    f"{field} does not match the prepared execution",
                )

    def close(self) -> None:
        if self._pipeline is not None:
            with contextlib.suppress(Exception):
                self._pipeline.set_state(self._gst.State.NULL)
        self._pipeline = None
        self._request = None
        self._identity = None
        self._committed = False
        self._errors = []
        self._eos = False
